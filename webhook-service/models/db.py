"""SQLite schema + helpers for the webhook service.

A real service would use SQLAlchemy + Alembic + Postgres. For a sandbox
SQLite keeps everything in-repo and the queries are simple enough that we
hand-roll them with the stdlib.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "data" / "webhooks.sqlite"


def db_path() -> Path:
    raw = os.environ.get("WEBHOOK_SERVICE_DB_PATH")
    return Path(raw) if raw else DEFAULT_PATH


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


SCHEMA = """
CREATE TABLE IF NOT EXISTS processed_events (
    event_id   TEXT PRIMARY KEY,
    topic      TEXT NOT NULL,
    received_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders_normalized (
    order_id    TEXT PRIMARY KEY,
    shop_domain TEXT NOT NULL,
    setup_type  TEXT NOT NULL,
    total       TEXT,
    currency    TEXT,
    customer    TEXT,
    line_items  TEXT,          -- JSON
    flagged     INTEGER NOT NULL DEFAULT 0,
    flag_reason TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id    TEXT NOT NULL,
    shop_domain   TEXT NOT NULL,
    audit_status  TEXT NOT NULL,
    detail        TEXT,        -- JSON
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shops (
    shop_domain TEXT PRIMARY KEY,
    state       TEXT NOT NULL DEFAULT 'active',
    last_seen   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS gdpr_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    shop_domain   TEXT NOT NULL,
    topic         TEXT NOT NULL,
    payload       TEXT NOT NULL,
    received_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def record_event(event_id: str, topic: str) -> bool:
    """Insert event_id; return True if this was a new event, False if dupe."""
    with connect() as conn:
        try:
            conn.execute(
                "INSERT INTO processed_events (event_id, topic) VALUES (?, ?)",
                (event_id, topic),
            )
            return True
        except sqlite3.IntegrityError:
            return False
