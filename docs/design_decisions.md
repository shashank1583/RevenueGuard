# RevenueGuard — Design Decisions

## 1. Project Architecture

RevenueGuard separates database initialization, synthetic data generation, detection rules, and evaluation into different modules.

**Decision:** Use a modular Python project structure.

**Reason:** Separating responsibilities makes the code easier to understand, test, maintain, and extend.

**Trade-off:** A modular structure introduces more files and requires the generators to run in the correct order.

## 2. Database Selection

**Decision:** Use SQLite as the relational database.

**Reason:** SQLite runs locally without requiring a separate database server, making the project straightforward to set up and evaluate.

**Trade-off:** SQLite is suitable for this demonstration but may not meet the concurrency, scalability, and operational requirements of a large production financial system.

## 3. Relational Data Model

**Decision:** Represent accounts, quotes, orders, shipments, invoices, payments, disputes, and related records in separate tables connected through identifiers and foreign keys.

**Reason:** This structure represents business relationships and supports SQL queries across the revenue lifecycle.

**Trade-off:** Cross-entity detection rules require joins and aggregation, which can make queries more complex.

## 4. Synthetic Data Generation

**Decision:** Generate synthetic business records using Python scripts and fixed random seeds where applicable.

**Reason:** Synthetic data provides a repeatable environment for demonstrating the detection rules without using confidential financial information.

**Trade-off:** Synthetic records cannot fully represent the complexity, exceptions, and distributions of real business transactions.

The generators expect a fresh database for initial dataset creation. They are not designed to be rerun repeatedly against the same populated database.

## 5. Rule-Based Detection

**Decision:** Implement five SQL-based detection rules rather than using a machine-learning model.

**Reason:** The rules represent explicit business checks and produce findings that can be investigated and explained.

**Trade-off:** Rule-based detection depends on the assumptions and conditions encoded in the queries. It may miss anomalies that are not covered by the rules.

The five rules are:

- RG001: Invoice overbilling.
- RG002: Payment overallocation.
- RG003: Closed orders with unpaid invoices.
- RG004: Invalid status transitions.
- RG005: Open disputes.

Findings indicate potential issues for investigation; they do not automatically establish financial loss or misconduct.

## 6. Status-Transition Validation

**Decision:** Define permitted status transitions explicitly and compare recorded transitions against the configured rules.

**Reason:** Explicit transition rules make workflow validation understandable and testable.

**Trade-off:** The configured transitions represent simplified workflow assumptions. A real business may require additional states, exceptions, or entity-specific policies.

## 7. Testing Strategy

**Decision:** Use pytest for unit tests and a separate script to inject controlled anomalies into a copy of the generated database.

**Reason:** Unit tests check individual detection rules, while controlled tests exercise selected rules against deliberately modified data.

**Trade-off:** The current controlled anomaly tests cover only RG001, RG002, and RG004. Their assertions should be strengthened to verify the exact affected records, and the other rules need additional controlled cases.

Passing tests demonstrates that the tested scenarios behave as expected. It does not establish overall detection accuracy.

## 8. Evaluation Approach

**Decision:** Report finding counts by rule in JSON and CSV files.

**Reason:** These reports provide a simple summary of which rules generate findings on the current dataset.

**Trade-off:** Finding counts alone cannot measure precision, recall, or F1-score. Those metrics require labelled cases identifying true anomalies and legitimate records.

The current baseline results are specific to the generated dataset and configured rules.

## 9. Financial Representation

**Decision:** Store monetary values in the existing database schema and use integer cents in parts of payment generation to reduce rounding issues during allocation calculations.

**Reason:** Integer-cent calculations are suitable for representing currency amounts during arithmetic operations.

**Trade-off:** Monetary consistency still depends on correct conversions, aggregation, allocation, and validation across the entire data pipeline.

## 10. Current Limitations and Future Improvements

The current implementation is a demonstration rather than a production financial-control system.

Potential improvements include:

- Strengthening controlled tests to assert exact affected entity identifiers.
- Adding labelled evaluation data and measuring precision, recall, and F1-score.
- Validating invoice eligibility against order and shipment status.
- Modeling payment refunds and allocation reversals more completely.
- Expanding status-transition coverage.
- Adding integration tests and stronger reconciliation checks.
- Improving finding explanations and recommended investigation steps.