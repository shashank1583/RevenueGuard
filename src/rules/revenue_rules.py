import sqlite3


def detect_invoice_overbilling(connection):
    """RG001: Find invoice quantities exceeding shipped quantities."""

    query = """
        SELECT
            i.invoice_id,
            il.invoice_line_id,
            il.order_line_id,
            il.quantity_billed,
            COALESCE(shipped.shipped_quantity, 0) AS shipped_quantity
        FROM invoices i
        JOIN invoice_lines il
            ON il.invoice_id = i.invoice_id
        LEFT JOIN (
            SELECT
                sl.order_line_id,
                SUM(sl.quantity_shipped) AS shipped_quantity
            FROM shipment_lines sl
            JOIN shipments s
                ON s.shipment_id = sl.shipment_id
            WHERE s.status IN ('shipped', 'delivered')
            GROUP BY sl.order_line_id
        ) shipped
            ON shipped.order_line_id = il.order_line_id
        WHERE il.quantity_billed >
            COALESCE(shipped.shipped_quantity, 0)
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "rule_id": "RG001",
            "entity_type": "invoice",
            "entity_id": row[0],
            "description": "Invoice quantity exceeds shipped quantity",
            "details": {
                "invoice_line_id": row[1],
                "order_line_id": row[2],
                "quantity_billed": row[3],
                "shipped_quantity": row[4],
            },
        }
        for row in rows
    ]


def detect_payment_overallocation(connection):
    """RG002: Find payments allocated beyond their recorded amount."""

    query = """
        SELECT
            p.payment_id,
            p.amount,
            COALESCE(SUM(pa.allocated_amount), 0) AS allocated_amount
        FROM payments p
        LEFT JOIN payment_allocations pa
            ON pa.payment_id = p.payment_id
        GROUP BY p.payment_id, p.amount
        HAVING COALESCE(SUM(pa.allocated_amount), 0) > p.amount
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "rule_id": "RG002",
            "entity_type": "payment",
            "entity_id": row[0],
            "description": "Payment allocations exceed payment amount",
            "details": {
                "payment_amount": row[1],
                "allocated_amount": row[2],
            },
        }
        for row in rows
    ]


def detect_closed_orders_with_unpaid_invoices(connection):
    """RG003: Find closed orders with outstanding invoice balances."""

    query = """
        SELECT
            so.order_id,
            i.invoice_id,
            i.status,
            ROUND(
                SUM(il.quantity_billed * il.unit_price), 2
            ) AS invoice_amount,
            ROUND(
                COALESCE(allocated.allocated_amount, 0), 2
            ) AS allocated_amount
        FROM sales_orders so
        JOIN order_lines ol
            ON ol.order_id = so.order_id
        JOIN invoice_lines il
            ON il.order_line_id = ol.order_line_id
        JOIN invoices i
            ON i.invoice_id = il.invoice_id
        LEFT JOIN (
            SELECT
                invoice_id,
                SUM(allocated_amount) AS allocated_amount
            FROM payment_allocations
            GROUP BY invoice_id
        ) allocated
            ON allocated.invoice_id = i.invoice_id
        WHERE so.status = 'closed'
        GROUP BY
            so.order_id,
            i.invoice_id,
            i.status,
            allocated.allocated_amount
        HAVING
            SUM(il.quantity_billed * il.unit_price)
            > COALESCE(allocated.allocated_amount, 0)
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "rule_id": "RG003",
            "entity_type": "order",
            "entity_id": row[0],
            "description": (
                "Closed order has an invoice with an outstanding balance"
            ),
            "details": {
                "invoice_id": row[1],
                "invoice_status": row[2],
                "invoice_amount": row[3],
                "allocated_amount": row[4],
                "outstanding_amount": round(row[3] - row[4], 2),
            },
        }
        for row in rows
    ]


def detect_invalid_status_transitions(connection):
    """RG004: Find status transitions outside the allowed workflow."""

    allowed_transitions = {
        "quote": {
            ("draft", "sent"),
            ("sent", "accepted"),
            ("sent", "rejected"),
            ("sent", "expired"),
        },
        "order": {
            ("open", "processing"),
            ("processing", "fulfilled"),
            ("fulfilled", "closed"),
            ("open", "cancelled"),
            ("processing", "cancelled"),
        },
        "shipment": {
            ("shipped", "delivered"),
        },
        "invoice": {
            ("draft", "issued"),
            ("issued", "paid"),
            ("issued", "void"),
        },
        "payment": {
            ("pending", "received"),
            ("pending", "failed"),
            ("received", "refunded"),
        },
        "dispute": {
            ("open", "under_review"),
            ("open", "resolved"),
            ("open", "rejected"),
            ("under_review", "resolved"),
            ("under_review", "rejected"),
        },
    }

    query = """
        SELECT
            event_id,
            entity_type,
            entity_id,
            previous_status,
            new_status
        FROM status_events
        WHERE previous_status IS NOT NULL
        ORDER BY event_id
    """

    findings = []

    for event_id, entity_type, entity_id, previous, new in (
        connection.execute(query).fetchall()
    ):
        permitted = allowed_transitions.get(entity_type, set())

        if (previous, new) not in permitted:
            findings.append(
                {
                    "rule_id": "RG004",
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "description": (
                        "Status transition is not in the allowed transition map"
                    ),
                    "details": {
                        "event_id": event_id,
                        "previous_status": previous,
                        "new_status": new,
                    },
                }
            )

    return findings


def detect_open_disputes(connection):
    """RG005: Find open disputes requiring receivables review."""

    query = """
        SELECT
            d.dispute_id,
            d.invoice_id,
            d.amount,
            d.status,
            i.status
        FROM disputes d
        JOIN invoices i
            ON i.invoice_id = d.invoice_id
        WHERE d.status IN ('open', 'under_review')
    """

    rows = connection.execute(query).fetchall()

    return [
        {
            "rule_id": "RG005",
            "entity_type": "invoice",
            "entity_id": row[1],
            "description": (
                "Invoice has an open or under-review dispute "
                "requiring receivables review"
            ),
            "details": {
                "dispute_id": row[0],
                "disputed_amount": row[2],
                "dispute_status": row[3],
                "invoice_status": row[4],
            },
        }
        for row in rows
    ]


def run_all_rules(connection):
    """Execute all RevenueGuard detection rules."""

    detectors = [
        detect_invoice_overbilling,
        detect_payment_overallocation,
        detect_closed_orders_with_unpaid_invoices,
        detect_invalid_status_transitions,
        detect_open_disputes,
    ]

    findings = []

    for detector in detectors:
        findings.extend(detector(connection))

    return findings