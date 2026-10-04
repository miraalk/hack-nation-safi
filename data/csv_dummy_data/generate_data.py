"""
FarmFlow synthetic coffee cooperative data generator.

Simulates smallholder coffee farmers delivering cherry to cooperative washing
stations in the Rwandan highlands, harvest seasons 2021-2026. Every number is an
ILLUSTRATIVE ASSUMPTION for a hackathon prototype, not a Rwandan statistic.
Say so in the README and the submission.

Mechanics (each gives the forecast model something to learn beyond "same as last year"):
  - tree count per farmer (lognormal), average tree age with a yield-by-age curve
  - management quality (cherry kg per tree)
  - biennial bearing: alternating high/low years, strength varies by farmer
  - pre-season rainfall anomaly per district (synthetic; swap for CHIRPS)
  - coffee leaf rust: wetter years and weaker management raise the risk; rust in
    one season cuts the NEXT season's yield (defoliation)
  - only some rust cases are reported to the washing station (diagnoses.csv)
  - side-selling: each farmer delivers only a share of the harvest to the coop
  - daily deliveries over the March-July harvest, peaking around April-May
  - first payment per kg at delivery, second payment after the coffee is sold

Usage:  python generate_data.py                 (writes CSVs next to this file)
        python generate_data.py --farmers 500 --seed 7
"""

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEASONS = [2021, 2022, 2023, 2024, 2025, 2026]   # harvest year
HARVEST_START = (3, 1)                            # 1 March
HARVEST_END = (7, 15)                             # 15 July
TODAY = date(2026, 10, 3)
N_FARMERS = 2000
N_DEMO = 60

# Minimum farm-gate price for cherry, RWF/kg. 2024-2026 from NAEB announcements
# (allAfrica, Jan 2025 and Jan 2026); 2021-2023 are illustrative assumptions.
FLOOR_PRICE = {2021: 350, 2022: 380, 2023: 410, 2024: 480, 2025: 600, 2026: 750}

COOPS = [
    # id, name, district, avg days to first payment, base cherry price RWF/kg
    ("C01", "Ondera Coffee Cooperative", "Nyamasheke", 10, 430),
    ("C02", "Abakundakawa Cooperative", "Gakenke", 14, 410),
    ("C03", "Twongere Umusaruro Cooperative", "Huye", 7, 450),
]
VILLAGES = {
    "C01": ["Ondera", "Kanjongo", "Macuba", "Rangiro"],
    "C02": ["Rushashi", "Muzo", "Janja", "Coko"],
    "C03": ["Maraba", "Simbi", "Rusatira", "Huye"],
}
FIRST_NAMES = [
    "Aline", "Jean Claude", "Marie", "Emmanuel", "Josiane", "Eric", "Claudine",
    "Patrick", "Vestine", "Innocent", "Diane", "Theogene", "Jeanne", "Olivier",
    "Esperance", "Didier", "Chantal", "Fabrice", "Solange", "Alexis", "Grace",
    "Janvier", "Beatha", "Celestin", "Immaculee", "Gaspard", "Odette", "Faustin",
    "Liberata", "Damascene",
]
LAST_NAMES = [
    "Mukamana", "Habimana", "Uwimana", "Niyonzima", "Mukeshimana", "Nsengimana",
    "Uwase", "Hakizimana", "Ingabire", "Ndayisaba", "Mukandayisenga", "Bizimana",
    "Nyiraneza", "Tuyisenge", "Umutoni", "Nshimiyimana", "Iradukunda", "Munyaneza",
    "Uwamahoro", "Kamanzi",
]


def age_factor(age):
    """Relative yield by average tree age (young trees ramp up, old trees decline)."""
    age = np.asarray(age, dtype=float)
    ramp = np.clip((age - 2) / 4, 0.1, 1.0)
    decline = np.clip(1 - (age - 20) * 0.025, 0.4, 1.0)
    return ramp * decline


def harvest_days(year):
    s = date(year, *HARVEST_START)
    e = date(year, *HARVEST_END)
    return [s + timedelta(days=i) for i in range((e - s).days + 1)]


