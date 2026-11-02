import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"

SEED = 20261025
PAYMENT_COUNT = 15000


def generate_payments(connection, seed=SEED):
    """Generate payments and allocate received funds to invoices."""

    rng = random.Random(seed)

    existing = connection.execute(
        "SELECT COUNT(*) FROM payments"
    ).fetchone()[0]

    if existing:
        raise RuntimeError(
            "Payments already exist. Use a fresh database "
            "before regenerating."
        )

    invoices = connection.execute(
        """
        SELECT
            i.invoice_id,
            i.account_id,
            i.invoice_date,
            i.due_date,
            ROUND(SUM(il.quantity_billed * il.unit_price) * 100)
                AS amount_cents
        FROM invoices i
        JOIN invoice_lines il
            ON il.invoice_id = i.invoice_id
        GROUP BY
            i.invoice_id,
            i.account_id,
            i.invoice_date,
            i.due_date
        ORDER BY i.invoice_id
        """
    ).fetchall()

    if not invoices:
        raise RuntimeError(
            "No invoices found. Generate invoices first."
        )

    # Store balances in cents to reduce floating-point errors.
    remaining_balances = {
        invoice_id: int(amount_cents)
        for (
            invoice_id,
            account_id,
            invoice_date,
            due_date,
            amount_cents,
        ) in invoices
    }

    invoice_details = {
        invoice_id: (
            account_id,
            date.fromisoformat(invoice_date),
            date.fromisoformat(due_date),
        )
        for (
            invoice_id,
            account_id,
            invoice_date,
            due_date,
            amount_cents,
        ) in invoices
    }

    account_ids = [
        row[0]
        for row in connection.execute(
            "SELECT account_id FROM accounts ORDER BY account_id"
        )
    ]

    payments = []
    allocations = []

    allocation_id = 1

    # Use a mix of received, pending, failed, and refunded payments.
    statuses = (
        ["received"] * 10500
        + ["pending"] * 2250
        + ["failed"] * 1500
        + ["refunded"] * 750
    )
    rng.shuffle(statuses)

    for index in range(1, PAYMENT_COUNT + 1):
        payment_id = f"PAY-2026-{index:06d}"
        status = statuses[index - 1]

        eligible_invoice_ids = [
            invoice_id
            for invoice_id, balance in remaining_balances.items()
            if balance > 0
        ]

        # Prefer an invoice with an outstanding balance for
        # received payments.
        if status == "received" and eligible_invoice_ids:
            invoice_id = rng.choice(eligible_invoice_ids)
            account_id, invoice_date, due_date = (
                invoice_details[invoice_id]
            )

            balance_cents = remaining_balances[invoice_id]

            # Allocate between 20% and 100% of the remaining balance.
            fraction = rng.randint(20, 100)
            allocation_cents = max(
                1,
                balance_cents * fraction // 100,
            )
            allocation_cents = min(
                allocation_cents,
                balance_cents,
            )

            payment_amount = allocation_cents / 100

            payment_date = invoice_date + timedelta(
                days=rng.randint(0, 90)
            )

            payments.append(
                (
                    payment_id,
                    account_id,
                    payment_date.isoformat(),
                    payment_amount,
                    status,
                )
            )

            allocations.append(
                (
                    allocation_id,
                    payment_id,
                    invoice_id,
                    payment_amount,
                    payment_date.isoformat(),
                )
            )

            allocation_id += 1
            remaining_balances[invoice_id] -= allocation_cents

        else:
            # Pending, failed, and refunded payments are not
            # allocated in this baseline dataset.
            account_id = rng.choice(account_ids)

            payment_date = date(2026, 1, 1) + timedelta(
                days=rng.randint(0, 300)
            )

            amount = rng.randint(1000, 500000) / 100

            payments.append(
                (
                    payment_id,
                    account_id,
                    payment_date.isoformat(),
                    amount,
                    status,
                )
            )

    connection.executemany(
        """
        INSERT INTO payments (
            payment_id, account_id, payment_date,
            amount, status
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        payments,
    )

    connection.executemany(
        """
        INSERT INTO payment_allocations (
            allocation_id, payment_id, invoice_id,
            allocated_amount, allocated_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        allocations,
    )

    return {
        "payments": len(payments),
        "payment_allocations": len(allocations),
        "received_payments": statuses.count("received"),
        "unallocated_payments": (
            len(payments) - len(allocations)
        ),
    }


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH}"
        )

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        with connection:
            summary = generate_payments(connection)

    print("Payment generation completed.")

    for name, count in summary.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()