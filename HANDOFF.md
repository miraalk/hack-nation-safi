# FarmFlow — HANDOFF

Read this first, Martin. We changed direction: we now build for **Noor**, the coffee farmer in the official Agriculture brief (Hack-Nation concept note, Annex B), not dairy. If something here is unclear, make the simplest reasonable choice, write it under "Decisions made while Mimi was away", and keep going.

## 0. The idea in one paragraph

Noor's coffee yields fell and she doesn't know why; she sells to a middleman because he lends to her during the year and she repays at harvest (side-selling study: four Rwandan coffee coops). FarmFlow runs three small models on the coop's Android phone at the washing station, offline: (1) it understands Noor's Kinyarwanda SMS describing the problem, (2) it classifies photos of her leaves, (3) it forecasts her next harvest so the coop can offer her input credit, which coop staff approve. Noor orders by USSD on her basic phone and repays from her coop cherry payments, so she sells to the coop instead of the middleman.

## 1. Locked decisions

| Decision | Choice |
| --- | --- |
| Sector / user | Agriculture / Noor (brief, Annex B) |
| Setting | Coffee cooperative with a washing station, Rwandan highlands (fictional "Ondera Coffee Cooperative") |
| Language | Kinyarwanda (named local language), English as second |
| Product | Diagnosis + input credit (never cash), repaid from coop cherry payments |
| Hub | One coop-owned Android phone at the washing station: data + all three models, offline |
| Hub software | **Martin decides.** Test first whether the image model runs on the phone (see section 6) |
| Noor | Basic phone: SMS (describe problem), USSD (credit, order) |
| Weekend path (Should) | Daughter's smartphone runs the same leaf model offline in a cached web page; result goes to the hub by SMS (`LEAF F0001 leaf_rust 87`). Credit and records stay on the hub |
| Why AI where | AI only for what rules can't do: free-text Kinyarwanda, leaf photos, harvest forecast. Credit amount, treatments and menus are plain rules on purpose |
| Humans in the loop | **One coop staff member** at the washing station: photographs leaves, approves every advance by SMS, follows up every "not sure". (Production: separate approver, and route crop questions to the district extension officer.) |
| Cloud | AWS Lambda + DynamoDB, relay only: approved limits for USSD, orders back. No inference |
| Demo farmers | `F0001` Noor Mukamana (rust in 2025, yields fell). `F0002` Jean Claude, new member (1 season → refer to coop staff) |
| Demo "today" | 2026-10-03, off-season; next harvest is 2027 (March–July) |

## 2. What's already built (run these first)

```
pip install numpy pandas scikit-learn        # training only
python3 tests/test_shared.py                  # forecast, credit, recommendations on Noor + Jean Claude
python3 language/train_text.py                # trains the text model from language/examples.csv
python3 backend/check_ussd.py                 # wording files: length, placeholders, Kinyarwanda gaps
```

