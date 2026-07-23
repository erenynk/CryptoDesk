import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.data_manager import DataManager


class DataManagerHarness:
    _attach_cost_basis_data = (
        DataManager._attach_cost_basis_data
    )
    _attach_history_data = (
        DataManager._attach_history_data
    )
    _attach_modified_dietz_performance = (
        DataManager._attach_modified_dietz_performance
    )
    _run_history_maintenance_if_needed = (
        DataManager._run_history_maintenance_if_needed
    )
    apply_app_settings = DataManager.apply_app_settings
    get_portfolio_history = (
        DataManager.get_portfolio_history
    )
    get_available_history_periods = (
        DataManager.get_available_history_periods
    )
    get_portfolio_analytics = (
        DataManager.get_portfolio_analytics
    )
    get_portfolio = DataManager.get_portfolio
    get_price = DataManager.get_price
    get_prices = DataManager.get_prices
    clear_cache = DataManager.clear_cache
    refresh_client = DataManager.refresh_client
    reconnect = DataManager.reconnect

    _safe_float = staticmethod(
        DataManager._safe_float
    )
    _empty_performance = staticmethod(
        DataManager._empty_performance
    )
    _empty_analytics = staticmethod(
        DataManager._empty_analytics
    )

    HISTORY_MAINTENANCE_INTERVAL = (
        DataManager.HISTORY_MAINTENANCE_INTERVAL
    )

    def __init__(self):
        self.okx = Mock()
        self.cache = Mock()
        self.cost_basis = Mock()
        self.portfolio_history = Mock()
        self.portfolio_history.APP_TIMEZONE = UTC
        self.account_performance = Mock()

        self.portfolio = None
        self._portfolio_history_enabled = True
        self._last_history_maintenance = None


