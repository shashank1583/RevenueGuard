import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DB_PATH = (
    PROJECT_ROOT / "data" / "output" / "revenueguard_evaluation.db"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "output" / "reconciliation_report.json"
)

EXPECTED_INVOICE_ANOMALY = "INV-2026-000001"
EXPECTED_PAYMENT_ANOMALY = "PAY-2026-000001"


def reconcile_data():

    connection = sqlite3.connect(DB_PATH)

    try:
        # 1. Check shipped quantities against ordered quantities.
        shipment_violations = connection.execute(
            """
            SELECT
                ol.order_line_id,
                ol.quantity AS ordered_quantity,
                COALESCE(SUM(
                    CASE
                        WHEN s.status IN ('shipped', 'delivered')
                        THEN sl.quantity_shipped
                        ELSE 0
                    END
                ), 0) AS shipped_quantity
            FROM order_lines ol
            LEFT JOIN shipment_lines sl
                ON sl.order_line_id = ol.order_line_id
            LEFT JOIN shipments s
                ON s.shipment_id = sl.shipment_id
            GROUP BY ol.order_line_id, ol.quantity
            HAVING shipped_quantity > ordered_quantity
            """
        ).fetchall()

        # 2. Check invoice quantities against shipped quantities.
        invoice_violations = connection.execute(
            """
            SELECT
                i.invoice_id,
                il.invoice_line_id,
                il.order_line_id,
                il.quantity_billed,
                COALESCE((
                    SELECT SUM(sl.quantity_shipped)
                    FROM shipment_lines sl
                    JOIN shipments s
                        ON s.shipment_id = sl.shipment_id
                    WHERE sl.order_line_id = il.order_line_id
                      AND s.status IN ('shipped', 'delivered')
                ), 0) AS shipped_quantity
            FROM invoices i
            JOIN invoice_lines il
                ON il.invoice_id = i.invoice_id
            WHERE il.quantity_billed > COALESCE((
                SELECT SUM(sl.quantity_shipped)
                FROM shipment_lines sl
                JOIN shipments s
                    ON s.shipment_id = sl.shipment_id
                WHERE sl.order_line_id = il.order_line_id
                  AND s.status IN ('shipped', 'delivered')
            ), 0)
            """
        ).fetchall()

        # 3. Check payment allocations against payment amounts.
        payment_violations = connection.execute(
            """
            SELECT
                p.payment_id,
                p.amount,
                SUM(pa.allocated_amount) AS allocated_amount
            FROM payments p
            JOIN payment_allocations pa
                ON pa.payment_id = p.payment_id
            GROUP BY p.payment_id, p.amount
            HAVING SUM(pa.allocated_amount) > p.amount
            """
        ).fetchall()

        expected_invoice_violations = [
            row for row in invoice_violations
            if row[0] == EXPECTED_INVOICE_ANOMALY
        ]

        unexpected_invoice_violations = [
            row for row in invoice_violations
            if row[0] != EXPECTED_INVOICE_ANOMALY
        ]

        expected_payment_violations = [
            row for row in payment_violations
            if row[0] == EXPECTED_PAYMENT_ANOMALY
        ]

        unexpected_payment_violations = [
            row for row in payment_violations
            if row[0] != EXPECTED_PAYMENT_ANOMALY
        ]

        checks = {
            "shipment_quantity": {
                "total_violations": len(shipment_violations),
                "unexpected_violations": len(shipment_violations),
                "status": (
                    "PASS" if not shipment_violations else "FAIL"
                ),
            },
            "invoice_quantity": {
                "total_violations": len(invoice_violations),
                "expected_test_violations": len(
                    expected_invoice_violations
                ),
                "unexpected_violations": len(
                    unexpected_invoice_violations
                ),
                "status": (
                    "PASS"
                    if len(expected_invoice_violations) == 1
                    and not unexpected_invoice_violations
                    else "FAIL"
                ),
            },
            "payment_allocation": {
                "total_violations": len(payment_violations),
                "expected_test_violations": len(
                    expected_payment_violations
                ),
                "unexpected_violations": len(
                    unexpected_payment_violations
                ),
                "status": (
                    "PASS"
                    if len(expected_payment_violations) == 1
                    and not unexpected_payment_violations
                    else "FAIL"
                ),
            },
        }

        overall_status = (
            "PASS"
            if all(
                check["status"] == "PASS"
                for check in checks.values()
            )
            else "FAIL"
        )

        report = {
            "database": str(DB_PATH),
            "checks": checks,
            "overall_status": overall_status,
        }

        OUTPUT_PATH.write_text(
            json.dumps(report, indent=4),
            encoding="utf-8",
        )

        print("\n--- DATA RECONCILIATION REPORT ---")

        for name, result in checks.items():
            print(f"\n{name}:")
            print(f"Status: {result['status']}")
            print(
                f"Total violations: "
                f"{result['total_violations']}"
            )
            print(
                f"Unexpected violations: "
                f"{result['unexpected_violations']}"
            )

        print(f"\nOverall status: {overall_status}")
        print(f"Report saved: {OUTPUT_PATH}")

    finally:
        connection.close()


if __name__ == "__main__":
    reconcile_data()