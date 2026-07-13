import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from security.dpapi import decrypt, encrypt


APP_DIR = Path.home() / "AppData" / "Local" / "CryptoDesk"
APP_DIR.mkdir(parents=True, exist_ok=True)

CONFIG = APP_DIR / "config.json"
DB_PATH = APP_DIR / "cryptodesk.db"

DEFAULT_APP_SETTINGS = {
    "windows_startup_enabled": False,
    "balance_widget_enabled": True,
    "minimize_to_tray_enabled": True,
    "notifications_enabled": True,
    "alarm_sound_enabled": False,
    "refresh_on_start_enabled": True,
    "portfolio_history_enabled": True,
}


def _get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


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

        column_names = [column["name"] for column in columns]

        if "added_price" not in column_names:
            conn.execute(
                """
                ALTER TABLE watchlist_symbols
                ADD COLUMN added_price REAL
                """
            )


def _init_price_alarms_table():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_alarms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                target_price REAL NOT NULL,
                condition TEXT NOT NULL
                    CHECK(condition IN ('above', 'below')),
                note TEXT NOT NULL DEFAULT '',
                is_active INTEGER NOT NULL DEFAULT 1
                    CHECK(is_active IN (0, 1)),
                is_triggered INTEGER NOT NULL DEFAULT 0
                    CHECK(is_triggered IN (0, 1)),
                created_at TEXT NOT NULL,
                triggered_at TEXT
            )
        """)

        columns = conn.execute(
            "PRAGMA table_info(price_alarms)"
        ).fetchall()

        column_names = [column["name"] for column in columns]

        if "note" not in column_names:
            conn.execute("""
                ALTER TABLE price_alarms
                ADD COLUMN note TEXT NOT NULL DEFAULT ''
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_alarms_active
            ON price_alarms(is_active, is_triggered)
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_price_alarms_symbol
            ON price_alarms(symbol)
        """)


def _init_app_settings_table():
    with _get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_settings (
                setting_key TEXT PRIMARY KEY,
                setting_value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        now = datetime.now(UTC).isoformat()

        for key, value in DEFAULT_APP_SETTINGS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO app_settings (
                    setting_key,
                    setting_value,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    key,
                    json.dumps(value),
                    now,
                ),
            )


_init_watchlist_table()
_init_price_alarms_table()
_init_app_settings_table()


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

    try:
        data = json.loads(CONFIG.read_text(encoding="utf-8"))

        return (
            decrypt(data["api"]),
            decrypt(data["secret"]),
            decrypt(data["passphrase"]),
        )

    except (OSError, json.JSONDecodeError, KeyError, TypeError):
        return "", "", ""


def get_app_setting(
    key: str,
    default: Any = None,
) -> Any:
    normalized_key = str(key or "").strip()

    if not normalized_key:
        return default

    try:
        with _get_connection() as conn:
            row = conn.execute(
                """
                SELECT setting_value
                FROM app_settings
                WHERE setting_key = ?
                """,
                (normalized_key,),
            ).fetchone()

        if row is None:
            return default

        return json.loads(row["setting_value"])

    except (
        sqlite3.Error,
        json.JSONDecodeError,
        TypeError,
    ):
        return default


def set_app_setting(
    key: str,
    value: Any,
) -> bool:
    normalized_key = str(key or "").strip()

    if not normalized_key:
        return False

    try:
        serialized_value = json.dumps(value)
        updated_at = datetime.now(UTC).isoformat()

        with _get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (
                    setting_key,
                    setting_value,
                    updated_at
                )
                VALUES (?, ?, ?)
                ON CONFLICT(setting_key)
                DO UPDATE SET
                    setting_value = excluded.setting_value,
                    updated_at = excluded.updated_at
                """,
                (
                    normalized_key,
                    serialized_value,
                    updated_at,
                ),
            )

        return True

    except (
        sqlite3.Error,
        TypeError,
        ValueError,
    ):
        return False


