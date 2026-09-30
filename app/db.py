"""SQLite persistence (stdlib sqlite3, one connection per request)."""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    username   TEXT NOT NULL,
    name       TEXT NOT NULL,
    category   TEXT NOT NULL,
    image_url  TEXT,
    note       TEXT,
    favorite   INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_items_username ON items(username);
"""


@contextmanager
def get_conn():
    connection = sqlite3.connect(DB_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    with get_conn() as connection:
        connection.executescript(SCHEMA)


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_item(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "username": row["username"],
        "name": row["name"],
        "category": row["category"],
        "image_url": row["image_url"],
        "note": row["note"],
        "favorite": bool(row["favorite"]),
        "created_at": row["created_at"],
    }
