import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

SEED = 20261024


def generate_shipments(connection, seed=SEED):
    """Generate shipments for eligible sales orders."""

    rng = random.Random(seed)

    existing = connection.execute(
        "SELECT COUNT(*) FROM shipments"
    ).fetchone()[0]

    if existing:
        raise RuntimeError(
            "Shipments already exist. "
            "Use a fresh database before regenerating."
        )

    orders = connection.execute(
        """
        SELECT order_id, order_date, status
        FROM sales_orders
        WHERE status IN ('processing', 'fulfilled', 'closed')
        ORDER BY order_id
        """
    ).fetchall()

    shipments = []
    shipment_lines = []

    shipment_counter = 1
    shipment_line_counter = 1

    for order_id, order_date_text, order_status in orders:
        order_date = date.fromisoformat(order_date_text)

        order_lines = connection.execute(
            """
            SELECT order_line_id, quantity
            FROM order_lines
            WHERE order_id = ?
            ORDER BY order_line_id
            """,
            (order_id,),
        ).fetchall()

        # Create one or two shipment batches for each eligible order.
        for order_line_id, ordered_quantity in order_lines:
            if order_status == "processing":
                # Some processing orders are only partially shipped.
                shipped_quantity = rng.randint(
                    0, ordered_quantity
                )
            else:
                shipped_quantity = ordered_quantity

            if shipped_quantity == 0:
                continue

            # Split some quantities across multiple shipment records.
            if shipped_quantity > 1 and rng.random() < 0.25:
                first_quantity = rng.randint(
                    1, shipped_quantity - 1
                )
                quantities = [
                    first_quantity,
                    shipped_quantity - first_quantity,
                ]
            else:
                quantities = [shipped_quantity]

            for quantity in quantities:
                shipment_id = f"SHP-2026-{shipment_counter:06d}"

                shipment_date = order_date + timedelta(
                    days=rng.randint(1, 20)
                )

                shipment_status = (
                    "delivered"
                    if order_status in ("fulfilled", "closed")
                    else "shipped"
                )

                shipments.append(
                    (
                        shipment_id,
                        order_id,
                        shipment_date.isoformat(),
                        shipment_status,
                    )
                )

                shipment_lines.append(
                    (
                        shipment_line_counter,
                        shipment_id,
                        order_line_id,
                        quantity,
                    )
                )

                shipment_counter += 1
                shipment_line_counter += 1

    connection.executemany(
        """
        INSERT INTO shipments (
            shipment_id, order_id, shipment_date, status
        )
        VALUES (?, ?, ?, ?)
        """,
        shipments,
    )

    connection.executemany(
        """
        INSERT INTO shipment_lines (
            shipment_line_id, shipment_id,
            order_line_id, quantity_shipped
        )
        VALUES (?, ?, ?, ?)
        """,
        shipment_lines,
    )

    return {
        "eligible_orders": len(orders),
        "shipments": len(shipments),
        "shipment_lines": len(shipment_lines),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            summary = generate_shipments(connection)

    print("Shipment generation completed.")

    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()