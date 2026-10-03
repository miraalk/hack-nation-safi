# FarmFlow

Small AI at the coffee washing station: it understands a farmer's Kinyarwanda SMS, checks her leaves from a photo, and forecasts her harvest so the cooperative can offer input credit, all on one Android phone with no internet.

Built for the World Bank Group Small AI for Development Hackathon 2026, Agriculture challenge (Annex B: Noor).

## The problem

Noor's coffee yields fell and she doesn't know why; the extension officer visits twice a year at best. At harvest she sells to a middleman at whatever price he names. Research on Rwandan coffee cooperatives finds members side-sell to traders who lend to them during the year, repaid at harvest, which coops don't offer ([source](https://www.sciencedirect.com/science/article/abs/pii/S0306919212001339)).

## What it does

1. Noor texts the coop hub in Kinyarwanda from her basic phone. A small text model maps her message to a likely problem.
2. At the washing station, the agent photographs her leaves and a small image model classifies the disease. At weekends, the same model runs offline on her daughter's smartphone and sends the result to the hub by SMS.
3. A small forecast model estimates her next harvest; a transparent rule proposes input credit; a coop officer approves it.
4. Noor orders the recommended treatment by USSD and repays from her coop cherry payments.

AI is used only where rules can't do the job (free-text Kinyarwanda, leaf photos, harvest forecast); the credit amount, treatment list and menus are deliberately plain rules so they stay predictable and checkable. Every model has a confidence threshold. Below it, FarmFlow says "not sure" and refers Noor to the extension officer.

## Small AI

| Model | Size | Runs on | Trained on |
| --- | --- | --- | --- |
| Symptom text classifier (char n-grams + logistic regression) | ~100 KB | Hub, pure Python | Kinyarwanda examples written by the team |
| Leaf disease classifier (MobileNetV3-Small, int8) | a few MB | Hub, ONNX Runtime | BRACOL coffee leaf images |
| Harvest forecast (gradient-boosted quantile trees) | 164 KB | Hub, pure Python | Synthetic cooperative delivery records |

## Data and what it doesn't cover

- **Forecast data is synthetic** (`data/generate_data.py`): yields, prices, rainfall and disease rates are illustrative assumptions, not Rwandan statistics. No real cooperative ledger was used.
- **BRACOL** images were not taken in East African fields; they may not include antestia bug or coffee berry disease.
- **Kinyarwanda examples** were written by the team; they don't cover all dialects, spellings or phrasings real farmers use.
- **Rainfall** is synthetic in the prototype; CHIRPS or NASA POWER would replace it.

## Run

```
pip install numpy pandas scikit-learn
python3 data/generate_data.py        # regenerate data (seeded)
python3 model/train_forecast.py      # train + export forecast
python3 language/train_text.py       # train + export text model
python3 tests/test_shared.py         # checks on demo farmers
python3 backend/check_ussd.py        # wording checks
```

Vision: see `vision/train_vision.py` (needs torch, torchvision, onnx, onnxruntime).

Start with `HANDOFF.md` for the full build notes.
