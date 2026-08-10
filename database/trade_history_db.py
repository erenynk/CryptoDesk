import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from app_paths import get_app_data_dir


DEFAULT_DB_PATH = get_app_data_dir() / "cryptodesk.db"

SORT_COLUMNS = {
    "coin": "coin",
    "side": "side",
    "quantity": "quantity",
    "price": "price",
    "total_usdt": "total_usdt",
    "pnl_usdt": "pnl_usdt",
    "pnl_percent": "pnl_percent",
    "executed_at": "executed_at_ms",
    "executed_at_ms": "executed_at_ms",
}


class TradeHistoryRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path or DEFAULT_DB_PATH)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_table()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _init_table(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    transaction_key TEXT NOT NULL UNIQUE,
                    order_id TEXT NOT NULL,
                    instrument_id TEXT NOT NULL,
                    coin TEXT NOT NULL,
                    side TEXT NOT NULL
                        CHECK(side IN ('buy', 'sell')),
                    quantity REAL NOT NULL,
                    price REAL NOT NULL,
                    total_usdt REAL NOT NULL,
                    average_cost REAL,
                    cost_basis_usdt REAL,
                    pnl_usdt REAL,
                    pnl_percent REAL,
                    executed_at_ms INTEGER NOT NULL,
                    executed_at TEXT NOT NULL,
                    source_trade_ids TEXT NOT NULL DEFAULT '[]'
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trade_history_coin
                ON trade_history(coin)
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_trade_history_time
                ON trade_history(executed_at_ms DESC)
                """
            )

    @staticmethod
    def _normalize_transaction(
        transaction: dict[str, Any],
    ) -> dict[str, Any]:
        side = str(transaction.get("side", "")).strip().lower()
        if side not in {"buy", "sell"}:
            raise ValueError("Geçersiz işlem yönü.")

        transaction_key = str(
            transaction.get("transaction_key", "")
        ).strip()
        order_id = str(transaction.get("order_id", "")).strip()
        instrument_id = str(
            transaction.get("instrument_id", "")
        ).strip().upper()
        coin = str(transaction.get("coin", "")).strip().upper()
        executed_at = str(
            transaction.get("executed_at", "")
        ).strip()

        if not transaction_key:
            raise ValueError("transaction_key boş olamaz.")
        if not order_id:
            raise ValueError("order_id boş olamaz.")
        if not instrument_id:
            raise ValueError("instrument_id boş olamaz.")
        if not coin:
            raise ValueError("coin boş olamaz.")
        if not executed_at:
            raise ValueError("executed_at boş olamaz.")

        source_trade_ids = transaction.get(
            "source_trade_ids",
            [],
        )
        if not isinstance(source_trade_ids, list):
            source_trade_ids = []

        return {
            "transaction_key": transaction_key,
            "order_id": order_id,
            "instrument_id": instrument_id,
            "coin": coin,
            "side": side,
            "quantity": float(transaction.get("quantity", 0.0)),
            "price": float(transaction.get("price", 0.0)),
            "total_usdt": float(
                transaction.get("total_usdt", 0.0)
            ),
            "average_cost": transaction.get("average_cost"),
            "cost_basis_usdt": transaction.get(
                "cost_basis_usdt"
            ),
            "pnl_usdt": transaction.get("pnl_usdt"),
            "pnl_percent": transaction.get("pnl_percent"),
            "executed_at_ms": int(
                transaction.get("executed_at_ms", 0)
            ),
            "executed_at": executed_at,
            "source_trade_ids": json.dumps(
                [str(item) for item in source_trade_ids],
                ensure_ascii=False,
            ),
        }

    def upsert_many(
        self,
        transactions: Iterable[dict[str, Any]],
    ) -> int:
        normalized = [
            self._normalize_transaction(item)
            for item in transactions
        ]

        if not normalized:
            return 0

        with self._connect() as connection:
            for item in normalized:
                connection.execute(
                    """
                    INSERT INTO trade_history (
                        transaction_key,
                        order_id,
                        instrument_id,
                        coin,
                        side,
                        quantity,
                        price,
                        total_usdt,
                        average_cost,
                        cost_basis_usdt,
                        pnl_usdt,
                        pnl_percent,
                        executed_at_ms,
                        executed_at,
                        source_trade_ids
                    )
                    VALUES (
                        :transaction_key,
                        :order_id,
                        :instrument_id,
                        :coin,
                        :side,
                        :quantity,
                        :price,
                        :total_usdt,
                        :average_cost,
                        :cost_basis_usdt,
                        :pnl_usdt,
                        :pnl_percent,
                        :executed_at_ms,
                        :executed_at,
                        :source_trade_ids
                    )
                    ON CONFLICT(transaction_key)
                    DO UPDATE SET
                        order_id = excluded.order_id,
                        instrument_id = excluded.instrument_id,
                        coin = excluded.coin,
                        side = excluded.side,
                        quantity = excluded.quantity,
                        price = excluded.price,
                        total_usdt = excluded.total_usdt,
                        average_cost = excluded.average_cost,
                        cost_basis_usdt = excluded.cost_basis_usdt,
                        pnl_usdt = excluded.pnl_usdt,
                        pnl_percent = excluded.pnl_percent,
                        executed_at_ms = excluded.executed_at_ms,
                        executed_at = excluded.executed_at,
                        source_trade_ids = excluded.source_trade_ids
                    """,
                    item,
                )

        return len(normalized)

    def list_transactions(
        self,
        coin: str | None = None,
        sort_by: str = "executed_at_ms",
        descending: bool = True,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sort_column = SORT_COLUMNS.get(
            str(sort_by or "").strip(),
            "executed_at_ms",
        )
        direction = "DESC" if descending else "ASC"
        parameters: list[Any] = []
        where_sql = ""

        normalized_coin = str(coin or "").strip().upper()
        if normalized_coin:
            where_sql = "WHERE coin = ?"
            parameters.append(normalized_coin)

        limit_sql = ""
        if limit is not None:
            normalized_limit = max(1, int(limit))
            limit_sql = "LIMIT ?"
            parameters.append(normalized_limit)

        query = f"""
            SELECT
                transaction_key,
                order_id,
                instrument_id,
                coin,
                side,
                quantity,
                price,
                total_usdt,
                average_cost,
                cost_basis_usdt,
                pnl_usdt,
                pnl_percent,
                executed_at_ms,
                executed_at,
                source_trade_ids
            FROM trade_history
            {where_sql}
            ORDER BY {sort_column} {direction}, id {direction}
            {limit_sql}
        """

        with self._connect() as connection:
            rows = connection.execute(
                query,
                tuple(parameters),
            ).fetchall()

        result = []
        for row in rows:
            item = dict(row)
            try:
                item["source_trade_ids"] = json.loads(
                    item.get("source_trade_ids") or "[]"
                )
            except (json.JSONDecodeError, TypeError):
                item["source_trade_ids"] = []
            result.append(item)

        return result

    def count(self) -> int:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS total FROM trade_history"
            ).fetchone()

        return int(row["total"]) if row else 0
