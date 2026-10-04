from shared.advance import compute_limit
from shared.data import (
    load_coops,
    load_diagnoses,
    load_farmers,
    load_payouts,
    load_rain,
    load_season_totals,
)
from shared.forecast import ForecastModel


def _latest_season(payouts):
    return max(season for (_coop_id, season) in payouts)


def get_credit_summary(farmer_id: str):
    farmers = load_farmers()

    if farmer_id not in farmers:
        return None

    coops = load_coops()
    diagnoses = load_diagnoses()
    payouts = load_payouts()
    rain = load_rain()
    season_totals = load_season_totals([farmer_id]).get(farmer_id, {})

    farmer = farmers[farmer_id]
    coop = coops[farmer["coop_id"]]

    last_season = _latest_season(payouts)

    payout = payouts.get((coop["coop_id"], last_season))
    price = payout["first_payment_rwf_per_kg"] if payout else 0

    rain_anomaly = rain.get(
        (coop["district"], last_season),
        0.0,
    )

    limit = compute_limit(
        farmer=farmer,
        coop=coop,
        season_totals=season_totals,
        diagnoses=diagnoses.get(farmer_id, []),
        rain_anomaly_last=rain_anomaly,
        last_price=price,
        last_season=last_season,
        model=ForecastModel(),
    )

    return {
        "farmer_id": farmer_id,
        "farmer_name": farmer["name"],
        "status": limit["status"],
        "season": limit["season"],
        "limit_rwf": limit["limit_rwf"],
        "forecast_p10_kg": limit["forecast_p10_kg"],
        "forecast_p50_kg": limit["forecast_p50_kg"],
        "forecast_p90_kg": limit["forecast_p90_kg"],
    }