import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

SEED = 20261023


def generate_orders(connection, seed=SEED):
    """Create one sales order for each accepted quote."""

    rng = random.Random(seed)

    existing = connection.execute(
        "SELECT COUNT(*) FROM sales_orders"
    ).fetchone()[0]

    if existing:
        raise RuntimeError(
            "Sales orders already exist. "
            "Use a fresh database before regenerating."
        )

    accepted_quotes = connection.execute(
        """
        SELECT quote_id, account_id, quote_date
        FROM quotes
        WHERE status = 'accepted'
        ORDER BY quote_id
        """
    ).fetchall()

    if not accepted_quotes:
        raise RuntimeError(
            "No accepted quotes found. Generate master data first."
        )

    # Assign a reproducible mix of order statuses.
    statuses = (
        ["open"] * 2500
        + ["processing"] * 1500
        + ["fulfilled"] * 1500
        + ["closed"] * 1200
        + ["cancelled"] * 300
    )

    if len(statuses) != len(accepted_quotes):
        raise ValueError(
            f"Expected {len(accepted_quotes)} statuses, "
            f"but configured {len(statuses)}."
        )

    rng.shuffle(statuses)

    orders = []
    order_lines = []
    order_line_id = 1

    for index, quote in enumerate(accepted_quotes):
        quote_id, account_id, quote_date_text = quote
        quote_date = date.fromisoformat(quote_date_text)

        order_date = quote_date + timedelta(
            days=rng.randint(0, 14)
        )

        order_id = f"SO-2026-{index + 1:06d}"

        orders.append(
            (
                order_id,
                account_id,
                quote_id,
                order_date.isoformat(),
                statuses[index],
            )
        )

        quote_lines = connection.execute(
            """
            SELECT quote_line_id, product_name, quantity, unit_price
            FROM quote_lines
            WHERE quote_id = ?
            ORDER BY quote_line_id
            """,
            (quote_id,),
        ).fetchall()

        for quote_line in quote_lines:
            (
                quote_line_id,
                product_name,
                quantity,
                unit_price,
            ) = quote_line

            order_lines.append(
                (
                    order_line_id,
                    order_id,
                    quote_line_id,
                    product_name,
                    quantity,
                    unit_price,
                )
            )

            order_line_id += 1

    connection.executemany(
        """
        INSERT INTO sales_orders (
            order_id, account_id, quote_id, order_date, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        orders,
    )

    connection.executemany(
        """
        INSERT INTO order_lines (
            order_line_id, order_id, quote_line_id,
            product_name, quantity, unit_price
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        order_lines,
    )

    return {
        "sales_orders": len(orders),
        "order_lines": len(order_lines),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            summary = generate_orders(connection)

    print("Sales order generation completed.")

    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()