"""Loading FarmFlow data from SQLite.

A coffee season is identified by its harvest year
(harvest runs March-July).
"""

import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DB_PATH = DATA_DIR / "farmflow.db"


def _connect(data_dir=None):
    db_path = Path(data_dir or DATA_DIR) / "farmflow.db"

    conn = sqlite3.connect(
        db_path,
        timeout=10,
    )

    conn.row_factory = sqlite3.Row

    return conn


def load_coops(data_dir=None):
    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM coops
            """
        ).fetchall()

    out = {}

    for row in rows:
        r = dict(row)

        r["avg_days_to_first_payment"] = int(
            r["avg_days_to_first_payment"]
        )

        out[r["coop_id"]] = r

    return out


def load_farmers(data_dir=None):
    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM farmers
            """
        ).fetchall()

    out = {}

    for row in rows:
        r = dict(row)

        r["trees"] = int(
            r["trees"]
        )

        r["avg_tree_age_2021"] = float(
            r["avg_tree_age_2021"]
        )

        r["member_since"] = int(
            r["member_since"]
        )

        r["is_demo"] = int(
            r["is_demo"]
        )

        out[r["farmer_id"]] = r

    return out


def load_season_totals(
    farmer_ids=None,
    data_dir=None,
):
    """{farmer_id: {season: paid_kg}}."""

    params = []

    sql = """
        SELECT
            farmer_id,
            CAST(substr(date, 1, 4) AS INTEGER) AS season,
            SUM(
                CAST(cherry_kg AS REAL)
                -
                CAST(rejected_kg AS REAL)
            ) AS paid_kg
        FROM deliveries
    """

    if farmer_ids:
        farmer_ids = list(farmer_ids)

        placeholders = ",".join(
            "?"
            for _ in farmer_ids
        )

        sql += f"""
            WHERE farmer_id IN ({placeholders})
        """

        params.extend(
            farmer_ids
        )

    sql += """
        GROUP BY
            farmer_id,
            season

        ORDER BY
            farmer_id,
            season
    """

    totals = defaultdict(dict)

    with _connect(data_dir) as conn:
        rows = conn.execute(
            sql,
            params,
        ).fetchall()

    for row in rows:
        totals[row["farmer_id"]][
            int(row["season"])
        ] = float(
            row["paid_kg"] or 0
        )

    return dict(totals)


def load_diagnoses(data_dir=None):
    """{farmer_id: [(date, diagnosis), ...]}"""

    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT
                farmer_id,
                date,
                diagnosis
            FROM diagnoses
            ORDER BY
                farmer_id,
                date
            """
        ).fetchall()

    out = defaultdict(list)

    for row in rows:
        out[row["farmer_id"]].append(
            (
                date.fromisoformat(
                    row["date"]
                ),
                row["diagnosis"],
            )
        )

    return dict(out)


def load_rain(data_dir=None):
    """{(district, season): anomaly}"""

    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT
                district,
                season,
                anomaly
            FROM rainfall
            """
        ).fetchall()

    return {
        (
            row["district"],
            int(row["season"]),
        ): float(row["anomaly"])
        for row in rows
    }


def load_payouts(data_dir=None):
    """{(coop_id, season): row}"""

    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM payouts
            """
        ).fetchall()

    out = {}

    for row in rows:
        r = dict(row)

        r["season"] = int(
            r["season"]
        )

        r["first_payment_rwf_per_kg"] = int(
            r["first_payment_rwf_per_kg"]
        )

        r["second_payment_rwf_per_kg"] = int(
            r["second_payment_rwf_per_kg"]
        )

        out[
            (
                r["coop_id"],
                r["season"],
            )
        ] = r

    return out


def load_inputs(data_dir=None):
    with _connect(data_dir) as conn:
        rows = conn.execute(
            """
            SELECT *
            FROM inputs
            ORDER BY rank
            """
        ).fetchall()

    out = []

    for row in rows:
        r = dict(row)

        r["price_rwf"] = int(
            r["price_rwf"]
        )

        r["per_trees"] = int(
            r["per_trees"]
        )

        r["rank"] = int(
            r["rank"]
        )

        r["diagnoses"] = (
            r["diagnoses"].split("|")
            if r["diagnoses"]
            else []
        )

        out.append(r)

    return out