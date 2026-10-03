# FarmFlow

Offline Small AI that turns a dairy farmer's milk deliveries into input credit while they wait for their cooperative payout.

Built for the World Bank Group Small AI for Development Hackathon 2026 (Agriculture).

- A coop-owned Android hub runs a small forecasting model locally, with no internet.
- Collection agents log deliveries and check limits by SMS from any phone.
- Farmers check their limit and order inputs by USSD on a basic phone.
- AWS only relays synced limits and orders.

Start with `HANDOFF.md`.

## Layout

| Folder | Contents |
| --- | --- |
| `data/` | Synthetic data generator and CSVs (simulated, illustrative assumptions) |
| `model/` | Training, evaluation, export |
| `hub/` | SMS loop, local storage, sync, advance rule |
| `backend/` | Lambda: `/sync` and `/ussd` |
| `docs/` | Write-up and video script |

## Regenerate the data

```
pip install numpy pandas
python data/generate_data.py
```

The generator is seeded, so it reproduces the same CSVs.