def main(n_farmers=N_FARMERS, seed=42, out_dir=None):
    rng = np.random.default_rng(seed)
    out = Path(out_dir) if out_dir else Path(__file__).parent
    coops = pd.DataFrame(COOPS, columns=["coop_id", "name", "district",
                                         "avg_days_to_first_payment", "base_price"])

    # ---- rainfall: pre-season (Sep-Feb before each harvest) anomaly per district
    rain_rows, rain_anom = [], {}
    for c in coops.itertuples():
        for s in SEASONS + [SEASONS[-1] + 1]:
            anom = float(np.clip(rng.normal(0, 0.15), -0.35, 0.35))
            rain_anom[(c.district, s)] = anom
            rain_rows.append({"district": c.district, "season": s,
                              "preseason_rain_mm": round(950 * (1 + anom)),
                              "anomaly": round(anom, 3)})

    # ---- prices and payouts per coop per season
    # 2024-2026: NAEB minimum cherry prices (RWF 480 / 600 / 750 per kg); coops in this
    # simulation pay the minimum plus a small premium. 2021-2023: illustrative assumptions.
    price, payout_rows = {}, []
    for c in coops.itertuples():
        for s in SEASONS:
            premium = int(round(np.clip(rng.normal(0, 15), -20, 40))) + (c.base_price - 410) // 2
            p = FLOOR_PRICE[s] + max(0, premium)
            second = int(round(rng.uniform(40, 120)))
            price[(c.coop_id, s)] = p
            payout_rows.append({
                "coop_id": c.coop_id, "season": s,
                "first_payment_rwf_per_kg": p,
                "avg_days_to_first_payment": c.avg_days_to_first_payment,
                "second_payment_rwf_per_kg": second,
                "second_payment_date": date(s, 11, 1) + timedelta(days=int(rng.integers(0, 45))),
            })
    payouts = pd.DataFrame(payout_rows)
    payouts.loc[payouts.second_payment_date > TODAY, "second_payment_date"] = None

    farmer_rows, delivery_frames, rust_rows, diag_rows, season_rows = [], [], [], [], []

    for i in range(n_farmers):
        fid = f"F{i + 1:04d}"
        coop = coops.iloc[0] if i < 30 else coops.iloc[i % len(coops)]
        trees = int(np.clip(rng.lognormal(np.log(600), 0.6), 100, 4000))
        age0 = float(rng.uniform(4, 35))                 # avg tree age in 2021
        mgmt = float(np.clip(rng.normal(1.8, 0.5), 0.6, 3.2))   # kg cherry / tree at peak
        bien = float(rng.uniform(0, 0.25)) * rng.choice([-1, 1])
        loyalty = float(rng.beta(6, 2))                  # share of harvest sold to the coop
        rust_base = float(np.clip(0.18 - 0.05 * (mgmt - 1.8), 0.03, 0.35))
        first_season = SEASONS[0]
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"

        # demo farmers
        rust_force = {}
        if i == 0:   # Noor: good history, rust in 2025 -> yields fell in 2026
            name, trees, age0, mgmt, bien, loyalty = "Noor Mukamana", 1500, 9.0, 2.1, 0.08, 0.62
            rust_force = {2021: 0.0, 2022: 0.0, 2023: 0.0, 2024: 0.0, 2025: 0.45, 2026: 0.30}
        if i == 1:   # new member: one season only -> "talk to coop staff"
            name, first_season = "Jean Claude Habimana", 2026

        farmer_rows.append({
            "farmer_id": fid, "coop_id": coop.coop_id, "name": name,
            "phone": f"+250700{i + 1:06d}",      # placeholder, not a real number
            "trees": trees, "avg_tree_age_2021": round(age0, 1),
            "village": rng.choice(VILLAGES[coop.coop_id]),
            "member_since": first_season, "is_demo": int(i < N_DEMO),
        })

        prev_rust = 0.0
        for s in SEASONS:
            anom = rain_anom[(coop.district, s)]
            sev = rust_force.get(s)
            if sev is None:
                p_rust = np.clip(rust_base * (1 + 2.0 * anom), 0.01, 0.6)
                sev = float(rng.uniform(0.15, 0.6)) if rng.random() < p_rust else 0.0
            age = age0 + (s - SEASONS[0])
            phase = 1 if (s % 2 == 0) else -1
            kg = (trees * mgmt * age_factor(age) * (1 + bien * phase) * (1 + 0.6 * anom)
                  * (1 - 0.55 * prev_rust) * (1 - 0.15 * sev)
                  * rng.lognormal(0, 0.10))
            share = float(np.clip(loyalty + rng.normal(0, 0.08), 0.1, 1.0))
            delivered_total = kg * share if s >= first_season else 0.0
            if sev > 0:
                rust_rows.append({"farmer_id": fid, "season": s, "severity": round(sev, 2)})
                if s >= first_season and (rng.random() < 0.5 or i == 0):
                    d = date(s, 8, 1) + timedelta(days=int(rng.integers(0, 60)))
                    diag_rows.append({"farmer_id": fid, "date": d, "diagnosis": "leaf_rust",
                                      "source": "extension_officer"})
            season_rows.append({"farmer_id": fid, "season": s, "harvest_kg": round(kg),
                                "delivered_kg": round(delivered_total), "rust_severity": round(sev, 2)})
            prev_rust = sev

            if delivered_total <= 0:
                continue
            days = harvest_days(s)
            n = len(days)
            # harvest curve: bell shape peaking around late April / May
            t = np.arange(n)
            curve = np.exp(-0.5 * ((t - n * 0.45) / (n * 0.2)) ** 2)
            visits = rng.random(n) < float(rng.uniform(0.25, 0.55))
            w = curve * visits
            if w.sum() == 0:
                continue
            kgs = np.round(delivered_total * w / w.sum() * rng.lognormal(0, 0.15, n), 1)
            floaters = np.round(kgs * rng.uniform(0, 0.06, n), 1)   # rejected cherry
            mask = kgs > 0
            delivery_frames.append(pd.DataFrame({
                "farmer_id": fid,
                "date": np.array(days)[mask],
                "cherry_kg": kgs[mask],
                "rejected_kg": floaters[mask],
                "price_rwf_per_kg": price[(coop.coop_id, s)],
            }))

    farmers = pd.DataFrame(farmer_rows)
    deliveries = pd.concat(delivery_frames, ignore_index=True)
    rain = pd.DataFrame(rain_rows)
    diagnoses = pd.DataFrame(diag_rows).sort_values(["farmer_id", "date"])
    truth = pd.DataFrame(season_rows)

    coops.drop(columns="base_price").to_csv(out / "coops.csv", index=False)
    farmers.to_csv(out / "farmers.csv", index=False)
    deliveries.to_csv(out / "deliveries.csv", index=False)
    payouts.to_csv(out / "payouts.csv", index=False)
    rain.to_csv(out / "rainfall.csv", index=False)
    diagnoses.to_csv(out / "diagnoses.csv", index=False)
    truth.to_csv(out / "truth_seasons.csv", index=False)
    # remove files from the old dairy version if present
    for old in ["truth_events.csv"]:
        (out / old).unlink(missing_ok=True)
    print(f"farmers={len(farmers)} deliveries={len(deliveries)} diagnoses={len(diagnoses)} -> {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--farmers", type=int, default=N_FARMERS)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=None)
    a = p.parse_args()
    main(a.farmers, a.seed, a.out)
