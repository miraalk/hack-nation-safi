# FarmFlow

Small AI at the coffee washing station: it understands a farmer's Kinyarwanda SMS, checks her leaves from a photo, and forecasts her harvest so the cooperative can offer input credit, all on one Android phone with no internet.

Built for the World Bank Group Small AI for Development Hackathon 2026, Agriculture challenge (Annex B: Noor).

## The problem

Noor's coffee yields fell and she doesn't know why; the extension officer visits twice a year at best. At harvest she sells to a middleman at whatever price he names. Research on Rwandan coffee cooperatives finds members side-sell to traders who lend to them during the year, repaid at harvest, which coops don't offer ([source](https://www.sciencedirect.com/science/article/abs/pii/S0306919212001339)).

## What it does

1. Noor texts the coop hub in Kinyarwanda from her basic phone. A small text model maps her message to a likely problem.
2. At the washing station, coop staff photograph her leaves and a small image model classifies the disease. At weekends, the same model runs offline on her daughter's smartphone and sends the result to the hub by SMS.
3. A small forecast model estimates her next harvest; a transparent rule proposes input credit; coop staff approve it.
4. Noor orders the recommended treatment by USSD and repays from her coop cherry payments.

AI is used only where rules can't do the job (free-text Kinyarwanda, leaf photos, harvest forecast); the credit amount, treatment list and menus are deliberately plain rules so they stay predictable and checkable. Every model has a confidence threshold. Below it, FarmFlow says "not sure" and a coop staff member follows up in person.

## Small AI

| Model | Size | Runs on | Trained on |
| --- | --- | --- | --- |
| Symptom text classifier (char n-grams + logistic regression) | ~220 KB | Hub, pure Python | Kinyarwanda + English examples written by the team (draft) |
| Leaf disease detector (Ultralytics YOLO) | ~52 MB (`.pt`) | Hub phone or laptop, PyTorch + Ultralytics | DECAFIA coffee leaf images (rust, leaf miner, weevil) |
| Harvest forecast (gradient-boosted quantile trees) | 164 KB | Hub, pure Python | Synthetic cooperative delivery records |

The text and forecast models are pure standard-library Python, so they run anywhere (Termux on the hub phone, a laptop, or AWS Lambda). The leaf model currently needs PyTorch; shrinking/quantising it (ONNX or TFLite) to meet the brief's "small enough to side-load" rule — and to power the weekend web page — is still to do.

## Repository layout

- `shared/` — the brain, pure Python and reused everywhere: data loading, harvest forecast, advance (credit) rule, recommendations, text model, diagnosis list. Reads from the SQLite database.
- `data/` — `farmflow.db` (SQLite, the runtime data store) plus a few sample leaf photos. The synthetic CSVs and their generator live in `data/csv_dummy_data/`.
- `scripts/` — `migrate_csv_to_sqlite.py` rebuilds `farmflow.db` from the CSVs.
- `model/`, `language/`, `vision/` — training code + exported models (forecast, text, leaf vision; the leaf model is in `vision/models/`).
- `hub/` — the Flask **hub app**: the coop-staff dashboard (English / Kinyarwanda), per-farmer detail, and the photo-diagnosis flow. It also registers the backend webhook routes.
- `backend/` — Africa's Talking SMS/USSD webhooks and services; wording lives in `backend/ussd_script.json` and `hub/sms_script.json`.

See `HANDOFF.md` for the full build notes and architecture.

## Data and what it doesn't cover

- **Forecast data is synthetic** (`data/csv_dummy_data/generate_data.py`): yields, rainfall and disease rates are illustrative assumptions, not Rwandan statistics. No real cooperative ledger was used. Cherry prices for 2024–2026 follow NAEB minimum prices (RWF 480, 600, 750/kg; [allAfrica, Jan 2026](https://allafrica.com/stories/202601140085.html)); earlier years are assumptions.
- **Input prices**: subsidised NPK uses the 2027A farmer price of RWF 1,861/kg ([New Times, July 2026](https://www.newtimes.co.rw/article/37079/news/agriculture/govt-increases-fertiliser-subsidies-amid-global-price-shocks/amp)); other inputs are illustrative.
- **DECAFIA** leaf images were not taken in East African fields; the model covers rust, leaf miner and weevil, and may not include antestia bug or coffee berry disease.
- **Kinyarwanda** (training examples and the dashboard/USSD/SMS wording) is a draft written by the team; it doesn't cover all dialects, spellings or phrasings real farmers use, and should be checked by a native speaker.
- **Rainfall** is synthetic in the prototype; CHIRPS or NASA POWER would replace it.

## Run the hub app

The hub app serves the coop dashboard, per-farmer detail, and the photo-diagnosis flow. It reads `data/farmflow.db` (committed), so no data setup is needed.

```
pip install -r requirements.txt     # includes torch/ultralytics for the leaf model (large)
python3 hub/app.py                   # open http://127.0.0.1:5001
```

- Binds to `$PORT` if set (for hosting), otherwise port **5001**.
- Switch language with the **EN / RW** toggle in the top bar (Kinyarwanda is a draft).
- The dashboard, farmer pages and credit numbers need only Flask + `shared/`; the leaf **Diagnose** button additionally uses `ultralytics`/`torch`.

### Run with Docker

```
docker build -t farmflow .
docker run -p 8080:8080 -e PORT=8080 -e AT_API_KEY=dummy farmflow
# open http://127.0.0.1:8080
```

### Regenerate data / retrain (optional)

```
pip install -r requirements.txt
python3 data/csv_dummy_data/generate_data.py     # regenerate the synthetic CSVs (seeded)
python3 scripts/migrate_csv_to_sqlite.py         # rebuild data/farmflow.db from the CSVs
python3 model/train_forecast.py                  # train + export the forecast model
python3 language/train_text.py                   # train + export the text model
python3 tests/test_shared.py                     # checks on the demo farmers
python3 backend/check_ussd.py                    # wording checks
```

Leaf vision training: see `vision/train_vision.py`.

## Deploy

The repo ships a `Dockerfile` whose entrypoint runs gunicorn and binds the host's port:

```
gunicorn hub.app:app --bind 0.0.0.0:${PORT:-8080} --workers 1 --timeout 180
```

On Railway/Render (Docker build) it deploys as-is — the port comes from `$PORT`, so **don't** put a literal `${PORT}` in a custom start command.

Environment variables:

| Variable | Purpose |
| --- | --- |
| `PORT` | Port to bind (injected by the host; the Dockerfile defaults to 8080) |
| `AT_API_KEY` | Africa's Talking API key. **Required for the app to start** (the SMS transport reads it at import). Use a sandbox key if you only need the dashboard. |
| `AT_USERNAME` | Africa's Talking username (default `sandbox`) |
| `AT_SENDER_ID`, `AT_COOP_SENDER_ID` | Optional sender IDs |

Note: installing `torch`/`ultralytics` makes the image large, so the first build is slow.

Start with `HANDOFF.md` for the full build notes.
