"""
FarmFlow synthetic dairy cooperative data generator.

Simulates daily milk deliveries from smallholder dairy farmers to Rwandan
cooperatives. Every number here is an ILLUSTRATIVE ASSUMPTION for a hackathon
prototype, not a Rwandan statistic. State this in the README and submission.

Mechanics simulated (each gives the model something to learn beyond an average):
  - herd size 1-5 cows, most farmers 1-2
  - per-cow lactation curve (Wood's curve), staggered calving, dry periods
  - seasonality: lower yield in dry seasons (Jun-Aug long dry, Dec-Feb short dry)
  - sickness shocks that cut a cow's yield for 1-3 weeks
  - home consumption kept back before delivery
  - missed delivery days, more common for small farmers
  - quality rejections, varying by farmer
  - monthly pay cycle per coop, payout 5-20 days after cutoff

Usage:  python generate_data.py            (writes CSVs next to this file)
        python generate_data.py --farmers 500 --seed 7
"""

import argparse
import calendar
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- config
START = date(2025, 9, 16)          # first day of simulated data (start of a cycle)
TODAY = date(2026, 10, 3)          # demo "today"; data runs up to and including this
N_FARMERS = 2000
N_DEMO = 60

COOPS = [
    # id, name, village, cutoff day, avg days to pay, base price RWF/L
    ("C01", "Twitezimbere Dairy Cooperative", "Nyagatare", 15, 9, 400),
    ("C02", "Abahizi Milk Cooperative", "Gicumbi", 15, 14, 380),
    ("C03", "Inyange Farmers Cooperative", "Nyabihu", 15, 6, 420),
]

