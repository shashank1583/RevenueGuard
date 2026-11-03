# RevenueGuard — Revenue Leakage Detection System

## 1. Overview

RevenueGuard is a Python-based revenue monitoring and anomaly detection system designed to identify potential revenue leakage, billing inconsistencies, payment allocation issues, and business workflow anomalies.

The system simulates an end-to-end Order-to-Cash (O2C) process using synthetic business data stored in a relational SQLite database.

It applies SQL-based detection rules to identify suspicious transactions and inconsistencies across sales orders, shipments, invoices, payments, and customer disputes.

The project demonstrates relational database design, synthetic data generation, business-rule implementation, automated testing, controlled anomaly injection, and evaluation.

## 2. Key Features

- Relational SQLite database with 14 tables.
- Deterministic synthetic business data generation.
- End-to-end quote-to-order-to-shipment-to-invoice workflow.
- Payment processing and invoice allocation tracking.
- Customer dispute and receivables adjustment tracking.
- Five SQL-based revenue anomaly detection rules.
- Lifecycle status transition validation.
- Controlled anomaly injection for all five detection rules.
- Ground-truth-based controlled evaluation.
- Database integrity and foreign-key validation.
- Financial and quantity reconciliation checks.
- JSON and CSV evaluation reports.
- Automated unit testing with pytest.

## 3. Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python |
| Database | SQLite |
| Data Processing | pandas |
| Data Validation | pydantic |
| Testing | pytest |
| Evaluation Output | JSON, CSV |
| Version Control | Git, GitHub |

## 4. Detection Rules

RevenueGuard currently implements five detection rules.

| Rule ID | Rule Name | Description |
|---|---|---|
| RG001 | Invoice Overbilling | Identifies invoice-line quantities exceeding the corresponding shipped quantities. |
| RG002 | Payment Overallocation | Identifies payments whose total allocated amount exceeds the payment amount. |
| RG003 | Closed Orders with Unpaid Invoices | Identifies closed sales orders with outstanding invoice balances. |
| RG004 | Invalid Status Transitions | Identifies recorded status transitions that violate configured lifecycle rules. |
| RG005 | Missing Receivables Adjustment | Identifies active disputes with missing or insufficient receivables adjustments. |

**Important:** Detection findings represent potential business anomalies requiring investigation. They do not automatically establish financial loss, fraud, or misconduct.

## 5. Database Design

The database contains 14 relational tables:

| Category | Tables |
|---|---|
| Customer Management | accounts |
| Quotation Management | quotes, quote_lines |
| Sales Management | sales_orders, order_lines |
| Shipment Management | shipments, shipment_lines |
| Billing | invoices, invoice_lines |
| Payments | payments, payment_allocations |
| Dispute Management | disputes, receivable_adjustments |
| Audit History | status_events |

The database uses primary keys, foreign keys, unique constraints, CHECK constraints, and indexes to maintain structural consistency.

### Data Dictionary

The detailed database schema, column descriptions, relationships, constraints, and indexes are documented in:

`docs/data_dictionary.md`

## 6. Project Structure

```text
RevenueGuard/
|-- data/
|   |-- input/
|   |-- output/                  # Generated files; excluded from Git
|   |-- ground_truth.csv
|
|-- docs/
|   |-- data_dictionary.md
|   |-- design_decisions.md
|   |-- prompt_history.md
|
|-- scripts/
|   |-- create_evaluation_db.py
|   |-- inject_evaluation_anomalies.py
|   |-- reconcile_data.py
|   |-- test_detection_rules.py
|   |-- validate_database.py
|
|-- src/
|   |-- database/
|   |   |-- init_db.py
|   |   |-- schema.sql
|   |
|   |-- evaluation/
|   |   |-- evaluate.py
|   |   |-- evaluate_controlled_cases.py
|   |
|   |-- generator/
|   |   |-- master_data.py
|   |   |-- order_data.py
|   |   |-- shipment_data.py
|   |   |-- invoice_data.py
|   |   |-- payment_data.py
|   |   |-- dispute_data.py
|   |
|   |-- rules/
|       |-- revenue_rules.py
|       |-- run_rules.py
|
|-- tests/
|   |-- test_revenue_rules.py
|
|-- .gitignore
|-- requirements.txt
|-- README.md
```

## 7. Setup

### Prerequisites

- Python 3.11 or later.
- Git.

The project was developed and tested using Python 3.13.7.

### Create a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Install dependencies

```powershell
python -m pip install -r requirements.txt
```

## 8. Initialize the Database

Initialize the SQLite database:

```powershell
python -m src.database.init_db
```

The database is created at:

```text
data/output/revenueguard.db
```

## 9. Generate Synthetic Data

Run the data generators in the following order:

```powershell
python -m src.generator.master_data
python -m src.generator.order_data
python -m src.generator.shipment_data
python -m src.generator.invoice_data
python -m src.generator.payment_data
python -m src.generator.dispute_data
```

The generators create synthetic customer accounts, quotes, sales orders, shipments, invoices, payments, and disputes.

Several generators use fixed random seeds to support reproducible data generation.

Invoice generation is restricted to fulfilled or closed orders and uses actual shipped or delivered quantities.

**Note:** Initialize a fresh database before regenerating the complete dataset. Generators include checks to prevent accidental duplicate generation.

## 10. Run Revenue Detection Rules

Execute all five detection rules:

```powershell
python -m src.rules.run_rules
```

Findings are saved to:

```text
data/output/findings.json
```

A custom database and output path can also be supplied:

```powershell
python -m src.rules.run_rules --db data/output/revenueguard_evaluation.db --output data/output/evaluation_findings.json
```

