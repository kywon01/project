import sqlite3
from datetime import datetime
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS prices (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    product    TEXT NOT NULL,
    price      INTEGER NOT NULL,
    matched    TEXT,
    source_url TEXT,
    fetched_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_prices_product ON prices(product, fetched_at);
"""


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.executescript(SCHEMA)
    return conn


def last_price(conn: sqlite3.Connection, product: str) -> Optional[int]:
    row = conn.execute(
        "SELECT price FROM prices WHERE product = ? ORDER BY id DESC LIMIT 1", (product,)
    ).fetchone()
    return row[0] if row else None


def lowest_price(conn: sqlite3.Connection, product: str) -> Optional[int]:
    row = conn.execute("SELECT MIN(price) FROM prices WHERE product = ?", (product,)).fetchone()
    return row[0]


def save_price(conn, product: str, price: int, matched: str, source_url: str) -> None:
    conn.execute(
        "INSERT INTO prices (product, price, matched, source_url, fetched_at) VALUES (?,?,?,?,?)",
        (product, price, matched, source_url, datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()


def all_rows(conn, product: str):
    """오래된 순 전체 이력 (fetched_at, price, matched)."""
    return conn.execute(
        "SELECT fetched_at, price, matched FROM prices WHERE product = ? ORDER BY id", (product,)
    ).fetchall()


def history(conn, product: str, limit: int = 30):
    return conn.execute(
        "SELECT fetched_at, price, matched FROM prices WHERE product = ? ORDER BY id DESC LIMIT ?",
        (product, limit),
    ).fetchall()
