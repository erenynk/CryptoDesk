import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from typing import Any


class PortfolioHistoryService:
    """
    CryptoDesk portföy geçmişi kayıtlarını ve performans hesaplarını yönetir.
    """

    DEFAULT_SNAPSHOT_INTERVAL_SECONDS = 300
    APP_TIMEZONE = timezone(timedelta(hours=3))

    PERFORMANCE_PERIODS = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }

    HISTORY_RANGES = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }

    MAX_REFERENCE_AGE = {
        "1d": timedelta(hours=6),
        "7d": timedelta(days=1),
        "30d": timedelta(days=3),
        "90d": timedelta(days=7),
        "1y": timedelta(days=30),
    }

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
        local_app_data = os.getenv("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / "CryptoDesk" / "cryptodesk.db"

        return Path.home() / ".cryptodesk" / "cryptodesk.db"

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

    def calculate_performance(
        self,
        current_total_usdt: float,
        reference_time: datetime | None = None,
        value_field: str = "total_usdt",
    ) -> dict[str, float | None]:
        """
        Seçilen portföy alanının dönemsel yüzde değişimini hesaplar.

        Desteklenen value_field değerleri:
        - total_usdt
        - funding_usdt
        - trading_usdt

        İlgili dönemi kapsayan yeterli geçmiş yoksa None döndürülür.
        """
        allowed_fields = {
            "total_usdt",
            "funding_usdt",
            "trading_usdt",
        }

        if value_field not in allowed_fields:
            raise ValueError(
                f"Geçersiz performans alanı: {value_field}"
            )

        current_total = self._safe_float(current_total_usdt)
        current_time = self._normalize_datetime(
            reference_time or self._now()
        )
        oldest_snapshot = self.get_oldest_snapshot()

        performance: dict[str, float | None] = {}

        if oldest_snapshot is None:
            return {
                period_key: None
                for period_key in self.PERFORMANCE_PERIODS
            }

        try:
            oldest_time = self._storage_to_datetime(
                oldest_snapshot["timestamp"]
            )
        except (KeyError, TypeError, ValueError):
            return {
                period_key: None
                for period_key in self.PERFORMANCE_PERIODS
            }

        for period_key, period_delta in self.PERFORMANCE_PERIODS.items():
            target_time = current_time - period_delta

            if oldest_time > target_time:
                performance[period_key] = None
                continue

            snapshot = self.get_snapshot_at_or_before(target_time)

            if snapshot is None:
                performance[period_key] = None
                continue

            try:
                snapshot_time = self._storage_to_datetime(
                    snapshot["timestamp"]
                )
            except (KeyError, TypeError, ValueError):
                performance[period_key] = None
                continue

            reference_age = target_time - snapshot_time

            if (
                reference_age < timedelta(0)
                or reference_age
                > self.MAX_REFERENCE_AGE[period_key]
            ):
                performance[period_key] = None
                continue

            previous_total = self._safe_float(
                snapshot.get(value_field)
            )

            if previous_total <= 0:
                performance[period_key] = None
                continue

            percentage_change = (
                (current_total - previous_total) / previous_total
            ) * 100

            performance[period_key] = round(
                percentage_change,
                2,
            )

        return performance

    def calculate_performance_breakdown(
        self,
        current_total_usdt: float,
        current_funding_usdt: float,
        current_trading_usdt: float,
        reference_time: datetime | None = None,
    ) -> dict[str, dict[str, float | None]]:
        """
        Toplam, Funding ve Trading performanslarını ayrı hesaplar.
        """
        return {
            "total": self.calculate_performance(
                current_total_usdt=current_total_usdt,
                reference_time=reference_time,
                value_field="total_usdt",
            ),
            "funding": self.calculate_performance(
                current_total_usdt=current_funding_usdt,
                reference_time=reference_time,
                value_field="funding_usdt",
            ),
            "trading": self.calculate_performance(
                current_total_usdt=current_trading_usdt,
                reference_time=reference_time,
                value_field="trading_usdt",
            ),
        }

    def calculate_portfolio_analytics(
        self,
        current_total_usdt: float,
        current_funding_usdt: float,
        current_trading_usdt: float,
        reference_time: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Portföy geçmişinden analiz metrikleri üretir.

        Dönemsel değişimler yeterli geçmiş yoksa None döndürür.
        Özet değerler mevcut tüm snapshot kayıtlarından hesaplanır.
        """
        current_time = self._normalize_datetime(
            reference_time or self._now()
        )

        current_values = {
            "total": self._safe_float(current_total_usdt),
            "funding": self._safe_float(current_funding_usdt),
            "trading": self._safe_float(current_trading_usdt),
        }
        field_map = {
            "total": "total_usdt",
            "funding": "funding_usdt",
            "trading": "trading_usdt",
        }

        period_changes: dict[str, dict[str, Any]] = {}
        oldest_snapshot = self.get_oldest_snapshot()

        oldest_time = None

        if oldest_snapshot is not None:
            try:
                oldest_time = self._storage_to_datetime(
                    oldest_snapshot["timestamp"]
                )
            except (KeyError, TypeError, ValueError):
                oldest_time = None

        for period_key, period_delta in self.PERFORMANCE_PERIODS.items():
            target_time = current_time - period_delta
            period_result: dict[str, Any] = {}

            if oldest_time is None or oldest_time > target_time:
                for account_name in field_map:
                    period_result[account_name] = {
                        "amount_usdt": None,
                        "percent": None,
                        "baseline_usdt": None,
                        "baseline_timestamp": None,
                    }

                period_changes[period_key] = period_result
                continue

            snapshot = self.get_snapshot_at_or_before(target_time)

            snapshot_is_valid = False

            if snapshot is not None:
                try:
                    snapshot_time = self._storage_to_datetime(
                        snapshot["timestamp"]
                    )
                    reference_age = target_time - snapshot_time
                    snapshot_is_valid = (
                        reference_age >= timedelta(0)
                        and reference_age
                        <= self.MAX_REFERENCE_AGE[period_key]
                    )
                except (KeyError, TypeError, ValueError):
                    snapshot_is_valid = False

            for account_name, field_name in field_map.items():
                if not snapshot_is_valid:
                    period_result[account_name] = {
                        "amount_usdt": None,
                        "percent": None,
                        "baseline_usdt": None,
                        "baseline_timestamp": None,
                    }
                    continue

                baseline = self._safe_float(snapshot.get(field_name))
                current_value = current_values[account_name]

                if baseline <= 0:
                    amount_change = None
                    percent_change = None
                else:
                    amount_change = round(current_value - baseline, 8)
                    percent_change = round(
                        ((current_value - baseline) / baseline) * 100,
                        2,
                    )

                period_result[account_name] = {
                    "amount_usdt": amount_change,
                    "percent": percent_change,
                    "baseline_usdt": baseline,
                    "baseline_timestamp": snapshot.get("timestamp"),
                }

            period_changes[period_key] = period_result

        summary = self._calculate_history_summary()

        return {
            "period_changes": period_changes,
            "summary": summary,
        }

    def _calculate_history_summary(self) -> dict[str, Any]:
        with self._lock:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT
                        COUNT(*) AS snapshot_count,
                        MIN(timestamp) AS first_timestamp,
                        MAX(timestamp) AS last_timestamp,
                        MAX(total_usdt) AS highest_total_usdt,
                        MIN(total_usdt) AS lowest_total_usdt,
                        AVG(total_usdt) AS average_total_usdt,
                        MAX(funding_usdt) AS highest_funding_usdt,
                        MIN(funding_usdt) AS lowest_funding_usdt,
                        AVG(funding_usdt) AS average_funding_usdt,
                        MAX(trading_usdt) AS highest_trading_usdt,
                        MIN(trading_usdt) AS lowest_trading_usdt,
                        AVG(trading_usdt) AS average_trading_usdt
                    FROM portfolio_history
                    """
                ).fetchone()

        if row is None or int(row["snapshot_count"] or 0) == 0:
            return {
                "snapshot_count": 0,
                "first_timestamp": None,
                "last_timestamp": None,
                "total": self._empty_summary_group(),
                "funding": self._empty_summary_group(),
                "trading": self._empty_summary_group(),
            }

        return {
            "snapshot_count": int(row["snapshot_count"]),
            "first_timestamp": row["first_timestamp"],
            "last_timestamp": row["last_timestamp"],
            "total": {
                "highest_usdt": self._nullable_float(
                    row["highest_total_usdt"]
                ),
                "lowest_usdt": self._nullable_float(
                    row["lowest_total_usdt"]
                ),
                "average_usdt": self._nullable_float(
                    row["average_total_usdt"]
                ),
            },
            "funding": {
                "highest_usdt": self._nullable_float(
                    row["highest_funding_usdt"]
                ),
                "lowest_usdt": self._nullable_float(
                    row["lowest_funding_usdt"]
                ),
                "average_usdt": self._nullable_float(
                    row["average_funding_usdt"]
                ),
            },
            "trading": {
                "highest_usdt": self._nullable_float(
                    row["highest_trading_usdt"]
                ),
                "lowest_usdt": self._nullable_float(
                    row["lowest_trading_usdt"]
                ),
                "average_usdt": self._nullable_float(
                    row["average_trading_usdt"]
                ),
            },
        }

    @staticmethod
    def _nullable_float(value: Any) -> float | None:
        if value is None:
            return None

        try:
            number = float(value)

            if number != number:
                return None

            return number
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _empty_summary_group() -> dict[str, None]:
        return {
            "highest_usdt": None,
            "lowest_usdt": None,
            "average_usdt": None,
        }

    def get_history_series(
        self,
        period: str,
        reference_time: datetime | None = None,
        max_points: int = 500,
    ) -> list[dict[str, Any]]:
        if period not in self.HISTORY_RANGES:
            raise ValueError(f"Geçersiz geçmiş dönemi: {period}")

        safe_max_points = max(2, int(max_points))
        end_time = self._normalize_datetime(
            reference_time or self._now()
        )
        start_time = end_time - self.HISTORY_RANGES[period]

        snapshots = self.get_snapshots(
            start_time=start_time,
            end_time=end_time,
            ascending=True,
        )

        if len(snapshots) <= safe_max_points:
            return snapshots

        last_index = len(snapshots) - 1
        step = last_index / (safe_max_points - 1)

        selected_indexes = {
            round(index * step)
            for index in range(safe_max_points)
        }
        selected_indexes.add(0)
        selected_indexes.add(last_index)

        return [
            snapshots[index]
            for index in sorted(selected_indexes)
        ]

    def get_available_history_periods(
        self,
        reference_time: datetime | None = None,
    ) -> dict[str, bool]:
        current_time = self._normalize_datetime(
            reference_time or self._now()
        )
        oldest_snapshot = self.get_oldest_snapshot()

        if oldest_snapshot is None:
            return {
                period: False
                for period in self.HISTORY_RANGES
            }

        try:
            oldest_time = self._storage_to_datetime(
                oldest_snapshot["timestamp"]
            )
        except (KeyError, TypeError, ValueError):
            return {
                period: False
                for period in self.HISTORY_RANGES
            }

        return {
            period: oldest_time <= current_time - delta
            for period, delta in self.HISTORY_RANGES.items()
        }

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
