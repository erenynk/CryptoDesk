import sqlite3
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

from services.portfolio_history_service import (
    PortfolioHistoryService,
)


class InMemoryPortfolioHistoryService(
    PortfolioHistoryService
):
    def __init__(
        self,
        snapshot_interval_seconds=(
            PortfolioHistoryService
            .DEFAULT_SNAPSHOT_INTERVAL_SECONDS
        ),
    ):
        self.db_path = Path(":memory:")
        self.snapshot_interval_seconds = max(
            0,
            int(snapshot_interval_seconds),
        )
        self._lock = Lock()
        self._connection = sqlite3.connect(
            ":memory:",
            check_same_thread=False,
        )
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            "PRAGMA foreign_keys = ON"
        )
        self._initialize_database()

    def _connect(self):
        return self._connection

    def close(self):
        self._connection.close()


class PortfolioHistoryServiceTestCase(
    unittest.TestCase
):
    def setUp(self):
        self.service = InMemoryPortfolioHistoryService(
            snapshot_interval_seconds=300
        )
        self.timezone = self.service.APP_TIMEZONE
        self.reference_time = datetime(
            2026,
            7,
            19,
            12,
            0,
            0,
            tzinfo=self.timezone,
        )

    def tearDown(self):
        self.service.close()

    def save(
        self,
        *,
        minutes=0,
        days=0,
        total=100.0,
        funding=40.0,
        trading=60.0,
        asset_count=2,
        force=True,
    ):
        timestamp = (
            self.reference_time
            + timedelta(
                days=days,
                minutes=minutes,
            )
        )

        return self.service.save_snapshot(
            total_usdt=total,
            funding_usdt=funding,
            trading_usdt=trading,
            asset_count=asset_count,
            timestamp=timestamp,
            force=force,
        )

    def snapshot(
        self,
        *,
        timestamp,
        total=100.0,
        funding=40.0,
        trading=60.0,
        asset_count=2,
    ):
        return {
            "id": 1,
            "timestamp": (
                self.service
                ._datetime_to_storage(timestamp)
            ),
            "total_usdt": total,
            "funding_usdt": funding,
            "trading_usdt": trading,
            "asset_count": asset_count,
        }

    def test_database_schema_and_index_are_initialized(
        self,
    ):
        with self.service._connect() as connection:
            columns = {
                row["name"]
                for row in connection.execute(
                    """
                    PRAGMA table_info(
                        portfolio_history
                    )
                    """
                ).fetchall()
            }
            indexes = {
                row["name"]
                for row in connection.execute(
                    """
                    PRAGMA index_list(
                        portfolio_history
                    )
                    """
                ).fetchall()
            }

        self.assertEqual(
            columns,
            {
                "id",
                "timestamp",
                "total_usdt",
                "funding_usdt",
                "trading_usdt",
                "asset_count",
            },
        )
        self.assertIn(
            "idx_portfolio_history_timestamp",
            indexes,
        )

    def test_save_snapshot_normalizes_invalid_values(
        self,
    ):
        result = self.service.save_snapshot(
            total_usdt="invalid",
            funding_usdt=float("nan"),
            trading_usdt=None,
            asset_count=-5,
            timestamp=self.reference_time,
            force=True,
        )

        self.assertTrue(result)

        snapshot = self.service.get_latest_snapshot()

        self.assertEqual(
            snapshot["total_usdt"],
            0.0,
        )
        self.assertEqual(
            snapshot["funding_usdt"],
            0.0,
        )
        self.assertEqual(
            snapshot["trading_usdt"],
            0.0,
        )
        self.assertEqual(
            snapshot["asset_count"],
            0,
        )

    def test_snapshot_interval_blocks_early_record(
        self,
    ):
        self.assertTrue(
            self.save(
                minutes=0,
                force=False,
            )
        )
        self.assertFalse(
            self.save(
                minutes=4,
                total=110.0,
                force=False,
            )
        )
        self.assertTrue(
            self.save(
                minutes=5,
                total=120.0,
                force=False,
            )
        )
        self.assertEqual(
            self.service.get_snapshot_count(),
            2,
        )

    def test_force_bypasses_snapshot_interval(self):
        self.assertTrue(
            self.save(
                minutes=0,
                force=False,
            )
        )
        self.assertTrue(
            self.save(
                minutes=1,
                total=110.0,
                force=True,
            )
        )
        self.assertEqual(
            self.service.get_snapshot_count(),
            2,
        )

    def test_latest_oldest_and_at_or_before_queries(
        self,
    ):
        self.save(
            minutes=0,
            total=100.0,
        )
        self.save(
            minutes=10,
            total=110.0,
        )
        self.save(
            minutes=20,
            total=120.0,
        )

        oldest = self.service.get_oldest_snapshot()
        latest = self.service.get_latest_snapshot()
        selected = (
            self.service.get_snapshot_at_or_before(
                self.reference_time
                + timedelta(minutes=15)
            )
        )

        self.assertEqual(
            oldest["total_usdt"],
            100.0,
        )
        self.assertEqual(
            latest["total_usdt"],
            120.0,
        )
        self.assertEqual(
            selected["total_usdt"],
            110.0,
        )

    def test_nearest_snapshot_selects_closest_record(
        self,
    ):
        self.save(
            minutes=0,
            total=100.0,
        )
        self.save(
            minutes=10,
            total=110.0,
        )

        before = self.service.get_snapshot_nearest(
            self.reference_time
            + timedelta(minutes=4)
        )
        after = self.service.get_snapshot_nearest(
            self.reference_time
            + timedelta(minutes=6)
        )

        self.assertEqual(
            before["total_usdt"],
            100.0,
        )
        self.assertEqual(
            after["total_usdt"],
            110.0,
        )

    def test_nearest_snapshot_prefers_before_on_tie(
        self,
    ):
        self.save(
            minutes=0,
            total=100.0,
        )
        self.save(
            minutes=10,
            total=110.0,
        )

        selected = self.service.get_snapshot_nearest(
            self.reference_time
            + timedelta(minutes=5)
        )

        self.assertEqual(
            selected["total_usdt"],
            100.0,
        )

    def test_get_snapshots_filters_orders_and_limits(
        self,
    ):
        for minutes, total in (
            (0, 100.0),
            (10, 110.0),
            (20, 120.0),
            (30, 130.0),
        ):
            self.save(
                minutes=minutes,
                total=total,
            )

        result = self.service.get_snapshots(
            start_time=(
                self.reference_time
                + timedelta(minutes=10)
            ),
            end_time=(
                self.reference_time
                + timedelta(minutes=30)
            ),
            limit=2,
            ascending=False,
        )

        self.assertEqual(
            [
                item["total_usdt"]
                for item in result
            ],
            [130.0, 120.0],
        )

    def test_count_and_clear_history(self):
        self.save(minutes=0)
        self.save(minutes=10)

        self.assertEqual(
            self.service.get_snapshot_count(),
            2,
        )
        self.assertEqual(
            self.service.clear_history(),
            2,
        )
        self.assertEqual(
            self.service.get_snapshot_count(),
            0,
        )
        self.assertIsNone(
            self.service.get_latest_snapshot()
        )

    def test_performance_returns_none_without_references(
        self,
    ):
        result = self.service.calculate_performance(
            current_total_usdt=120.0,
            reference_time=self.reference_time,
            reference_snapshots={},
        )

        self.assertEqual(
            result,
            {
                "1d": None,
                "7d": None,
                "30d": None,
                "90d": None,
                "1y": None,
            },
        )

    def test_performance_calculates_percent_and_adjustment(
        self,
    ):
        reference = self.snapshot(
            timestamp=(
                self.reference_time
                - timedelta(days=1)
            ),
            total=100.0,
        )
        references = {
            "1d": reference,
        }

        result = self.service.calculate_performance(
            current_total_usdt=130.0,
            reference_time=self.reference_time,
            period_adjustments={
                "1d": 10.0,
            },
            reference_snapshots=references,
        )

        self.assertEqual(
            result["1d"],
            20.0,
        )
        self.assertIsNone(result["7d"])

    def test_performance_rejects_invalid_field(self):
        with self.assertRaises(ValueError):
            self.service.calculate_performance(
                current_total_usdt=100.0,
                value_field="invalid",
                reference_snapshots={},
            )

    def test_performance_breakdown_applies_transfer_sides(
        self,
    ):
        reference = self.snapshot(
            timestamp=(
                self.reference_time
                - timedelta(days=1)
            ),
            total=200.0,
            funding=100.0,
            trading=100.0,
        )
        references = {
            "1d": reference,
        }

        result = (
            self.service
            .calculate_performance_breakdown(
                current_total_usdt=200.0,
                current_funding_usdt=130.0,
                current_trading_usdt=70.0,
                reference_time=self.reference_time,
                funding_transfer_adjustments={
                    "1d": 10.0,
                },
                reference_snapshots=references,
            )
        )

        self.assertEqual(
            result["total"]["1d"],
            0.0,
        )
        self.assertEqual(
            result["funding"]["1d"],
            20.0,
        )
        self.assertEqual(
            result["trading"]["1d"],
            -20.0,
        )

    def test_analytics_returns_changes_and_summary(
        self,
    ):
        self.save(
            days=-2,
            total=90.0,
            funding=30.0,
            trading=60.0,
        )
        self.save(
            days=-1,
            total=100.0,
            funding=40.0,
            trading=60.0,
        )

        reference = self.snapshot(
            timestamp=(
                self.reference_time
                - timedelta(days=1)
            ),
            total=100.0,
            funding=40.0,
            trading=60.0,
        )

        result = (
            self.service
            .calculate_portfolio_analytics(
                current_total_usdt=110.0,
                current_funding_usdt=50.0,
                current_trading_usdt=60.0,
                reference_time=self.reference_time,
                reference_snapshots={
                    "1d": reference,
                },
            )
        )

        daily = result["period_changes"]["1d"]
        summary = result["summary"]

        self.assertEqual(
            daily["total"]["amount_usdt"],
            10.0,
        )
        self.assertEqual(
            daily["total"]["percent"],
            10.0,
        )
        self.assertEqual(
            summary["snapshot_count"],
            2,
        )
        self.assertEqual(
            summary["total"]["highest_usdt"],
            100.0,
        )
        self.assertEqual(
            summary["total"]["lowest_usdt"],
            90.0,
        )
        self.assertEqual(
            summary["total"]["average_usdt"],
            95.0,
        )

    def test_history_series_rejects_invalid_period(
        self,
    ):
        with self.assertRaises(ValueError):
            self.service.get_history_series(
                period="invalid",
                reference_time=self.reference_time,
            )

    def test_history_series_downsamples_and_keeps_ends(
        self,
    ):
        for index in range(10):
            self.save(
                minutes=index,
                total=100.0 + index,
            )

        result = self.service.get_history_series(
            period="1d",
            reference_time=(
                self.reference_time
                + timedelta(minutes=10)
            ),
            max_points=4,
        )

        self.assertEqual(len(result), 4)
        self.assertEqual(
            result[0]["total_usdt"],
            100.0,
        )
        self.assertEqual(
            result[-1]["total_usdt"],
            109.0,
        )

    def test_available_periods_use_oldest_snapshot(
        self,
    ):
        self.save(
            days=-8,
            total=100.0,
        )

        result = (
            self.service
            .get_available_history_periods(
                reference_time=self.reference_time
            )
        )

        self.assertTrue(result["1d"])
        self.assertTrue(result["7d"])
        self.assertFalse(result["30d"])
        self.assertFalse(result["90d"])
        self.assertFalse(result["1y"])

    def test_reference_snapshot_requires_sufficient_history(
        self,
    ):
        self.save(
            days=-1,
            total=100.0,
        )

        result = (
            self.service
            .get_performance_reference_snapshots(
                reference_time=self.reference_time
            )
        )

        self.assertIsNotNone(result["1d"])
        self.assertIsNone(result["7d"])
        self.assertIsNone(result["30d"])
        self.assertIsNone(result["90d"])
        self.assertIsNone(result["1y"])

    def test_optimize_history_deletes_and_deduplicates(
        self,
    ):
        fixed_now = self.reference_time
        self.service._now = lambda: fixed_now

        entries = (
            (
                fixed_now - timedelta(days=800),
                10.0,
            ),
            (
                fixed_now - timedelta(
                    days=100,
                    hours=2,
                ),
                20.0,
            ),
            (
                fixed_now - timedelta(
                    days=100,
                    hours=1,
                ),
                21.0,
            ),
            (
                fixed_now - timedelta(
                    days=40,
                    minutes=50,
                ),
                30.0,
            ),
            (
                fixed_now - timedelta(
                    days=40,
                    minutes=10,
                ),
                31.0,
            ),
            (
                fixed_now - timedelta(
                    days=10,
                    minutes=5,
                ),
                40.0,
            ),
            (
                fixed_now - timedelta(
                    days=10,
                    minutes=1,
                ),
                41.0,
            ),
        )

        for timestamp, total in entries:
            self.service.save_snapshot(
                total_usdt=total,
                timestamp=timestamp,
                force=True,
            )

        deleted = self.service.optimize_history(
            detailed_days=30,
            hourly_days=90,
            daily_days=730,
        )

        remaining = self.service.get_snapshots()

        self.assertEqual(deleted, 3)
        self.assertEqual(len(remaining), 4)
        self.assertEqual(
            {
                item["total_usdt"]
                for item in remaining
            },
            {
                20.0,
                30.0,
                40.0,
                41.0,
            },
        )

    def test_datetime_and_safe_value_helpers(self):
        naive = datetime(
            2026,
            7,
            19,
            12,
            0,
            0,
        )
        normalized = (
            self.service._normalize_datetime(naive)
        )
        stored = (
            self.service._datetime_to_storage(naive)
        )
        restored = (
            self.service._storage_to_datetime(stored)
        )

        self.assertEqual(
            normalized.tzinfo,
            self.timezone,
        )
        self.assertEqual(
            restored,
            normalized,
        )
        self.assertEqual(
            self.service._safe_float("12.5"),
            12.5,
        )
        self.assertEqual(
            self.service._safe_float("invalid"),
            0.0,
        )
        self.assertEqual(
            self.service._safe_int("4"),
            4,
        )
        self.assertEqual(
            self.service._safe_int(-2),
            0,
        )


if __name__ == "__main__":
    unittest.main()
