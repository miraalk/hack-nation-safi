"""Loading FarmFlow CSVs (standard library only).

The hub keeps the same tables in SQLite; these loaders read the CSV versions.
A coffee season is identified by its harvest year (harvest runs March-July).
"""

import csv
from collections import defaultdict
from datetime import date
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def _read(name, data_dir=None):
    with open(Path(data_dir or DATA_DIR) / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_coops(data_dir=None):
    rows = _read("coops.csv", data_dir)
    for r in rows:
        r["avg_days_to_first_payment"] = int(r["avg_days_to_first_payment"])
    return {r["coop_id"]: r for r in rows}


def load_farmers(data_dir=None):
    rows = _read("farmers.csv", data_dir)
    for r in rows:
        r["trees"] = int(r["trees"])
        r["avg_tree_age_2021"] = float(r["avg_tree_age_2021"])
        r["member_since"] = int(r["member_since"])
        r["is_demo"] = int(r["is_demo"])
    return {r["farmer_id"]: r for r in rows}


def load_season_totals(farmer_ids=None, data_dir=None):
    """{farmer_id: {season: paid_kg}} from daily deliveries (cherry minus rejected)."""
    wanted = set(farmer_ids) if farmer_ids else None
    totals = defaultdict(lambda: defaultdict(float))
    with open(Path(data_dir or DATA_DIR) / "deliveries.csv", newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            fid = r["farmer_id"]
            if wanted is not None and fid not in wanted:
                continue
            season = int(r["date"][:4])
            totals[fid][season] += float(r["cherry_kg"]) - float(r["rejected_kg"])
    return {fid: dict(s) for fid, s in totals.items()}


def load_diagnoses(data_dir=None):
    """{farmer_id: [(date, diagnosis), ...]}"""
    out = defaultdict(list)
    for r in _read("diagnoses.csv", data_dir):
        out[r["farmer_id"]].append((date.fromisoformat(r["date"]), r["diagnosis"]))
    return dict(out)


def load_rain(data_dir=None):
    """{(district, season): anomaly}"""
    return {(r["district"], int(r["season"])): float(r["anomaly"])
            for r in _read("rainfall.csv", data_dir)}


def load_payouts(data_dir=None):
    """{(coop_id, season): row}"""
    rows = _read("payouts.csv", data_dir)
    for r in rows:
        r["season"] = int(r["season"])
        r["first_payment_rwf_per_kg"] = int(r["first_payment_rwf_per_kg"])
        r["second_payment_rwf_per_kg"] = int(r["second_payment_rwf_per_kg"])
    return {(r["coop_id"], r["season"]): r for r in rows}


def load_inputs(data_dir=None):
    rows = _read("inputs.csv", data_dir)
    for r in rows:
        r["price_rwf"] = int(r["price_rwf"])
        r["per_trees"] = int(r["per_trees"])
        r["rank"] = int(r["rank"])
        r["diagnoses"] = r["diagnoses"].split("|") if r["diagnoses"] else []
    return rows
