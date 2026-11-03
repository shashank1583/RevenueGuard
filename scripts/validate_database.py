import argparse
import json
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DB_PATH = (
    PROJECT_ROOT / "data" / "output" / "revenueguard_evaluation.db"
)

OUTPUT_PATH = (
    PROJECT_ROOT / "data" / "output" / "validation_report.json"
)


def validate_database(db_path):

    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    connection = sqlite3.connect(
        f"{db_path.resolve().as_uri()}?mode=ro",
        uri=True,
    )

    report = {
        "database": str(db_path),
        "integrity_check": None,
        "foreign_key_errors": [],
        "tables": {},
        "total_tables": 0,
        "total_records": 0,
        "null_violations": [],
        "overall_status": "PASS",
    }

    try:
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        report["integrity_check"] = integrity

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        report["foreign_key_errors"] = [
            {
                "table": row[0],
                "row_id": row[1],
                "parent_table": row[2],
                "foreign_key_id": row[3],
            }
            for row in foreign_key_errors
        ]

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        for (table_name,) in tables:

            quoted_table = '"' + table_name.replace('"', '""') + '"'

            row_count = connection.execute(
                f"SELECT COUNT(*) FROM {quoted_table}"
            ).fetchone()[0]

            columns = connection.execute(
                f"PRAGMA table_info({quoted_table})"
            ).fetchall()

            table_violations = []

            for column in columns:

                column_name = column[1]
                is_required = column[3] == 1 or column[5] > 0

                if not is_required:
                    continue

                quoted_column = (
                    '"' + column_name.replace('"', '""') + '"'
                )

                null_count = connection.execute(
                    f"""
                    SELECT COUNT(*)
                    FROM {quoted_table}
                    WHERE {quoted_column} IS NULL
                    """
                ).fetchone()[0]

                if null_count > 0:
                    violation = {
                        "table": table_name,
                        "column": column_name,
                        "null_count": null_count,
                    }

                    table_violations.append(violation)
                    report["null_violations"].append(violation)

            report["tables"][table_name] = {
                "record_count": row_count,
                "column_count": len(columns),
                "required_field_violations": table_violations,
            }

            report["total_records"] += row_count

        report["total_tables"] = len(tables)

        if (
            integrity != "ok"
            or foreign_key_errors
            or report["null_violations"]
        ):
            report["overall_status"] = "FAIL"

    finally:
        connection.close()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(report, indent=4),
        encoding="utf-8",
    )

    print("\n--- DATABASE VALIDATION REPORT ---")
    print(f"Database: {db_path}")
    print(f"Integrity check: {report['integrity_check']}")
    print(f"Foreign key errors: {len(report['foreign_key_errors'])}")
    print(f"Required field violations: {len(report['null_violations'])}")
    print(f"Total tables: {report['total_tables']}")
    print(f"Total records: {report['total_records']}")

    print("\n--- TABLE RECORD COUNTS ---")

    for table, details in report["tables"].items():
        print(f"{table}: {details['record_count']}")

    print(f"\nOverall status: {report['overall_status']}")
    print(f"Report saved: {OUTPUT_PATH}")

    return report


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Validate RevenueGuard database integrity."
    )

    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB_PATH,
        help="Path to the database to validate.",
    )

    args = parser.parse_args()

    validate_database(args.db)