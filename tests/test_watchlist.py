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
    QLabel,
    QLineEdit,
    QTableWidget,
    QWidget,
)

import ui.watchlist as watchlist_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class BareWatchlistPage(watchlist_module.WatchlistPage):
    def __init__(self):
        QWidget.__init__(self)
        self.headers = [
            "",
            "VARLIK",
            "ANLIK FİYAT",
            "EKLENME FİYATI",
            "DEĞİŞİM",
            "EKLENME TARİHİ",
            "İŞLEM",
        ]


class WatchlistPageTestCase(unittest.TestCase):
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
        page = BareWatchlistPage()
        self.pages.append(page)
        return page

    def prepare_add_page(self):
        page = self.make_page()
        page.symbol_input = QLineEdit()
        page.add_button = Mock()
        page.set_status = Mock()
        page.clear_status = Mock()
        page.load_symbols = Mock()
        page.data_manager = SimpleNamespace(
            okx=SimpleNamespace(
                is_spot_symbol_available=Mock()
            ),
            get_price=Mock(),
        )
        return page

    def test_constructor_initializes_and_loads(self):
        with (
            patch.object(
                watchlist_module.WatchlistPage,
                "_build_ui",
            ) as build_ui,
            patch.object(
                watchlist_module.WatchlistPage,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                watchlist_module.WatchlistPage,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                watchlist_module.WatchlistPage,
                "load_symbols",
            ) as load_symbols,
        ):
            page = watchlist_module.WatchlistPage(
                sentinel.data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            sentinel.data_manager,
        )
        self.assertEqual(
            page.objectName(),
            "watchlistPage",
        )
        self.assertEqual(len(page.headers), 7)
        self.assertTrue(
            page.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        connect_signals.assert_called_once_with()
        load_symbols.assert_called_once_with()

    def test_numeric_item_and_signal_connections(self):
        item = (
            watchlist_module.NumericTableWidgetItem(
                "123.45"
            )
        )
        self.assertEqual(item.text(), "123.45")

        page = self.make_page()
        return_pressed = SignalStub()
        clicked = SignalStub()
        cell_clicked = SignalStub()
        page.symbol_input = SimpleNamespace(
            returnPressed=return_pressed
        )
        page.add_button = SimpleNamespace(
            clicked=clicked
        )
        page.table = SimpleNamespace(
            cellClicked=cell_clicked
        )

        page._connect_signals()

        self.assertEqual(
            return_pressed.callbacks,
            [page.add_symbol],
        )
        self.assertEqual(
            clicked.callbacks,
            [page.add_symbol],
        )
        self.assertEqual(
            cell_clicked.callbacks,
            [page.on_table_cell_clicked],
        )

    def test_table_click_filters_and_removes_symbol(
        self,
    ):
        page = self.make_page()
        page.table = Mock()
        page.remove_symbol = Mock()

        page.on_table_cell_clicked(1, 5)
        page.table.item.assert_not_called()

        page.table.item.return_value = None
        page.on_table_cell_clicked(1, 6)
        page.remove_symbol.assert_not_called()

        symbol_item = Mock()
        symbol_item.text.return_value = "  BTC  "
        page.table.item.return_value = symbol_item
        page.on_table_cell_clicked(2, 6)

        page.remove_symbol.assert_called_once_with(
            "BTC"
        )

    def test_status_helpers(self):
        page = self.make_page()
        page.status_label = QLabel()
        page.status_label.hide()

        page.set_status("Hata", error=True)

        self.assertEqual(
            page.status_label.text(),
            "Hata",
        )
        self.assertIn(
            watchlist_module.Theme.ERROR,
            page.status_label.styleSheet(),
        )
        self.assertFalse(
            page.status_label.isHidden()
        )

        page.clear_status()

        self.assertEqual(
            page.status_label.text(),
            "",
        )
        self.assertTrue(
            page.status_label.isHidden()
        )

    def test_add_symbol_rejects_empty_value(self):
        page = self.prepare_add_page()
        page.symbol_input.setText("   ")

        with patch.object(
            watchlist_module.watchlist_service,
            "normalize_symbol",
            return_value="",
        ):
            page.add_symbol()

        page.set_status.assert_called_once_with(
            "Coin adı boş olamaz.",
            error=True,
        )
        page.add_button.setEnabled.assert_not_called()
        page.data_manager.okx.is_spot_symbol_available.assert_not_called()

    def test_add_symbol_handles_lookup_failure(self):
        page = self.prepare_add_page()
        page.symbol_input.setText("btc")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            False,
            "Sembol listesi alınamadı.",
        )

        with patch.object(
            watchlist_module.watchlist_service,
            "normalize_symbol",
            return_value="BTC",
        ):
            page.add_symbol()

        page.set_status.assert_called_once_with(
            "Sembol listesi alınamadı.",
            error=True,
        )
        self.assertEqual(
            page.add_button.setEnabled.call_args_list,
            [
                call(False),
                call(True),
            ],
        )
        self.assertEqual(
            page.add_button.setText.call_args_list,
            [
                call("Kontrol ediliyor..."),
                call("Watchlist'e Ekle"),
            ],
        )

    def test_add_symbol_rejects_unavailable_symbol(self):
        page = self.prepare_add_page()
        page.symbol_input.setText("abc")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            False,
        )

        with patch.object(
            watchlist_module.watchlist_service,
            "normalize_symbol",
            return_value="ABC",
        ):
            page.add_symbol()

        page.set_status.assert_called_once_with(
            (
                "ABC OKX Spot piyasasında "
                "bulunamadı."
            ),
            error=True,
        )
        page.data_manager.get_price.assert_not_called()

    def test_add_symbol_success(self):
        page = self.prepare_add_page()
        page.symbol_input.setText(" btc-usdt ")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            True,
        )
        page.data_manager.get_price.return_value = (
            70000.0
        )

        with (
            patch.object(
                watchlist_module.watchlist_service,
                "normalize_symbol",
                return_value="BTC",
            ),
            patch.object(
                watchlist_module.watchlist_service,
                "add_symbol",
                return_value=True,
            ) as add_symbol,
        ):
            page.add_symbol()

        add_symbol.assert_called_once_with(
            "BTC",
            70000.0,
        )
        self.assertEqual(
            page.symbol_input.text(),
            "",
        )
        page.clear_status.assert_called_once_with()
        page.load_symbols.assert_called_once_with()
        page.set_status.assert_not_called()
        page.add_button.setEnabled.assert_called_with(
            True
        )

    def test_add_symbol_duplicate_and_exception(self):
        page = self.prepare_add_page()
        page.symbol_input.setText("eth")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            True,
        )
        page.data_manager.get_price.return_value = (
            3000.0
        )

        with (
            patch.object(
                watchlist_module.watchlist_service,
                "normalize_symbol",
                return_value="ETH",
            ),
            patch.object(
                watchlist_module.watchlist_service,
                "add_symbol",
                return_value=False,
            ),
        ):
            page.add_symbol()

        page.set_status.assert_called_once_with(
            "ETH zaten watchlist'te.",
            error=True,
        )

        page.set_status.reset_mock()
        page.data_manager.okx.is_spot_symbol_available.side_effect = (
            RuntimeError("network error")
        )

        with patch.object(
            watchlist_module.watchlist_service,
            "normalize_symbol",
            return_value="ETH",
        ):
            page.add_symbol()

        page.set_status.assert_called_once_with(
            "Coin kontrol edilemedi: network error",
            error=True,
        )
        page.add_button.setText.assert_called_with(
            "Watchlist'e Ekle"
        )

    def test_remove_symbol_success_and_failure(self):
        page = self.make_page()
        page.clear_status = Mock()
        page.load_symbols = Mock()
        page.set_status = Mock()

        with patch.object(
            watchlist_module.watchlist_service,
            "remove_symbol",
            return_value=True,
        ):
            page.remove_symbol("BTC")

        page.clear_status.assert_called_once_with()
        page.load_symbols.assert_called_once_with()

        page.clear_status.reset_mock()
        page.load_symbols.reset_mock()

        with patch.object(
            watchlist_module.watchlist_service,
            "remove_symbol",
            return_value=False,
        ):
            page.remove_symbol("ETH")

        page.set_status.assert_called_once_with(
            "ETH silinemedi.",
            error=True,
        )
        page.clear_status.assert_not_called()
        page.load_symbols.assert_not_called()

    def test_format_price(self):
        cases = (
            (None, "-"),
            (0, "-"),
            (-1, "-"),
            (1, "$1.00"),
            (1234.567, "$1,234.57"),
            (0.123456, "$0.1235"),
        )

        for price, expected in cases:
            with self.subTest(price=price):
                self.assertEqual(
                    (
                        watchlist_module
                        .WatchlistPage
                        .format_price(price)
                    ),
                    expected,
                )

    def test_format_date(self):
        cases = (
            (
                "2026-07-22T18:45:00",
                "22.07.2026 18:45",
            ),
            (
                "2026-07-22T15:45:00Z",
                "22.07.2026 15:45",
            ),
            (None, "-"),
            ("invalid", "-"),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    (
                        watchlist_module
                        .WatchlistPage
                        .format_date(value)
                    ),
                    expected,
                )

    def test_format_change(self):
        self.assertEqual(
            (
                watchlist_module
                .WatchlistPage
                .format_change(None, 100)
            ),
            (
                "-",
                watchlist_module.Theme.TEXT_MUTED,
            ),
        )
        self.assertEqual(
            (
                watchlist_module
                .WatchlistPage
                .format_change(120, 100)
            ),
            (
                "+20.00%",
                watchlist_module.Theme.ACCENT,
            ),
        )
        self.assertEqual(
            (
                watchlist_module
                .WatchlistPage
                .format_change(80, 100)
            ),
            (
                "-20.00%",
                watchlist_module.Theme.ERROR,
            ),
        )

    def test_make_item_applies_style(self):
        item = (
            watchlist_module.WatchlistPage.make_item(
                "BTC",
                color="#123456",
                bold=False,
                alignment=(
                    Qt.AlignLeft
                    | Qt.AlignVCenter
                ),
            )
        )

        self.assertIsInstance(
            item,
            watchlist_module.NumericTableWidgetItem,
        )
        self.assertEqual(item.text(), "BTC")
        self.assertEqual(
            item.foreground().color(),
            QColor("#123456"),
        )
        self.assertFalse(item.font().bold())
        self.assertEqual(
            item.textAlignment(),
            int(
                Qt.AlignLeft
                | Qt.AlignVCenter
            ),
        )

    def test_load_symbols_populates_table(self):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(7)
        page.asset_count_badge = Mock()
        page.data_manager = SimpleNamespace(
            get_price=Mock(
                side_effect=lambda symbol: {
                    "BTC": 120.0,
                    "ETH": 80.0,
                }[symbol]
            )
        )

        items = [
            {
                "symbol": " btc-usdt ",
                "added_price": 100.0,
                "created_at": (
                    "2026-07-22T10:30:00"
                ),
            },
            {
                "symbol": "eth",
                "added_price": 100.0,
                "created_at": (
                    "2026-07-21T09:15:00"
                ),
            },
        ]

        with (
            patch.object(
                watchlist_module.watchlist_service,
                "get_items",
                return_value=items,
            ),
            patch.object(
                watchlist_module.watchlist_service,
                "normalize_symbol",
                side_effect=[
                    "BTC",
                    "ETH",
                ],
            ),
        ):
            page.load_symbols()

        self.assertEqual(page.table.rowCount(), 2)

        expected = {
            (0, 0): "1",
            (0, 1): "BTC",
            (0, 2): "$120.00",
            (0, 3): "$100.00",
            (0, 4): "+20.00%",
            (0, 5): "22.07.2026 10:30",
            (0, 6): "Kaldır",
            (1, 0): "2",
            (1, 1): "ETH",
            (1, 2): "$80.00",
            (1, 3): "$100.00",
            (1, 4): "-20.00%",
            (1, 5): "21.07.2026 09:15",
            (1, 6): "Kaldır",
        }

        for position, text in expected.items():
            with self.subTest(position=position):
                self.assertEqual(
                    page.table.item(
                        *position
                    ).text(),
                    text,
                )

        self.assertTrue(
            page.table.updatesEnabled()
        )
        page.asset_count_badge.set_status.assert_called_once_with(
            "2 varlık",
            watchlist_module.StatusBadge.SUCCESS,
        )

    def test_load_symbols_handles_empty_list(self):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(7)
        page.table.setRowCount(3)
        page.asset_count_badge = Mock()
        page.data_manager = SimpleNamespace(
            get_price=Mock()
        )

        with patch.object(
            watchlist_module.watchlist_service,
            "get_items",
            return_value=[],
        ):
            page.load_symbols()

        self.assertEqual(page.table.rowCount(), 0)
        page.data_manager.get_price.assert_not_called()
        page.asset_count_badge.set_status.assert_called_once_with(
            "0 varlık",
            watchlist_module.StatusBadge.NEUTRAL,
        )


if __name__ == "__main__":
    unittest.main()
