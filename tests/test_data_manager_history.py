import unittest
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from services.data_manager import DataManager


class DataManagerHarness:
    _attach_cost_basis_data = (
        DataManager._attach_cost_basis_data
    )
    _prefer_okx_trading_pnl = classmethod(
        DataManager._prefer_okx_trading_pnl.__func__
    )
    _merge_total_pnl_with_funding = classmethod(
        DataManager._merge_total_pnl_with_funding.__func__
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
    _optional_float = staticmethod(
        DataManager._optional_float
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



    def test_okx_native_trading_pnl_replaces_ledger_result(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "DOGE",
            "total": 100.0,
            "funding_total": 0.0,
            "trading_total": 100.0,
            "funding_usdt_value": 0.0,
            "trading_usdt_value": 12.0,
            "average_price": 0.11,
            "cost_basis_usdt": 11.0,
            "pnl_usdt": 1.0,
            "pnl_percent": 9.0909,
            "cost_basis_available": True,
            "trading_average_price": 0.11,
            "trading_cost_basis_usdt": 11.0,
            "trading_pnl_usdt": 1.0,
            "trading_pnl_percent": 9.0909,
            "trading_cost_basis_available": True,
            "okx_trading_spot_balance": 100.0,
            "okx_trading_average_price": 0.10,
            "okx_trading_pnl_usdt": 2.0,
            "okx_trading_pnl_percent": 20.0,
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertEqual(
            asset["trading_average_price"],
            0.10,
        )
        self.assertEqual(
            asset["trading_cost_basis_usdt"],
            10.0,
        )
        self.assertEqual(
            asset["trading_pnl_usdt"],
            2.0,
        )
        self.assertEqual(
            asset["trading_pnl_percent"],
            20.0,
        )
        self.assertEqual(asset["average_price"], 0.10)
        self.assertEqual(asset["cost_basis_usdt"], 10.0)
        self.assertEqual(asset["pnl_usdt"], 2.0)
        self.assertEqual(asset["pnl_percent"], 20.0)
        self.assertEqual(
            asset["trading_pnl_source"],
            "okx",
        )
        self.assertEqual(
            asset["pnl_source"],
            "okx_trading",
        )

    def test_okx_native_trading_pnl_combines_with_known_funding_cost(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "LINK",
            "total": 15.0,
            "funding_total": 5.0,
            "trading_total": 10.0,
            "funding_usdt_value": 55.0,
            "trading_usdt_value": 120.0,
            "funding_cost_basis_available": True,
            "funding_cost_basis_usdt": 50.0,
            "funding_pnl_usdt": 5.0,
            "okx_trading_spot_balance": 10.0,
            "okx_trading_average_price": 10.0,
            "okx_trading_pnl_usdt": 20.0,
            "okx_trading_pnl_percent": 20.0,
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertEqual(
            asset["trading_cost_basis_usdt"],
            100.0,
        )
        self.assertEqual(asset["cost_basis_usdt"], 150.0)
        self.assertEqual(asset["pnl_usdt"], 25.0)
        self.assertAlmostEqual(
            asset["pnl_percent"],
            16.666666666666664,
        )
        self.assertEqual(asset["average_price"], 10.0)
        self.assertTrue(asset["cost_basis_available"])
        self.assertEqual(
            asset["pnl_source"],
            "okx_trading+caspian_funding",
        )

    def test_okx_native_trading_pnl_keeps_total_unknown_when_funding_cost_is_unknown(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "SOL",
            "total": 3.0,
            "funding_total": 1.0,
            "trading_total": 2.0,
            "funding_usdt_value": 75.0,
            "trading_usdt_value": 150.0,
            "funding_cost_basis_available": False,
            "funding_cost_basis_usdt": None,
            "funding_pnl_usdt": None,
            "okx_trading_spot_balance": 2.0,
            "okx_trading_average_price": 70.0,
            "okx_trading_pnl_usdt": 10.0,
            "okx_trading_pnl_percent": 7.142857,
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertTrue(
            asset["trading_cost_basis_available"]
        )
        self.assertEqual(asset["trading_pnl_usdt"], 10.0)
        self.assertFalse(asset["cost_basis_available"])
        self.assertIsNone(asset["average_price"])
        self.assertIsNone(asset["cost_basis_usdt"])
        self.assertIsNone(asset["pnl_usdt"])
        self.assertIsNone(asset["pnl_percent"])
        self.assertEqual(
            asset["pnl_source"],
            "unknown_funding",
        )

    def test_okx_native_trading_pnl_is_not_used_for_dust_position(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "MORPHO",
            "total": 0.0002,
            "funding_total": 0.0,
            "trading_total": 0.0002,
            "funding_usdt_value": 0.0,
            "trading_usdt_value": 0.0004,
            "trading_average_price": None,
            "trading_cost_basis_available": False,
            "okx_trading_spot_balance": 0.0002,
            "okx_trading_average_price": 1.9,
            "okx_trading_pnl_usdt": 0.00001,
            "okx_trading_pnl_percent": 1.5,
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertIsNone(asset["trading_average_price"])
        self.assertFalse(
            asset["trading_cost_basis_available"]
        )
        self.assertNotIn("trading_pnl_source", asset)

    def test_okx_native_trading_pnl_is_not_used_when_spot_balance_differs(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "BTC",
            "total": 1.0,
            "funding_total": 0.0,
            "trading_total": 1.0,
            "funding_usdt_value": 0.0,
            "trading_usdt_value": 65000.0,
            "trading_average_price": 64000.0,
            "trading_pnl_usdt": 1000.0,
            "trading_cost_basis_available": True,
            "okx_trading_spot_balance": 0.5,
            "okx_trading_average_price": 63000.0,
            "okx_trading_pnl_usdt": 900.0,
            "okx_trading_pnl_percent": 2.0,
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertEqual(
            asset["trading_average_price"],
            64000.0,
        )
        self.assertEqual(asset["trading_pnl_usdt"], 1000.0)
        self.assertNotIn("trading_pnl_source", asset)



    def test_okx_native_trading_pnl_skips_unsupported_assets(self):
        manager = DataManagerHarness()
        invalid_native = {
            "coin": "ETH",
            "trading_total": 1.0,
            "trading_usdt_value": 100.0,
            "okx_trading_spot_balance": 1.0,
            "okx_trading_average_price": None,
            "okx_trading_pnl_usdt": 5.0,
            "okx_trading_pnl_percent": 5.0,
            "okx_trading_pnl_available": True,
            "trading_average_price": 90.0,
        }
        unavailable = {
            "coin": "SOL",
            "okx_trading_pnl_available": False,
            "trading_average_price": 80.0,
        }
        usdt = {
            "coin": "USDT",
            "okx_trading_pnl_available": True,
        }

        manager._prefer_okx_trading_pnl(
            [
                "invalid",
                usdt,
                unavailable,
                invalid_native,
            ]
        )

        self.assertEqual(
            invalid_native["trading_average_price"],
            90.0,
        )
        self.assertNotIn(
            "trading_pnl_source",
            invalid_native,
        )
        self.assertEqual(
            unavailable["trading_average_price"],
            80.0,
        )
        self.assertNotIn("pnl_source", usdt)

    def test_okx_native_trading_pnl_skips_zero_underflow_cost(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "BTC",
            "trading_total": 1e-300,
            "trading_usdt_value": 1.0,
            "okx_trading_spot_balance": 1e-300,
            "okx_trading_average_price": 1e-300,
            "okx_trading_pnl_usdt": 0.0,
            "okx_trading_pnl_percent": 0.0,
            "okx_trading_pnl_available": True,
            "trading_average_price": 64000.0,
        }

        manager._prefer_okx_trading_pnl([asset])

        self.assertEqual(
            asset["trading_average_price"],
            64000.0,
        )
        self.assertNotIn("trading_pnl_source", asset)

    def test_merge_total_marks_nonpositive_total_quantity_invalid(self):
        manager = DataManagerHarness()
        asset = {
            "coin": "BTC",
            "total": 0.0,
            "funding_total": 1.0,
            "funding_usdt_value": 100.0,
            "funding_cost_basis_available": True,
            "funding_cost_basis_usdt": 90.0,
            "funding_pnl_usdt": 10.0,
        }

        manager._merge_total_pnl_with_funding(
            asset=asset,
            trading_cost=50.0,
            trading_pnl=5.0,
            trading_percent=10.0,
            trading_average=50.0,
        )

        self.assertIsNone(asset["average_price"])
        self.assertIsNone(asset["cost_basis_usdt"])
        self.assertIsNone(asset["pnl_usdt"])
        self.assertIsNone(asset["pnl_percent"])
        self.assertFalse(asset["cost_basis_available"])
        self.assertEqual(
            asset["pnl_source"],
            "invalid_total",
        )

    def test_optional_float_rejects_nonfinite_and_invalid_values(self):
        cases = (
            ("12.5", 12.5),
            (float("nan"), None),
            (float("inf"), None),
            (float("-inf"), None),
            (None, None),
            ("invalid", None),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    DataManager._optional_float(value),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
