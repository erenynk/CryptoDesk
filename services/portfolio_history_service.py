import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class PortfolioHistoryService:
    """
    Caspian portföy geçmişi kayıtlarını yöneten SQLite servisi.

    Görevleri:
    - portfolio_history tablosunu oluşturmak
    - Portföy snapshot kayıtlarını saklamak
    - Belirli bir zamana en yakın kaydı bulmak
    - Son kayıtları listelemek
    - Eski kayıtları optimize etmek
    """

    DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 300
    APP_TIMEZONE = timezone(timedelta(hours=3))

    def __init__(
        self,
        db_path: str | Path | None = None,
        snapshot_interval_seconds: int = DEFAULT_SNAPSHOT_INTERVAL_SECONDS,
    ):
        self.db_path = Path(db_path) if db_path else self._get_default_db_path()
        self.snapshot_interval_seconds = max(0, int(snapshot_interval_seconds))
        self._lock = Lock()

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_database()

    @staticmethod
    def _get_default_db_path() -> Path:
        """
        Windows:
            C:\\Users\\<kullanıcı>\\AppData\\Local\\Caspian\\caspian.db

        Diğer işletim sistemlerinde güvenli bir kullanıcı veri klasörü kullanılır.
        """
        local_app_data = os.getenv("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / "Caspian" / "caspian.db"

        return Path.home() / ".caspian" / "caspian.db"

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.db_path,
            timeout=10,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row

        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")

        return connection

    def _initialize_database(self) -> None:
        with self._lock:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS portfolio_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        total_usdt REAL NOT NULL DEFAULT 0,
                        funding_usdt REAL NOT NULL DEFAULT 0,
                        trading_usdt REAL NOT NULL DEFAULT 0,
                        asset_count INTEGER NOT NULL DEFAULT 0
                    )
                    """
                )

                connection.execute(
                    """
                    CREATE INDEX IF NOT EXISTS
                    idx_portfolio_history_timestamp
                    ON portfolio_history(timestamp)
                    """
                )

                self._ensure_column(
                    connection=connection,
                    column_name="asset_count",
                    column_definition="INTEGER NOT NULL DEFAULT 0",
                )

                connection.commit()

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection,
        column_name: str,
        column_definition: str,
    ) -> None:
        columns = connection.execute(
            "PRAGMA table_info(portfolio_history)"
        ).fetchall()

        existing_columns = {
            str(column["name"])
            for column in columns
        }

        if column_name not in existing_columns:
            connection.execute(
                f"""
                ALTER TABLE portfolio_history
                ADD COLUMN {column_name} {column_definition}
                """
            )

    @classmethod
    def _now(cls) -> datetime:
        return datetime.now(cls.APP_TIMEZONE)

    @classmethod
    def _normalize_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=cls.APP_TIMEZONE)

        return value.astimezone(cls.APP_TIMEZONE)

    @classmethod
    def _datetime_to_storage(cls, value: datetime) -> str:
        normalized = cls._normalize_datetime(value)
        return normalized.isoformat(timespec="seconds")

    @classmethod
    def _storage_to_datetime(cls, value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        return cls._normalize_datetime(parsed)

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return max(0, int(value))
        except (TypeError, ValueError, OverflowError):
            return 0

    def save_snapshot(
        self,
        total_usdt: float,
        funding_usdt: float = 0.0,
        trading_usdt: float = 0.0,
        asset_count: int = 0,
        timestamp: datetime | None = None,
        force: bool = False,
    ) -> bool:
        """
        Yeni portföy snapshot kaydı oluşturur.

        force=False olduğunda, son kayıt belirtilen snapshot aralığından
        daha yeniyse tekrar kayıt oluşturmaz.

        Returns:
            True: Yeni kayıt oluşturuldu.
            False: Kayıt aralık kontrolü nedeniyle atlandı.
        """
        snapshot_time = self._normalize_datetime(timestamp or self._now())
        snapshot_time_text = self._datetime_to_storage(snapshot_time)

        total_value = self._safe_float(total_usdt)
        funding_value = self._safe_float(funding_usdt)
        trading_value = self._safe_float(trading_usdt)
        assets_value = self._safe_int(asset_count)

        with self._lock:
            with self._connect() as connection:
                if not force and not self._should_save_snapshot(
                    connection=connection,
                    snapshot_time=snapshot_time,
                ):
                    return False

                connection.execute(
                    """
                    INSERT INTO portfolio_history (
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        snapshot_time_text,
                        total_value,
                        funding_value,
                        trading_value,
                        assets_value,
                    ),
                )

                connection.commit()
                return True

    def _should_save_snapshot(
        self,
        connection: sqlite3.Connection,
        snapshot_time: datetime,
    ) -> bool:
        if self.snapshot_interval_seconds <= 0:
            return True

        row = connection.execute(
            """
            SELECT timestamp
            FROM portfolio_history
            ORDER BY timestamp DESC
            LIMIT 1
            """
        ).fetchone()

        if row is None:
            return True

        try:
            last_snapshot_time = self._storage_to_datetime(row["timestamp"])
        except (TypeError, ValueError):
            return True

        elapsed_seconds = (
            self._normalize_datetime(snapshot_time) - last_snapshot_time
        ).total_seconds()

        return elapsed_seconds >= self.snapshot_interval_seconds

    def get_latest_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        id,
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    FROM portfolio_history
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """
                ).fetchone()

        return self._row_to_dict(row)

    def get_oldest_snapshot(self) -> dict[str, Any] | None:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        id,
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    FROM portfolio_history
                    ORDER BY timestamp ASC
                    LIMIT 1
                    """
                ).fetchone()

        return self._row_to_dict(row)

    def get_snapshot_at_or_before(
        self,
        target_time: datetime,
    ) -> dict[str, Any] | None:
        target_time_text = self._datetime_to_storage(target_time)

        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        id,
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    FROM portfolio_history
                    WHERE timestamp <= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (target_time_text,),
                ).fetchone()

        return self._row_to_dict(row)

    def get_snapshot_nearest(
        self,
        target_time: datetime,
    ) -> dict[str, Any] | None:
        """
        Hedef zamana en yakın snapshot kaydını döndürür.
        """
        target_time_local = self._normalize_datetime(target_time)
        target_time_text = self._datetime_to_storage(target_time_local)

        with self._lock:
            with self._connect() as connection:
                before_row = connection.execute(
                    """
                    SELECT
                        id,
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    FROM portfolio_history
                    WHERE timestamp <= ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (target_time_text,),
                ).fetchone()

                after_row = connection.execute(
                    """
                    SELECT
                        id,
                        timestamp,
                        total_usdt,
                        funding_usdt,
                        trading_usdt,
                        asset_count
                    FROM portfolio_history
                    WHERE timestamp > ?
                    ORDER BY timestamp ASC
                    LIMIT 1
                    """,
                    (target_time_text,),
                ).fetchone()

        if before_row is None:
            return self._row_to_dict(after_row)

        if after_row is None:
            return self._row_to_dict(before_row)

        before_time = self._storage_to_datetime(before_row["timestamp"])
        after_time = self._storage_to_datetime(after_row["timestamp"])

        before_difference = abs(
            (target_time_local - before_time).total_seconds()
        )
        after_difference = abs(
            (after_time - target_time_local).total_seconds()
        )

        selected_row = (
            before_row
            if before_difference <= after_difference
            else after_row
        )

        return self._row_to_dict(selected_row)

    def get_snapshots(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int | None = None,
        ascending: bool = True,
    ) -> list[dict[str, Any]]:
        conditions = []
        parameters: list[Any] = []

        if start_time is not None:
            conditions.append("timestamp >= ?")
            parameters.append(self._datetime_to_storage(start_time))

        if end_time is not None:
            conditions.append("timestamp <= ?")
            parameters.append(self._datetime_to_storage(end_time))

        query = """
            SELECT
                id,
                timestamp,
                total_usdt,
                funding_usdt,
                trading_usdt,
                asset_count
            FROM portfolio_history
        """

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY timestamp "
        query += "ASC" if ascending else "DESC"

        if limit is not None:
            safe_limit = max(1, int(limit))
            query += " LIMIT ?"
            parameters.append(safe_limit)

        with self._lock:
            with self._connect() as connection:
                rows = connection.execute(
                    query,
                    tuple(parameters),
                ).fetchall()

        return [
            snapshot
            for row in rows
            if (snapshot := self._row_to_dict(row)) is not None
        ]

    def get_snapshot_count(self) -> int:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT COUNT(*) AS snapshot_count
                    FROM portfolio_history
                    """
                ).fetchone()

        if row is None:
            return 0

        return int(row["snapshot_count"])

    def optimize_history(
        self,
        detailed_days: int = 30,
        hourly_days: int = 90,
        daily_days: int = 730,
    ) -> int:
        """
        Eski kayıtların sayısını azaltır.

        Saklama stratejisi:
        - Son detailed_days: tüm kayıtlar
        - detailed_days ile hourly_days arası: saat başına bir kayıt
        - hourly_days ile daily_days arası: gün başına bir kayıt
        - daily_days değerinden eski kayıtlar: silinir

        Returns:
            Silinen toplam kayıt sayısı.
        """
        detailed_days = max(1, int(detailed_days))
        hourly_days = max(detailed_days + 1, int(hourly_days))
        daily_days = max(hourly_days + 1, int(daily_days))

        now = self._now()
        detailed_cutoff = now - timedelta(days=detailed_days)
        hourly_cutoff = now - timedelta(days=hourly_days)
        daily_cutoff = now - timedelta(days=daily_days)

        deleted_count = 0

        with self._lock:
            with self._connect() as connection:
                deleted_count += self._delete_older_than(
                    connection=connection,
                    cutoff=daily_cutoff,
                )

                deleted_count += self._deduplicate_period(
                    connection=connection,
                    start_time=hourly_cutoff,
                    end_time=detailed_cutoff,
                    grouping_format="%Y-%m-%dT%H",
                )

                deleted_count += self._deduplicate_period(
                    connection=connection,
                    start_time=daily_cutoff,
                    end_time=hourly_cutoff,
                    grouping_format="%Y-%m-%d",
                )

                connection.commit()

                if deleted_count > 0:
                    connection.execute("PRAGMA optimize")

        return deleted_count

    def _delete_older_than(
        self,
        connection: sqlite3.Connection,
        cutoff: datetime,
    ) -> int:
        cursor = connection.execute(
            """
            DELETE FROM portfolio_history
            WHERE timestamp < ?
            """,
            (self._datetime_to_storage(cutoff),),
        )

        return max(0, cursor.rowcount)

    def _deduplicate_period(
        self,
        connection: sqlite3.Connection,
        start_time: datetime,
        end_time: datetime,
        grouping_format: str,
    ) -> int:
        rows = connection.execute(
            """
            SELECT id, timestamp
            FROM portfolio_history
            WHERE timestamp >= ?
              AND timestamp < ?
            ORDER BY timestamp ASC
            """,
            (
                self._datetime_to_storage(start_time),
                self._datetime_to_storage(end_time),
            ),
        ).fetchall()

        ids_to_delete: list[int] = []
        seen_groups: set[str] = set()

        for row in rows:
            try:
                timestamp = self._storage_to_datetime(row["timestamp"])
            except (TypeError, ValueError):
                continue

            group_key = timestamp.strftime(grouping_format)

            if group_key in seen_groups:
                ids_to_delete.append(int(row["id"]))
            else:
                seen_groups.add(group_key)

        if not ids_to_delete:
            return 0

        placeholders = ",".join("?" for _ in ids_to_delete)

        cursor = connection.execute(
            f"""
            DELETE FROM portfolio_history
            WHERE id IN ({placeholders})
            """,
            tuple(ids_to_delete),
        )

        return max(0, cursor.rowcount)

    def clear_history(self) -> int:
        """
        Tüm portföy geçmişini siler.

        Uygulama akışında otomatik kullanılmamalıdır.
        """
        with self._lock:
            with self._connect() as connection:
                cursor = connection.execute(
                    "DELETE FROM portfolio_history"
                )
                connection.commit()

        return max(0, cursor.rowcount)

    @staticmethod
    def _row_to_dict(
        row: sqlite3.Row | None,
    ) -> dict[str, Any] | None:
        if row is None:
            return None

        return {
            "id": int(row["id"]),
            "timestamp": str(row["timestamp"]),
            "total_usdt": float(row["total_usdt"]),
            "funding_usdt": float(row["funding_usdt"]),
            "trading_usdt": float(row["trading_usdt"]),
            "asset_count": int(row["asset_count"]),
        }
