import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

SEED = 20261022
ACCOUNT_COUNT = 2500
QUOTE_COUNT = 10000

PRODUCTS = [
    "Analytics Package",
    "Cloud Subscription",
    "Data Migration",
    "Integration Service",
    "Technical Support",
]

QUOTE_STATUSES = (
    ["accepted"] * 7000
    + ["sent"] * 1000
    + ["rejected"] * 1000
    + ["draft"] * 500
    + ["expired"] * 500
)


def random_date(rng, start_date, end_date):
    """Return a deterministic random date within the given range."""
    days = (end_date - start_date).days
    return start_date + timedelta(days=rng.randint(0, days))


def generate_master_data(connection, seed=SEED):
    """Generate synthetic accounts, quotes, and quote lines."""
    rng = random.Random(seed)

    # This initial stage expects an empty database.
    existing_accounts = connection.execute(
        "SELECT COUNT(*) FROM accounts"
    ).fetchone()[0]

    existing_quotes = connection.execute(
        "SELECT COUNT(*) FROM quotes"
    ).fetchone()[0]

    if existing_accounts or existing_quotes:
        raise RuntimeError(
            "Master data already exists. "
            "Use a fresh database before running this stage again."
        )

    start_date = date(2026, 1, 1)
    end_date = date(2026, 10, 1)

    accounts = []

    for i in range(1, ACCOUNT_COUNT + 1):
        created = random_date(rng, date(2024, 1, 1), end_date)

        accounts.append(
            (
                f"ACC-{i:06d}",
                f"Synthetic Account {i:05d}",
                created.isoformat(),
            )
        )

    connection.executemany(
        """
        INSERT INTO accounts (
            account_id, account_name, created_at
        )
        VALUES (?, ?, ?)
        """,
        accounts,
    )

    statuses = QUOTE_STATUSES.copy()
    rng.shuffle(statuses)

    quotes = []
    quote_lines = []

    quote_line_id = 1

    for i in range(1, QUOTE_COUNT + 1):
        quote_id = f"QTE-2026-{i:06d}"
        account_id = rng.choice(accounts)[0]

        quote_date = random_date(rng, start_date, end_date)
        expiry_date = quote_date + timedelta(
            days=rng.randint(14, 45)
        )

        status = statuses[i - 1]

        quotes.append(
            (
                quote_id,
                account_id,
                quote_date.isoformat(),
                expiry_date.isoformat(),
                status,
            )
        )

        line_count = rng.randint(1, 4)

        for _ in range(line_count):
            product = rng.choice(PRODUCTS)
            quantity = rng.randint(1, 50)

            # Store monetary values to two decimal places.
            unit_price = rng.randint(5000, 250000) / 100

            quote_lines.append(
                (
                    quote_line_id,
                    quote_id,
                    product,
                    quantity,
                    unit_price,
                )
            )

            quote_line_id += 1

    connection.executemany(
        """
        INSERT INTO quotes (
            quote_id, account_id, quote_date,
            expiry_date, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        quotes,
    )

    connection.executemany(
        """
        INSERT INTO quote_lines (
            quote_line_id, quote_id, product_name,
            quantity, unit_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        quote_lines,
    )

    return {
        "accounts": len(accounts),
        "quotes": len(quotes),
        "accepted_quotes": statuses.count("accepted"),
        "quote_lines": len(quote_lines),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. "
            "Run the database initialization step first."
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        try:
            with connection:
                summary = generate_master_data(connection)
        except Exception:
            raise

    print("Master data generation completed.")
    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()