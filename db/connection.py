import sqlite3
import os
from contextlib import contextmanager
from pathlib import Path

from config import settings


def init_db() -> None:
    db_path = Path(settings.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    schema_path = Path(__file__).parent / "schema.sql"
    schema = schema_path.read_text()

    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema)
        conn.commit()


@contextmanager
def get_connection():
    db_path = Path(settings.db_path)
    conn = sqlite3.connect(db_path, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
