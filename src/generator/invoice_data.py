import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

INVOICE_COUNT = 8000


def generate_invoices(connection):
    """Generate invoices from fulfilled order-line quantities."""

    existing = connection.execute(
        "SELECT COUNT(*) FROM invoices"
    ).fetchone()[0]

    if existing:
        raise RuntimeError(
            "Invoices already exist. Use a fresh database "
            "before regenerating."
        )

    # Aggregate actual shipped quantities and find the latest
    # shipment date for each order line.
    fulfilled_lines = connection.execute(
        """
        SELECT
            o.order_id,
            o.account_id,
            ol.order_line_id,
            ol.unit_price,
            SUM(sl.quantity_shipped) AS fulfilled_quantity,
            MAX(s.shipment_date) AS last_shipment_date
        FROM sales_orders o
        JOIN order_lines ol
            ON ol.order_id = o.order_id
        JOIN shipment_lines sl
            ON sl.order_line_id = ol.order_line_id
        JOIN shipments s
            ON s.shipment_id = sl.shipment_id
        WHERE o.status IN ('fulfilled', 'closed')
            AND s.status IN ('shipped', 'delivered')
        GROUP BY
            o.order_id,
            o.account_id,
            ol.order_line_id,
            ol.unit_price
        HAVING SUM(sl.quantity_shipped) > 0
        ORDER BY o.order_id, ol.order_line_id
        """
    ).fetchall()

    if len(fulfilled_lines) < INVOICE_COUNT:
        raise ValueError(
            f"Need {INVOICE_COUNT} fulfilled order lines, "
            f"but found {len(fulfilled_lines)}. "
            "Review shipment generation."
        )

    invoices = []
    invoice_lines = []

    for index, row in enumerate(
        fulfilled_lines[:INVOICE_COUNT], start=1
    ):
        (
            order_id,
            account_id,
            order_line_id,
            unit_price,
            fulfilled_quantity,
            last_shipment_date,
        ) = row

        invoice_id = f"INV-2026-{index:06d}"

        shipment_date = date.fromisoformat(last_shipment_date)
        invoice_date = shipment_date + timedelta(days=1)
        due_date = invoice_date + timedelta(days=30)

        invoices.append(
            (
                invoice_id,
                account_id,
                order_id,
                invoice_date.isoformat(),
                due_date.isoformat(),
                "issued",
            )
        )

        invoice_lines.append(
            (
                index,
                invoice_id,
                order_line_id,
                int(fulfilled_quantity),
                float(unit_price),
            )
        )

    connection.executemany(
        """
        INSERT INTO invoices (
            invoice_id, account_id, order_id,
            invoice_date, due_date, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        invoices,
    )

    connection.executemany(
        """
        INSERT INTO invoice_lines (
            invoice_line_id, invoice_id,
            order_line_id, quantity_billed, unit_price
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        invoice_lines,
    )

    return {
        "invoices": len(invoices),
        "invoice_lines": len(invoice_lines),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            summary = generate_invoices(connection)

    print("Invoice generation completed.")

    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()