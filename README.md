# RevenueGuard — Revenue Leakage Detection System

## 1. Overview

RevenueGuard is a Python-based revenue monitoring system that uses a relational database and rule-based detection to identify potential revenue leakage, billing inconsistencies, payment allocation issues, and workflow anomalies.

The project generates synthetic business data, stores it in SQLite, and executes SQL-based detection rules to identify records that may require further investigation.

The system is designed to demonstrate database design, data generation, business-rule implementation, testing, and evaluation.

## 2. Key Features

- Relational SQLite database with 13 tables.
- Deterministic synthetic business data generation.
- Quote-to-order-to-shipment-to-invoice data flow.
- Payment and payment-allocation tracking.
- Dispute tracking and status-event history.
- Five rule-based revenue checks.
- Unit tests for all five detection rules.
- Controlled anomaly testing.
- JSON and CSV evaluation reports.

## 3. Technology Stack

- **Language:** Python
- **Database:** SQLite
- **Data processing:** pandas
- **Data validation:** pydantic
- **Testing:** pytest
- **Output formats:** JSON and CSV

## 4. Detection Rules

| Rule ID | Rule Name | Description |
|---|---|---|
| RG001 | Invoice Overbilling | Identifies invoice-line quantities exceeding the corresponding shipped quantities. |
| RG002 | Payment Overallocation | Identifies payments whose total allocated amount exceeds the payment amount. |
| RG003 | Closed Orders with Unpaid Invoices | Identifies closed orders associated with outstanding invoice balances. |
| RG004 | Invalid Status Transitions | Identifies recorded status transitions that violate the configured transition rules. |
| RG005 | Open Disputes | Identifies disputes that remain open or under review. |

**Important:** These rules identify potential issues for investigation. A finding does not automatically prove revenue leakage, fraud, or financial loss.

## 5. Project Structure

```text
RevenueGuard/
├── data/
│   ├── input/
│   └── output/
├── docs/
│   ├── design_decisions.md
│   └── prompt_history.md
├── scripts/
│   └── test_detection_rules.py
├── src/
│   ├── database/
│   │   ├── init_db.py
│   │   └── schema.sql
│   ├── evaluation/
│   │   └── evaluate.py
│   ├── generator/
│   │   ├── master_data.py
│   │   ├── order_data.py
│   │   ├── shipment_data.py
│   │   ├── invoice_data.py
│   │   ├── payment_data.py
│   │   └── dispute_data.py
│   └── rules/
│       ├── revenue_rules.py
│       └── run_rules.py
├── tests/
│   └── test_revenue_rules.py
├── .gitignore
├── requirements.txt
└── README.md
```

## 6. Setup

### Prerequisites

- Python 3.11 or later is recommended.
- Git is recommended for version control.

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

## 7. Initialize the Database

Create the SQLite database and its tables:

```powershell
python -m src.database.init_db
```

The generated database is stored at:

```text
data/output/revenueguard.db
```

## 8. Generate Synthetic Data

Run the generators in the following order so that related records are created before dependent records.

```powershell
python -m src.generator.master_data
python -m src.generator.order_data
python -m src.generator.shipment_data
python -m src.generator.invoice_data
python -m src.generator.payment_data
python -m src.generator.dispute_data
```

The generators create synthetic accounts, quotes, orders, shipments, invoices, payments, disputes, and related records.

Several generators use fixed random seeds to support reproducible data generation.

**Note:** Initialize a fresh database before regenerating the complete dataset. Re-running generators against an existing database may produce duplicate records or other inconsistencies, depending on their implementation.

## 9. Run Revenue Detection Rules

Execute all five detection rules:

```powershell
python -m src.rules.run_rules
```

The generated findings are written to:

```text
data/output/findings.json
```

Each finding represents a record identified by a detection rule for further review.

## 10. Run Tests

### Unit tests

Run the unit tests for the five detection rules:

```powershell
python -m pytest tests/test_revenue_rules.py -v
```

The current test suite contains five tests covering RG001 through RG005.

### Controlled anomaly tests

Run:

```powershell
python scripts/test_detection_rules.py
```

This script copies the generated database, injects controlled anomalies for RG001, RG002, and RG004, and checks whether the corresponding rules appear in the findings.

The script operates on a test copy rather than intentionally modifying the original database.

## 11. Evaluate the Dataset

Run:

```powershell
python -m src.evaluation.evaluate
```

The evaluation produces:

```text
data/output/evaluation_summary.json
data/output/evaluation_by_rule.csv
```

These files summarize the number of findings produced by each rule.

### Current baseline results

| Rule ID | Findings |
|---|---:|
| RG001 | 0 |
| RG002 | 0 |
| RG003 | 2,309 |
| RG004 | 0 |
| RG005 | 650 |
| **Total** | **2,959** |

These figures describe the current generated dataset and may change when the dataset or detection logic changes.

### Evaluation limitations

Finding counts alone do not establish detection accuracy.

Reliable precision, recall, and F1-score calculations require labelled evaluation cases identifying which records genuinely contain anomalies and which records are legitimate.

A zero finding count for a rule does not, by itself, prove that the rule is ineffective. It may indicate that the current dataset contains no matching cases.

## 12. Design Decisions

The project uses SQLite because it provides a lightweight relational database that can be initialized locally without a separate database server.

The data model separates business entities into related tables and uses foreign keys to represent relationships between records.

Detection rules are implemented separately from data generation so that the same rules can be evaluated against generated data and controlled test cases.

For additional implementation details and trade-offs, see:

```text
docs/design_decisions.md
```

## 13. Limitations

- The project uses synthetic data rather than real financial records.
- Detection is based on configured business rules rather than a trained machine-learning model.
- Findings require business review before being treated as confirmed anomalies.
- The baseline finding counts are not ground-truth accuracy metrics.
- Controlled anomaly testing currently covers RG001, RG002, and RG004.
- The current test suite is not a substitute for production integration, performance, security, and financial reconciliation testing.

## 14. AI-Assisted Development

AI tools were used during development. The project maintains a prompt-history document to support transparency.

See:

```text
docs/prompt_history.md
```

The prompt history should be updated to include the actual prompts used with AI tools during development.

## 15. Future Improvements

- Expand controlled anomaly tests to cover all five detection rules.
- Build a labelled evaluation dataset.
- Calculate precision, recall, and F1-score against known ground truth.
- Add stronger data-integrity and integration tests.
- Improve the reporting of findings with supporting evidence and recommended review actions.
- Add configurable rule thresholds and business-specific validation policies.

## 16. Disclaimer

RevenueGuard is a demonstration project for revenue monitoring and anomaly detection. Its findings are candidates for investigation and should not be treated as definitive evidence of financial loss or misconduct.