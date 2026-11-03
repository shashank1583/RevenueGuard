PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    account_id TEXT PRIMARY KEY,
    account_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS quotes (
    quote_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    quote_date TEXT NOT NULL,
    expiry_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'sent', 'accepted', 'rejected', 'expired')
    ),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CHECK (expiry_date >= quote_date)
);

CREATE TABLE IF NOT EXISTS quote_lines (
    quote_line_id INTEGER PRIMARY KEY,
    quote_id TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id)
);

CREATE TABLE IF NOT EXISTS sales_orders (
    order_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    quote_id TEXT UNIQUE,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('open', 'processing', 'fulfilled', 'closed', 'cancelled')
    ),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (quote_id) REFERENCES quotes(quote_id)
);

CREATE TABLE IF NOT EXISTS order_lines (
    order_line_id INTEGER PRIMARY KEY,
    order_id TEXT NOT NULL,
    quote_line_id INTEGER,
    product_name TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id) REFERENCES sales_orders(order_id),
    FOREIGN KEY (quote_line_id) REFERENCES quote_lines(quote_line_id)
);

CREATE TABLE IF NOT EXISTS shipments (
    shipment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    shipment_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'shipped', 'delivered', 'cancelled')
    ),
    FOREIGN KEY (order_id) REFERENCES sales_orders(order_id)
);

CREATE TABLE IF NOT EXISTS shipment_lines (
    shipment_line_id INTEGER PRIMARY KEY,
    shipment_id TEXT NOT NULL,
    order_line_id INTEGER NOT NULL,
    quantity_shipped INTEGER NOT NULL CHECK (quantity_shipped > 0),
    FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id),
    FOREIGN KEY (order_line_id) REFERENCES order_lines(order_line_id)
);

CREATE TABLE IF NOT EXISTS invoices (
    invoice_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    order_id TEXT NOT NULL,
    invoice_date TEXT NOT NULL,
    due_date TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('draft', 'issued', 'partially_paid', 'paid', 'disputed', 'void')
    ),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    FOREIGN KEY (order_id) REFERENCES sales_orders(order_id),
    CHECK (due_date >= invoice_date)
);

CREATE TABLE IF NOT EXISTS invoice_lines (
    invoice_line_id INTEGER PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    order_line_id INTEGER NOT NULL,
    quantity_billed INTEGER NOT NULL CHECK (quantity_billed > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    FOREIGN KEY (order_line_id) REFERENCES order_lines(order_line_id)
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    payment_date TEXT NOT NULL,
    amount REAL NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL CHECK (
        status IN ('received', 'pending', 'failed', 'refunded')
    ),
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

CREATE TABLE IF NOT EXISTS payment_allocations (
    allocation_id INTEGER PRIMARY KEY,
    payment_id TEXT NOT NULL,
    invoice_id TEXT NOT NULL,
    allocated_amount REAL NOT NULL CHECK (allocated_amount > 0),
    allocated_at TEXT NOT NULL,
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

CREATE TABLE IF NOT EXISTS disputes (
    dispute_id TEXT PRIMARY KEY,
    invoice_id TEXT NOT NULL,
    opened_at TEXT NOT NULL,
    resolved_at TEXT,
    amount REAL NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL CHECK (
        status IN ('open', 'under_review', 'resolved', 'rejected')
    ),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    CHECK (resolved_at IS NULL OR resolved_at >= opened_at)
);

CREATE TABLE IF NOT EXISTS receivable_adjustments (
    adjustment_id TEXT PRIMARY KEY,
    dispute_id TEXT NOT NULL UNIQUE,
    invoice_id TEXT NOT NULL,
    adjusted_amount REAL NOT NULL CHECK (adjusted_amount > 0),
    adjustment_date TEXT NOT NULL,

    FOREIGN KEY (dispute_id) REFERENCES disputes(dispute_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

CREATE TABLE IF NOT EXISTS status_events (
    event_id INTEGER PRIMARY KEY,
    entity_type TEXT NOT NULL CHECK (
        entity_type IN (
            'quote', 'order', 'shipment',
            'invoice', 'payment', 'dispute'
        )
    ),
    entity_id TEXT NOT NULL,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    event_at TEXT NOT NULL,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_quotes_account
    ON quotes(account_id);

CREATE INDEX IF NOT EXISTS idx_orders_account
    ON sales_orders(account_id);

CREATE INDEX IF NOT EXISTS idx_shipments_order
    ON shipments(order_id);

CREATE INDEX IF NOT EXISTS idx_invoices_account
    ON invoices(account_id);

CREATE INDEX IF NOT EXISTS idx_invoices_due_date
    ON invoices(due_date);

CREATE INDEX IF NOT EXISTS idx_allocations_payment
    ON payment_allocations(payment_id);

CREATE INDEX IF NOT EXISTS idx_allocations_invoice
    ON payment_allocations(invoice_id);

CREATE INDEX IF NOT EXISTS idx_status_entity
    ON status_events(entity_type, entity_id);