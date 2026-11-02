# RevenueGuard — AI Prompt History

## Purpose

This document records representative AI-assisted development tasks for RevenueGuard. It summarizes the types of prompts used and the intended outcomes.

**Transparency note:** The entries below are representative summaries, not a verbatim transcript of every prompt used during development.

## 1. Project Architecture

**Task:** Design a modular Python project for revenue leakage detection.

**Representative prompt:**

"Help design a Python project for revenue leakage detection using SQLite. Separate database initialization, synthetic data generation, business-rule detection, testing, and evaluation into appropriate modules."

**Intended outcome:** Establish a maintainable project structure with clear separation of responsibilities.

## 2. Database Schema

**Task:** Model the business entities and their relationships.

**Representative prompt:**

"Review the relational data model for accounts, quotes, orders, shipments, invoices, payments, payment allocations, disputes, and status events. Identify important relationships and data-integrity considerations."

**Intended outcome:** Support revenue-lifecycle queries and cross-entity validation.

## 3. Synthetic Data Generation

**Task:** Create reproducible synthetic business data.

**Representative prompt:**

"Review the Python data generators for the revenue lifecycle. Check record relationships, transaction handling, reproducibility, duplicate-generation safeguards, and assumptions in the generated data."

**Intended outcome:** Generate a dataset suitable for testing revenue detection rules without real financial records.

## 4. Detection Rules

**Task:** Review rule logic and expected behavior.

**Representative prompt:**

"Review the SQL-based revenue detection rules for invoice overbilling, payment overallocation, closed orders with unpaid invoices, invalid status transitions, and open disputes. Identify assumptions, edge cases, and possible false positives."

**Intended outcome:** Improve the clarity and reliability of rule-based anomaly detection.

## 5. Unit Testing

**Task:** Validate individual detection rules.

**Representative prompt:**

"Review the pytest tests for the five revenue detection rules. Check whether each test creates suitable sample data and verifies the expected finding."

**Intended outcome:** Test each detection rule against defined scenarios.

## 6. Controlled Anomaly Testing

**Task:** Test selected rules using deliberately injected anomalies.

**Representative prompt:**

"Review the controlled anomaly test script. It should work on a copy of the database, introduce selected anomalies, execute the detection rules, and verify that the intended anomalies are detected."

**Intended outcome:** Exercise selected detection rules against controlled modifications without intentionally changing the baseline database.

**Known limitation:** The initial script checks whether the corresponding rule IDs appear in the findings. Stronger assertions should verify the exact affected records.

## 7. Evaluation

**Task:** Summarize detection results.

**Representative prompt:**

"Review the evaluation module that summarizes findings by rule and exports JSON and CSV reports. Explain what the finding counts establish and what additional data is required to calculate precision, recall, and F1-score."

**Intended outcome:** Produce reproducible summaries without incorrectly treating finding counts as accuracy metrics.

## 8. Documentation and Final Validation

**Task:** Prepare the repository for review.

**Representative prompt:**

"Review the README, design decisions, testing instructions, evaluation limitations, and project structure. Identify inconsistencies and recommend the remaining validation steps before submission."

**Intended outcome:** Make the project easier to install, understand, test, and evaluate.

## 9. Developer Review and Verification

AI-generated suggestions were treated as assistance rather than proof of correctness. The project was also checked by running the following commands locally:

```powershell
python -m pytest -v
python scripts/test_detection_rules.py
python -m src.evaluation.evaluate
```

The observed unit-test result was **5 passed**. The controlled anomaly script reported passing checks for RG001, RG002, and RG004. These results cover the tested scenarios and do not establish overall detection accuracy.

## 10. Remaining Work

- Strengthen controlled anomaly assertions to verify exact affected records.
- Add controlled test cases for RG003 and RG005.
- Review data-generation assumptions and financial reconciliation behavior.
- Run the complete test suite after any changes.
- Update this document if additional AI-assisted development work is performed.