VILLAGES = {
    "C01": ["Nyagatare", "Karangazi", "Rwimiyaga", "Matimba"],
    "C02": ["Gicumbi", "Byumba", "Rukomo", "Mukarange"],
    "C03": ["Nyabihu", "Mukamira", "Jenda", "Rambura"],
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

# Lactation (Wood's curve y = a * t^b * exp(-c t)), peak at t = b/c days in milk
WOOD_B, WOOD_C = 0.20, 0.004       # peak around day 50
LACTATION_DAYS = 305
CALVING_INTERVAL_MEAN, CALVING_INTERVAL_SD = 420, 45

SICKNESS_HAZARD = 1 / 220          # per cow per day
SEASON = {1: 0.88, 2: 0.86, 3: 1.00, 4: 1.06, 5: 1.06, 6: 0.92,
          7: 0.84, 8: 0.82, 9: 0.95, 10: 1.02, 11: 1.05, 12: 0.92}
NOISE_SD = 0.08                    # daily lognormal noise on yield


# ---------------------------------------------------------------- helpers
def cycle_bounds(d: date, cutoff_day: int):
    """Return (cycle_start, cycle_end) for the pay cycle containing date d."""
    if d.day <= cutoff_day:
        end = d.replace(day=cutoff_day)
    else:
        y, m = (d.year + (d.month == 12), d.month % 12 + 1)
        end = date(y, m, min(cutoff_day, calendar.monthrange(y, m)[1]))
    py, pm = (end.year - (end.month == 1), (end.month - 2) % 12 + 1)
    prev_end = date(py, pm, min(cutoff_day, calendar.monthrange(py, pm)[1]))
    return prev_end + timedelta(days=1), end


def wood(dim, peak):
    a = peak / ((WOOD_B / WOOD_C) ** WOOD_B * np.exp(-WOOD_B))
    t = np.maximum(dim, 1)
    return a * t ** WOOD_B * np.exp(-WOOD_C * t)


def simulate_cow(rng, days, start_ord, peak, anchor_calving=None):
    """Daily litres for one cow over `days` days, plus its events.

    anchor_calving: optional ordinal date of one known calving (used to pin
    demo farmers' cows in mid-lactation); other calvings are spaced from it.
    """
    n = len(days)
    anchor = anchor_calving if anchor_calving is not None else \
        start_ord - int(rng.integers(0, CALVING_INTERVAL_MEAN))
    calvings = [anchor]
    while calvings[0] > start_ord:
        calvings.insert(0, calvings[0] - int(rng.normal(CALVING_INTERVAL_MEAN, CALVING_INTERVAL_SD)))
    while calvings[-1] < start_ord + n:
        calvings.append(calvings[-1] + int(rng.normal(CALVING_INTERVAL_MEAN, CALVING_INTERVAL_SD)))
    calvings = np.array(calvings)
    day_ords = start_ord + np.arange(n)
    idx = np.searchsorted(calvings, day_ords, side="right") - 1
    dim = day_ords - calvings[idx]
    milk = np.where(dim <= LACTATION_DAYS, wood(dim, peak), 0.0)

    # sickness shocks
    events = []
    sick = np.ones(n)
    d = 0
    while d < n:
        if rng.random() < SICKNESS_HAZARD:
            length = int(rng.integers(7, 22))
            severity = rng.uniform(0.35, 0.7)
            # gradual recovery: worst at start, back to normal at the end
            ramp = severity + (1 - severity) * np.linspace(0, 1, length)
            sick[d:d + length] = np.minimum(sick[d:d + length], ramp[: n - d])
            events.append(("sickness", d, min(d + length, n) - 1))
            d += length
        else:
            d += 1
    for c in calvings:
        if start_ord <= c < start_ord + n:
            events.append(("calving", int(c - start_ord), None))
    return milk * sick, events, sick


# ---------------------------------------------------------------- main
def main(n_farmers=N_FARMERS, seed=42, out_dir=None):
    rng = np.random.default_rng(seed)
    out = Path(out_dir) if out_dir else Path(__file__).parent
    n_days = (TODAY - START).days + 1
    days = [START + timedelta(days=i) for i in range(n_days)]
    start_ord = START.toordinal()
    months = np.array([d.month for d in days])
    season = np.array([SEASON[m] for m in months])

    coops = pd.DataFrame(COOPS, columns=["coop_id", "name", "village", "cycle_cutoff_day",
                                         "avg_days_to_pay", "base_price"])

    # prices per coop per cycle (small drift), and payouts
    price_lookup, payout_rows = {}, []
    for c in coops.itertuples():
        d, price = START, c.base_price
        while d <= TODAY:
            cs, ce = cycle_bounds(d, c.cycle_cutoff_day)
            price = int(round(np.clip(price + rng.normal(0, 8), c.base_price - 40, c.base_price + 40)))
            price_lookup[(c.coop_id, ce)] = price
            pay_delay = int(np.clip(rng.normal(c.avg_days_to_pay, 3), 3, 25))
            payout = ce + timedelta(days=pay_delay)
            payout_rows.append({"coop_id": c.coop_id, "cycle_start": cs, "cycle_end": ce,
                                "payout_date": payout if payout <= TODAY else None})
            d = ce + timedelta(days=1)

    farmer_rows, delivery_frames, event_rows = [], [], []
    herd_probs = [0.42, 0.30, 0.15, 0.08, 0.05]

    for i in range(n_farmers):
        fid = f"F{i + 1:04d}"
        coop = coops.iloc[i % len(coops)] if i >= N_DEMO else coops.iloc[0 if i < 30 else (i % 3)]
        herd = int(rng.choice([1, 2, 3, 4, 5], p=herd_probs))
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        if i == 0:
            name, herd, coop = "Aline Mukamana", 2, coops.iloc[0]
        if i == 1:
            name, herd, coop = "Jean Claude Habimana", 2, coops.iloc[0]

        # farmer-level traits
        peak_mean = rng.uniform(7, 13)                 # breed/feeding quality
        home_use = rng.uniform(0.5, 2.0)               # litres kept at home daily
        miss_p = np.clip(0.10 - 0.015 * herd + rng.normal(0, 0.02), 0.01, 0.15)
        reject_p = rng.beta(1.2, 30)                   # chance a day has a rejection
        full_reject_p = reject_p * 0.15

        # demo farmers: cows pinned in mid-lactation so the story is clear
        pinned = {0: [date(2026, 7, 10), date(2026, 6, 5)],
                  1: [date(2026, 7, 20), date(2026, 5, 25)]}.get(i)
        if pinned:
            peak_mean = 12.0

        total = np.zeros(n_days)
        for cow in range(herd):
            peak = max(3.0, rng.normal(peak_mean, 1.5))
            anchor = pinned[cow].toordinal() if pinned else None
            milk, events, sick = simulate_cow(rng, days, start_ord, peak, anchor)
            if pinned:
                # no random sickness in the current cycle for demo farmers
                cs = (date(2026, 9, 16) - START).days
                events = [e for e in events if not (e[0] == "sickness" and e[2] >= cs)]
                milk[cs:] = milk[cs:] / sick[cs:]
            if i == 1 and cow == 0:
                # demo story: Jean Claude's cow falls sick on 2026-09-27
                s = (date(2026, 9, 27) - START).days
                length, severity = 18, 0.35
                ramp = severity + (1 - severity) * np.linspace(0, 1, length)
                milk[s:s + length] *= ramp[: n_days - s]
                events.append(("sickness", s, min(s + length, n_days) - 1))
            total += milk
            for ev, s, e in events:
                event_rows.append({"farmer_id": fid, "cow": cow + 1, "event": ev,
                                   "start": days[s], "end": days[e] if e is not None else None})

        noise = rng.lognormal(0, NOISE_SD, n_days)
        delivered = np.maximum(0, total * season * noise - home_use)
        delivered = np.round(delivered, 1)
        missed = rng.random(n_days) < miss_p
        delivered[missed] = 0.0

        rejected = np.zeros(n_days)
        partial = rng.random(n_days) < reject_p
        rejected[partial] = np.round(delivered[partial] * rng.uniform(0.1, 0.5, partial.sum()), 1)
        full = rng.random(n_days) < full_reject_p
        rejected[full] = delivered[full]

        mask = delivered > 0
        prices = [price_lookup[(coop.coop_id, cycle_bounds(d, coop.cycle_cutoff_day)[1])] for d in days]
        delivery_frames.append(pd.DataFrame({
            "farmer_id": fid,
            "date": np.array(days)[mask],
            "litres_delivered": delivered[mask],
            "litres_rejected": rejected[mask],
            "price_per_litre": np.array(prices)[mask],
        }))

        farmer_rows.append({
            "farmer_id": fid, "coop_id": coop.coop_id, "name": name,
            "phone": f"+250700{i + 1:06d}",      # placeholder, not a real number
            "herd_size": herd,
            "village": rng.choice(VILLAGES[coop.coop_id]),
            "is_demo": int(i < N_DEMO),
        })

    farmers = pd.DataFrame(farmer_rows)
    deliveries = pd.concat(delivery_frames, ignore_index=True)
    payouts = pd.DataFrame(payout_rows)
    events = pd.DataFrame(event_rows).sort_values(["farmer_id", "start"])

    coops.drop(columns="base_price").to_csv(out / "coops.csv", index=False)
    farmers.to_csv(out / "farmers.csv", index=False)
    deliveries.to_csv(out / "deliveries.csv", index=False)
    payouts.to_csv(out / "payouts.csv", index=False)
    events.to_csv(out / "truth_events.csv", index=False)
    print(f"farmers={len(farmers)} deliveries={len(deliveries)} days={n_days} "
          f"events={len(events)} -> {out}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--farmers", type=int, default=N_FARMERS)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--out", default=None)
    a = p.parse_args()
    main(a.farmers, a.seed, a.out)
