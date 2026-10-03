"""Checks the shared logic on the demo farmers. Run: python tests/test_shared.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared import config
from shared.advance import approve, compute_limit, explain
from shared.data import (load_coops, load_diagnoses, load_farmers, load_inputs, load_payouts,
                         load_rain, load_season_totals)
from shared.forecast import ForecastModel
from shared.recommend import bundle_text, recommend

LAST_SEASON = 2026


def main():
    coops, farmers, catalogue = load_coops(), load_farmers(), load_inputs()
    totals = load_season_totals(["F0001", "F0002"])
    diags, rain, payouts = load_diagnoses(), load_rain(), load_payouts()
    model = ForecastModel()

    limits = {}
    for fid in ("F0001", "F0002"):
        f = farmers[fid]
        coop = coops[f["coop_id"]]
        price = payouts[(coop["coop_id"], LAST_SEASON)]["first_payment_rwf_per_kg"]
        lim = compute_limit(f, coop, totals.get(fid, {}), diags.get(fid, []),
                            rain[(coop["district"], LAST_SEASON)], price, LAST_SEASON, model=model)
        limits[fid] = lim
        seasons = {s: round(v) for s, v in sorted(totals.get(fid, {}).items())}
        print(f"{f['name']} ({f['trees']} trees) deliveries {seasons}")
        print(f"  -> {lim['status']}, limit RWF {lim['limit_rwf']:,}; "
              f"forecast {lim['forecast_p10_kg']}/{lim['forecast_p50_kg']}/{lim['forecast_p90_kg']} kg; "
              f"{explain(lim)}")

    noor, jc = limits["F0001"], limits["F0002"]
    assert noor["status"] == "pending_approval" and noor["limit_rwf"] > 0
    assert 0 <= noor["limit_rwf"] <= config.CAP_RWF and noor["limit_rwf"] % config.ROUND_TO_RWF == 0
    assert noor["forecast_p10_kg"] <= noor["forecast_p50_kg"] <= noor["forecast_p90_kg"]
    assert jc["status"] == "insufficient_history" and jc["limit_rwf"] == 0, "new member must be referred"
    assert approve(noor, "officer-01")["status"] == "approved"

    # outstanding advances reduce the limit
    f, coop = farmers["F0001"], coops[farmers["F0001"]["coop_id"]]
    price = payouts[(coop["coop_id"], LAST_SEASON)]["first_payment_rwf_per_kg"]
    owed = compute_limit(f, coop, totals["F0001"], diags.get("F0001", []),
                         rain[(coop["district"], LAST_SEASON)], price, LAST_SEASON,
                         outstanding_rwf=50_000, model=model)
    assert owed["limit_rwf"] < noor["limit_rwf"]

    print()
    for diagnosis in ("leaf_rust", "pests", "nutrient", "drought", "old_trees"):
        rec = recommend(noor["limit_rwf"], diagnosis, f["trees"], catalogue)
        print(f"Noor, {diagnosis:10} -> {bundle_text(rec)} = RWF {rec['total_rwf']:,} "
              f"(left {rec['remaining_rwf']:,})")
        assert rec["status"] == "ok" and rec["total_rwf"] <= noor["limit_rwf"]

    rust = recommend(noor["limit_rwf"], "leaf_rust", f["trees"], catalogue)
    assert rust["items"][0]["input_id"] == "I01", "rust should get fungicide first"
    assert recommend(noor["limit_rwf"], "unknown", 1500, catalogue)["status"] == "refer"
    assert recommend(noor["limit_rwf"], "healthy", 1500, catalogue)["status"] == "no_treatment"
    assert recommend(0, "leaf_rust", 1500, catalogue)["status"] == "no_credit"
    assert recommend(3000, "leaf_rust", 1500, catalogue)["status"] == "too_low"
    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
