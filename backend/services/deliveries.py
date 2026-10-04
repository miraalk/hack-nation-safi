from datetime import date
from pathlib import Path
import sqlite3

from shared.data import load_farmers, load_payouts


ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "farmflow.db"


def _get_connection():
    conn = sqlite3.connect(
        DB_PATH,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


def _current_price_for_farmer(
    farmer_id: str,
) -> int:
    farmers = load_farmers()

    farmer = farmers.get(
        farmer_id
    )

    if not farmer:
        raise ValueError(
            f"Unknown farmer: {farmer_id}"
        )

    coop_id = farmer["coop_id"]

    payouts = load_payouts()

    matching = [
        row
        for (row_coop_id, _season), row
        in payouts.items()
        if row_coop_id == coop_id
    ]

    if not matching:
        raise ValueError(
            f"No payout price found for coop {coop_id}"
        )

    latest = max(
        matching,
        key=lambda r: r["season"],
    )

    return int(
        latest["first_payment_rwf_per_kg"]
    )


def record_delivery(
    farmer_id: str,
    cherry_kg: float,
    rejected_kg: float = 0.0,
    price_rwf_per_kg: int = None,
):
    farmer_id = (
        farmer_id
        .strip()
        .upper()
    )

    farmers = load_farmers()

    if farmer_id not in farmers:
        raise ValueError(
            f"Unknown farmer: {farmer_id}"
        )

    cherry_kg = float(
        cherry_kg
    )

    rejected_kg = float(
        rejected_kg
    )

    if cherry_kg <= 0:
        raise ValueError(
            "Cherry kg must be greater than zero."
        )

    if rejected_kg < 0:
        raise ValueError(
            "Rejected kg cannot be negative."
        )

    if rejected_kg > cherry_kg:
        raise ValueError(
            "Rejected kg cannot exceed cherry kg."
        )

    if price_rwf_per_kg is None:
        price_rwf_per_kg = (
            _current_price_for_farmer(
                farmer_id
            )
        )

    price_rwf_per_kg = int(
        price_rwf_per_kg
    )

    if price_rwf_per_kg <= 0:
        raise ValueError(
            "Price must be greater than zero."
        )

    row = {
        "farmer_id": farmer_id,
        "date": date.today().isoformat(),
        "cherry_kg": round(
            cherry_kg,
            1,
        ),
        "rejected_kg": round(
            rejected_kg,
            1,
        ),
        "price_rwf_per_kg": (
            price_rwf_per_kg
        ),
    }

    with _get_connection() as conn:
        conn.execute(
            """
            INSERT INTO deliveries (
                farmer_id,
                date,
                cherry_kg,
                rejected_kg,
                price_rwf_per_kg
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                row["farmer_id"],
                row["date"],
                row["cherry_kg"],
                row["rejected_kg"],
                row["price_rwf_per_kg"],
            ),
        )

    print(
        "Delivery saved to SQLite:",
        row,
    )

    return row