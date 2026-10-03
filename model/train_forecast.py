"""Train the harvest forecast (P10/P50/P90) and export it to JSON for the hub.

Usage: python model/train_forecast.py
Needs: numpy, scikit-learn (training only; the hub needs neither).

Examples: for each farmer and each season S in 2023-2025, features from seasons
up to S, target = cherry kg delivered in S+1. Split by farmer (20% held out).
"""

import json
import random
import sys
import time
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingRegressor

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shared.data import load_coops, load_diagnoses, load_farmers, load_rain, load_season_totals
from shared.forecast import FEATURES, MIN_HISTORY_SEASONS, ForecastModel, baseline, build_features

QUANTILES = {"p10": 0.1, "p50": 0.5, "p90": 0.9}
PARAMS = dict(n_estimators=150, max_depth=3, learning_rate=0.05, min_samples_leaf=20, subsample=0.8)


def build_examples():
    farmers, coops = load_farmers(), load_coops()
    totals, diags, rain = load_season_totals(), load_diagnoses(), load_rain()
    rows = []
    for fid, f in farmers.items():
        district = coops[f["coop_id"]]["district"]
        for s in (2023, 2024, 2025):
            feats = build_features(totals.get(fid, {}), s, f["trees"], f["avg_tree_age_2021"],
                                   diags.get(fid, []), rain[(district, s)])
            target = totals.get(fid, {}).get(s + 1, 0.0)
            if feats["n_hist"] >= MIN_HISTORY_SEASONS and target > 0:
                rows.append((fid, feats, target))
    return rows


def export_gbr(model):
    trees = []
    for est in model.estimators_[:, 0]:
        t = est.tree_
        trees.append({
            "feature": t.feature.tolist(),
            "threshold": [round(float(v), 6) for v in t.threshold],
            "left": t.children_left.tolist(),
            "right": t.children_right.tolist(),
            "value": [round(float(v), 4) for v in t.value[:, 0, 0]],
        })
    init = float(model.init_.constant_.ravel()[0])
    return {"init": init, "learning_rate": model.learning_rate, "trees": trees}


def main():
    rows = build_examples()
    farmers = sorted({fid for fid, _, _ in rows})
    random.Random(0).shuffle(farmers)
    test_f = set(farmers[: len(farmers) // 5])
    X = np.array([[r[1][k] for k in FEATURES] for r in rows])
    y = np.array([r[2] for r in rows])
    test = np.array([r[0] in test_f for r in rows])
    print(f"examples: {len(rows)} (train {(~test).sum()}, test {test.sum()})")

    spec = {"version": "forecast-v1", "features": FEATURES, "quantiles": {}}
    preds = {}
    for name, q in QUANTILES.items():
        m = GradientBoostingRegressor(loss="quantile", alpha=q, random_state=0, **PARAMS)
        m.fit(X[~test], y[~test])
        preds[name] = m.predict(X[test])
        spec["quantiles"][name] = export_gbr(m)

    out = ROOT / "model" / "forecast_model.json"
    out.write_text(json.dumps(spec, separators=(",", ":")))

    yt = y[test]
    base = np.array([baseline(r[1]) for r, t in zip(rows, test) if t])
    mae_m, mae_b = np.abs(preds["p50"] - yt).mean(), np.abs(base - yt).mean()
    cover = ((yt >= preds["p10"]) & (yt <= preds["p90"])).mean()
    above_p10 = (yt >= preds["p10"]).mean()

    # parity: pure-Python evaluator must match sklearn
    fm = ForecastModel(out)
    t_rows = [r for r, t in zip(rows, test) if t][:200]
    t0 = time.perf_counter()
    py = [fm.predict(r[1])["p50_kg"] for r in t_rows]
    ms = (time.perf_counter() - t0) / len(t_rows) * 1000
    max_diff = max(abs(a - b) for a, b in zip(py, preds["p50"][:200]))

    report = {
        "test_examples": int(test.sum()),
        "mae_p50_kg": round(float(mae_m), 1),
        "mae_baseline_kg": round(float(mae_b), 1),
        "improvement_vs_baseline": f"{(1 - mae_m / mae_b) * 100:.0f}%",
        "p10_p90_coverage": round(float(cover), 3),
        "share_above_p10": round(float(above_p10), 3),
        "model_file_kb": round(out.stat().st_size / 1024, 1),
        "pure_python_ms_per_farmer": round(ms, 2),
        "parity_max_abs_diff_kg": round(float(max_diff), 2),
    }
    (ROOT / "model" / "forecast_report.json").write_text(json.dumps(report, indent=2))
    for k, v in report.items():
        print(f"{k:28} {v}")


if __name__ == "__main__":
    main()
