import sqlite3
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "farmflow.db"


TABLES = {
    "farmers": "farmers.csv",
    "coops": "coops.csv",
    "deliveries": "deliveries.csv",
    "diagnoses": "diagnoses.csv",
    "inputs": "inputs.csv",
    "payouts": "payouts.csv",
    "rainfall": "rainfall.csv",
    "truth_seasons": "truth_seasons.csv",
}


def main():
    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)

    try:
        for table_name, filename in TABLES.items():
            csv_path = DATA_DIR / filename

            if not csv_path.exists():
                print(
                    f"Skipping {filename}: "
                    f"file not found"
                )
                continue

            df = pd.read_csv(csv_path)

            df.to_sql(
                table_name,
                conn,
                if_exists="replace",
                index=False,
            )

            print(
                f"{table_name}: "
                f"{len(df):,} rows"
            )

        # Useful indexes
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_deliveries_farmer
            ON deliveries(farmer_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_deliveries_farmer_date
            ON deliveries(farmer_id, date)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_diagnoses_farmer
            ON diagnoses(farmer_id)
            """
        )

        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_diagnoses_farmer_date
            ON diagnoses(farmer_id, date)
            """
        )

        conn.commit()

    finally:
        conn.close()

    print()
    print("Database created:")
    print(DB_PATH)


if __name__ == "__main__":
    main()