def get_all_app_settings() -> dict[str, Any]:
    settings = DEFAULT_APP_SETTINGS.copy()

    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    setting_key,
                    setting_value
                FROM app_settings
                """
            ).fetchall()

        for row in rows:
            key = row["setting_key"]

            try:
                settings[key] = json.loads(
                    row["setting_value"]
                )
            except (json.JSONDecodeError, TypeError):
                continue

    except sqlite3.Error:
        pass

    return settings


def save_app_settings(
    settings: dict[str, Any],
) -> bool:
    if not isinstance(settings, dict):
        return False

    try:
        updated_at = datetime.now(UTC).isoformat()

        with _get_connection() as conn:
            for key, value in settings.items():
                normalized_key = str(key or "").strip()

                if not normalized_key:
                    continue

                conn.execute(
                    """
                    INSERT INTO app_settings (
                        setting_key,
                        setting_value,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(setting_key)
                    DO UPDATE SET
                        setting_value = excluded.setting_value,
                        updated_at = excluded.updated_at
                    """,
                    (
                        normalized_key,
                        json.dumps(value),
                        updated_at,
                    ),
                )

        return True

    except (
        sqlite3.Error,
        TypeError,
        ValueError,
    ):
        return False


def reset_app_settings() -> bool:
    try:
        updated_at = datetime.now(UTC).isoformat()

        with _get_connection() as conn:
            for key, value in DEFAULT_APP_SETTINGS.items():
                conn.execute(
                    """
                    INSERT INTO app_settings (
                        setting_key,
                        setting_value,
                        updated_at
                    )
                    VALUES (?, ?, ?)
                    ON CONFLICT(setting_key)
                    DO UPDATE SET
                        setting_value = excluded.setting_value,
                        updated_at = excluded.updated_at
                    """,
                    (
                        key,
                        json.dumps(value),
                        updated_at,
                    ),
                )

        return True

    except (
        sqlite3.Error,
        TypeError,
        ValueError,
    ):
        return False


def add_watchlist_symbol(
    symbol: str,
    added_price: float | None = None,
) -> bool:
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
                """
                DELETE FROM watchlist_symbols
                WHERE symbol = ?
                """,
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

            return [row["symbol"] for row in rows]

    except sqlite3.Error:
        return []


def get_watchlist_items() -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    symbol,
                    added_price,
                    created_at
                FROM watchlist_symbols
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()

            return [
                {
                    "symbol": row["symbol"],
                    "added_price": row["added_price"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

    except sqlite3.Error:
        return []


def add_price_alarm(
    symbol: str,
    target_price: float,
    condition: str,
    note: str = "",
) -> int | None:
    normalized = _normalize_symbol(symbol)
    normalized_condition = condition.strip().lower()
    normalized_note = str(note or "").strip()

    if not normalized:
        return None

    if target_price <= 0:
        return None

    if normalized_condition not in {"above", "below"}:
        return None

    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO price_alarms (
                    symbol,
                    target_price,
                    condition,
                    note,
                    is_active,
                    is_triggered,
                    created_at,
                    triggered_at
                )
                VALUES (?, ?, ?, ?, 1, 0, ?, NULL)
                """,
                (
                    normalized,
                    float(target_price),
                    normalized_condition,
                    normalized_note,
                    datetime.now(UTC).isoformat(),
                ),
            )

            return cursor.lastrowid

    except sqlite3.Error:
        return None


def get_price_alarms() -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    symbol,
                    target_price,
                    condition,
                    note,
                    is_active,
                    is_triggered,
                    created_at,
                    triggered_at
                FROM price_alarms
                ORDER BY created_at DESC, id DESC
                """
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "target_price": row["target_price"],
                    "condition": row["condition"],
                    "note": row["note"] or "",
                    "is_active": bool(row["is_active"]),
                    "is_triggered": bool(row["is_triggered"]),
                    "created_at": row["created_at"],
                    "triggered_at": row["triggered_at"],
                }
                for row in rows
            ]

    except sqlite3.Error:
        return []


def get_active_price_alarms() -> list[dict]:
    try:
        with _get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    id,
                    symbol,
                    target_price,
                    condition,
                    note,
                    is_active,
                    is_triggered,
                    created_at,
                    triggered_at
                FROM price_alarms
                WHERE is_active = 1
                  AND is_triggered = 0
                ORDER BY created_at ASC, id ASC
                """
            ).fetchall()

            return [
                {
                    "id": row["id"],
                    "symbol": row["symbol"],
                    "target_price": row["target_price"],
                    "condition": row["condition"],
                    "note": row["note"] or "",
                    "is_active": bool(row["is_active"]),
                    "is_triggered": bool(row["is_triggered"]),
                    "created_at": row["created_at"],
                    "triggered_at": row["triggered_at"],
                }
                for row in rows
            ]

    except sqlite3.Error:
        return []


def set_price_alarm_active(
    alarm_id: int,
    is_active: bool,
) -> bool:
    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE price_alarms
                SET is_active = ?
                WHERE id = ?
                """,
                (
                    1 if is_active else 0,
                    alarm_id,
                ),
            )

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def mark_price_alarm_triggered(alarm_id: int) -> bool:
    triggered_at = datetime.now(UTC).isoformat()

    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                UPDATE price_alarms
                SET
                    is_active = 0,
                    is_triggered = 1,
                    triggered_at = ?
                WHERE id = ?
                  AND is_triggered = 0
                """,
                (
                    triggered_at,
                    alarm_id,
                ),
            )

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False


def delete_price_alarm(alarm_id: int) -> bool:
    try:
        with _get_connection() as conn:
            cursor = conn.execute(
                """
                DELETE FROM price_alarms
                WHERE id = ?
                """,
                (alarm_id,),
            )

            return cursor.rowcount > 0

    except sqlite3.Error:
        return False
