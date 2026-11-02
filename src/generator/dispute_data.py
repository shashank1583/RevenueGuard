import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

SEED = 20261026
DISPUTE_COUNT = 1000


def generate_disputes(connection, seed=SEED):
    """Generate invoice disputes and their status-event history."""

    rng = random.Random(seed)

    existing = connection.execute(
        "SELECT COUNT(*) FROM disputes"
    ).fetchone()[0]

    if existing:
        raise RuntimeError(
            "Disputes already exist. Use a fresh database "
            "before regenerating."
        )

    invoices = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.invoice_date,
            ROUND(SUM(il.quantity_billed * il.unit_price) * 100)
                AS amount_cents
        FROM invoices i
        JOIN invoice_lines il
            ON il.invoice_id = i.invoice_id
        GROUP BY i.invoice_id, i.invoice_date
        ORDER BY i.invoice_id
        """
    ).fetchall()

    if len(invoices) < DISPUTE_COUNT:
        raise ValueError(
            f"Need {DISPUTE_COUNT} invoices, "
            f"but found {len(invoices)}."
        )

    selected_invoices = rng.sample(invoices, DISPUTE_COUNT)

    statuses = (
        ["open"] * 400
        + ["under_review"] * 250
        + ["resolved"] * 250
        + ["rejected"] * 100
    )
    rng.shuffle(statuses)

    disputes = []
    event_rows = []

    event_id = 1

    for index, (invoice_id, invoice_date_text, amount_cents) in enumerate(
        selected_invoices, start=1
    ):
        dispute_id = f"DSP-2026-{index:06d}"

        invoice_date = date.fromisoformat(invoice_date_text)
        opened_at = invoice_date + timedelta(
            days=rng.randint(1, 45)
        )

        status = statuses[index - 1]

        disputed_cents = rng.randint(
            1, max(1, int(amount_cents))
        )
        disputed_amount = disputed_cents / 100

        if status in ("resolved", "rejected"):
            resolved_at = (
                opened_at + timedelta(days=rng.randint(1, 30))
            ).isoformat()
        else:
            resolved_at = None

        disputes.append(
            (
                dispute_id,
                invoice_id,
                opened_at.isoformat(),
                resolved_at,
                disputed_amount,
                status,
            )
        )

        # Record dispute creation.
        event_rows.append(
            (
                event_id,
                "dispute",
                dispute_id,
                None,
                "open",
                opened_at.isoformat(),
                "Dispute opened",
            )
        )
        event_id += 1

        # Record a later status transition when applicable.
        if status != "open":
            event_date = (
                date.fromisoformat(resolved_at)
                if resolved_at
                else opened_at + timedelta(
                    days=rng.randint(1, 15)
                )
            )

            event_rows.append(
                (
                    event_id,
                    "dispute",
                    dispute_id,
                    "open",
                    status,
                    event_date.isoformat(),
                    "Dispute status updated",
                )
            )
            event_id += 1

    connection.executemany(
        """
        INSERT INTO disputes (
            dispute_id, invoice_id, opened_at,
            resolved_at, amount, status
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        disputes,
    )

    # Record a baseline event for each existing business entity.
    entity_queries = [
        (
            "quote",
            """
            SELECT quote_id, status, quote_date
            FROM quotes
            """,
        ),
        (
            "order",
            """
            SELECT order_id, status, order_date
            FROM sales_orders
            """,
        ),
        (
            "shipment",
            """
            SELECT shipment_id, status, shipment_date
            FROM shipments
            """,
        ),
        (
            "invoice",
            """
            SELECT invoice_id, status, invoice_date
            FROM invoices
            """,
        ),
        (
            "payment",
            """
            SELECT payment_id, status, payment_date
            FROM payments
            """,
        ),
    ]

    for entity_type, query in entity_queries:
        records = connection.execute(query).fetchall()

        for entity_id, current_status, event_date in records:
            event_rows.append(
                (
                    event_id,
                    entity_type,
                    entity_id,
                    None,
                    current_status,
                    event_date,
                    "Initial status recorded",
                )
            )
            event_id += 1

    connection.executemany(
        """
        INSERT INTO status_events (
            event_id, entity_type, entity_id,
            previous_status, new_status, event_at, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        event_rows,
    )

    return {
        "disputes": len(disputes),
        "status_events": len(event_rows),
        "open_disputes": statuses.count("open"),
        "under_review_disputes": statuses.count("under_review"),
        "resolved_disputes": statuses.count("resolved"),
        "rejected_disputes": statuses.count("rejected"),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            summary = generate_disputes(connection)

    print("Dispute and event generation completed.")

    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()