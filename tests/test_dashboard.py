import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import (
    QEvent,
    QPointF,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QEnterEvent,
    QPainter,
    QPaintEvent,
    QPixmap,
    QResizeEvent,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
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



    def test_full_constructor_builds_complete_dashboard(
        self,
    ):
        updated = SignalStub()
        error = SignalStub()
        data_manager = SimpleNamespace(
            portfolio_updated=updated,
            portfolio_error=error,
            get_portfolio=Mock(return_value=None),
            get_price=Mock(return_value=None),
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
                return_value=[],
            ),
        ):
            page = dashboard_module.DashboardPage(
                data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            data_manager,
        )
        self.assertEqual(
            page.layout_mode,
            "wide",
        )
        self.assertEqual(
            len(page.account_cards),
            2,
        )
        self.assertEqual(
            len(page.summary_sections),
            3,
        )
        self.assertEqual(
            len(page.period_cells),
            5,
        )
        self.assertEqual(
            len(page.period_value_labels),
            5,
        )

        self.assertEqual(
            page.layout().count(),
            1,
        )
        self.assertEqual(
            page.scroll_area.objectName(),
            "dashboardScrollArea",
        )
        self.assertTrue(
            page.scroll_area.widgetResizable()
        )
        self.assertIs(
            page.scroll_area.widget(),
            page.content_widget,
        )
        self.assertEqual(
            page.content_widget.objectName(),
            "dashboardContent",
        )
        self.assertEqual(
            page.main_layout.count(),
            5,
        )

        self.assertEqual(
            page.status_badge.objectName(),
            "dashboardStatusBadge",
        )
        self.assertEqual(
            page.status_badge.text(),
            "Bekleniyor",
        )
        self.assertEqual(
            page.header.objectName(),
            "dashboardHeader",
        )

        self.assertEqual(
            page.hero_surface.objectName(),
            "dashboardHeroSurface",
        )
        self.assertEqual(
            page.period_surface.objectName(),
            "dashboardPeriodSurface",
        )
        self.assertEqual(
            page.overview_surface.objectName(),
            "overviewContainer",
        )

        self.assertEqual(
            page.value.text(),
            "$0.00",
        )
        self.assertEqual(
            page.funding_value.text(),
            "$0.00",
        )
        self.assertEqual(
            page.trading_value.text(),
            "$0.00",
        )
        self.assertEqual(
            page.hero_status.text(),
            "Portföy verileri bekleniyor",
        )

        self.assertEqual(
            page.hero_grid.count(),
            3,
        )
        self.assertEqual(
            page.period_layout.count(),
            9,
        )
        self.assertEqual(
            page.overview_layout.count(),
            3,
        )

        self.assertEqual(
            updated.callbacks,
            [page.on_portfolio_updated],
        )
        self.assertEqual(
            error.callbacks,
            [page.on_portfolio_error],
        )
        data_manager.get_portfolio.assert_called_once_with()

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        for expected in (
            "Dashboard",
            "TOPLAM PORTFÖY",
            "Funding",
            "Trading",
            "1 Gün",
            "7 Gün",
            "30 Gün",
            "90 Gün",
            "1 Yıl",
            "Portfolio",
            "Alarmlar",
            "Watchlist",
        ):
            with self.subTest(
                expected=expected
            ):
                self.assertIn(
                    expected,
                    labels,
                )

        stylesheet = page.styleSheet()

        for selector in (
            "QWidget#dashboardPage",
            "QScrollArea#dashboardScrollArea",
            "QFrame#dashboardHeroSurface",
            "QFrame#dashboardAccountPanel",
            "QFrame#dashboardPeriodSurface",
            "QFrame#dashboardSummarySurface",
            "QLabel#heroValue",
            "QLabel#periodValue",
            "QLabel#summaryValue",
        ):
            with self.subTest(
                selector=selector
            ):
                self.assertIn(
                    selector,
                    stylesheet,
                )

        self.assertIn(
            dashboard_module.Theme.ACCENT,
            stylesheet,
        )
        self.assertIn(
            dashboard_module.Theme.TEXT_PRIMARY,
            stylesheet,
        )

    def test_layout_mode_rebuilds_narrow_wide_and_ignores_same(
        self,
    ):
        updated = SignalStub()
        error = SignalStub()
        data_manager = SimpleNamespace(
            portfolio_updated=updated,
            portfolio_error=error,
            get_portfolio=Mock(return_value=None),
            get_price=Mock(return_value=None),
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
                return_value=[],
            ),
        ):
            page = dashboard_module.DashboardPage(
                data_manager
            )
            self.pages.append(page)

        page._set_layout_mode("narrow")

        self.assertEqual(
            page.layout_mode,
            "narrow",
        )
        self.assertEqual(
            page.hero_grid.count(),
            3,
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                0,
                0,
            ).widget(),
            page.metric_widget,
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                1,
                0,
            ).widget(),
            page.account_cards[0],
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                2,
                0,
            ).widget(),
            page.account_cards[1],
        )
        self.assertEqual(
            page.period_layout.count(),
            5,
        )
        self.assertEqual(
            page.overview_layout.count(),
            3,
        )

        period_cells_before = [
            page.period_layout.itemAt(index).widget()
            for index in range(
                page.period_layout.count()
            )
        ]

        page._set_layout_mode("narrow")

        self.assertEqual(
            [
                page.period_layout.itemAt(
                    index
                ).widget()
                for index in range(
                    page.period_layout.count()
                )
            ],
            period_cells_before,
        )

        page._set_layout_mode("wide")

        self.assertEqual(
            page.layout_mode,
            "wide",
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                0,
                0,
            ).widget(),
            page.metric_widget,
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                0,
                1,
            ).widget(),
            page.account_cards[0],
        )
        self.assertIs(
            page.hero_grid.itemAtPosition(
                1,
                1,
            ).widget(),
            page.account_cards[1],
        )
        self.assertEqual(
            page.period_layout.count(),
            9,
        )
        self.assertEqual(
            len(
                page.period_surface.findChildren(
                    QFrame,
                    "verticalDivider",
                )
            ),
            4,
        )
        self.assertEqual(
            page.overview_layout.count(),
            3,
        )

    def test_surface_engine_draws_surface_and_background(
        self,
    ):
        dashboard_module.SurfaceEngine._noise_tile = (
            None
        )

        surface_pixmap = QPixmap(180, 120)
        surface_pixmap.fill(Qt.transparent)
        surface_painter = QPainter(
            surface_pixmap
        )

        dashboard_module.SurfaceEngine.draw_surface(
            painter=surface_painter,
            rect=QRectF(
                5.0,
                5.0,
                170.0,
                110.0,
            ),
            radius=18,
            base_color="#101B24",
            start_color="#182B38",
            end_color="#0D1720",
            glow_color=QColor(
                58,
                78,
                103,
                18,
            ),
            border_color="#293B46",
            border_top_color="#304550",
        )
        surface_painter.end()

        self.assertFalse(
            surface_pixmap.isNull()
        )
        self.assertIsNotNone(
            dashboard_module.SurfaceEngine
            ._noise_tile
        )

        background_pixmap = QPixmap(
            200,
            140,
        )
        background_pixmap.fill(
            Qt.transparent
        )
        background_painter = QPainter(
            background_pixmap
        )

        dashboard_module.SurfaceEngine.draw_page_background(
            background_painter,
            QRectF(
                0.0,
                0.0,
                200.0,
                140.0,
            ),
        )
        background_painter.end()

        self.assertFalse(
            background_pixmap.isNull()
        )

    def test_corporate_surface_hover_shadow_and_paint(
        self,
    ):
        parent = QWidget()
        self.pages.append(parent)

        surface = dashboard_module.CorporateSurface(
            role="hero",
            object_name="testCorporateSurface",
            hover_enabled=True,
            parent=parent,
        )
        surface.resize(220, 130)

        self.assertIs(
            surface.parent(),
            parent,
        )
        self.assertEqual(
            surface._role,
            "hero",
        )
        self.assertTrue(
            surface._hover_enabled
        )
        self.assertFalse(
            surface._hovered
        )
        self.assertFalse(
            surface.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        self.assertTrue(
            surface.testAttribute(
                Qt.WA_TranslucentBackground
            )
        )
        self.assertIsInstance(
            surface.graphicsEffect(),
            QGraphicsDropShadowEffect,
        )
        self.assertEqual(
            surface._shadow.blurRadius(),
            48.0,
        )
        self.assertEqual(
            surface._shadow.yOffset(),
            6.0,
        )
        self.assertEqual(
            surface._shadow.color().getRgb(),
            (0, 0, 0, 72),
        )

        paint_event = QPaintEvent(
            surface.rect()
        )

        with (
            patch.object(
                dashboard_module.SurfaceEngine,
                "draw_surface",
            ) as draw_surface,
            patch.object(
                QFrame,
                "paintEvent",
            ),
        ):
            surface.paintEvent(
                paint_event
            )

        draw_surface.assert_called_once()
        self.assertEqual(
            draw_surface.call_args.kwargs[
                "border_color"
            ],
            "#293B46",
        )

        enter_event = QEnterEvent(
            QPointF(2.0, 2.0),
            QPointF(2.0, 2.0),
            QPointF(2.0, 2.0),
        )
        surface.enterEvent(enter_event)

        self.assertTrue(
            surface._hovered
        )
        self.assertEqual(
            surface._shadow.blurRadius(),
            52.0,
        )

        with (
            patch.object(
                dashboard_module.SurfaceEngine,
                "draw_surface",
            ) as draw_surface,
            patch.object(
                QFrame,
                "paintEvent",
            ),
        ):
            surface.paintEvent(
                paint_event
            )

        draw_surface.assert_called_once()
        self.assertEqual(
            draw_surface.call_args.kwargs[
                "border_color"
            ],
            "#3A5664",
        )

        surface.leaveEvent(
            QEvent(QEvent.Leave)
        )

        self.assertFalse(
            surface._hovered
        )
        self.assertEqual(
            surface._shadow.blurRadius(),
            48.0,
        )

        non_hover_surface = (
            dashboard_module.CorporateSurface(
                role="account",
                object_name="noHoverSurface",
                hover_enabled=False,
                parent=parent,
            )
        )
        non_hover_surface.resize(
            160,
            90,
        )
        original_blur = (
            non_hover_surface
            ._shadow
            .blurRadius()
        )

        non_hover_surface.enterEvent(
            enter_event
        )
        non_hover_surface.leaveEvent(
            QEvent(QEvent.Leave)
        )

        self.assertFalse(
            non_hover_surface._hovered
        )
        self.assertEqual(
            non_hover_surface
            ._shadow
            .blurRadius(),
            original_blur,
        )

    def test_elevated_panels_render_hero_and_standard_palettes(
        self,
    ):
        parent = QWidget()
        self.pages.append(parent)

        for object_name, radius in (
            (
                "dashboardHeroSurface",
                24,
            ),
            (
                "dashboardSummarySurface",
                18,
            ),
        ):
            with self.subTest(
                object_name=object_name
            ):
                panel = (
                    dashboard_module
                    .ElevatedInnerPanel(
                        object_name,
                        radius=radius,
                        parent=parent,
                    )
                )
                panel.resize(
                    260,
                    170,
                )

                self.assertEqual(
                    panel._radius,
                    radius,
                )
                self.assertEqual(
                    panel.objectName(),
                    object_name,
                )
                self.assertFalse(
                    panel.testAttribute(
                        Qt.WA_StyledBackground
                    )
                )
                self.assertTrue(
                    panel.testAttribute(
                        Qt.WA_TranslucentBackground
                    )
                )

                target = QPixmap(
                    260,
                    170,
                )
                target.fill(
                    Qt.transparent
                )
                panel.render(target)

                self.assertFalse(
                    target.isNull()
                )

    def test_dashboard_render_and_resize_event(
        self,
    ):
        updated = SignalStub()
        error = SignalStub()
        data_manager = SimpleNamespace(
            portfolio_updated=updated,
            portfolio_error=error,
            get_portfolio=Mock(return_value=None),
            get_price=Mock(return_value=None),
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
                return_value=[],
            ),
        ):
            page = dashboard_module.DashboardPage(
                data_manager
            )
            self.pages.append(page)

        page.resize(
            920,
            720,
        )
        target = QPixmap(
            920,
            720,
        )
        target.fill(
            Qt.transparent
        )

        with patch.object(
            dashboard_module.SurfaceEngine,
            "draw_page_background",
            wraps=(
                dashboard_module.SurfaceEngine
                .draw_page_background
            ),
        ) as draw_background:
            page.render(target)

        self.assertTrue(
            draw_background.called
        )

        page._sync_layout_mode = Mock()
        resize_event = QResizeEvent(
            QSize(900, 700),
            QSize(800, 600),
        )

        with patch.object(
            QWidget,
            "resizeEvent",
        ) as super_resize:
            page.resizeEvent(
                resize_event
            )

        super_resize.assert_called_once_with(
            resize_event
        )
        page._sync_layout_mode.assert_called_once_with()

    def test_account_daily_changes_handles_nested_invalid_data(
        self,
    ):
        page = self.make_page()
        self.build_value_labels(page)

        page._update_account_daily_changes(
            breakdown={
                "funding": {
                    "1d": 1.0,
                },
                "trading": {
                    "1d": -1.0,
                },
            },
            analytics={
                "period_changes": "invalid",
            },
        )

        self.assertEqual(
            page.funding_change_amount.text(),
            "—",
        )
        self.assertEqual(
            page.trading_change_amount.text(),
            "—",
        )

        page._update_account_daily_changes(
            breakdown={},
            analytics={
                "period_changes": {
                    "1d": "invalid",
                },
            },
        )

        self.assertEqual(
            page.funding_change.text(),
            "—",
        )
        self.assertEqual(
            page.trading_change.text(),
            "—",
        )

        page._update_account_daily_changes(
            breakdown={},
            analytics={
                "period_changes": {
                    "1d": {
                        "funding": "invalid",
                        "trading": [],
                    },
                },
            },
        )

        self.assertEqual(
            page.funding_change_amount.text(),
            "—",
        )
        self.assertEqual(
            page.trading_change_amount.text(),
            "—",
        )

    def test_show_event_normalizes_invalid_performance(
        self,
    ):
        page = self.make_page()
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value={
                    "performance": "invalid",
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
            ),
            patch.object(
                dashboard_module.QTimer,
                "singleShot",
            ),
        ):
            page.showEvent(event)

        page._update_period_cards.assert_called_once_with(
            {}
        )
        page._update_dashboard_summaries.assert_called_once_with(
            {}
        )



if __name__ == "__main__":
    unittest.main()
