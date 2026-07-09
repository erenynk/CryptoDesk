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
    conn = sqlite3.connect(DB_PATH)
    return conn


def _init_watchlist_table():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_symbols (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT UNIQUE NOT NULL,
                created_at TEXT
            )
        """)


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


def add_watchlist_symbol(symbol: str) -> bool:
    normalized = _normalize_symbol(symbol)

    if not normalized:
        return False

    try:
        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO watchlist_symbols (symbol, created_at)
                VALUES (?, ?)
                """,
                (normalized, datetime.now(UTC).isoformat()),
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