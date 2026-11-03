# RevenueGuard — Database Data Dictionary

## 1. Overview

RevenueGuard uses a relational SQLite database to represent the end-to-end order-to-cash process.

The database contains 14 tables covering:

- Customer account management
- Sales quotations
- Sales orders and order lines
- Shipment tracking
- Invoice generation
- Payment processing and allocation
- Customer disputes
- Receivables adjustments
- Entity status history

Primary keys uniquely identify records. Foreign keys maintain relationships between related business entities.

## 2. Database Tables

### 2.1 accounts

**Purpose:** Stores customer account information.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| account_id | TEXT | Primary Key | Unique customer account identifier |
| account_name | TEXT | NOT NULL | Customer or organization name |
| created_at | TEXT | NOT NULL | Account creation timestamp |

### 2.2 quotes

**Purpose:** Stores sales quotations created for customer accounts.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| quote_id | TEXT | Primary Key | Unique quote identifier |
| account_id | TEXT | NOT NULL, Foreign Key | Associated customer account |
| quote_date | TEXT | NOT NULL | Date the quote was created |
| expiry_date | TEXT | NOT NULL | Quote expiration date |
| status | TEXT | NOT NULL, CHECK | Quote lifecycle status |

Allowed statuses: draft, sent, accepted, rejected, expired.

Business constraint: expiry_date must be on or after quote_date.

### 2.3 quote_lines

**Purpose:** Stores individual products and quantities included in quotations.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| quote_line_id | INTEGER | Primary Key | Unique quote line identifier |
| quote_id | TEXT | NOT NULL, Foreign Key | Associated quotation |
| product_name | TEXT | NOT NULL | Product description |
| quantity | INTEGER | NOT NULL, CHECK | Quoted quantity; must be positive |
| unit_price | REAL | NOT NULL, CHECK | Price per unit; must be non-negative |

### 2.4 sales_orders

**Purpose:** Stores confirmed customer sales orders.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| order_id | TEXT | Primary Key | Unique sales order identifier |
| account_id | TEXT | NOT NULL, Foreign Key | Associated customer account |
| quote_id | TEXT | UNIQUE, Foreign Key | Source quotation, when available |
| order_date | TEXT | NOT NULL | Date the order was created |
| status | TEXT | NOT NULL, CHECK | Current order status |

Allowed statuses: open, processing, fulfilled, closed, cancelled.

The unique quote_id constraint prevents one quotation from being linked to multiple sales orders.

### 2.5 order_lines

**Purpose:** Stores individual products and quantities belonging to sales orders.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| order_line_id | INTEGER | Primary Key | Unique order line identifier |
| order_id | TEXT | NOT NULL, Foreign Key | Associated sales order |
| quote_line_id | INTEGER | Foreign Key | Original quotation line, when available |
| product_name | TEXT | NOT NULL | Product description |
| quantity | INTEGER | NOT NULL, CHECK | Ordered quantity; must be positive |
| unit_price | REAL | NOT NULL, CHECK | Agreed unit price; must be non-negative |

### 2.6 shipments

**Purpose:** Records shipment activities associated with sales orders.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| shipment_id | TEXT | Primary Key | Unique shipment identifier |
| order_id | TEXT | NOT NULL, Foreign Key | Associated sales order |
| shipment_date | TEXT | NOT NULL | Shipment date |
| status | TEXT | NOT NULL, CHECK | Current shipment status |

Allowed statuses: pending, shipped, delivered, cancelled.

### 2.7 shipment_lines

**Purpose:** Tracks quantities of individual order lines included in shipments.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| shipment_line_id | INTEGER | Primary Key | Unique shipment line identifier |
| shipment_id | TEXT | NOT NULL, Foreign Key | Associated shipment |
| order_line_id | INTEGER | NOT NULL, Foreign Key | Associated sales order line |
| quantity_shipped | INTEGER | NOT NULL, CHECK | Shipped quantity; must be positive |

This table supports multiple shipments for a single order line.

### 2.8 invoices

**Purpose:** Stores customer invoices generated against sales orders.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| invoice_id | TEXT | Primary Key | Unique invoice identifier |
| account_id | TEXT | NOT NULL, Foreign Key | Associated customer account |
| order_id | TEXT | NOT NULL, Foreign Key | Associated sales order |
| invoice_date | TEXT | NOT NULL | Invoice creation date |
| due_date | TEXT | NOT NULL | Payment due date |
| status | TEXT | NOT NULL, CHECK | Current invoice status |

Allowed statuses: draft, issued, partially_paid, paid, disputed, void.

Business constraint: due_date must be on or after invoice_date.

### 2.9 invoice_lines

**Purpose:** Stores billed quantities and prices for individual order lines.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| invoice_line_id | INTEGER | Primary Key | Unique invoice line identifier |
| invoice_id | TEXT | NOT NULL, Foreign Key | Associated invoice |
| order_line_id | INTEGER | NOT NULL, Foreign Key | Associated sales order line |
| quantity_billed | INTEGER | NOT NULL, CHECK | Billed quantity; must be positive |
| unit_price | REAL | NOT NULL, CHECK | Billed unit price; must be non-negative |

Invoice line amounts are calculated using quantity_billed multiplied by unit_price.

### 2.10 payments

**Purpose:** Records customer payment transactions.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| payment_id | TEXT | Primary Key | Unique payment identifier |
| account_id | TEXT | NOT NULL, Foreign Key | Associated customer account |
| payment_date | TEXT | NOT NULL | Payment transaction date |
| amount | REAL | NOT NULL, CHECK | Payment amount; must be positive |
| status | TEXT | NOT NULL, CHECK | Payment processing status |

