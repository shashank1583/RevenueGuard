import shutil
import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.rules.revenue_rules import run_all_rules


SOURCE_DB = PROJECT_ROOT / "data" / "output" / "revenueguard.db"
TEST_DB = PROJECT_ROOT / "data" / "output" / "revenueguard_test.db"


def main():
    if not SOURCE_DB.exists():
        raise FileNotFoundError(f"Database not found: {SOURCE_DB}")

    # Close any previous test run before replacing the test database.
    if TEST_DB.exists():
        try:
            TEST_DB.unlink()
        except PermissionError as exc:
            raise RuntimeError(
                "The test database is locked. Stop other Python processes "
                "using it, then rerun this script."
            ) from exc

    shutil.copy2(SOURCE_DB, TEST_DB)

    try:
        with sqlite3.connect(TEST_DB) as connection:
            connection.execute("PRAGMA foreign_keys = ON")

            # Test RG001: invoice quantity exceeds shipped quantity.
            row = connection.execute(
                """
                SELECT
                    il.invoice_line_id,
                    COALESCE(SUM(
                        CASE
                            WHEN s.status IN ('shipped', 'delivered')
                            THEN sl.quantity_shipped
                            ELSE 0
                        END
                    ), 0)
                FROM invoice_lines il
                LEFT JOIN shipment_lines sl
                    ON sl.order_line_id = il.order_line_id
                LEFT JOIN shipments s
                    ON s.shipment_id = sl.shipment_id
                GROUP BY il.invoice_line_id
                LIMIT 1
                """
            ).fetchone()

            if row is None:
                raise RuntimeError("No invoice line available for testing.")

            invoice_line_id, shipped_quantity = row

            connection.execute(
                """
                UPDATE invoice_lines
                SET quantity_billed = ?
                WHERE invoice_line_id = ?
                """,
                (shipped_quantity + 1, invoice_line_id),
            )

            # Test RG002: payment allocations exceed payment amount.
            payment = connection.execute(
                """
                SELECT payment_id, amount
                FROM payments
                ORDER BY payment_id
                LIMIT 1
                """
            ).fetchone()

            invoice = connection.execute(
                """
                SELECT invoice_id
                FROM invoices
                ORDER BY invoice_id
                LIMIT 1
                """
            ).fetchone()

            if payment is None or invoice is None:
                raise RuntimeError("A payment and invoice are required.")

            payment_id, payment_amount = payment

            current_allocations = connection.execute(
                """
                SELECT COALESCE(SUM(allocated_amount), 0)
                FROM payment_allocations
                WHERE payment_id = ?
                """,
                (payment_id,),
            ).fetchone()[0]

            extra_amount = max(
                1.0,
                payment_amount - current_allocations + 1.0,
            )

            connection.execute(
                """
                INSERT INTO payment_allocations (
                    payment_id, invoice_id, allocated_amount, allocated_at
                )
                VALUES (?, ?, ?, DATE('now'))
                """,
                (payment_id, invoice[0], extra_amount),
            )

            # Test RG004: invalid order transition.
            order = connection.execute(
                """
                SELECT order_id
                FROM sales_orders
                ORDER BY order_id
                LIMIT 1
                """
            ).fetchone()

            if order is None:
                raise RuntimeError("No order available for testing.")

            connection.execute(
                """
                INSERT INTO status_events (
                    entity_type, entity_id, previous_status,
                    new_status, event_at, notes
                )
                VALUES (?, ?, ?, ?, DATE('now'), ?)
                """,
                (
                    "order",
                    order[0],
                    "open",
                    "closed",
                    "Controlled test: invalid transition",
                ),
            )

            connection.commit()

            findings = run_all_rules(connection)
            detected_rules = {
                finding["rule_id"] for finding in findings
            }

            expected_rules = {"RG001", "RG002", "RG004"}

            print("Controlled anomaly test results")
            print("--------------------------------")

            for rule_id in sorted(expected_rules):
                if rule_id in detected_rules:
                    print(f"PASS: {rule_id} detected the test anomaly")
                else:
                    print(f"FAIL: {rule_id} did not detect the test anomaly")

            failed = expected_rules - detected_rules
            print(f"\nTotal findings in test database: {len(findings)}")

            if failed:
                raise AssertionError(
                    f"Detection failed for rules: {sorted(failed)}"
                )

            print("All three controlled anomaly tests passed.")

    finally:
        # The database connection is closed before cleanup.
        # Keep the test database if Windows still holds a file lock.
        try:
            if TEST_DB.exists():
                TEST_DB.unlink()
        except PermissionError:
            print(
                f"Note: Test database could not be deleted automatically: "
                f"{TEST_DB}"
            )
            print("You can delete it manually after closing processes using it.")


if __name__ == "__main__":
    main()