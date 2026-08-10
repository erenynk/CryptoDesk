import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QWidget,
)

import ui.portfolio as portfolio_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class WorkerStub:
    def __init__(self, running=False):
        self.result_ready = SignalStub()
        self.isRunning = Mock(return_value=running)
        self.start = Mock()
        self.deleteLater = Mock()
        self.quit = Mock()
        self.wait = Mock()


class BarePortfolioPage(portfolio_module.PortfolioPage):
    def __init__(self):
        QWidget.__init__(self)

        self.worker = None
        self.raw_assets_data = []
        self.headers = [
            "",
            "VARLIK",
            "TOPLAM DEĞER",
            "ANLIK FİYAT",
            "TOPLAM MİKTAR",
            "PNL",
        ]


class PortfolioPageTestCase(unittest.TestCase):
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
        page = BarePortfolioPage()
        self.pages.append(page)
        return page

    @staticmethod
    def make_table():
        table = QTableWidget()
        table.setColumnCount(6)
        table.setHorizontalHeaderLabels(
            [
                "",
                "VARLIK",
                "TOPLAM DEĞER",
                "ANLIK FİYAT",
                "TOPLAM MİKTAR",
                "PNL",
            ]
        )
        return table

    @staticmethod
    def attach_summary_labels(page):
        page.total_balance_label = QLabel()
        page.asset_count_label = QLabel()
        page.daily_pnl_label = QLabel()
        page.daily_pnl_usdt_label = QLabel()
        page.portfolio_total_pnl_percent_value = QLabel()
        page.portfolio_total_pnl_usdt_value = QLabel()
        page.trading_total_pnl_percent_value = QLabel()
        page.trading_total_pnl_usdt_value = QLabel()
        page.connection_badge = Mock()
        page.refresh_button = Mock()

    def test_numeric_item_uses_numeric_comparison_and_fallback(
        self,
    ):
        first = portfolio_module.NumericTableWidgetItem(
            10.0,
            "10",
        )
        second = portfolio_module.NumericTableWidgetItem(
            20.0,
            "2",
        )
        plain = QTableWidgetItem("30")

        self.assertTrue(first < second)
        self.assertFalse(second < first)
        self.assertIsInstance(
            first.__lt__(plain),
            bool,
        )
        self.assertEqual(first.value, 10.0)
        self.assertEqual(first.text(), "10")

    def test_full_constructor_builds_ui_styles_and_timer(
        self,
    ):
        data_manager = SimpleNamespace(
            loading=False,
        )

        with patch.object(
            portfolio_module.QTimer,
            "singleShot",
        ) as single_shot:
            page = portfolio_module.PortfolioPage(
                data_manager,
                sentinel.dashboard_page,
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            data_manager,
        )
        self.assertIs(
            page.dashboard_page,
            sentinel.dashboard_page,
        )
        self.assertIsNone(page.worker)
        self.assertEqual(page.raw_assets_data, [])
        self.assertEqual(len(page.headers), 6)
        self.assertEqual(
            page.objectName(),
            "portfolioPage",
        )
        self.assertTrue(
            page.testAttribute(
                Qt.WA_StyledBackground
            )
        )

        self.assertEqual(
            page.layout().count(),
            1,
        )
        self.assertEqual(
            page.scroll_area.objectName(),
            "portfolioScrollArea",
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
            "portfolioContent",
        )
        self.assertEqual(
            page.main_layout.count(),
            5,
        )

        self.assertEqual(
            page.header.objectName(),
            "portfolioHeader",
        )
        self.assertEqual(
            page.hide_dust_checkbox.objectName(),
            "hideDustCheckbox",
        )
        self.assertEqual(
            page.hide_dust_checkbox.text(),
            "Küçük Bakiyeleri Gizle (< $1)",
        )
        self.assertEqual(
            page.refresh_button.objectName(),
            "refreshButton",
        )
        self.assertEqual(
            page.refresh_button.text(),
            "Bakiyeleri Yenile",
        )

        self.assertEqual(
            page.summary_card.objectName(),
            "portfolioSummaryCard",
        )
        self.assertEqual(
            page.total_balance_label.text(),
            "$0.00",
        )
        self.assertEqual(
            page.asset_count_label.text(),
            "0 farklı kripto varlık listeleniyor",
        )
        self.assertEqual(
            page.connection_badge.objectName(),
            "portfolioConnectionBadge",
        )
        self.assertEqual(
            page.connection_badge.text(),
            "Bekleniyor",
        )
        self.assertEqual(
            page.daily_pnl_label.text(),
            "—",
        )
        self.assertEqual(
            page.daily_pnl_usdt_label.text(),
            "—",
        )

        self.assertEqual(
            page.table_card.objectName(),
            "portfolioTableCard",
        )
        self.assertEqual(
            page.trading_table_card.objectName(),
            "portfolioTradingTableCard",
        )
        self.assertEqual(
            page.table.objectName(),
            "portfolioTable",
        )
        self.assertEqual(
            page.trading_table.objectName(),
            "portfolioTradingTable",
        )
        self.assertEqual(
            page.table.columnCount(),
            6,
        )
        self.assertEqual(
            page.trading_table.columnCount(),
            6,
        )
        self.assertEqual(
            page.table.horizontalHeader().objectName(),
            "portfolioTableHeader",
        )
        self.assertEqual(
            page.trading_table.horizontalHeader().objectName(),
            "portfolioTradingTableHeader",
        )
        self.assertFalse(page.table.showGrid())
        self.assertFalse(
            page.trading_table.showGrid()
        )
        self.assertFalse(
            page.table.verticalHeader().isVisible()
        )
        self.assertFalse(
            page.trading_table.verticalHeader().isVisible()
        )

        self.assertEqual(
            page.portfolio_header_row.objectName(),
            "portfolioAssetHeaderRow",
        )
        self.assertEqual(
            page.trading_header_row.objectName(),
            "portfolioTradingHeaderRow",
        )
        self.assertEqual(
            page.portfolio_total_pnl_widget.objectName(),
            "portfolioTotalPnlContainer",
        )
        self.assertEqual(
            page.trading_total_pnl_widget.objectName(),
            "tradingTotalPnlContainer",
        )

        self.assertEqual(
            page.refresh_timer.interval(),
            30000,
        )

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        for expected in (
            "Portfolio",
            "TOPLAM PORTFÖY DEĞERİ",
            "GÜNLÜK PNL",
            "Varlık Dağılımı",
            "Trading Hesabı",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, labels)

        stylesheet = page.styleSheet()

        for selector in (
            "QWidget#portfolioPage",
            "QScrollArea#portfolioScrollArea",
            "QFrame#portfolioSummaryCard",
            "QFrame#portfolioTableCard",
            "QFrame#portfolioTradingTableCard",
            "QTableWidget#portfolioTable",
            "QTableWidget#portfolioTradingTable",
            "QHeaderView#portfolioTableHeader",
            "QHeaderView#portfolioTradingTableHeader",
            "QLabel#dailyPnlValue",
        ):
            with self.subTest(selector=selector):
                self.assertIn(
                    selector,
                    stylesheet,
                )

        self.assertIn(
            portfolio_module.Theme.ACCENT,
            stylesheet,
        )
        self.assertIn(
            portfolio_module.Theme.TEXT_PRIMARY,
            stylesheet,
        )

        self.assertGreaterEqual(
            single_shot.call_count,
            2,
        )
        self.assertTrue(
            any(
                args.args
                and args.args[0] == 100
                for args in single_shot.call_args_list
            )
        )

    def test_schedule_and_sync_total_pnl_headers(
        self,
    ):
        page = self.make_page()
        page._sync_total_pnl_headers = Mock()

        with patch.object(
            portfolio_module.QTimer,
            "singleShot",
        ) as single_shot:
            page._schedule_total_pnl_header_sync(
                1,
                2,
            )

        single_shot.assert_called_once_with(
            0,
            page._sync_total_pnl_headers,
        )

        page._position_total_pnl_widget = Mock()
        page.trading_header_row = sentinel.trading_header
        page.trading_table = sentinel.trading_table
        page.trading_total_pnl_widget = sentinel.trading_pnl
        page.portfolio_header_row = sentinel.portfolio_header
        page.table = sentinel.portfolio_table
        page.portfolio_total_pnl_widget = sentinel.portfolio_pnl

        portfolio_module.PortfolioPage._sync_total_pnl_headers(
            page
        )

        self.assertEqual(
            page._position_total_pnl_widget.call_args_list,
            [
                call(
                    sentinel.trading_header,
                    sentinel.trading_table,
                    sentinel.trading_pnl,
                ),
                call(
                    sentinel.portfolio_header,
                    sentinel.portfolio_table,
                    sentinel.portfolio_pnl,
                ),
            ],
        )

    def test_position_total_pnl_widget_centers_and_raises(
        self,
    ):
        page = self.make_page()
        page.headers = ["", "A", "B", "C", "D", "PNL"]

        header = Mock()
        header.x.return_value = 10
        header.sectionViewportPosition.return_value = 120
        header.sectionSize.return_value = 200

        table = Mock()
        table.horizontalHeader.return_value = header

        header_row = Mock()
        header_row.height.return_value = 70

        size_hint = Mock()
        size_hint.height.return_value = 30

        pnl_widget = Mock()
        pnl_widget.width.return_value = 100
        pnl_widget.sizeHint.return_value = size_hint

        page._position_total_pnl_widget(
            header_row,
            table,
            pnl_widget,
        )

        header.sectionViewportPosition.assert_called_once_with(
            5
        )
        header.sectionSize.assert_called_once_with(5)
        pnl_widget.resize.assert_called_once_with(
            100,
            30,
        )
        pnl_widget.move.assert_called_once_with(
            180,
            20,
        )
        pnl_widget.raise_.assert_called_once_with()

    def test_configure_refresh_timer_connects_timeout(
        self,
    ):
        page = self.make_page()
        page.load_balances = Mock()

        page._configure_refresh_timer()

        self.assertEqual(
            page.refresh_timer.interval(),
            30000,
        )

        page.refresh_timer.timeout.emit()

        page.load_balances.assert_called_once_with()

    def test_sort_indicator_updates_headers_and_skips_none(
        self,
    ):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(7)
        page.table.setHorizontalHeaderLabels(
            page.headers
        )

        page.on_sort_indicator_changed(
            2,
            Qt.AscendingOrder,
        )

        self.assertEqual(
            page.table.horizontalHeaderItem(2).text(),
            "TOPLAM DEĞER ▲",
        )
        self.assertEqual(
            page.table.horizontalHeaderItem(1).text(),
            "VARLIK",
        )
        self.assertIsNone(
            page.table.horizontalHeaderItem(6)
        )

        page.on_sort_indicator_changed(
            3,
            Qt.DescendingOrder,
        )

        self.assertEqual(
            page.table.horizontalHeaderItem(3).text(),
            "ANLIK FİYAT ▼",
        )
        self.assertEqual(
            page.table.horizontalHeaderItem(2).text(),
            "TOPLAM DEĞER",
        )

        before = (
            page.table.horizontalHeaderItem(3).text()
        )
        page.on_sort_indicator_changed(
            -1,
            Qt.AscendingOrder,
        )
        self.assertEqual(
            page.table.horizontalHeaderItem(3).text(),
            before,
        )

    def test_trading_sort_indicator_updates_headers(
        self,
    ):
        page = self.make_page()
        page.trading_table = QTableWidget()
        page.trading_table.setColumnCount(7)
        page.trading_table.setHorizontalHeaderLabels(
            page.headers
        )

        page.on_trading_sort_indicator_changed(
            1,
            Qt.AscendingOrder,
        )
        self.assertEqual(
            page.trading_table
            .horizontalHeaderItem(1)
            .text(),
            "VARLIK ▲",
        )
        self.assertIsNone(
            page.trading_table
            .horizontalHeaderItem(6)
        )

        page.on_trading_sort_indicator_changed(
            5,
            Qt.DescendingOrder,
        )
        self.assertEqual(
            page.trading_table
            .horizontalHeaderItem(5)
            .text(),
            "PNL ▼",
        )
        self.assertEqual(
            page.trading_table
            .horizontalHeaderItem(1)
            .text(),
            "VARLIK",
        )

        page.on_trading_sort_indicator_changed(
            -1,
            Qt.AscendingOrder,
        )

    def test_start_page_loads_and_starts_timer(
        self,
    ):
        page = self.make_page()
        page.load_balances = Mock()
        page.refresh_timer = Mock()

        page.start_page()

        page.load_balances.assert_called_once_with()
        page.refresh_timer.start.assert_called_once_with()

    def test_load_balances_respects_loading_and_running_worker(
        self,
    ):
        page = self.make_page()
        page.data_manager = SimpleNamespace(
            loading=True
        )
        page._set_loading_state = Mock()

        with patch.object(
            portfolio_module,
            "PortfolioRefreshWorker",
        ) as worker_class:
            page.load_balances()

        worker_class.assert_not_called()
        page._set_loading_state.assert_not_called()

        page.data_manager.loading = False
        page.worker = WorkerStub(running=True)

        with patch.object(
            portfolio_module,
            "PortfolioRefreshWorker",
        ) as worker_class:
            page.load_balances()

        worker_class.assert_not_called()
        page._set_loading_state.assert_not_called()

    def test_load_balances_creates_connects_and_starts_worker(
        self,
    ):
        page = self.make_page()
        page.data_manager = sentinel.data_manager
        page.data_manager = SimpleNamespace(
            loading=False
        )
        page._set_loading_state = Mock()
        page.on_balances_loaded = Mock()
        worker = WorkerStub(running=False)

        with patch.object(
            portfolio_module,
            "PortfolioRefreshWorker",
            return_value=worker,
        ) as worker_class:
            page.load_balances()

        page._set_loading_state.assert_called_once_with()
        worker_class.assert_called_once_with(
            page.data_manager
        )
        self.assertIs(page.worker, worker)
        self.assertEqual(
            worker.result_ready.callbacks,
            [
                page.on_balances_loaded,
                worker.deleteLater,
            ],
        )
        worker.start.assert_called_once_with()

    def test_balances_loaded_success_uses_result_fallback(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)
        portfolio = {
            "total_usdt": 12345.678,
            "assets": [
                {
                    "coin": "BTC",
                    "total": 1.0,
                }
            ],
        }
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value=None
            )
        )
        page._update_daily_pnl = Mock()
        page._update_portfolio_total_pnl = Mock()
        page._update_trading_total_pnl = Mock()
        page.update_table_view = Mock()
        page.update_trading_table_view = Mock()
        page._set_connected_state = Mock()
        page._set_error_state = Mock()
        page.worker = sentinel.worker

        page.on_balances_loaded(
            True,
            portfolio,
        )

        self.assertEqual(
            page.total_balance_label.text(),
            "$12,345.68",
        )
        self.assertEqual(
            page.raw_assets_data,
            portfolio["assets"],
        )
        page._update_daily_pnl.assert_called_once_with(
            portfolio
        )
        page._update_portfolio_total_pnl.assert_called_once_with()
        page._update_trading_total_pnl.assert_called_once_with()
        page.update_table_view.assert_called_once_with()
        page.update_trading_table_view.assert_called_once_with()
        page._set_connected_state.assert_called_once_with()
        page._set_error_state.assert_not_called()
        page.refresh_button.setEnabled.assert_called_once_with(
            True
        )
        page.refresh_button.setText.assert_called_once_with(
            "Bakiyeleri Yenile"
        )
        self.assertIsNone(page.worker)

    def test_balances_loaded_success_prefers_manager_cache(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)
        cached = {
            "total_usdt": 500.0,
            "assets": [],
        }
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value=cached
            )
        )
        page._update_daily_pnl = Mock()
        page._update_portfolio_total_pnl = Mock()
        page._update_trading_total_pnl = Mock()
        page.update_table_view = Mock()
        page.update_trading_table_view = Mock()
        page._set_connected_state = Mock()

        page.on_balances_loaded(
            True,
            {
                "total_usdt": 1.0,
                "assets": [
                    {
                        "coin": "IGNORED",
                    }
                ],
            },
        )

        self.assertEqual(
            page.total_balance_label.text(),
            "$500.00",
        )
        self.assertEqual(
            page.raw_assets_data,
            [],
        )

    def test_balances_loaded_failure_sets_error_and_prints(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)
        page._set_error_state = Mock()
        page.worker = sentinel.worker

        with patch("builtins.print") as print_mock:
            page.on_balances_loaded(
                False,
                "network failed",
            )

        self.assertEqual(
            page.total_balance_label.text(),
            "Bağlantı Hatası",
        )
        page._set_error_state.assert_called_once_with()
        print_mock.assert_called_once_with(
            "Portfolio refresh error:",
            "network failed",
        )
        page.refresh_button.setEnabled.assert_called_once_with(
            True
        )
        page.refresh_button.setText.assert_called_once_with(
            "Bakiyeleri Yenile"
        )
        self.assertIsNone(page.worker)

    def test_balances_loaded_failure_keeps_cached_portfolio(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)
        cached = {
            "total_usdt": 4321.5,
            "assets": [
                {
                    "coin": "BTC",
                    "total": 1.0,
                }
            ],
        }
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(
                return_value=cached
            )
        )
        page._update_daily_pnl = Mock()
        page._update_portfolio_total_pnl = Mock()
        page._update_trading_total_pnl = Mock()
        page.update_table_view = Mock()
        page.update_trading_table_view = Mock()
        page._set_error_state = Mock()
        page.worker = sentinel.worker

        with patch("builtins.print") as print_mock:
            page.on_balances_loaded(
                False,
                (
                    "Connection aborted.",
                    ConnectionResetError(
                        104,
                        "Bağlantı karşıdan kesildi",
                    ),
                ),
            )

        self.assertEqual(
            page.total_balance_label.text(),
            "$4,321.50",
        )
        self.assertEqual(
            page.raw_assets_data,
            cached["assets"],
        )
        page._update_daily_pnl.assert_called_once_with(
            cached
        )
        page._update_portfolio_total_pnl.assert_called_once_with()
        page._update_trading_total_pnl.assert_called_once_with()
        page.update_table_view.assert_called_once_with()
        page.update_trading_table_view.assert_called_once_with()
        page._set_error_state.assert_called_once_with()
        print_mock.assert_called_once()
        page.refresh_button.setEnabled.assert_called_once_with(
            True
        )
        page.refresh_button.setText.assert_called_once_with(
            "Bakiyeleri Yenile"
        )
        self.assertIsNone(page.worker)

    def test_connection_state_helpers_update_controls(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)

        page._set_loading_state()

        page.refresh_button.setEnabled.assert_called_with(
            False
        )
        page.refresh_button.setText.assert_called_with(
            "Güncelleniyor..."
        )
        page.connection_badge.set_status.assert_called_with(
            "Güncelleniyor",
            portfolio_module.StatusBadge.WARNING,
        )

        page._set_connected_state()
        page.connection_badge.set_status.assert_called_with(
            "API Bağlı",
            portfolio_module.StatusBadge.SUCCESS,
        )

        page._set_error_state()
        page.connection_badge.set_status.assert_called_with(
            "Bağlantı Hatası",
            portfolio_module.StatusBadge.ERROR,
        )

    def test_format_helpers(
        self,
    ):
        amount_cases = (
            (0, "0"),
            (1, "1"),
            (1.2300, "1.23"),
            (0.0001, "0.0001"),
        )

        for value, expected in amount_cases:
            with self.subTest(
                helper="amount",
                value=value,
            ):
                self.assertEqual(
                    portfolio_module.PortfolioPage
                    .format_amount(value),
                    expected,
                )

        price_cases = (
            (1234.567, "$1,234.57"),
            (1, "$1.00"),
            (0.123456, "$0.1235"),
            (0, "$0.00"),
            (-1, "$0.00"),
        )

        for value, expected in price_cases:
            with self.subTest(
                helper="price",
                value=value,
            ):
                self.assertEqual(
                    portfolio_module.PortfolioPage
                    .format_price(value),
                    expected,
                )

    def test_extract_percentage_numeric_string_invalid_and_missing(
        self,
    ):
        extract = (
            portfolio_module.PortfolioPage
            ._extract_percentage
        )

        self.assertEqual(
            extract(
                {
                    "first": 1.25,
                },
                ("first",),
            ),
            1.25,
        )
        self.assertEqual(
            extract(
                {
                    "first": " 2.50% ",
                },
                ("first",),
            ),
            2.5,
        )
        self.assertEqual(
            extract(
                {
                    "first": "invalid",
                    "second": -3,
                },
                (
                    "first",
                    "second",
                ),
            ),
            -3.0,
        )
        self.assertIsNone(
            extract(
                {
                    "first": None,
                },
                (
                    "first",
                    "missing",
                ),
            )
        )

    def test_asset_pnl_percent_direct_and_cost_fallbacks(
        self,
    ):
        page = self.make_page()

        self.assertEqual(
            page._get_asset_pnl_percent(
                {
                    "pnl_pct": "12.5%",
                }
            ),
            12.5,
        )
        self.assertEqual(
            page._get_asset_pnl_percent(
                {
                    "trading_pnl_percent": -4.5,
                },
                account_prefix="trading_",
            ),
            -4.5,
        )
        self.assertEqual(
            page._get_asset_pnl_percent(
                {
                    "price": 120.0,
                    "average_price": 100.0,
                }
            ),
            20.0,
        )
        self.assertEqual(
            page._get_asset_pnl_percent(
                {
                    "price": 80.0,
                    "trading_average_price": 100.0,
                },
                account_prefix="trading_",
            ),
            -20.0,
        )
        self.assertIsNone(
            page._get_asset_pnl_percent(
                {
                    "price": 100.0,
                    "average_price": "invalid",
                    "avg_price": 0,
                }
            )
        )
        self.assertIsNone(
            page._get_asset_pnl_percent(
                {
                    "price": 0,
                    "average_price": 100.0,
                }
            )
        )

    def test_daily_pnl_usdt_nested_fallback_and_missing(
        self,
    ):
        get_value = (
            portfolio_module.PortfolioPage
            ._get_daily_pnl_usdt
        )

        self.assertEqual(
            get_value(
                {
                    "analytics": {
                        "period_changes": {
                            "1d": {
                                "total": {
                                    "amount_usdt": 15.5,
                                }
                            }
                        }
                    }
                }
            ),
            15.5,
        )
        self.assertEqual(
            get_value(
                {
                    "analytics": {
                        "period_changes": "invalid",
                    },
                    "daily_profit_usdt": -8,
                }
            ),
            -8.0,
        )
        self.assertEqual(
            get_value(
                {
                    "analytics": {
                        "period_changes": {
                            "1d": "invalid",
                        }
                    },
                    "pnl_1d_usdt": 3,
                }
            ),
            3.0,
        )
        self.assertEqual(
            get_value(
                {
                    "analytics": {
                        "period_changes": {
                            "1d": {
                                "total": {
                                    "amount_usdt": "bad",
                                }
                            }
                        }
                    },
                    "daily_pnl_usdt": 1,
                }
            ),
            1.0,
        )
        self.assertIsNone(
            get_value(
                {
                    "analytics": None,
                }
            )
        )

    def test_update_daily_pnl_positive_negative_and_missing(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)

        page._update_daily_pnl(
            {
                "performance": {
                    "1d": 2.5,
                },
                "analytics": {
                    "period_changes": {
                        "1d": {
                            "total": {
                                "amount_usdt": 25.0,
                            }
                        }
                    }
                },
            }
        )

        self.assertEqual(
            page.daily_pnl_label.text(),
            "+2.50%",
        )
        self.assertEqual(
            page.daily_pnl_usdt_label.text(),
            "+25.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            page.daily_pnl_label.styleSheet(),
        )

        page._update_daily_pnl(
            {
                "performance": "invalid",
                "daily_pnl_percent": "-3.25%",
                "daily_pnl_usdt": -10.0,
            }
        )

        self.assertEqual(
            page.daily_pnl_label.text(),
            "-3.25%",
        )
        self.assertEqual(
            page.daily_pnl_usdt_label.text(),
            "-10.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ERROR,
            page.daily_pnl_label.styleSheet(),
        )

        page._update_daily_pnl(
            {
                "daily_pnl_usdt": 4.0,
            }
        )

        self.assertEqual(
            page.daily_pnl_label.text(),
            "—",
        )
        self.assertEqual(
            page.daily_pnl_usdt_label.text(),
            "+4.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            page.daily_pnl_usdt_label.styleSheet(),
        )

        page._update_daily_pnl({})

        self.assertEqual(
            page.daily_pnl_label.text(),
            "—",
        )
        self.assertEqual(
            page.daily_pnl_usdt_label.text(),
            "—",
        )
        self.assertIn(
            portfolio_module.Theme.TEXT_MUTED,
            page.daily_pnl_label.styleSheet(),
        )

    def test_portfolio_total_pnl_placeholder_and_calculation(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)

        page._set_portfolio_total_pnl_placeholder()

        self.assertEqual(
            page.portfolio_total_pnl_percent_value.text(),
            "—",
        )
        self.assertEqual(
            page.portfolio_total_pnl_usdt_value.text(),
            "—",
        )
        self.assertIn(
            portfolio_module.Theme.TEXT_MUTED,
            page.portfolio_total_pnl_percent_value.styleSheet(),
        )

        page.raw_assets_data = [
            {
                "coin": "USDT",
                "total": 100.0,
            },
            {
                "coin": "BTC",
                "total": 0.0,
            },
        ]
        page._update_portfolio_total_pnl()
        self.assertEqual(
            page.portfolio_total_pnl_percent_value.text(),
            "—",
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": False,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "total": 2.0,
                "cost_basis_available": True,
                "cost_basis_usdt": "bad",
                "pnl_usdt": 5.0,
            },
            {
                "coin": "SOL",
                "total": 3.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 0.0,
                "pnl_usdt": 1.0,
            },
        ]
        page._update_portfolio_total_pnl()
        self.assertEqual(
            page.portfolio_total_pnl_percent_value.text(),
            "—",
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": 20.0,
            },
            {
                "coin": "ETH",
                "total": 2.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 200.0,
                "pnl_usdt": -5.0,
            },
        ]
        page._update_portfolio_total_pnl()

        self.assertEqual(
            page.portfolio_total_pnl_percent_value.text(),
            "+5.00%",
        )
        self.assertEqual(
            page.portfolio_total_pnl_usdt_value.text(),
            "+15.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            page.portfolio_total_pnl_percent_value.styleSheet(),
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": -25.0,
            }
        ]
        page._update_portfolio_total_pnl()

        self.assertEqual(
            page.portfolio_total_pnl_percent_value.text(),
            "-25.00%",
        )
        self.assertIn(
            portfolio_module.Theme.ERROR,
            page.portfolio_total_pnl_percent_value.styleSheet(),
        )

    def test_trading_total_pnl_placeholder_and_calculation(
        self,
    ):
        page = self.make_page()
        self.attach_summary_labels(page)

        page._set_trading_total_pnl_placeholder()

        self.assertEqual(
            page.trading_total_pnl_percent_value.text(),
            "—",
        )
        self.assertEqual(
            page.trading_total_pnl_usdt_value.text(),
            "—",
        )

        page.raw_assets_data = [
            {
                "coin": "USDT",
                "trading_total": 100.0,
            },
            {
                "coin": "BTC",
                "trading_total": 0.0,
            },
        ]
        page._update_trading_total_pnl()
        self.assertEqual(
            page.trading_total_pnl_percent_value.text(),
            "—",
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "trading_total": 1.0,
                "trading_cost_basis_available": False,
                "trading_cost_basis_usdt": 100.0,
                "trading_pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "trading_total": 2.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": "bad",
                "trading_pnl_usdt": 5.0,
            },
            {
                "coin": "SOL",
                "trading_total": 3.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 0.0,
                "trading_pnl_usdt": 1.0,
            },
        ]
        page._update_trading_total_pnl()
        self.assertEqual(
            page.trading_total_pnl_percent_value.text(),
            "—",
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "trading_total": 1.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 100.0,
                "trading_pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "trading_total": 2.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 100.0,
                "trading_pnl_usdt": -5.0,
            },
        ]
        page._update_trading_total_pnl()

        self.assertEqual(
            page.trading_total_pnl_percent_value.text(),
            "+2.50%",
        )
        self.assertEqual(
            page.trading_total_pnl_usdt_value.text(),
            "+5.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            page.trading_total_pnl_percent_value.styleSheet(),
        )

        page.raw_assets_data = [
            {
                "coin": "BTC",
                "trading_total": 1.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 100.0,
                "trading_pnl_usdt": -10.0,
            }
        ]
        page._update_trading_total_pnl()

        self.assertEqual(
            page.trading_total_pnl_percent_value.text(),
            "-10.00%",
        )
        self.assertIn(
            portfolio_module.Theme.ERROR,
            page.trading_total_pnl_percent_value.styleSheet(),
        )

    def test_populate_asset_table_handles_all_pnl_states(
        self,
    ):
        page = self.make_page()
        table = self.make_table()
        assets = [
            {
                "coin": "USDT",
                "price": 1.0,
                "trading_total": 100.0,
                "trading_usdt_value": 100.0,
                "trading_pnl_percent": 0.0,
                "trading_pnl_usdt": 0.0,
            },
            {
                "coin": "BTC",
                "price": 70000.0,
                "trading_total": 0.1,
                "trading_usdt_value": 7000.0,
                "trading_pnl_percent": 10.0,
                "trading_pnl_usdt": 500.0,
            },
            {
                "coin": "ETH",
                "price": 3000.0,
                "trading_total": 1.5,
                "trading_usdt_value": 4500.0,
                "trading_pnl_percent": -5.0,
                "trading_pnl_usdt": -200.0,
            },
            {
                "coin": "DOGE",
                "price": 0.12,
                "trading_total": 1000.0,
                "trading_usdt_value": 120.0,
            },
        ]

        page._populate_asset_table(
            table,
            assets,
            amount_key="trading_total",
            value_key="trading_usdt_value",
            pnl_prefix="trading_",
        )

        self.assertEqual(table.rowCount(), 4)
        self.assertTrue(table.updatesEnabled())
        self.assertTrue(table.isSortingEnabled())

        rows = {
            table.item(row, 1).text(): row
            for row in range(table.rowCount())
        }

        self.assertEqual(
            table.item(rows["BTC"], 2).text(),
            "$7,000.00",
        )
        self.assertEqual(
            table.item(rows["BTC"], 3).text(),
            "$70,000.00",
        )
        self.assertEqual(
            table.item(rows["BTC"], 4).text(),
            "0.1",
        )
        self.assertIsInstance(
            table.item(rows["BTC"], 5),
            portfolio_module.NumericTableWidgetItem,
        )

        usdt_labels = table.cellWidget(
            rows["USDT"],
            5,
        ).findChildren(QLabel)
        self.assertEqual(
            [label.text() for label in usdt_labels],
            ["", ""],
        )

        btc_labels = table.cellWidget(
            rows["BTC"],
            5,
        ).findChildren(QLabel)
        self.assertEqual(
            [label.text() for label in btc_labels],
            [
                "+10.00%",
                "+500.00 USDT",
            ],
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            btc_labels[0].styleSheet(),
        )

        eth_labels = table.cellWidget(
            rows["ETH"],
            5,
        ).findChildren(QLabel)
        self.assertEqual(
            [label.text() for label in eth_labels],
            [
                "-5.00%",
                "-200.00 USDT",
            ],
        )
        self.assertIn(
            portfolio_module.Theme.ERROR,
            eth_labels[0].styleSheet(),
        )

        doge_labels = table.cellWidget(
            rows["DOGE"],
            5,
        ).findChildren(QLabel)
        self.assertEqual(
            [label.text() for label in doge_labels],
            [
                "—",
                "—",
            ],
        )
        self.assertIn(
            portfolio_module.Theme.TEXT_MUTED,
            doge_labels[0].styleSheet(),
        )

    def test_update_trading_table_view_filters_and_delegates(
        self,
    ):
        page = self.make_page()
        page.hide_dust_checkbox = QCheckBox()
        page.trading_table = self.make_table()
        page._populate_asset_table = Mock()
        page.on_trading_sort_indicator_changed = Mock()
        page.raw_assets_data = [
            {
                "coin": "ZERO",
                "trading_total": 0.0,
                "trading_usdt_value": 0.0,
            },
            {
                "coin": "DUST",
                "trading_total": 10.0,
                "trading_usdt_value": 0.5,
            },
            {
                "coin": "BTC",
                "trading_total": 1.0,
                "trading_usdt_value": 100.0,
            },
        ]

        page.hide_dust_checkbox.setChecked(False)
        page.update_trading_table_view()

        first_assets = (
            page._populate_asset_table
            .call_args_list[0]
            .args[1]
        )
        self.assertEqual(
            [
                asset["coin"]
                for asset in first_assets
            ],
            [
                "DUST",
                "BTC",
            ],
        )

        page.hide_dust_checkbox.setChecked(True)
        page.update_trading_table_view()

        second_assets = (
            page._populate_asset_table
            .call_args_list[1]
            .args[1]
        )
        self.assertEqual(
            [
                asset["coin"]
                for asset in second_assets
            ],
            ["BTC"],
        )
        self.assertEqual(
            page._populate_asset_table
            .call_args_list[1]
            .kwargs,
            {
                "amount_key": "trading_total",
                "value_key": "trading_usdt_value",
                "pnl_prefix": "trading_",
            },
        )
        self.assertEqual(
            page.on_trading_sort_indicator_changed.call_count,
            2,
        )

    def test_update_table_view_populates_filters_and_styles(
        self,
    ):
        page = self.make_page()
        page.hide_dust_checkbox = QCheckBox()
        page.hide_dust_checkbox.setChecked(True)
        page.table = self.make_table()
        page.asset_count_label = QLabel()
        page.raw_assets_data = [
            {
                "coin": "USDT",
                "total": 100.0,
                "usdt_value": 100.0,
                "price": 1.0,
                "pnl_percent": 0.0,
                "pnl_usdt": 0.0,
            },
            {
                "coin": "BTC",
                "total": 0.1,
                "usdt_value": 7000.0,
                "price": 70000.0,
                "pnl_percent": 10.0,
                "pnl_usdt": 500.0,
            },
            {
                "coin": "ETH",
                "total": 1.5,
                "usdt_value": 4500.0,
                "price": 3000.0,
                "pnl_percent": -5.0,
                "pnl_usdt": -200.0,
            },
            {
                "coin": "DOGE",
                "total": 1000.0,
                "usdt_value": 120.0,
                "price": 0.12,
            },
            {
                "coin": "DUST",
                "total": 5.0,
                "usdt_value": 0.5,
                "price": 0.1,
                "pnl_percent": 1.0,
                "pnl_usdt": 0.1,
            },
        ]

        page.update_table_view()

        self.assertEqual(page.table.rowCount(), 4)
        self.assertEqual(
            page.asset_count_label.text(),
            "4 farklı kripto varlık listeleniyor",
        )
        self.assertTrue(
            page.table.updatesEnabled()
        )
        self.assertTrue(
            page.table.isSortingEnabled()
        )

        rows = {
            page.table.item(row, 1).text(): row
            for row in range(
                page.table.rowCount()
            )
        }

        self.assertNotIn("DUST", rows)
        self.assertEqual(
            page.table.item(rows["BTC"], 2).text(),
            "$7,000.00",
        )
        self.assertEqual(
            page.table.item(rows["BTC"], 3).text(),
            "$70,000.00",
        )
        self.assertEqual(
            page.table.item(rows["BTC"], 4).text(),
            "0.1",
        )

        usdt_percent = page.table.cellWidget(
            rows["USDT"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlPercent",
        )
        usdt_amount = page.table.cellWidget(
            rows["USDT"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlUsdt",
        )
        self.assertEqual(usdt_percent.text(), "")
        self.assertEqual(usdt_amount.text(), "")

        btc_percent = page.table.cellWidget(
            rows["BTC"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlPercent",
        )
        btc_amount = page.table.cellWidget(
            rows["BTC"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlUsdt",
        )
        self.assertEqual(
            btc_percent.text(),
            "+10.00%",
        )
        self.assertEqual(
            btc_amount.text(),
            "+500.00 USDT",
        )
        self.assertIn(
            portfolio_module.Theme.ACCENT,
            btc_percent.styleSheet(),
        )

        eth_percent = page.table.cellWidget(
            rows["ETH"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlPercent",
        )
        self.assertEqual(
            eth_percent.text(),
            "-5.00%",
        )
        self.assertIn(
            portfolio_module.Theme.ERROR,
            eth_percent.styleSheet(),
        )

        doge_percent = page.table.cellWidget(
            rows["DOGE"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlPercent",
        )
        doge_amount = page.table.cellWidget(
            rows["DOGE"],
            5,
        ).findChild(
            QLabel,
            "portfolioPnlUsdt",
        )
        self.assertEqual(
            doge_percent.text(),
            "—",
        )
        self.assertEqual(
            doge_amount.text(),
            "—",
        )
        self.assertIn(
            portfolio_module.Theme.TEXT_MUTED,
            doge_percent.styleSheet(),
        )

        page.hide_dust_checkbox.setChecked(False)
        page.update_table_view()

        self.assertEqual(page.table.rowCount(), 5)
        self.assertEqual(
            page.asset_count_label.text(),
            "5 farklı kripto varlık listeleniyor",
        )

    def test_resize_and_show_events_schedule_sync_and_start_timer(
        self,
    ):
        page = self.make_page()
        page._schedule_total_pnl_header_sync = Mock()
        page.refresh_timer = Mock()
        page.refresh_timer.isActive.return_value = False
        resize_event = Mock()
        show_event = Mock()

        with patch.object(
            QWidget,
            "resizeEvent",
        ) as super_resize:
            page.resizeEvent(resize_event)

        super_resize.assert_called_once_with(
            resize_event
        )
        page._schedule_total_pnl_header_sync.assert_called_once_with()

        page._schedule_total_pnl_header_sync.reset_mock()

        with patch.object(
            QWidget,
            "showEvent",
        ) as super_show:
            page.showEvent(show_event)

        super_show.assert_called_once_with(
            show_event
        )
        page._schedule_total_pnl_header_sync.assert_called_once_with()
        page.refresh_timer.start.assert_called_once_with()

        page.refresh_timer.start.reset_mock()
        page.refresh_timer.isActive.return_value = True

        with patch.object(
            QWidget,
            "showEvent",
        ):
            page.showEvent(show_event)

        page.refresh_timer.start.assert_not_called()

    def test_close_event_stops_timer_and_running_worker(
        self,
    ):
        page = self.make_page()
        page.refresh_timer = Mock()
        page.worker = WorkerStub(running=True)
        event = Mock()

        with patch.object(
            QWidget,
            "closeEvent",
        ) as super_close:
            page.closeEvent(event)

        page.refresh_timer.stop.assert_called_once_with()
        page.worker.quit.assert_called_once_with()
        page.worker.wait.assert_called_once_with(
            3000
        )
        super_close.assert_called_once_with(event)

    def test_close_event_handles_absent_or_stopped_worker(
        self,
    ):
        page = self.make_page()
        page.refresh_timer = Mock()
        page.worker = None
        event = Mock()

        with patch.object(
            QWidget,
            "closeEvent",
        ):
            page.closeEvent(event)

        page.refresh_timer.stop.assert_called_once_with()

        page.refresh_timer.reset_mock()
        page.worker = WorkerStub(running=False)

        with patch.object(
            QWidget,
            "closeEvent",
        ):
            page.closeEvent(event)

        page.refresh_timer.stop.assert_called_once_with()
        page.worker.quit.assert_not_called()
        page.worker.wait.assert_not_called()


if __name__ == "__main__":
    unittest.main()
