import sqlite3

import pytest

from src.rules.revenue_rules import (
    detect_invoice_overbilling,
    detect_payment_overallocation,
    detect_closed_orders_with_unpaid_invoices,
    detect_invalid_status_transitions,
    detect_open_disputes,
)


@pytest.fixture
def connection():
    """Create an isolated in-memory database for rule tests."""

    conn = sqlite3.connect(":memory:")

    conn.executescript(
        """
        CREATE TABLE invoices (
            invoice_id TEXT PRIMARY KEY,
            status TEXT,
            invoice_date TEXT
        );

        CREATE TABLE invoice_lines (
            invoice_line_id INTEGER PRIMARY KEY,
            invoice_id TEXT,
            order_line_id INTEGER,
            quantity_billed INTEGER,
            unit_price REAL
        );

        CREATE TABLE shipments (
            shipment_id TEXT PRIMARY KEY,
            status TEXT
        );

        CREATE TABLE shipment_lines (
            shipment_line_id INTEGER PRIMARY KEY,
            shipment_id TEXT,
            order_line_id INTEGER,
            quantity_shipped INTEGER
        );

        CREATE TABLE payments (
            payment_id TEXT PRIMARY KEY,
            amount REAL
        );

        CREATE TABLE payment_allocations (
            allocation_id INTEGER PRIMARY KEY,
            payment_id TEXT,
            invoice_id TEXT,
            allocated_amount REAL
        );

        CREATE TABLE status_events (
            event_id INTEGER PRIMARY KEY,
            entity_type TEXT,
            entity_id TEXT,
            previous_status TEXT,
            new_status TEXT,
            event_at TEXT,
            notes TEXT
        );

        CREATE TABLE sales_orders (
            order_id TEXT PRIMARY KEY,
            status TEXT
        );

        CREATE TABLE order_lines (
            order_line_id INTEGER PRIMARY KEY,
            order_id TEXT
        );

        CREATE TABLE disputes (
            dispute_id TEXT PRIMARY KEY,
            invoice_id TEXT,
            amount REAL,
            status TEXT
        );

        INSERT INTO invoices VALUES
            ('INV-TEST-001', 'issued', '2026-01-01');

        INSERT INTO invoice_lines VALUES
            (1, 'INV-TEST-001', 101, 5, 100.0);

        INSERT INTO shipments VALUES
            ('SHP-TEST-001', 'delivered');

        INSERT INTO shipment_lines VALUES
            (1, 'SHP-TEST-001', 101, 3);

        INSERT INTO payments VALUES
            ('PAY-TEST-001', 100.0);

        INSERT INTO payment_allocations VALUES
            (1, 'PAY-TEST-001', 'INV-TEST-001', 120.0);

        INSERT INTO status_events VALUES
            (1, 'order', 'SO-TEST-001',
             'open', 'closed', '2026-01-01',
             'Test invalid transition');

        INSERT INTO sales_orders VALUES
            ('SO-TEST-002', 'closed');

        INSERT INTO order_lines VALUES
            (102, 'SO-TEST-002');

        INSERT INTO invoice_lines VALUES
            (2, 'INV-TEST-001', 102, 2, 100.0);

        INSERT INTO disputes VALUES
            ('DSP-TEST-001', 'INV-TEST-001', 75.0, 'open');
        """
    )

    yield conn
    conn.close()


def test_detects_invoice_overbilling(connection):
    """RG001: Detect invoice quantities exceeding shipped quantities."""

    findings = detect_invoice_overbilling(connection)

    assert any(
        finding["rule_id"] == "RG001"
        and finding["entity_id"] == "INV-TEST-001"
        for finding in findings
    )


def test_detects_payment_overallocation(connection):
    """RG002: Detect payment allocations exceeding the payment amount."""

    findings = detect_payment_overallocation(connection)

    assert any(
        finding["rule_id"] == "RG002"
        and finding["entity_id"] == "PAY-TEST-001"
        for finding in findings
    )


def test_detects_closed_orders_with_unpaid_invoices(connection):
    """RG003: Detect closed orders with outstanding invoice balances."""

    connection.execute(
        """
        INSERT INTO payment_allocations
            (allocation_id, payment_id, invoice_id, allocated_amount)
        VALUES (2, 'PAY-TEST-001', 'INV-TEST-001', 0.0)
        """
    )

    findings = detect_closed_orders_with_unpaid_invoices(connection)

    matching_findings = [
        finding
        for finding in findings
        if finding["rule_id"] == "RG003"
        and finding["entity_id"] == "SO-TEST-002"
    ]

    assert matching_findings, (
        "Expected RG003 to flag the closed order with an unpaid invoice."
    )

    assert matching_findings[0]["details"]["outstanding_amount"] == 80.0

def test_detects_invalid_status_transition(connection):
    """RG004: Detect status transitions outside the allowed workflow."""

    findings = detect_invalid_status_transitions(connection)

    assert any(
        finding["rule_id"] == "RG004"
        and finding["entity_id"] == "SO-TEST-001"
        for finding in findings
    )


def test_detects_open_disputes(connection):
    """RG005: Detect open disputes requiring receivables review."""

    findings = detect_open_disputes(connection)

    assert any(
        finding["rule_id"] == "RG005"
        and finding["entity_id"] == "INV-TEST-001"
        and finding["details"]["dispute_status"] == "open"
        for finding in findings
    )