| Piece | File(s) | Status |
| --- | --- | --- |
| Synthetic coffee data | `data/generate_data.py`, `data/*.csv` | Done |
| Harvest forecast | `shared/forecast.py`, `model/train_forecast.py`, `model/forecast_model.json` | Trained: MAE 147 kg vs 181 kg baseline (−18%), 88% of actuals above P10, 164 KB, 0.3 ms |
| Advance rule + coop staff approval | `shared/advance.py`, `shared/config.py` | Done |
| Recommendations | `shared/recommend.py`, `data/inputs.csv` | Done (prices illustrative) |
| Diagnosis list | `shared/diagnoses.py` | Done; map BRACOL folder names in `VISION_CLASS_TO_DIAGNOSIS` |
| Text model | `shared/text_model.py`, `language/train_text.py` | Pipeline done; needs Mimi's Kinyarwanda examples |
| Vision model | `vision/train_vision.py`, `vision/predict.py` | **Written, never run** (no PyTorch or dataset in Claude's sandbox) |
| Wording | `backend/ussd_script.json`, `hub/sms_script.json` | English done; Kinyarwanda drafted by Claude, **Mimi checking** |
| Hub dashboard (read-only) | `hub/app.py`, `hub/dashboard.py`, `hub/templates/`, `hub/static/` | Done. Flask; `pip install flask && python hub/app.py`. Aggregate of every farmer + per-farmer detail, reuses `shared/` |
| Hub SMS loop, Lambda, sync | `hub/`, `backend/` | **Martin** |

Everything in `shared/` is standard-library Python: it runs on Termux, in Lambda, or as the reference for a Kotlin port.

## 3. Data schema (`/data`, all synthetic, illustrative numbers)

| File | Columns | Notes |
| --- | --- | --- |
| `coops.csv` | coop_id, name, district, avg_days_to_first_payment | 3 fictional coops |
| `farmers.csv` | farmer_id, coop_id, name, phone, trees, avg_tree_age_2021, village, member_since, is_demo | Phones are placeholders: put your test SIMs on F0001/F0002 |
| `deliveries.csv` | farmer_id, date, cherry_kg, rejected_kg, price_rwf_per_kg | Daily cherry deliveries, harvests 2021–2026 (Mar–Jul). Season = harvest year. Prices 2024–2026 follow NAEB minimums (480 / 600 / 750 RWF/kg) |
| `payouts.csv` | coop_id, season, first_payment_rwf_per_kg, avg_days_to_first_payment, second_payment_rwf_per_kg, second_payment_date | Second payment blank if not yet paid |
| `rainfall.csv` | district, season, preseason_rain_mm, anomaly | Synthetic; swap for CHIRPS if time |
| `diagnoses.csv` | farmer_id, date, diagnosis, source | Confirmed diagnoses (only some rust cases get reported). The hub appends here |
| `inputs.csv` | input_id, short_en, short_rw, name_en, category, unit, price_rwf, per_trees, rank, diagnoses, note_en, price_source | Catalogue; `per_trees` = one unit per N trees (0 = one unit). NPK price is real (subsidised farmer price); others illustrative |
| `truth_seasons.csv` | farmer_id, season, harvest_kg, delivered_kg, rust_severity | **Simulator ground truth. Never a model feature** |

## 4. Contracts

**Forecast** (`shared/forecast.py`): `build_features(...)` then `ForecastModel().predict(feats)` → `{"p10_kg", "p50_kg", "p90_kg"}` or `None` when fewer than 2 seasons of history.

**Text** (`shared/text_model.py`): `TextModel().classify(text)` → `{"label", "confidence", "diagnosis", "sure"}`. `sure` is False below `TEXT_THRESHOLD` or for label `other`.

**Vision** (`vision/predict.py`): `LeafModel().classify(path)` → `{"class", "confidence", "diagnosis", "sure", "quality"}`. Quality `too_dark` / `too_blurry` → ask for a new photo.

**Credit** (`shared/advance.py`): `compute_limit(...)` → limit object with `status` = `insufficient_history` or `pending_approval`; `approve(lim, approver)` → `approved`. **Only approved limits sync to USSD.**

```
limit = clamp(ALPHA x P10_kg x first-payment price - outstanding, 0, CAP)   # ALPHA 0.3, CAP 300,000 RWF
```

**Recommendations** (`shared/recommend.py`): `recommend(limit, diagnosis, trees, catalogue)` → status `ok` / `refer` / `no_treatment` / `no_credit` / `too_low`, up to 3 items.

**Limit object** (what syncs to the cloud):

```json
{"farmer_id": "F0001", "season": 2027, "status": "approved", "approved_by": "staff-01",
 "seasons_of_history": 3, "forecast_p10_kg": 1038, "forecast_p50_kg": 1329, "forecast_p90_kg": 1930,
 "price_rwf_per_kg": 769, "outstanding_rwf": 0, "limit_rwf": 239000,
 "computed_at": "2026-10-03T19:30:00Z", "model_version": "forecast-v1"}
```

## 5. Hub SMS loop (Martin builds; wording in `hub/sms_script.json`)

There is **one coop staff member** in the prototype: messages tagged `coop_staff` (photo results, approval requests, referrals) all go to one number. Message keys still say `agent_` / `officer_` / `extension_`; that's just naming.

| Sender | Message | Hub does |
| --- | --- | --- |
| A registered farmer (by phone number) | Free text, any language | Text model → `noor_likely_bring_leaves` (diagnoses needing a photo), `noor_likely_no_photo` (nutrient, drought, old trees) or `noor_unsure` + `extension_referral` (goes to coop staff) |
| Coop staff (optional) | `D F0001 25.5` / `D F0001 25.5 R1.0` | Log cherry delivery → `agent_logged`. Optional: demo data is preloaded, and real coops already record weights |
| Coop staff | `L F0001` | Credit status |
| Coop staff | Photo (taken on the hub itself) | Vision model → `agent_photo_result` / `agent_photo_unsure` / `agent_photo_quality`; save to `diagnoses.csv`; if sure → compute limit → `officer_request` to coop staff (or `officer_no_history`) |
| Coop staff | `OK 4821` / `NO 4821` | Approve/decline → `noor_credit_ready` → sync |
| Farmer or a registered household number (daughter's phone) | `LEAF F0001 leaf_rust 87` (sent by the weekend web page) | Treat like a hub photo result: save to `diagnoses.csv` with source `household_phone`; if confidence ≥ threshold → compute limit → `officer_request`, and `noor_confirmed` to Noor; else `extension_referral` |
| Unknown number | anything | Ignore or `not_registered` |

Photos: simplest is coop staff taking them in the hub's camera app into a watched folder (e.g. `DCIM/FarmFlow/F0001_*.jpg`); the loop picks up new files and reads the farmer ID from the file name.

## 6. Vision (Martin owns; highest risk)

1. **First hour: prove a model runs on the hub phone.** Try `onnxruntime` on Termux with any small ONNX model. If it won't install, choose: native app with ONNX Runtime Mobile / TFLite, or run vision on a laptop beside the hub and say so honestly.
2. Get BRACOL from Mimi (Mendeley Data). Put images in `vision/data/<class>/`. Check the licence.
3. `python vision/train_vision.py --data vision/data --epochs 8` (add `--group-regex` if file names share a leaf ID). Colab GPU if the laptop is slow.
4. Read `vision/vision_report.json`: accuracy, per-class, threshold. Map folder names in `shared/diagnoses.py`.
5. Copy `leaf_model.int8.onnx` + `leaf_labels.json` to the hub; time one prediction.
6. **Weekend web page (first extra, 3–4 h, only after step 5 works).** One self-contained page for the daughter's smartphone:
   - camera capture (`<input type="file" accept="image/*" capture="environment">`)
   - the same `leaf_model.int8.onnx` + `leaf_labels.json`, run with ONNX Runtime Web; same resize/crop/normalise, darkness/blur check and threshold as `vision/predict.py`
   - result screen in Kinyarwanda, then an "SMS to coop" button: `sms:<hub number>?body=LEAF F0001 leaf_rust 87` (farmer ID typed once and remembered)
   - a service worker so it works offline after one load; keep the total download to a few MB (this also meets the brief's "small enough to send over a weak connection" rule)
   - add a `household_phones` field to the farmer record so the hub accepts `LEAF` messages from the daughter's number

## 7. Cloud endpoints (Martin)

- `POST /sync` — body `{"limits": [<approved limit objects>]}` → response `{"orders": [...]}` created since last sync.
- `POST /ussd` — Africa's Talking callback (`sessionId`, `phoneNumber`, `text`) → `CON …` / `END …`, wording from `backend/ussd_script.json`. Flow: language → main menu → credit (or `pending` / `no_history`) → `diagnosis_known` if the farmer has a confirmed diagnosis, else `problem` menu → `recommend` → `order_done`. Uses `shared/recommend.py`.

Order object: `{"order_id", "farmer_id", "items": [{"input_id", "qty"}], "total_rwf", "status": "requested", "created_at"}`.

## 8. Writing the Kinyarwanda examples (Mimi)

Full guide, vocabulary prompts and the message for the test writer: `language/WRITING_GUIDE.md`.

`language/examples.csv`: columns `text, label, lang, author, split`.

- Labels: `yellow_orange_spots, brown_spots, leaf_tunnels, berries_black_drop, insects, leaves_pale, wilting_dry, old_low_yield, other`.
- ~30 per label, as farmers really text: short, misspellings, no apostrophes, Kinyarwanda–English mixing. `lang` = rw / en / mixed.
- `other` matters: greetings, price questions, payment questions, unrelated problems.
- Test set: ask someone else to write ~50 messages, mark `split` = test. Never train on them.
- The 46 English rows from `author=seed` were written by Claude to test the pipeline; keep or delete them.

## 9. Repo layout

```
/data      generator + CSVs + input catalogue
/shared    config, diagnoses, data loading, forecast, text model, advance rule, recommendations
/model     forecast training + exported model + report
/language  Kinyarwanda examples + text training + exported model
/vision    leaf model training + hub prediction
/hub       read-only dashboard (app.py, dashboard.py, templates, static), SMS loop (Martin), sms_script.json
/backend   Lambda (Martin), ussd_script.json, check_ussd.py
/tests     checks on the demo farmers
/docs      write-up, video script
```

## Decisions made while Mimi was away

(Martin: add anything you decided here.)
