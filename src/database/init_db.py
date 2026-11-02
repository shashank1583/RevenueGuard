from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = PROJECT_ROOT / "src" / "database" / "schema.sql"
DATA_DIR = PROJECT_ROOT / "data" / "output"
DB_PATH = DATA_DIR / "revenueguard.db"


def initialize_database():
    """Create the SQLite database using the project's schema."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
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

    print(f"Database created at: {DB_PATH}")
    print(f"Tables created: {len(tables)}")

    for (table_name,) in tables:
        print(f" - {table_name}")


if __name__ == "__main__":
    initialize_database()