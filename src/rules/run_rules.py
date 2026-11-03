import argparse
import json
import sqlite3
from pathlib import Path

from src.rules.revenue_rules import run_all_rules


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "output" / "revenueguard.db"
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def main():
    parser = argparse.ArgumentParser(
        description="Run RevenueGuard detection rules."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the SQLite database.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_DIR / "findings.json",
        help="Path to save detection findings.",
    )

    args = parser.parse_args()

    if not args.db.exists():
        raise FileNotFoundError(f"Database not found: {args.db}")

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(args.db) as connection:
        findings = run_all_rules(connection)

    args.output.write_text(
        json.dumps(findings, indent=2),
        encoding="utf-8",
    )

    print(f"Database: {args.db}")
    print(f"Total findings: {len(findings)}")
    print(f"Results saved to: {args.output}")

    counts = {}

    for finding in findings:
        rule_id = finding["rule_id"]
        counts[rule_id] = counts.get(rule_id, 0) + 1

    for rule_id, count in sorted(counts.items()):
        print(f"{rule_id}: {count}")


if __name__ == "__main__":
    main()