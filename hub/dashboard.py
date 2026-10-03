"""Aggregates every farmer's deliveries, forecast and proposed credit for the hub dashboard.

Read-only: reuses shared/ so the numbers match the SMS loop and the tests exactly.
Pure standard library + the shared modules (no numpy), so it runs on the hub phone.
"""

from shared.advance import compute_limit, explain
from shared.data import (load_coops, load_diagnoses, load_farmers, load_payouts,
                         load_rain, load_season_totals)
from shared.forecast import ForecastModel

STATUS_LABEL = {
    "pending_approval": "Pending approval",
    "insufficient_history": "New member",
    "approved": "Approved",
}


def latest_season(payouts):
    return max(season for (_coop, season) in payouts)


def _price(payouts, coop_id, season):
    row = payouts.get((coop_id, season))
    return row["first_payment_rwf_per_kg"] if row else None


def _farmer_row(f, coop, season_totals, diagnoses, rain_last, price, season, model):
    lim = compute_limit(f, coop, season_totals, diagnoses, rain_last,
                        price or 0, season, model=model)
    seasons_sorted = dict(sorted(season_totals.items()))
    latest_diag = sorted(diagnoses)[-1][1] if diagnoses else ""
    return {
        "farmer_id": f["farmer_id"],
        "name": f["name"],
        "coop_id": coop["coop_id"],
        "coop_name": coop["name"],
        "district": coop["district"],
        "village": f["village"],
        "trees": f["trees"],
        "member_since": f["member_since"],
        "is_demo": f["is_demo"],
        "seasons": seasons_sorted,
        "latest_kg": round(seasons_sorted.get(season, 0.0)),
        "total_kg": round(sum(season_totals.values())),
        "n_seasons": len([v for v in season_totals.values() if v > 0]),
        "forecast_p50": lim["forecast_p50_kg"],
        "limit": lim,
        "explain": explain(lim),
        "latest_diag": latest_diag,
        "diagnoses": sorted(diagnoses),
        "status": lim["status"],
        "status_label": STATUS_LABEL.get(lim["status"], lim["status"]),
        "price": price,
    }


def build(data_dir=None):
    """Return {rows, coops, overall, season} with one row per farmer (demo first)."""
    coops = load_coops(data_dir)
    farmers = load_farmers(data_dir)
    totals = load_season_totals(data_dir=data_dir)
    diags = load_diagnoses(data_dir)
    rain = load_rain(data_dir)
    payouts = load_payouts(data_dir)
    model = ForecastModel()
    season = latest_season(payouts)

    rows = []
    for fid, f in farmers.items():
        coop = coops[f["coop_id"]]
        rows.append(_farmer_row(
            f, coop, totals.get(fid, {}), diags.get(fid, []),
            rain.get((coop["district"], season), 0.0),
            _price(payouts, coop["coop_id"], season), season, model))
    rows.sort(key=lambda r: (-r["is_demo"], r["farmer_id"]))

    coop_summary = []
    for cid, c in coops.items():
        members = [r for r in rows if r["coop_id"] == cid]
        coop_summary.append({
            "coop_id": cid,
            "name": c["name"],
            "district": c["district"],
            "farmers": len(members),
            "trees": sum(r["trees"] for r in members),
            "latest_kg": sum(r["latest_kg"] for r in members),
            "total_kg": sum(r["total_kg"] for r in members),
            "pending_rwf": sum(r["limit"]["limit_rwf"] for r in members
                               if r["status"] == "pending_approval"),
            "price": _price(payouts, cid, season),
        })

    overall = {
        "farmers": len(rows),
        "coops": len(coops),
        "trees": sum(r["trees"] for r in rows),
        "latest_kg": sum(r["latest_kg"] for r in rows),
        "total_kg": sum(r["total_kg"] for r in rows),
        "pending_rwf": sum(c["pending_rwf"] for c in coop_summary),
        "season": season,
    }
    return {"rows": rows, "coops": coop_summary, "overall": overall, "season": season}


def farmer(farmer_id, data_dir=None):
    """Full detail for one farmer, or None if the id is unknown."""
    coops = load_coops(data_dir)
    farmers = load_farmers(data_dir)
    if farmer_id not in farmers:
        return None
    payouts = load_payouts(data_dir)
    season = latest_season(payouts)
    f = farmers[farmer_id]
    coop = coops[f["coop_id"]]
    totals = load_season_totals([farmer_id], data_dir=data_dir).get(farmer_id, {})
    diags = load_diagnoses(data_dir).get(farmer_id, [])
    rain = load_rain(data_dir).get((coop["district"], season), 0.0)
    row = _farmer_row(f, coop, totals, diags, rain,
                      _price(payouts, coop["coop_id"], season), season, ForecastModel())
    row["coop"] = coop
    return row
