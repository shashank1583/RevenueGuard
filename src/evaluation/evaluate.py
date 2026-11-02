import csv
import json
import sqlite3
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from src.rules.revenue_rules import run_all_rules


# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATABASE_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

SUMMARY_PATH = OUTPUT_DIR / "evaluation_summary.json"
CSV_PATH = OUTPUT_DIR / "evaluation_by_rule.csv"


def evaluate_dataset():
    """Run all detection rules and summarize their findings."""

    if not DATABASE_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DATABASE_PATH}\n"
            "Run the database initialization and data generators first."
        )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Open the existing database without modifying its contents.
    connection = sqlite3.connect(
        f"{DATABASE_PATH.resolve().as_uri()}?mode=ro",
        uri=True,
    )

    try:
        findings = run_all_rules(connection)
    finally:
        connection.close()

    # Count findings by rule.
    rule_counts = Counter(
        finding["rule_id"] for finding in findings
    )

    # Count findings by entity type.
    entity_counts = Counter(
        finding["entity_type"] for finding in findings
    )

    expected_rules = ["RG001", "RG002", "RG003", "RG004", "RG005"]

    summary = {
        "evaluation_timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "database": str(DATABASE_PATH.relative_to(PROJECT_ROOT)),
        "total_findings": len(findings),
        "findings_by_rule": {
            rule_id: rule_counts.get(rule_id, 0)
            for rule_id in expected_rules
        },
        "findings_by_entity_type": dict(
            sorted(entity_counts.items())
        ),
        "rules_executed": expected_rules,
        "metrics_note": (
            "These are finding counts, not precision, recall, "
            "or accuracy. Ground-truth labels are required "
            "to calculate those metrics reliably."
        ),
    }

    # Save the JSON summary.
    SUMMARY_PATH.write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    # Save a CSV summary with one row per rule.
    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["rule_id", "finding_count"],
        )
        writer.writeheader()

        for rule_id in expected_rules:
            writer.writerow(
                {
                    "rule_id": rule_id,
                    "finding_count": rule_counts.get(rule_id, 0),
                }
            )

    print("\nRevenueGuard Dataset Evaluation")
    print("=" * 36)
    print(f"Database: {DATABASE_PATH.name}")
    print(f"Total findings: {len(findings)}")
    print("\nFindings by rule:")

    for rule_id in expected_rules:
        print(f"  {rule_id}: {rule_counts.get(rule_id, 0)}")

    print("\nFindings by entity type:")

    for entity_type, count in sorted(entity_counts.items()):
        print(f"  {entity_type}: {count}")

    print("\nEvaluation files saved:")
    print(f"  JSON: {SUMMARY_PATH}")
    print(f"  CSV:  {CSV_PATH}")

    print(
        "\nNote: Finding counts alone do not establish "
        "detection accuracy."
    )


if __name__ == "__main__":
    evaluate_dataset()