Allowed statuses: received, pending, failed, refunded.

### 2.11 payment_allocations

**Purpose:** Maps payment amounts to customer invoices.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| allocation_id | INTEGER | Primary Key | Unique allocation identifier |
| payment_id | TEXT | NOT NULL, Foreign Key | Associated payment |
| invoice_id | TEXT | NOT NULL, Foreign Key | Associated invoice |
| allocated_amount | REAL | NOT NULL, CHECK | Amount allocated to the invoice; must be positive |
| allocated_at | TEXT | NOT NULL | Allocation date |

A payment can have multiple allocations, and an invoice can receive allocations from multiple payments.

### 2.12 disputes

**Purpose:** Records customer disputes raised against invoices.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| dispute_id | TEXT | Primary Key | Unique dispute identifier |
| invoice_id | TEXT | NOT NULL, Foreign Key | Associated invoice |
| opened_at | TEXT | NOT NULL | Dispute opening date |
| resolved_at | TEXT | Nullable | Dispute resolution date |
| amount | REAL | NOT NULL, CHECK | Disputed amount; must be positive |
| status | TEXT | NOT NULL, CHECK | Current dispute status |

Allowed statuses: open, under_review, resolved, rejected.

Business constraint: resolved_at cannot precede opened_at.

### 2.13 receivable_adjustments

**Purpose:** Records receivables adjustments associated with customer disputes.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| adjustment_id | TEXT | Primary Key | Unique adjustment identifier |
| dispute_id | TEXT | NOT NULL, UNIQUE, Foreign Key | Associated dispute |
| invoice_id | TEXT | NOT NULL, Foreign Key | Associated invoice |
| adjusted_amount | REAL | NOT NULL, CHECK | Adjustment amount; must be positive |
| adjustment_date | TEXT | NOT NULL | Adjustment date |

The unique dispute_id constraint permits at most one adjustment record per dispute.

RevenueGuard uses this table to identify active disputes with missing or insufficient receivables adjustments.

### 2.14 status_events

**Purpose:** Maintains a history of lifecycle status changes across business entities.

| Column | Data Type | Constraints | Description |
|---|---|---|---|
| event_id | INTEGER | Primary Key | Unique status event identifier |
| entity_type | TEXT | NOT NULL, CHECK | Type of business entity |
| entity_id | TEXT | NOT NULL | Identifier of the affected entity |
| previous_status | TEXT | Nullable | Previous lifecycle status |
| new_status | TEXT | NOT NULL | New lifecycle status |
| event_at | TEXT | NOT NULL | Event timestamp |
| notes | TEXT | Nullable | Additional event information |

Supported entity types: quote, order, shipment, invoice, payment, dispute.

This table supports lifecycle auditing and invalid status transition detection.

Note: entity_id is a polymorphic reference. It does not have a conventional foreign key to each business entity table.

## 3. Entity Relationships

The primary relationships are:

| Parent Table | Child Table | Relationship |
|---|---|---|
| accounts | quotes | One-to-many |
| accounts | sales_orders | One-to-many |
| accounts | invoices | One-to-many |
| accounts | payments | One-to-many |
| quotes | quote_lines | One-to-many |
| quotes | sales_orders | One-to-zero-or-one |
| sales_orders | order_lines | One-to-many |
| sales_orders | shipments | One-to-many |
| sales_orders | invoices | One-to-many |
| quote_lines | order_lines | One-to-many |
| order_lines | shipment_lines | One-to-many |
| order_lines | invoice_lines | One-to-many |
| shipments | shipment_lines | One-to-many |
| invoices | invoice_lines | One-to-many |
| invoices | payment_allocations | One-to-many |
| payments | payment_allocations | One-to-many |
| invoices | disputes | One-to-many |
| disputes | receivable_adjustments | One-to-zero-or-one |
| invoices | receivable_adjustments | One-to-many |

## 4. Database Indexes

The schema defines the following indexes to support common lookup and join operations.

| Index | Table | Indexed Column(s) |
|---|---|---|
| idx_quotes_account | quotes | account_id |
| idx_orders_account | sales_orders | account_id |
| idx_shipments_order | shipments | order_id |
| idx_invoices_account | invoices | account_id |
| idx_invoices_due_date | invoices | due_date |
| idx_allocations_payment | payment_allocations | payment_id |
| idx_allocations_invoice | payment_allocations | invoice_id |
| idx_status_entity | status_events | entity_type, entity_id |

Primary keys and unique constraints also create supporting indexes in SQLite.

## 5. Data Integrity Constraints

The database implements several integrity protections:

- Primary keys prevent duplicate entity identifiers.
- Foreign keys enforce references between related records.
- NOT NULL constraints protect required fields.
- CHECK constraints restrict allowed statuses and invalid numeric values.
- Date checks prevent invalid quote, invoice, and dispute date sequences.
- UNIQUE constraints prevent duplicate quote-to-order and dispute-to-adjustment relationships.

Additional cross-table business rules are implemented in RevenueGuard detection logic rather than solely through SQL constraints.

## 6. Known Design Limitations

- Monetary values currently use SQLite REAL rather than integer minor units or a decimal representation.
- Status event entity references are polymorphic and are not enforced through conventional foreign keys.
- The schema does not enforce all cross-table quantity and financial reconciliation rules.
- The unique dispute_id constraint permits only one adjustment record per dispute.
- Payment allocation records do not independently model refunds or allocation reversals.

These limitations are documented for transparency and can be addressed in future versions.