Each finding includes its rule identifier, affected entity, description, and supporting details.

## 11. Testing

### Unit Tests

Run:

```powershell
python -m pytest -v
```

The current test suite contains seven passing tests covering:

- Invoice overbilling.
- Payment overallocation.
- Closed orders with outstanding invoices.
- Invalid status transitions.
- Active disputes without receivables adjustments.
- Partially adjusted disputes.
- Fully adjusted disputes.

**Latest result: 7 passed.**

### Controlled Anomaly Testing

The project supports controlled anomaly injection for all five detection rules.

First, create a separate evaluation database:

```powershell
python scripts/create_evaluation_db.py
```

Inject controlled anomalies:

```powershell
python scripts/inject_evaluation_anomalies.py
```

Run the detection rules:

```powershell
python -m src.rules.run_rules --db data/output/revenueguard_evaluation.db --output data/output/evaluation_findings.json
```

The evaluation database is kept separate from the original generated database.

The controlled scenarios cover:

- RG001: Invoice overbilling.
- RG002: Payment overallocation.
- RG003: Closed order with an outstanding invoice.
- RG004: Invalid status transition.
- RG005: Active dispute without a receivables adjustment.

The expected results are maintained in:

`data/ground_truth.csv`

### Controlled Evaluation

Run:

```powershell
python -m src.evaluation.evaluate_controlled_cases
```

Generated reports:

```text
data/output/controlled_evaluation_summary.json
data/output/controlled_evaluation_by_case.csv
```

### Controlled Evaluation Results

| Metric | Result |
|---|---:|
| Controlled test cases | 5 |
| Correctly detected cases | 5 |
| Missed cases | 0 |
| Detection rate | 100% |

All five injected anomaly scenarios were detected against their expected rule and entity identifiers.

Precision and F1-score are not reported because complete positive and negative ground-truth labels are not available for the entire dataset.

The 100% detection rate applies only to the five controlled scenarios. It should not be interpreted as production-wide model accuracy.

## 12. Database Validation

Run:

```powershell
python -m scripts.validate_database
```

This checks:

- SQLite database integrity.
- Foreign-key violations.
- Missing values in required columns.
- Table and record counts.

### Latest Validation Results

| Metric | Result |
|---|---:|
| Database tables | 14 |
| Total records | 184,182 |
| SQLite integrity | PASS |
| Foreign-key violations | 0 |
| Required-field violations | 0 |
| Overall status | PASS |

The record count represents the controlled evaluation database after anomaly injection.

## 13. Financial and Quantity Reconciliation

Run:

```powershell
python -m scripts.reconcile_data
```

The reconciliation script checks:

- Shipped quantities against ordered quantities.
- Invoiced quantities against shipped quantities.
- Payment allocations against payment amounts.

### Latest Reconciliation Results

| Check | Total Violations | Expected Test Anomalies | Unexpected Violations | Status |
|---|---:|---:|---:|---|
| Shipment vs Ordered Quantity | 0 | 0 | 0 | PASS |
| Invoice vs Shipped Quantity | 1 | 1 | 0 | PASS |
| Payment Allocation | 1 | 1 | 0 | PASS |

Both reported financial/quantity violations correspond to deliberately injected evaluation scenarios.

No unexpected violations were identified by these checks.

## 14. Baseline Evaluation Results

The original generated database produced the following baseline findings before controlled anomaly injection:

| Rule ID | Findings |
|---|---:|
| RG001 | 0 |
| RG002 | 0 |
| RG003 | 2,309 |
| RG004 | 0 |
| RG005 | 650 |
| **Total** | **2,959** |

These are baseline detection counts, not accuracy measurements.

The controlled evaluation database is a separate copy containing additional adjustments and deliberately injected anomalies. Its findings should not be confused with the baseline results.

## 15. Design Decisions

Key design decisions include:

- SQLite was selected for lightweight relational storage without requiring a separate database server.
- Business entities are separated into related tables.
- Detection rules are implemented independently from data generation.
- Synthetic data is used to avoid dependence on real financial records.
- Controlled anomaly injection provides known test scenarios.
- Ground truth is maintained separately from detection results.
- Structural validation and business reconciliation are performed independently.

For additional details, see:

`docs/design_decisions.md`

## 16. Limitations

- The project uses synthetic data rather than real financial records.
- Detection is based on predefined business rules, not a trained machine-learning model.
- Findings require business review before being considered confirmed anomalies.
- Global precision and F1-score are unavailable because the full dataset does not have complete ground-truth labels.
- Monetary values currently use SQLite REAL rather than integer minor units or a decimal representation.
- Refund reversals and more advanced receivables accounting workflows are not fully modelled.
- The project is a demonstration implementation and has not been validated for production financial operations.

## 17. AI-Assisted Development

AI tools were used during development for implementation assistance, debugging, testing, and documentation.

Representative development prompts and AI-assisted workflow notes are maintained in:

`docs/prompt_history.md`

## 18. Future Improvements

- Expand ground-truth coverage beyond the five controlled scenarios.
- Introduce comprehensive positive and negative evaluation labels.
- Calculate precision, recall, and F1-score against a fully labelled dataset.
- Use integer minor units or decimal arithmetic for financial calculations.
- Add refund and payment reversal workflows.
- Add stronger integration and performance tests.
- Improve anomaly reporting with evidence, severity, and recommended investigation actions.
- Introduce configurable business rules and thresholds.

## 19. Disclaimer

RevenueGuard is a demonstration project for revenue monitoring and anomaly detection.

Its findings represent potential business inconsistencies requiring investigation. They should not be treated as definitive evidence of financial loss, fraud, or misconduct.