class DataManagerHistoryTestCase(unittest.TestCase):
    @staticmethod
    def make_performance_result(
        *,
        percent,
        pnl,
        start,
    ):
        return SimpleNamespace(
            return_percent=percent,
            pnl_usdt=pnl,
            start_value_usdt=start,
        )

    def test_cost_basis_uses_fills_and_transfers(self):
        manager = DataManagerHarness()
        assets = [
            {
                "coin": "BTC",
                "total": 1.0,
            }
        ]
        portfolio = {
            "assets": assets,
        }
        fills = [
            {
                "tradeId": "1",
            }
        ]
        transfers = [
            {
                "billId": "2",
            }
        ]
        calculated = {
            "BTC": {
                "average_cost": 50000.0,
            }
        }

        manager.okx.get_spot_fills_history.return_value = (
            True,
            fills,
        )
        manager.okx.get_funding_transfer_bills.return_value = (
            True,
            transfers,
        )
        manager.cost_basis.calculate.return_value = (
            calculated
        )

        manager._attach_cost_basis_data(portfolio)

        manager.cost_basis.calculate.assert_called_once_with(
            fills=fills,
            transfers=transfers,
            current_assets=assets,
        )
        manager.cost_basis.attach_to_assets.assert_called_once_with(
            assets,
            calculated,
        )

    def test_cost_basis_uses_empty_transfers_on_failure(
        self,
    ):
        manager = DataManagerHarness()
        assets = [
            {
                "coin": "ETH",
            }
        ]
        fills = [
            {
                "tradeId": "1",
            }
        ]

        manager.okx.get_spot_fills_history.return_value = (
            True,
            fills,
        )
        manager.okx.get_funding_transfer_bills.return_value = (
            False,
            "transfer error",
        )
        manager.cost_basis.calculate.return_value = {}

        manager._attach_cost_basis_data(
            {
                "assets": assets,
            }
        )

        manager.cost_basis.calculate.assert_called_once_with(
            fills=fills,
            transfers=[],
            current_assets=assets,
        )

    @patch(
        "services.data_manager."
        "CostBasisService.attach_to_assets"
    )
    def test_cost_basis_failure_marks_assets_unknown(
        self,
        attach_to_assets,
    ):
        manager = DataManagerHarness()
        assets = [
            {
                "coin": "SOL",
            }
        ]

        manager.okx.get_spot_fills_history.return_value = (
            False,
            "fills error",
        )

        manager._attach_cost_basis_data(
            {
                "assets": assets,
            }
        )

        attach_to_assets.assert_called_once_with(
            assets,
            {},
        )
        manager.cost_basis.calculate.assert_not_called()

    @patch(
        "services.data_manager."
        "CostBasisService.attach_to_assets"
    )
    def test_cost_basis_exception_is_contained(
        self,
        attach_to_assets,
    ):
        manager = DataManagerHarness()
        assets = [
            {
                "coin": "BTC",
            }
        ]
        manager.okx.get_spot_fills_history.side_effect = (
            RuntimeError("fills failed")
        )

        manager._attach_cost_basis_data(
            {
                "assets": assets,
            }
        )

        attach_to_assets.assert_called_once_with(
            assets,
            {},
        )

    def test_cost_basis_ignores_non_list_assets(self):
        manager = DataManagerHarness()

        manager._attach_cost_basis_data(
            {
                "assets": "invalid",
            }
        )

        manager.okx.get_spot_fills_history.assert_not_called()
        manager.cost_basis.calculate.assert_not_called()

    def test_history_data_saves_normalized_snapshot(self):
        manager = DataManagerHarness()
        analytics = {
            "period_changes": {},
            "summary": {
                "snapshot_count": 3,
            },
        }
        manager.portfolio_history.calculate_portfolio_analytics.return_value = (
            analytics
        )
        portfolio = {
            "total_usdt": "125.50",
            "funding_usdt": None,
            "trading_usdt": float("nan"),
            "assets": [
                {
                    "coin": "BTC",
                },
                {
                    "coin": "ETH",
                },
            ],
        }

        manager._attach_history_data(portfolio)

        manager.portfolio_history.save_snapshot.assert_called_once_with(
            total_usdt=125.5,
            funding_usdt=0.0,
            trading_usdt=0.0,
            asset_count=2,
        )
        manager.portfolio_history.calculate_portfolio_analytics.assert_called_once_with(
            current_total_usdt=125.5,
            current_funding_usdt=0.0,
            current_trading_usdt=0.0,
        )
        self.assertIs(
            portfolio["analytics"],
            analytics,
        )
        self.assertEqual(
            portfolio["performance"],
            DataManager._empty_performance(),
        )
        self.assertEqual(
            set(portfolio["performance_breakdown"]),
            {
                "total",
                "funding",
                "trading",
            },
        )

    def test_history_data_skips_snapshot_when_disabled(
        self,
    ):
        manager = DataManagerHarness()
        manager._portfolio_history_enabled = False
        manager.portfolio_history.calculate_portfolio_analytics.return_value = (
            {}
        )
        portfolio = {
            "total_usdt": 10.0,
            "assets": [],
        }

        manager._attach_history_data(portfolio)

        manager.portfolio_history.save_snapshot.assert_not_called()
        manager.portfolio_history.calculate_portfolio_analytics.assert_called_once()

    def test_history_snapshot_error_does_not_stop_analytics(
        self,
    ):
        manager = DataManagerHarness()
        manager.portfolio_history.save_snapshot.side_effect = (
            RuntimeError("database failure")
        )
        manager.portfolio_history.calculate_portfolio_analytics.return_value = (
            {
                "period_changes": {},
                "summary": {},
            }
        )
        portfolio = {
            "total_usdt": 50.0,
            "funding_usdt": 20.0,
            "trading_usdt": 30.0,
            "assets": [],
        }

        manager._attach_history_data(portfolio)

        self.assertIn("analytics", portfolio)
        manager.portfolio_history.calculate_portfolio_analytics.assert_called_once()

    def test_history_analytics_error_uses_empty_payload(
        self,
    ):
        manager = DataManagerHarness()
        manager.portfolio_history.calculate_portfolio_analytics.side_effect = (
            RuntimeError("analytics failed")
        )
        portfolio = {
            "total_usdt": 75.0,
            "assets": [],
        }

        manager._attach_history_data(portfolio)

        self.assertEqual(
            portfolio["analytics"],
            DataManager._empty_analytics(),
        )

    def test_modified_dietz_populates_all_output_groups(
        self,
    ):
        manager = DataManagerHarness()
        reference_timestamp = (
            "2026-07-21T12:00:00+00:00"
        )
        references = {
            "1d": {
                "timestamp": reference_timestamp,
            }
        }
        manager.portfolio_history.get_performance_reference_snapshots.return_value = (
            references
        )

        result_1d = {
            "total": self.make_performance_result(
                percent=5.0,
                pnl=50.0,
                start=1000.0,
            ),
            "funding": self.make_performance_result(
                percent=2.0,
                pnl=8.0,
                start=400.0,
            ),
            "trading": self.make_performance_result(
                percent=7.0,
                pnl=42.0,
                start=600.0,
            ),
            "reference_snapshot": {
                "timestamp": reference_timestamp,
            },
        }
        manager.account_performance.calculate_periods.return_value = {
            "1d": result_1d,
        }

        portfolio = {
            "performance": "invalid",
            "performance_breakdown": "invalid",
            "analytics": DataManager._empty_analytics(),
        }

        manager._attach_modified_dietz_performance(
            portfolio
        )

        self.assertEqual(
            portfolio["performance"]["1d"],
            5.0,
        )
        self.assertEqual(
            portfolio["performance_breakdown"][
                "funding"
            ]["1d"],
            2.0,
        )
        self.assertEqual(
            portfolio["performance_breakdown"][
                "trading"
            ]["1d"],
            7.0,
        )
        self.assertIsNone(
            portfolio["performance"]["7d"]
        )

        one_day = portfolio["analytics"][
            "period_changes"
        ]["1d"]

        self.assertEqual(
            one_day["total"]["amount_usdt"],
            50.0,
        )
        self.assertEqual(
            one_day["funding"]["baseline_usdt"],
            400.0,
        )
        self.assertEqual(
            one_day["trading"]["percent"],
            7.0,
        )
        self.assertEqual(
            one_day["total"][
                "baseline_timestamp"
            ],
            reference_timestamp,
        )
        manager.account_performance.calculate_periods.assert_called_once()
        call_kwargs = (
            manager.account_performance
            .calculate_periods.call_args.kwargs
        )
        self.assertIs(
            call_kwargs["portfolio"],
            portfolio,
        )
        self.assertIs(
            call_kwargs["reference_snapshots"],
            references,
        )
        self.assertIsInstance(
            call_kwargs["period_end"],
            datetime,
        )

    def test_modified_dietz_exception_clears_results(
        self,
    ):
        manager = DataManagerHarness()
        manager.portfolio_history.get_performance_reference_snapshots.return_value = (
            {}
        )
        manager.account_performance.calculate_periods.side_effect = (
            RuntimeError("performance failed")
        )
        portfolio = {
            "performance": {
                "1d": 99.0,
            },
            "performance_breakdown": {
                "total": {
                    "1d": 99.0,
                }
            },
        }

        manager._attach_modified_dietz_performance(
            portfolio
        )

        empty = DataManager._empty_performance()
        self.assertEqual(
            portfolio["performance"],
            empty,
        )
        self.assertEqual(
            portfolio["performance_breakdown"],
            {
                "total": empty,
                "funding": empty,
                "trading": empty,
            },
        )

    def test_maintenance_is_skipped_when_disabled(self):
        manager = DataManagerHarness()
        manager._portfolio_history_enabled = False

        manager._run_history_maintenance_if_needed()

        manager.portfolio_history.optimize_history.assert_not_called()
        self.assertIsNone(
            manager._last_history_maintenance
        )

    def test_first_maintenance_run_updates_timestamp(self):
        manager = DataManagerHarness()

        manager._run_history_maintenance_if_needed()

        manager.portfolio_history.optimize_history.assert_called_once_with()
        self.assertIsInstance(
            manager._last_history_maintenance,
            datetime,
        )

    def test_recent_maintenance_is_not_repeated(self):
        manager = DataManagerHarness()
        manager._last_history_maintenance = (
            datetime.now(UTC)
        )

        manager._run_history_maintenance_if_needed()

        manager.portfolio_history.optimize_history.assert_not_called()

    def test_overdue_maintenance_runs_again(self):
        manager = DataManagerHarness()
        old_timestamp = (
            datetime.now(UTC)
            - timedelta(hours=25)
        )
        manager._last_history_maintenance = (
            old_timestamp
        )

        manager._run_history_maintenance_if_needed()

        manager.portfolio_history.optimize_history.assert_called_once_with()
        self.assertGreater(
            manager._last_history_maintenance,
            old_timestamp,
        )

    def test_maintenance_error_does_not_update_timestamp(
        self,
    ):
        manager = DataManagerHarness()
        manager.portfolio_history.optimize_history.side_effect = (
            RuntimeError("optimize failed")
        )

        manager._run_history_maintenance_if_needed()

        self.assertIsNone(
            manager._last_history_maintenance
        )

    def test_apply_settings_toggles_history_and_runs_maintenance(
        self,
    ):
        manager = DataManagerHarness()
        manager._run_history_maintenance_if_needed = (
            Mock()
        )

        manager.apply_app_settings(
            {
                "portfolio_history_enabled": False,
            }
        )

        self.assertFalse(
            manager._portfolio_history_enabled
        )
        manager._run_history_maintenance_if_needed.assert_not_called()

        manager.apply_app_settings(
            {
                "portfolio_history_enabled": True,
            }
        )

        self.assertTrue(
            manager._portfolio_history_enabled
        )
        manager._run_history_maintenance_if_needed.assert_called_once_with()

    def test_apply_settings_ignores_non_dictionary(self):
        manager = DataManagerHarness()
        manager._portfolio_history_enabled = False

        manager.apply_app_settings("invalid")

        self.assertFalse(
            manager._portfolio_history_enabled
        )

    def test_history_accessors_delegate_and_fallback(
        self,
    ):
        manager = DataManagerHarness()
        history = [
            {
                "timestamp": "now",
            }
        ]
        periods = {
            "1d": True,
            "7d": False,
            "30d": False,
            "90d": False,
            "1y": False,
        }
        manager.portfolio_history.get_history_series.return_value = (
            history
        )
        manager.portfolio_history.get_available_history_periods.return_value = (
            periods
        )

        self.assertIs(
            manager.get_portfolio_history(
                "7d",
                max_points=120,
            ),
            history,
        )
        manager.portfolio_history.get_history_series.assert_called_once_with(
            period="7d",
            max_points=120,
        )

        self.assertIs(
            manager.get_available_history_periods(),
            periods,
        )

        manager.portfolio_history.get_history_series.side_effect = (
            RuntimeError("history error")
        )
        manager.portfolio_history.get_available_history_periods.side_effect = (
            RuntimeError("period error")
        )

        self.assertEqual(
            manager.get_portfolio_history("1d"),
            [],
        )
        self.assertEqual(
            manager.get_available_history_periods(),
            {
                "1d": False,
                "7d": False,
                "30d": False,
                "90d": False,
                "1y": False,
            },
        )

    def test_portfolio_analytics_returns_cached_or_empty(
        self,
    ):
        manager = DataManagerHarness()
        analytics = {
            "period_changes": {
                "1d": {},
            },
            "summary": {},
        }
        manager.portfolio = {
            "analytics": analytics,
        }

        self.assertIs(
            manager.get_portfolio_analytics(),
            analytics,
        )

        manager.portfolio = {
            "analytics": "invalid",
        }
        self.assertEqual(
            manager.get_portfolio_analytics(),
            DataManager._empty_analytics(),
        )

        manager.portfolio = None
        self.assertEqual(
            manager.get_portfolio_analytics(),
            DataManager._empty_analytics(),
        )

    def test_safe_float_handles_invalid_numbers(self):
        cases = (
            ("12.5", 12.5),
            (None, 0.0),
            ("invalid", 0.0),
            (float("nan"), 0.0),
            (float("inf"), float("inf")),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    DataManager._safe_float(value),
                    expected,
                )

    def test_cache_and_reconnect_delegate_to_services(
        self,
    ):
        manager = DataManagerHarness()
        manager.cache.get.return_value = 123.0
        manager.cache.get_all.return_value = {
            "BTC": 123.0,
        }

        self.assertEqual(
            manager.get_price("BTC"),
            123.0,
        )
        self.assertEqual(
            manager.get_prices(),
            {
                "BTC": 123.0,
            },
        )

        manager.reconnect()

        manager.okx.refresh_client.assert_called_once_with()
        manager.cache.clear.assert_called_once_with()


    def test_singleton_initializes_dependencies_once(
        self,
    ):
        DataManager._instance = None

        cache = Mock()
        okx = Mock()
        cost_basis = Mock()
        portfolio_history = Mock()
        account_performance = Mock()

        try:
            with (
                patch(
                    "services.data_manager.PriceCache",
                    return_value=cache,
                ) as price_cache_class,
                patch(
                    "services.data_manager.OKXService",
                    return_value=okx,
                ) as okx_service_class,
                patch(
                    "services.data_manager.CostBasisService",
                    return_value=cost_basis,
                ) as cost_basis_class,
                patch(
                    "services.data_manager.PortfolioHistoryService",
                    return_value=portfolio_history,
                ) as history_service_class,
                patch(
                    "services.data_manager.AccountPerformanceService",
                    return_value=account_performance,
                ) as performance_service_class,
                patch(
                    "services.data_manager.get_app_setting",
                    return_value=False,
                ) as get_app_setting,
                patch.object(
                    DataManager,
                    "_run_history_maintenance_if_needed",
                ) as run_maintenance,
            ):
                first = DataManager()
                second = DataManager()

            self.assertIs(first, second)
            self.assertIs(first.cache, cache)
            self.assertIs(first.okx, okx)
            self.assertIs(first.cost_basis, cost_basis)
            self.assertIs(
                first.portfolio_history,
                portfolio_history,
            )
            self.assertIs(
                first.account_performance,
                account_performance,
            )
            self.assertIsNone(first.portfolio)
            self.assertIsNone(first.last_error)
            self.assertFalse(first.loading)
            self.assertIsNone(
                first._last_history_maintenance
            )
            self.assertFalse(
                first._portfolio_history_enabled
            )

            price_cache_class.assert_called_once_with()
            okx_service_class.assert_called_once_with()
            cost_basis_class.assert_called_once_with()
            history_service_class.assert_called_once_with()
            performance_service_class.assert_called_once_with(
                okx_service=okx,
                history_service=portfolio_history,
            )
            get_app_setting.assert_called_once_with(
                "portfolio_history_enabled",
                True,
            )
            run_maintenance.assert_called_once_with()
        finally:
            DataManager._instance = None

    def test_cost_basis_non_list_fills_marks_assets_unknown(
        self,
    ):
        manager = DataManagerHarness()
        assets = [
            {
                "coin": "BTC",
                "average_price": 50000.0,
                "cost_basis_available": True,
            }
        ]
        manager.okx.get_spot_fills_history.return_value = (
            True,
            "invalid",
        )
        manager.okx.get_funding_transfer_bills.return_value = (
            True,
            [],
        )

        manager._attach_cost_basis_data(
            {
                "assets": assets,
            }
        )

        manager.cost_basis.calculate.assert_not_called()
        self.assertIsNone(
            assets[0]["average_price"]
        )
        self.assertIsNone(
            assets[0]["cost_basis_usdt"]
        )
        self.assertIsNone(
            assets[0]["pnl_usdt"]
        )
        self.assertIsNone(
            assets[0]["pnl_percent"]
        )
        self.assertFalse(
            assets[0]["cost_basis_available"]
        )

    def test_modified_dietz_skips_invalid_analytics_account(
        self,
    ):
        manager = DataManagerHarness()
        reference_timestamp = (
            "2026-07-21T12:00:00+00:00"
        )
        manager.portfolio_history.get_performance_reference_snapshots.return_value = {
            "1d": {
                "timestamp": reference_timestamp,
            }
        }
        manager.account_performance.calculate_periods.return_value = {
            "1d": {
                "total": self.make_performance_result(
                    percent=5.0,
                    pnl=50.0,
                    start=1000.0,
                ),
                "funding": self.make_performance_result(
                    percent=2.0,
                    pnl=8.0,
                    start=400.0,
                ),
                "trading": self.make_performance_result(
                    percent=7.0,
                    pnl=42.0,
                    start=600.0,
                ),
                "reference_snapshot": {
                    "timestamp": reference_timestamp,
                },
            }
        }
        empty = DataManager._empty_performance()
        portfolio = {
            "performance": empty.copy(),
            "performance_breakdown": {
                "total": empty.copy(),
                "funding": empty.copy(),
                "trading": empty.copy(),
            },
            "analytics": {
                "period_changes": {
                    "1d": {
                        "total": "invalid",
                        "funding": {},
                        "trading": {},
                    }
                }
            },
        }

        manager._attach_modified_dietz_performance(
            portfolio
        )

        self.assertEqual(
            portfolio["analytics"][
                "period_changes"
            ]["1d"]["total"],
            "invalid",
        )
        self.assertEqual(
            portfolio["analytics"][
                "period_changes"
            ]["1d"]["funding"]["amount_usdt"],
            8.0,
        )
        self.assertEqual(
            portfolio["analytics"][
                "period_changes"
            ]["1d"]["trading"]["percent"],
            7.0,
        )

    def test_get_portfolio_returns_cached_object(self):
        manager = DataManagerHarness()
        portfolio = {
            "total_usdt": 125.0,
        }
        manager.portfolio = portfolio

        self.assertIs(
            manager.get_portfolio(),
            portfolio,
        )



if __name__ == "__main__":
    unittest.main()
