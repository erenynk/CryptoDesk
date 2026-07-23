import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QGridLayout,
    QWidget,
)

import ui.dashboard as dashboard_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class BareDashboardPage(dashboard_module.DashboardPage):
    def __init__(self):
        QWidget.__init__(self)
        self.layout_mode = None
        self.account_cards = []
        self.summary_sections = []
        self.period_cells = []


class DashboardPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    def setUp(self):
        self.pages = []

    def tearDown(self):
        for page in self.pages:
            page.deleteLater()

    def make_page(self):
        page = BareDashboardPage()
        self.pages.append(page)
        return page

    @staticmethod
    def build_value_labels(page):
        page.value = QLabel()
        page.funding_value = QLabel()
        page.trading_value = QLabel()
        page.funding_change = QLabel()
        page.funding_change_amount = QLabel()
        page.trading_change = QLabel()
        page.trading_change_amount = QLabel()
        page.performance_summary_value = QLabel()
        page.performance_summary_detail = QLabel()
        page.alarms_summary_value = QLabel()
        page.alarms_summary_detail = QLabel()
        page.watchlist_summary_value = QLabel()
        page.watchlist_summary_detail = QLabel()
        page.period_value_labels = {
            key: QLabel()
            for key in (
                "1d",
                "7d",
                "30d",
                "90d",
                "1y",
            )
        }
        page.status_badge = Mock()
        page.hero_status = QLabel()

    def test_constructor_initializes_and_refreshes(self):
        with (
            patch.object(
                dashboard_module.DashboardPage,
                "_build_ui",
            ) as build_ui,
            patch.object(
                dashboard_module.DashboardPage,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                dashboard_module.DashboardPage,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                dashboard_module.DashboardPage,
                "refresh",
            ) as refresh,
        ):
            page = dashboard_module.DashboardPage(
                sentinel.data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            sentinel.data_manager,
        )
        self.assertIsNone(page.layout_mode)
        self.assertEqual(page.account_cards, [])
        self.assertEqual(page.summary_sections, [])
        self.assertEqual(page.period_cells, [])
        self.assertEqual(
            page.objectName(),
            "dashboardPage",
        )
        self.assertFalse(
            page.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        self.assertTrue(
            page.testAttribute(
                Qt.WA_TranslucentBackground
            )
        )
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        connect_signals.assert_called_once_with()
        refresh.assert_called_once_with()

    def test_surface_noise_tile_is_cached(self):
        dashboard_module.SurfaceEngine._noise_tile = (
            None
        )

        first = dashboard_module.SurfaceEngine.noise_tile()
        second = dashboard_module.SurfaceEngine.noise_tile()

        self.assertIs(first, second)
        self.assertFalse(first.isNull())
        self.assertEqual(first.width(), 96)
        self.assertEqual(first.height(), 96)

    def test_corporate_surface_rejects_unknown_role(
        self,
    ):
        with self.assertRaisesRegex(
            ValueError,
            "Geçersiz yüzey rolü",
        ):
            dashboard_module.CorporateSurface(
                role="invalid",
                object_name="badSurface",
            )

    def test_connect_signals_wires_manager_events(
        self,
    ):
        page = self.make_page()
        updated = SignalStub()
        error = SignalStub()
        page.data_manager = SimpleNamespace(
            portfolio_updated=updated,
            portfolio_error=error,
        )

        page._connect_signals()

        self.assertEqual(
            updated.callbacks,
            [page.on_portfolio_updated],
        )
        self.assertEqual(
            error.callbacks,
            [page.on_portfolio_error],
        )

    def test_refresh_sets_waiting_when_cache_is_empty(
        self,
    ):
        page = self.make_page()
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value=None
            )
        )
        page._set_waiting_status = Mock()
        page.on_portfolio_updated = Mock()

        page.refresh()

        page.data_manager.get_portfolio.assert_called_once_with()
        page._set_waiting_status.assert_called_once_with()
        page.on_portfolio_updated.assert_not_called()

    def test_refresh_uses_cached_portfolio(self):
        page = self.make_page()
        portfolio = {
            "total_usdt": 1000.0,
        }
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value=portfolio
            )
        )
        page._set_waiting_status = Mock()
        page.on_portfolio_updated = Mock()

        page.refresh()

        page.on_portfolio_updated.assert_called_once_with(
            portfolio
        )
        page._set_waiting_status.assert_not_called()

    def test_portfolio_update_formats_balances_and_delegates(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)
        page._update_account_daily_changes = Mock()
        page._update_period_cards = Mock()
        page._update_dashboard_summaries = Mock()
        page._set_connected_status = Mock()

        breakdown = {
            "funding": {
                "1d": 1.0,
            }
        }
        analytics = {
            "period_changes": {},
        }
        performance = {
            "1d": 2.5,
        }

        page.on_portfolio_updated(
            {
                "total_usdt": 12345.678,
                "funding_usdt": 2345.5,
                "trading_usdt": 10000.178,
                "performance": performance,
                "performance_breakdown": breakdown,
                "analytics": analytics,
            }
        )

        self.assertEqual(
            page.value.text(),
            "$12,345.68",
        )
        self.assertEqual(
            page.funding_value.text(),
            "$2,345.50",
        )
        self.assertEqual(
            page.trading_value.text(),
            "$10,000.18",
        )
        page._update_account_daily_changes.assert_called_once_with(
            breakdown,
            analytics,
        )
        page._update_period_cards.assert_called_once_with(
            performance
        )
        page._update_dashboard_summaries.assert_called_once_with(
            performance
        )
        page._set_connected_status.assert_called_once_with()

    def test_portfolio_update_normalizes_invalid_performance(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)
        page._update_account_daily_changes = Mock()
        page._update_period_cards = Mock()
        page._update_dashboard_summaries = Mock()
        page._set_connected_status = Mock()

        page.on_portfolio_updated(
            {
                "performance": "invalid",
                "performance_breakdown": [],
                "analytics": None,
            }
        )

        page._update_period_cards.assert_called_once_with(
            {}
        )
        page._update_dashboard_summaries.assert_called_once_with(
            {}
        )

    def test_account_daily_changes_formats_values(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)

        page._update_account_daily_changes(
            breakdown={
                "funding": {
                    "1d": 1.234,
                },
                "trading": {
                    "1d": -2.345,
                },
            },
            analytics={
                "period_changes": {
                    "1d": {
                        "funding": {
                            "amount_usdt": 12.5,
                        },
                        "trading": {
                            "amount_usdt": -8.75,
                        },
                    }
                }
            },
        )

        self.assertEqual(
            page.funding_change.text(),
            "+1.23%",
        )
        self.assertEqual(
            page.funding_change_amount.text(),
            "+12.50 USDT",
        )
        self.assertIn(
            dashboard_module.Theme.ACCENT,
            page.funding_change.styleSheet(),
        )
        self.assertEqual(
            page.trading_change.text(),
            "-2.35%",
        )
        self.assertEqual(
            page.trading_change_amount.text(),
            "-8.75 USDT",
        )
        self.assertIn(
            dashboard_module.Theme.ERROR,
            page.trading_change.styleSheet(),
        )

    def test_account_daily_changes_handles_missing_values(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)

        page._update_account_daily_changes(
            breakdown="invalid",
            analytics="invalid",
        )

        for label in (
            page.funding_change,
            page.funding_change_amount,
            page.trading_change,
            page.trading_change_amount,
        ):
            self.assertEqual(label.text(), "—")
            self.assertIn(
                "#6F8093",
                label.styleSheet(),
            )

    def test_period_cards_format_positive_negative_and_missing(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)

        page._update_period_cards(
            {
                "1d": 1.234,
                "7d": -2.345,
                "30d": 0,
                "90d": None,
            }
        )

        self.assertEqual(
            page.period_value_labels["1d"].text(),
            "+1.23%",
        )
        self.assertIn(
            dashboard_module.Theme.ACCENT,
            page.period_value_labels[
                "1d"
            ].styleSheet(),
        )
        self.assertEqual(
            page.period_value_labels["7d"].text(),
            "-2.35%",
        )
        self.assertIn(
            dashboard_module.Theme.ERROR,
            page.period_value_labels[
                "7d"
            ].styleSheet(),
        )
        self.assertEqual(
            page.period_value_labels["30d"].text(),
            "+0.00%",
        )
        self.assertEqual(
            page.period_value_labels["90d"].text(),
            "—",
        )
        self.assertEqual(
            page.period_value_labels["1y"].text(),
            "—",
        )

    def test_dashboard_summaries_populate_counts_and_average(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)
        page.data_manager = SimpleNamespace(
            get_price=Mock(
                side_effect=lambda symbol: {
                    "BTC": 120.0,
                    "ETH": 80.0,
                }[symbol]
            )
        )

        alarms = [
            {
                "is_active": True,
                "is_triggered": False,
            },
            {
                "is_active": False,
                "is_triggered": True,
            },
            {
                "is_active": True,
                "is_triggered": True,
            },
        ]
        watchlist_items = [
            {
                "symbol": "btc",
                "added_price": 100.0,
            },
            {
                "symbol": "eth",
                "added_price": 100.0,
            },
        ]

        with (
            patch.object(
                dashboard_module.alarm_service,
                "get_all_alarms",
                return_value=alarms,
            ),
            patch.object(
                dashboard_module.watchlist_service,
                "get_items",
                return_value=watchlist_items,
            ),
            patch.object(
                dashboard_module.watchlist_service,
                "normalize_symbol",
                side_effect=[
                    "BTC",
                    "ETH",
                ],
            ),
        ):
            page._update_dashboard_summaries(
                {
                    "1d": 3.456,
                }
            )

        self.assertEqual(
            page.performance_summary_value.text(),
            "+3.46%",
        )
        self.assertEqual(
            page.performance_summary_detail.text(),
            "1 günlük portföy değişimi",
        )
        self.assertEqual(
            page.alarms_summary_value.text(),
            "1",
        )
        self.assertEqual(
            page.alarms_summary_detail.text(),
            "2 tamamlanan alarm",
        )
        self.assertEqual(
            page.watchlist_summary_value.text(),
            "2",
        )
        self.assertEqual(
            page.watchlist_summary_detail.text(),
            "Ortalama değişim +0.00%",
        )

    def test_dashboard_summaries_handle_empty_performance_and_prices(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)
        page.data_manager = SimpleNamespace(
            get_price=Mock(
                return_value=None
            )
        )

        with (
            patch.object(
                dashboard_module.alarm_service,
                "get_all_alarms",
                return_value=[],
            ),
            patch.object(
                dashboard_module.watchlist_service,
                "get_items",
                return_value=[
                    {
                        "symbol": "BTC",
                        "added_price": 100.0,
                    }
                ],
            ),
            patch.object(
                dashboard_module.watchlist_service,
                "normalize_symbol",
                return_value="BTC",
            ),
        ):
            page._update_dashboard_summaries({})

        self.assertEqual(
            page.performance_summary_value.text(),
            "—",
        )
        self.assertEqual(
            page.performance_summary_detail.text(),
            "Geçmiş kayıt oluşması bekleniyor",
        )
        self.assertEqual(
            page.alarms_summary_value.text(),
            "0",
        )
        self.assertEqual(
            page.alarms_summary_detail.text(),
            "0 tamamlanan alarm",
        )
        self.assertEqual(
            page.watchlist_summary_value.text(),
            "1",
        )
        self.assertEqual(
            page.watchlist_summary_detail.text(),
            "Takip edilen toplam varlık",
        )

    def test_sync_layout_mode_uses_viewport_width(
        self,
    ):
        page = self.make_page()
        page._set_layout_mode = Mock()
        viewport = SimpleNamespace(
            width=Mock(return_value=700)
        )
        page.scroll_area = SimpleNamespace(
            viewport=Mock(
                return_value=viewport
            )
        )

        page._sync_layout_mode()

        page._set_layout_mode.assert_called_once_with(
            "narrow"
        )

        viewport.width.return_value = 900
        page._sync_layout_mode()

        page._set_layout_mode.assert_called_with(
            "wide"
        )

    def test_sync_layout_mode_falls_back_to_page_width(
        self,
    ):
        page = self.make_page()
        page._set_layout_mode = Mock()
        viewport = SimpleNamespace(
            width=Mock(return_value=0)
        )
        page.scroll_area = SimpleNamespace(
            viewport=Mock(
                return_value=viewport
            )
        )
        page.resize(800, 600)

        page._sync_layout_mode()

        page._set_layout_mode.assert_called_once_with(
            "wide"
        )

    def test_clear_grid_detaches_widgets(self):
        parent = QWidget()
        self.pages.append(parent)
        layout = QGridLayout(parent)
        first = QWidget(parent)
        second = QWidget(parent)
        layout.addWidget(first, 0, 0)
        layout.addWidget(second, 0, 1)

        dashboard_module.DashboardPage._clear_grid(
            layout
        )

        self.assertEqual(layout.count(), 0)
        self.assertIsNone(first.parent())
        self.assertIsNone(second.parent())

        first.deleteLater()
        second.deleteLater()

    def test_status_helpers_and_error_handler(self):
        page = self.make_page()
        self.build_value_labels(page)

        page._set_waiting_status()

        page.status_badge.set_status.assert_called_with(
            "Bekleniyor",
            dashboard_module.StatusBadge.NEUTRAL,
        )
        self.assertEqual(
            page.hero_status.text(),
            "Portföy verileri bekleniyor",
        )

        page._set_connected_status()

        page.status_badge.set_status.assert_called_with(
            "API Bağlı",
            dashboard_module.StatusBadge.SUCCESS,
        )
        self.assertEqual(
            page.hero_status.text(),
            "Portföy verileri güncel",
        )

        page.on_portfolio_error(
            "network failed"
        )

        page.status_badge.set_status.assert_called_with(
            "Bağlantı Hatası",
            dashboard_module.StatusBadge.ERROR,
        )
        self.assertEqual(
            page.hero_status.text(),
            "Portföy verileri alınamadı",
        )

    def test_show_event_schedules_layout_and_updates_summaries(
        self,
    ):
        page = self.make_page()
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value={
                    "performance": {
                        "1d": 1.0,
                    },
                    "performance_breakdown": {},
                }
            )
        )
        page._set_layout_mode = Mock()
        page._sync_layout_mode = Mock()
        page._update_period_cards = Mock()
        page._update_dashboard_summaries = Mock()
        event = Mock()

        with (
            patch.object(
                QWidget,
                "showEvent",
            ) as super_show,
            patch.object(
                dashboard_module.QTimer,
                "singleShot",
            ) as single_shot,
        ):
            page.showEvent(event)

        super_show.assert_called_once_with(event)
        page._set_layout_mode.assert_called_once_with(
            "wide"
        )
        self.assertEqual(
            single_shot.call_args_list,
            [
                call(
                    0,
                    page._sync_layout_mode,
                ),
                call(
                    120,
                    page._sync_layout_mode,
                ),
            ],
        )
        page._update_period_cards.assert_called_once_with(
            {
                "1d": 1.0,
            }
        )
        page._update_dashboard_summaries.assert_called_once_with(
            {
                "1d": 1.0,
            }
        )


if __name__ == "__main__":
    unittest.main()
