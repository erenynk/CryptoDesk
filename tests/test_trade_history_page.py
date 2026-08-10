import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLabel

from ui.trade_history import TradeHistoryPage


class FakeTradeService:
    def __init__(self, transactions):
        self.transactions = list(transactions)

    def get_transactions(self, **_kwargs):
        return list(self.transactions)


class FakeDataManager:
    loading = False
    okx = object()

    @staticmethod
    def get_portfolio():
        return {"assets": []}


class TradeHistoryPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def transaction(
        coin="BTC",
        side="buy",
        pnl_usdt=None,
        pnl_percent=None,
        quantity=1.0,
        timestamp=1000,
    ):
        return {
            "coin": coin,
            "side": side,
            "quantity": quantity,
            "price": 100.0,
            "total_usdt": quantity * 100.0,
            "pnl_usdt": pnl_usdt,
            "pnl_percent": pnl_percent,
            "executed_at_ms": timestamp,
            "executed_at": "2026-08-10T23:40:00+03:00",
        }

    def make_page(self, transactions):
        page = TradeHistoryPage(
            FakeDataManager(),
            trade_service=FakeTradeService(transactions),
        )
        self.addCleanup(page.close)
        return page

    def test_headers_and_row_height(self):
        page = self.make_page([])
        headers = [
            page.table.horizontalHeaderItem(index).text()
            .replace(" ▼", "")
            .replace(" ▲", "")
            for index in range(page.table.columnCount())
        ]

        self.assertEqual(
            headers,
            [
                "",
                "VARLIK",
                "İŞLEM",
                "MİKTAR",
                "FİYAT",
                "TOPLAM",
                "PNL",
                "TARİH",
            ],
        )
        self.assertEqual(
            page.table.verticalHeader().defaultSectionSize(),
            74,
        )

    def test_buy_pnl_cell_is_empty(self):
        page = self.make_page([self.transaction()])

        self.assertEqual(page.table.item(0, 6).text(), "")
        self.assertIsNone(page.table.cellWidget(0, 6))

    def test_sell_pnl_has_percent_and_usdt(self):
        page = self.make_page(
            [
                self.transaction(
                    side="sell",
                    pnl_usdt=25.0,
                    pnl_percent=12.5,
                )
            ]
        )

        widget = page.table.cellWidget(0, 6)
        texts = [
            label.text()
            for label in widget.findChildren(QLabel)
        ]
        self.assertEqual(
            texts,
            ["+12.50%", "+25.00 USDT"],
        )

    def test_coin_filter_and_sort(self):
        page = self.make_page(
            [
                self.transaction("BTC", quantity=1.0),
                self.transaction(
                    "ETH",
                    quantity=3.0,
                    timestamp=2000,
                ),
            ]
        )

        page.coin_filter.setText("bt")
        self.assertEqual(page.table.rowCount(), 1)
        self.assertEqual(page.table.item(0, 1).text(), "BTC")

        page.coin_filter.clear()
        page._on_header_clicked(3)
        self.assertEqual(page.table.item(0, 1).text(), "ETH")

        page._on_header_clicked(3)
        self.assertEqual(page.table.item(0, 1).text(), "BTC")

    def test_number_column_is_not_sortable(self):
        page = self.make_page(
            [
                self.transaction("BTC", quantity=1.0),
                self.transaction(
                    "ETH",
                    quantity=3.0,
                    timestamp=2000,
                ),
            ]
        )

        original_sort_column = page._sort_column
        original_sort_descending = page._sort_descending

        page._on_header_clicked(0)

        self.assertEqual(
            page._sort_column,
            original_sort_column,
        )
        self.assertEqual(
            page._sort_descending,
            original_sort_descending,
        )

    def test_row_numbers_stay_sequential_after_sort(self):
        page = self.make_page(
            [
                self.transaction("BTC", quantity=1.0),
                self.transaction(
                    "ETH",
                    quantity=3.0,
                    timestamp=2000,
                ),
                self.transaction(
                    "SOL",
                    quantity=2.0,
                    timestamp=3000,
                ),
            ]
        )

        page._on_header_clicked(3)

        self.assertEqual(
            [
                page.table.item(row, 0).text()
                for row in range(page.table.rowCount())
            ],
            ["1", "2", "3"],
        )

        page._on_header_clicked(3)

        self.assertEqual(
            [
                page.table.item(row, 0).text()
                for row in range(page.table.rowCount())
            ],
            ["1", "2", "3"],
        )

    def test_sort_does_not_reuse_sell_pnl_widget_for_buy(self):
        page = self.make_page(
            [
                self.transaction(
                    "BTC",
                    side="sell",
                    pnl_usdt=25.0,
                    pnl_percent=12.5,
                    quantity=3.0,
                    timestamp=3000,
                ),
                self.transaction(
                    "ETH",
                    side="buy",
                    quantity=1.0,
                    timestamp=1000,
                ),
            ]
        )

        self.assertEqual(
            page.table.item(0, 1).text(),
            "BTC",
        )
        self.assertIsNotNone(
            page.table.cellWidget(0, 6)
        )
        self.assertEqual(
            page.table.item(1, 1).text(),
            "ETH",
        )
        self.assertIsNone(
            page.table.cellWidget(1, 6)
        )

        page._on_header_clicked(3)
        page._on_header_clicked(3)

        self.assertEqual(
            page.table.item(0, 1).text(),
            "ETH",
        )
        self.assertEqual(
            page.table.item(0, 6).text(),
            "",
        )
        self.assertIsNone(
            page.table.cellWidget(0, 6)
        )

if __name__ == "__main__":
    unittest.main()
