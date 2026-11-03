import shutil
import sqlite3
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

BASELINE_DB = (
    PROJECT_ROOT / "data" / "output" / "revenueguard.db"
)

EVALUATION_DB = (
    PROJECT_ROOT / "data" / "output" / "revenueguard_evaluation.db"
)

SCHEMA_PATH = (
    PROJECT_ROOT / "src" / "database" / "schema.sql"
)


def create_evaluation_database():
    if not BASELINE_DB.exists():
        raise FileNotFoundError(
            f"Baseline database not found: {BASELINE_DB}"
        )

    if EVALUATION_DB.exists():
        raise FileExistsError(
            "Evaluation database already exists. "
            "Stopping to avoid overwriting it."
        )

    # Copy the original database.
    shutil.copy2(BASELINE_DB, EVALUATION_DB)

    print("Baseline database copied successfully.")

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    with sqlite3.connect(EVALUATION_DB) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        # Apply the updated schema to the evaluation copy.
        connection.executescript(schema_sql)

        tables = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
              AND name NOT LIKE 'sqlite_%'
            ORDER BY name
            """
        ).fetchall()

        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

    print(f"\nEvaluation database: {EVALUATION_DB}")
    print(f"Total tables: {len(tables)}")
    print(f"Database integrity: {integrity}")
    print(f"Foreign key errors: {len(foreign_key_errors)}")

    if integrity != "ok" or foreign_key_errors:
        raise RuntimeError(
            "Evaluation database validation failed."
        )

    print("\nTables:")

    for (table_name,) in tables:
        print(f"- {table_name}")

    print("\nEvaluation database created successfully!")


if __name__ == "__main__":
    create_evaluation_database()