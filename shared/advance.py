"""Advance rule: turns the harvest forecast into a PROPOSED input-credit limit.

limit = clamp(ALPHA x P10_kg x first-payment price - outstanding, 0, CAP),
rounded down to ROUND_TO_RWF. No AI here: the model forecasts, this rule decides
the number, and coop staff approve it before Noor can use it.
"""

from datetime import datetime, timezone

from . import config
from .forecast import ForecastModel, build_features


def compute_limit(farmer, coop, season_totals, diagnoses, rain_anomaly_last, last_price,
                  last_season, outstanding_rwf=0, model=None):
    """Build the limit object (HANDOFF section 4) for one farmer."""
    model = model or ForecastModel()
    feats = build_features(season_totals, last_season, farmer["trees"],
                           farmer["avg_tree_age_2021"], diagnoses, rain_anomaly_last)
    fc = model.predict(feats)
    base = {
        "farmer_id": farmer["farmer_id"],
        "season": last_season + 1,
        "outstanding_rwf": outstanding_rwf,
        "computed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "model_version": model.version,
        "approved_by": None,
    }
    if fc is None:
        return {**base, "status": "insufficient_history", "seasons_of_history": feats["n_hist"],
                "forecast_p10_kg": None, "forecast_p50_kg": None, "forecast_p90_kg": None,
                "price_rwf_per_kg": last_price, "limit_rwf": 0}

    raw = config.ALPHA * fc["p10_kg"] * last_price - outstanding_rwf
    limit = int(max(0, min(config.CAP_RWF, raw)) // config.ROUND_TO_RWF * config.ROUND_TO_RWF)
    return {**base, "status": "pending_approval", "seasons_of_history": feats["n_hist"],
            "forecast_p10_kg": fc["p10_kg"], "forecast_p50_kg": fc["p50_kg"],
            "forecast_p90_kg": fc["p90_kg"], "price_rwf_per_kg": last_price, "limit_rwf": limit}


def approve(limit_obj, approver):
    """Coop staff approval (e.g. from an 'OK <code>' SMS). Only approved limits sync to USSD."""
    return {**limit_obj, "status": "approved", "approved_by": approver}


def explain(lim):
    """One-line breakdown for the hub log and the coop staff approval SMS."""
    if lim["status"] == "insufficient_history":
        return f"Only {lim['seasons_of_history']} season(s) of deliveries: no forecast, refer to coop staff"
    return (f"{config.ALPHA} x {lim['forecast_p10_kg']:,} kg (low-end forecast) x "
            f"RWF {lim['price_rwf_per_kg']}/kg - {lim['outstanding_rwf']:,} owed")
