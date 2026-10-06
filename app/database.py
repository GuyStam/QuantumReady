from pathlib import Path
import sqlite3


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "quantumready.db"


def get_db_connection():
    connection = sqlite3.connect(DB_PATH)

    connection.row_factory = sqlite3.Row

    connection.execute(
        "PRAGMA foreign_keys = ON"
    )

    return connection