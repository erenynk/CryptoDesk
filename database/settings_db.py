import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from security.dpapi import encrypt, decrypt


APP_DIR = Path.home() / "AppData" / "Local" / "CryptoDesk"
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = APP_DIR / "config.json"
DB_PATH = APP_DIR / "cryptodesk.db"


def _get_connection():
    return sqlite3.connect(DB_PATH)


def _init_watchlist_table():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                created_at TEXT,
                added_price REAL
            )
        """)

        columns = conn.execute(
            "PRAGMA table_info(watchlist_symbols)"
        ).fetchall()

        column_names = [column[1] for column in columns]

        if "added_price" not in column_names:
            conn.execute(
                "ALTER TABLE watchlist_symbols ADD COLUMN added_price REAL"
            )


_init_watchlist_table()


def _normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def save_settings(api, secret, passphrase):
    data = {
        "api": encrypt(api),
        "secret": encrypt(secret),
        "passphrase": encrypt(passphrase),
    }

    CONFIG.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )


def load_settings():
    if not CONFIG.exists():
        return "", "", ""

    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    return (
        decrypt(data["api"]),
        decrypt(data["secret"]),
        decrypt(data["passphrase"]),
    )


def add_watchlist_symbol(symbol: str, added_price: float | None = None) -> bool:
    normalized = _normalize_symbol(symbol)

    if not normalized:
        return False

    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO watchlist_symbols (
                    symbol,
                    created_at,
                    added_price
                )
                VALUES (?, ?, ?)
                """,
                (
                    normalized,
                    datetime.now(UTC).isoformat(),
                    added_price,
                ),
            )
        return True

    except sqlite3.IntegrityError:
        return False


def remove_watchlist_symbol(symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)

    if not normalized:
        return False

    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM watchlist_symbols WHERE symbol = ?",
                (normalized,),
            )
            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def get_watchlist_symbols() -> list[str]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT symbol
                FROM watchlist_symbols
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()

            return [row[0] for row in rows]

    except sqlite3.Error:
        return []


def get_watchlist_items() -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT symbol, added_price, created_at
                FROM watchlist_symbols
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()

            return [
                {
                    "symbol": row[0],
                    "added_price": row[1],
                    "created_at": row[2],
                }
                for row in rows
            ]

    except sqlite3.Error:
        return []