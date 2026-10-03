"""Harvest forecast: next season's cherry deliveries to the coop, as P10/P50/P90.

build_features() is the ONE place features are computed, used by training
(model/train_forecast.py) and by the hub, so both see identical inputs.

The trained model is gradient-boosted quantile trees exported to JSON
(model/forecast_model.json) and evaluated here in pure Python: no numpy,
no sklearn, so it runs on the hub phone.
"""

import json
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parent.parent / "model" / "forecast_model.json"
MIN_HISTORY_SEASONS = 2   # fewer than this -> no forecast, refer to coop staff

FEATURES = [
    "d1", "d2", "d3", "mean3", "trend", "n_hist", "trees", "tree_age",
    "kg_per_tree", "rust_last", "rust_prev", "rain_last",
]


def build_features(season_totals, last_season, trees, avg_tree_age_2021,
                   diagnoses, rain_anomaly_last):
    """Features to forecast season last_season+1, using data up to last_season.

    season_totals: {season: paid_kg delivered to the coop}
    diagnoses: [(date, diagnosis), ...] confirmed at the hub (or historically by an extension officer)
    """
    d = [season_totals.get(last_season - k, 0.0) for k in range(3)]
    hist = [x for x in d if x > 0]
    rust = lambda s: int(any(dt.year == s and dx == "leaf_rust" for dt, dx in diagnoses))
    return {
        "d1": d[0], "d2": d[1], "d3": d[2],
        "mean3": sum(hist) / len(hist) if hist else 0.0,
        "trend": d[0] - d[1],
        "n_hist": len(hist),
        "trees": trees,
        "tree_age": avg_tree_age_2021 + (last_season + 1 - 2021),
        "kg_per_tree": d[0] / trees if trees else 0.0,
        "rust_last": rust(last_season),
        "rust_prev": rust(last_season - 1),
        "rain_last": rain_anomaly_last,
    }


def _tree_predict(tree, x):
    node = 0
    while tree["left"][node] != -1:
        f = tree["feature"][node]
        node = tree["left"][node] if x[f] <= tree["threshold"][node] else tree["right"][node]
    return tree["value"][node]


class ForecastModel:
    def __init__(self, path=MODEL_PATH):
        spec = json.loads(Path(path).read_text())
        self.features = spec["features"]
        self.models = spec["quantiles"]          # {"p10": {...}, "p50": {...}, "p90": {...}}
        self.version = spec["version"]

    def _predict_one(self, m, x):
        return m["init"] + m["learning_rate"] * sum(_tree_predict(t, x) for t in m["trees"])

    def predict(self, feats):
        """Returns kg quantiles, or None when history is too thin to forecast."""
        if feats["n_hist"] < MIN_HISTORY_SEASONS:
            return None
        x = [float(feats[f]) for f in self.features]
        p10, p50, p90 = (max(0.0, self._predict_one(self.models[q], x)) for q in ("p10", "p50", "p90"))
        p10, p50, p90 = sorted((p10, p50, p90))   # guard against quantile crossing
        return {"p10_kg": round(p10), "p50_kg": round(p50), "p90_kg": round(p90)}


def baseline(feats):
    """What a spreadsheet would do: average of the last two seasons."""
    vals = [v for v in (feats["d1"], feats["d2"]) if v > 0]
    return sum(vals) / len(vals) if vals else 0.0
