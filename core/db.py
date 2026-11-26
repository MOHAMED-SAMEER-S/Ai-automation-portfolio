"""SQLite storage shared by both projects."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (               -- Project 1
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL, name TEXT, email TEXT, language TEXT DEFAULT 'en',
    intent TEXT, interest TEXT, area TEXT, budget_bhd REAL, urgency TEXT, timeline TEXT,
    summary TEXT, score INTEGER DEFAULT 0, status TEXT DEFAULT 'new', crm_id TEXT,
    alerted INTEGER DEFAULT 0, source TEXT DEFAULT 'WhatsApp', created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, lead_id INTEGER, direction TEXT, body TEXT,
    wa_id TEXT UNIQUE, created_at TEXT
);
CREATE TABLE IF NOT EXISTS subscribers (         -- Project 2
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL, name TEXT, language TEXT DEFAULT 'en', interest TEXT, source TEXT,
    status TEXT DEFAULT 'active',                -- active / replied / converted / unsubscribed
    crm_id TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS drip (
    id INTEGER PRIMARY KEY AUTOINCREMENT, subscriber_id INTEGER NOT NULL, step INTEGER, step_name TEXT,
    due_at TEXT, sent_at TEXT, subject TEXT, body TEXT, ai_source TEXT,
    status TEXT DEFAULT 'pending'                -- pending / sent / skipped
);
CREATE TABLE IF NOT EXISTS crm_records (         -- the built-in "CRM" used when CRM_MODE=local
    crm_id TEXT PRIMARY KEY, kind TEXT, payload TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS outbox (              -- every WhatsApp message / email the system sends
    id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT, to_addr TEXT, subject TEXT, body TEXT,
    delivery TEXT, created_at TEXT
);
CREATE TABLE IF NOT EXISTS events (              -- activity log
    id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, kind TEXT, detail TEXT
);
"""


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@contextmanager
def conn():
    config.DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(config.DB_PATH)
    c.row_factory = sqlite3.Row
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init() -> None:
    with conn() as c:
        c.executescript(SCHEMA)


def rows(sql: str, params=()) -> list[dict]:
    with conn() as c:
        return [dict(r) for r in c.execute(sql, params).fetchall()]


def one(sql: str, params=()) -> dict | None:
    r = rows(sql, params)
    return r[0] if r else None


def execute(sql: str, params=()) -> int:
    with conn() as c:
        return c.execute(sql, params).lastrowid


def log_event(kind: str, detail: str) -> None:
    execute("INSERT INTO events (ts, kind, detail) VALUES (?,?,?)", (now(), kind, detail[:500]))
