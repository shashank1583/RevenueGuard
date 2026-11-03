import sqlite3
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = (
    PROJECT_ROOT
    / "data"
    / "output"
    / "revenueguard_evaluation.db"
)

TARGET_DISPUTE = "DSP-2026-000005"


def next_event_date(connection, entity_id):
    row = connection.execute(
        """
        SELECT MAX(event_at)
        FROM status_events
        WHERE entity_type = 'order'
          AND entity_id = ?
        """,
        (entity_id,),
    ).fetchone()

    if not row or not row[0]:
        return "2026-10-31"

    latest = date.fromisoformat(row[0][:10])
    return (latest + timedelta(days=1)).isoformat()


def inject_anomalies():
    if not DB_PATH.exists():
        raise FileNotFoundError(DB_PATH)

    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA foreign_keys = ON")

    try:
        connection.execute("BEGIN IMMEDIATE")

        # -------------------------------------------------
        # 1. Prepare RG005 baseline:
        #    Adjust all other active disputes fully.
        # -------------------------------------------------

        active_disputes = connection.execute(
            """
            SELECT dispute_id, invoice_id, amount, opened_at
            FROM disputes
            WHERE status IN ('open', 'under_review')
              AND dispute_id != ?
            ORDER BY dispute_id
            """,
            (TARGET_DISPUTE,),
        ).fetchall()

        adjustment_number = 1

        for dispute_id, invoice_id, amount, opened_at in active_disputes:

            existing = connection.execute(
                """
                SELECT COALESCE(SUM(adjusted_amount), 0)
                FROM receivable_adjustments
                WHERE dispute_id = ?
                """,
                (dispute_id,),
            ).fetchone()[0]

            difference = round(amount - existing, 2)

            if difference < 0:
                raise ValueError(
                    f"Dispute {dispute_id} is over-adjusted."
                )

            if difference > 0:
                adjustment_id = (
                    f"RA-EVAL-{adjustment_number:06d}"
                )

                connection.execute(
                    """
                    INSERT INTO receivable_adjustments (
                        adjustment_id,
                        dispute_id,
                        invoice_id,
                        adjusted_amount,
                        adjustment_date
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        adjustment_id,
                        dispute_id,
                        invoice_id,
                        difference,
                        opened_at,
                    ),
                )

                adjustment_number += 1

        # Confirm RG005 target remains unadjusted.
        target_adjustments = connection.execute(
            """
            SELECT COUNT(*)
            FROM receivable_adjustments
            WHERE dispute_id = ?
            """,
            (TARGET_DISPUTE,),
        ).fetchone()[0]

        if target_adjustments != 0:
            raise ValueError(
                "RG005 target already has an adjustment."
            )

        # -------------------------------------------------
        # 2. RG001: Invoice overbilling.
        # -------------------------------------------------

        result = connection.execute(
            """
            UPDATE invoice_lines
            SET quantity_billed = quantity_billed + 1
            WHERE invoice_id = 'INV-2026-000001'
              AND invoice_line_id = 1
              AND quantity_billed = 18
            """
        )

        if result.rowcount != 1:
            raise ValueError("RG001 precondition failed.")

        # -------------------------------------------------
        # 3. RG002: Payment overallocation.
        # -------------------------------------------------

        payment = connection.execute(
            """
            SELECT amount
            FROM payments
            WHERE payment_id = 'PAY-2026-000001'
            """
        ).fetchone()

        if not payment:
            raise ValueError("RG002 payment not found.")

        allocated = connection.execute(
            """
            SELECT COALESCE(SUM(allocated_amount), 0)
            FROM payment_allocations
            WHERE payment_id = 'PAY-2026-000001'
            """
        ).fetchone()[0]

        if round(allocated, 2) != round(payment[0], 2):
            raise ValueError(
                "RG002 payment is not in its expected baseline state."
            )

        next_allocation_id = connection.execute(
            """
            SELECT COALESCE(MAX(allocation_id), 0) + 1
            FROM payment_allocations
            """
        ).fetchone()[0]

        connection.execute(
            """
            INSERT INTO payment_allocations (
                allocation_id,
                payment_id,
                invoice_id,
                allocated_amount,
                allocated_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                next_allocation_id,
                "PAY-2026-000001",
                "INV-2026-006213",
                1.00,
                "2026-04-13",
            ),
        )

        # -------------------------------------------------
        # 4. RG003: Close an order with an unpaid invoice.
        # -------------------------------------------------

        order = connection.execute(
            """
            SELECT status
            FROM sales_orders
            WHERE order_id = 'SO-2026-000004'
            """
        ).fetchone()

        if not order or order[0] != "fulfilled":
            raise ValueError("RG003 precondition failed.")

        invoice_balance = connection.execute(
            """
            SELECT
                ROUND(SUM(il.quantity_billed * il.unit_price), 2)
                - COALESCE((
                    SELECT ROUND(SUM(pa.allocated_amount), 2)
                    FROM payment_allocations pa
                    WHERE pa.invoice_id = i.invoice_id
                ), 0)
            FROM invoices i
            JOIN invoice_lines il
              ON il.invoice_id = i.invoice_id
            WHERE i.invoice_id = 'INV-2026-000008'
            GROUP BY i.invoice_id
            """
        ).fetchone()

        if not invoice_balance or invoice_balance[0] <= 0:
            raise ValueError(
                "RG003 invoice does not have an outstanding balance."
            )

        connection.execute(
            """
            UPDATE sales_orders
            SET status = 'closed'
            WHERE order_id = 'SO-2026-000004'
              AND status = 'fulfilled'
            """
        )

        rg003_date = next_event_date(
            connection, "SO-2026-000004"
        )

        # Valid transition: fulfilled -> closed.
        next_event_id = connection.execute(
            """
            SELECT COALESCE(MAX(event_id), 0) + 1
            FROM status_events
            """
        ).fetchone()[0]

        connection.execute(
            """
            INSERT INTO status_events (
                event_id, entity_type, entity_id,
                previous_status, new_status, event_at, notes
            )
            VALUES (?, 'order', ?, 'fulfilled', 'closed', ?, ?)
            """,
            (
                next_event_id,
                "SO-2026-000004",
                rg003_date,
                "Controlled RG003 evaluation scenario",
            ),
        )

        # -------------------------------------------------
        # 5. RG004: Invalid status transition.
        # -------------------------------------------------

        order = connection.execute(
            """
            SELECT status
            FROM sales_orders
            WHERE order_id = 'SO-2026-000006'
            """
        ).fetchone()

        if not order or order[0] != "open":
            raise ValueError("RG004 precondition failed.")

        rg004_date = next_event_date(
            connection, "SO-2026-000006"
        )

        next_event_id += 1

        # Invalid transition: open -> closed.
        connection.execute(
            """
            INSERT INTO status_events (
                event_id, entity_type, entity_id,
                previous_status, new_status, event_at, notes
            )
            VALUES (?, 'order', ?, 'open', 'closed', ?, ?)
            """,
            (
                next_event_id,
                "SO-2026-000006",
                rg004_date,
                "Controlled RG004 evaluation scenario",
            ),
        )

        connection.commit()

        print("Evaluation anomalies injected successfully.")
        print(f"Database: {DB_PATH}")
        print(f"RG005 baseline disputes adjusted: {len(active_disputes)}")
        print("RG001: Invoice overbilling injected.")
        print("RG002: Payment overallocation injected.")
        print("RG003: Closed order with outstanding invoice injected.")
        print("RG004: Invalid status transition injected.")
        print("RG005: One active dispute remains without adjustment.")

    except Exception:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    inject_anomalies()