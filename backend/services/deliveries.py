import csv
from datetime import date
from pathlib import Path

from shared.data import load_farmers


ROOT = Path(__file__).resolve().parents[2]
DELIVERIES_PATH = ROOT / "data" / "deliveries.csv"


def record_delivery(
    farmer_id: str,
    cherry_kg: float,
    rejected_kg: float = 0.0,
    price_rwf_per_kg: int = 350,
):
    farmers = load_farmers()

    if farmer_id not in farmers:
        raise ValueError(f"Unknown farmer: {farmer_id}")

    if cherry_kg <= 0:
        raise ValueError("Cherry kg must be greater than zero.")

    if rejected_kg < 0:
        raise ValueError("Rejected kg cannot be negative.")

    if rejected_kg > cherry_kg:
        raise ValueError("Rejected kg cannot exceed cherry kg.")

    if price_rwf_per_kg <= 0:
        raise ValueError("Price must be greater than zero.")

    row = {
        "farmer_id": farmer_id,
        "date": date.today().isoformat(),
        "cherry_kg": round(float(cherry_kg), 1),
        "rejected_kg": round(float(rejected_kg), 1),
        "price_rwf_per_kg": int(price_rwf_per_kg),
    }

    with open(
        DELIVERIES_PATH,
        "a",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "farmer_id",
                "date",
                "cherry_kg",
                "rejected_kg",
                "price_rwf_per_kg",
            ],
        )
        writer.writerow(row)

    return row