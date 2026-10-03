# FarmFlow — HANDOFF

Read this first, Martin. Everything here is fixed unless we both agree to change it. If something is unclear, make the simplest reasonable choice, write it at the bottom under "Decisions made while Mimi was away", and keep going.

## 0. Locked decisions

| Decision | Choice |
| --- | --- |
| Sector | Agriculture — dairy |
| Setting | Rwandan dairy cooperative (simulated), Kinyarwanda + English |
| Product | Input advances (feed, minerals, vet, etc.), never cash. Repaid by deduction from the next coop payout |
| Hub | One coop-owned Android phone at the collection centre. Holds the data and runs the model locally |
| Hub software | **TBD by Mimi:** Termux + Python, or native background Android app |
| Agents | Any phone, SMS to the hub |
| Farmers | Basic phone, USSD (Africa's Talking sandbox → Lambda) |
| Cloud | AWS Lambda + DynamoDB. Relay only: sync + USSD. No model inference in the cloud |
| Demo farmer | Aline Mukamana, `F001`. Second demo farmer with a sick cow: `F002` |
| Demo "today" | 2026-10-03 (current cycle: 2026-09-16 → 2026-10-15) |

## 1. Data schema

All files are in `/data`. Dates are ISO `YYYY-MM-DD`. Money is integer RWF. Litres have 1 decimal.

**`coops.csv`**

| Column | Type | Meaning |
| --- | --- | --- |
| coop_id | str | `C01`… |
| name | str | Coop name (fictional) |
| village | str | Where the collection centre is |
| cycle_cutoff_day | int | Day of month the pay cycle closes (inclusive) |
| avg_days_to_pay | int | Typical days from cutoff to payout |

**`farmers.csv`**

| Column | Type | Meaning |
| --- | --- | --- |
| farmer_id | str | `F0001`… (demo farmers are `F0001`–`F0060`) |
| coop_id | str | FK to coops |
| name | str | Fictional name |
| phone | str | Placeholder number. Replace demo farmers' numbers with your test SIMs |
| herd_size | int | Milking-age cows, 1–5 |
| village | str | |
| is_demo | int | 1 for the 60 named demo farmers |

**`deliveries.csv`** — one row per farmer per day **they delivered**. A missing day = no delivery.

| Column | Type | Meaning |
| --- | --- | --- |
| farmer_id | str | |
| date | date | |
| litres_delivered | float | Litres brought to the centre |
| litres_rejected | float | Litres refused on quality (not paid) |
| price_per_litre | int | RWF, set by the coop per cycle |

**`payouts.csv`** — one row per coop per cycle.

| Column | Type | Meaning |
| --- | --- | --- |
| coop_id | str | |
| cycle_start | date | Day after previous cutoff |
| cycle_end | date | Cutoff day (inclusive) |
| payout_date | date | When the coop actually paid. Blank for the current, unpaid cycle |

**`truth_events.csv`** — simulator ground truth. **Never use as a model feature.** Use it only to check that the drop flag catches real shocks and for the demo story.

| Column | Type | Meaning |
| --- | --- | --- |
| farmer_id | str | |
| cow | int | Cow index within the farmer's herd |
| event | str | `calving` or `sickness` |
| start | date | |
| end | date | Blank for calving |

## 2. The model (Martin owns)

**Label:** for farmer *f* on day *t*, `target = sum(litres_delivered − litres_rejected)` for days *t+1* … *cycle_end* (net paid litres still to come this cycle). Only make examples where the whole horizon is inside the data.

**Split:** by farmer (e.g. 80/20 of farmer_ids), never by row.

**Baseline to beat:** `mean net litres over last 7 days × days remaining`.

**Suggested features** (per farmer-day, computed only from data up to and including *t*):
net litres last 3 / 7 / 14 days (mean), trend (last 7 vs previous 7), days remaining in cycle, delivery days in last 14, rejection rate last 30 days, herd_size, month, day of week, coop_id.

**Outputs:** three quantile models (P10, P50, P90) + a drop flag.

**Function the hub calls** (Python if Termux; same signature in Kotlin if native):

```python
predict(features: dict) -> {
    "p10_litres": float,
    "p50_litres": float,
    "p90_litres": float,
    "drop_flag": bool,   # P50 implies a daily rate well below the last-7-day rate
}
```

Until the real model is ready, `hub/model_stub.py` returns the baseline with ±20% bands. Swapping in the real model must be a one-file change.

Record for the submission: model file size, inference time on the hub phone, MAE vs baseline, P10–P90 coverage.

## 3. Advance rule (Mimi owns, shared module)

```
accrued        = sum((delivered − rejected) × price) for this cycle up to today
forecast_p10   = p10_litres × current price
raw_limit      = ALPHA × (accrued + forecast_p10) − outstanding_advances
limit          = clamp(raw_limit, 0, CAP), rounded down to nearest 1,000 RWF
```

Defaults: `ALPHA = 0.5`, `CAP = 150,000`. Both live in one config file, not buried in code.

## 4. Limit object (everything downstream reads this)

```json
{
  "farmer_id": "F0001",
  "cycle_end": "2026-10-15",
  "payout_date_est": "2026-10-24",
  "accrued_rwf": 152000,
  "forecast_p10_rwf": 41000,
  "forecast_p50_rwf": 52000,
  "outstanding_rwf": 0,
  "limit_rwf": 80000,
  "drop_flag": false,
  "computed_at": "2026-10-03T14:05:00Z",
  "model_version": "v1"
}
```

## 5. Agent SMS commands (Mimi writes wording, Martin implements parser)

Replies must stay under 160 characters.

| Agent texts | Hub does | Example reply |
| --- | --- | --- |
| `D F0001 12.5` | Logs a delivery for today | `Logged: Aline 12.5L. Cycle total 152.0L.` |
| `D F0001 12.5 R1.0` | Logs delivery with 1.0 L rejected | `Logged: Aline 12.5L (1.0L rejected). Cycle total 163.5L.` |
| `L F0001` | Runs model, returns limit | `Aline: limit RWF 80,000. Payday ~24 Oct. 152L so far + forecast.` |
| `HELP` | Lists commands | `D <id> <litres> [R<rej>] / L <id> / HELP` |
| anything else | Error | `Not understood. Try: D F0001 12.5 or L F0001` |

Unknown farmer ID → `Farmer F9999 not found.`

## 6. Backend endpoints (Martin owns)

- `POST /sync` — body: `{"limits": [<limit object>, ...]}`. Response: `{"orders": [<order>, ...]}` (orders created since the hub's last sync).
- `POST /ussd` — Africa's Talking callback (`sessionId`, `phoneNumber`, `text`). Returns `CON …` or `END …`. Looks up farmer by phone, reads latest synced limit, runs the survey, stores order with status `requested`.

Order object: `{"order_id", "farmer_id", "items": [{"input_id", "qty"}], "total_rwf", "status", "created_at"}`.

## 7. Repo layout

```
/data      generator + CSVs
/model     training, evaluation, export
/hub       SMS loop, local SQLite, sync, model_stub.py, advance rule
/backend   Lambda: /sync + /ussd
/docs      README, video script
```

One repo, small commits, commit messages that say what changed.

## 8. Martin's first hour

1. Read this file.
2. `python data/generate_data.py` (already run; CSVs are in `/data`). Look at `F0001` and `F0002`.
3. Build features + labels, train baseline, then quantile models.
4. Target: hub answers `L F0001` with the real model and data off by about T+9.

## Decisions made while Mimi was away

(Martin: add anything you decided here.)
