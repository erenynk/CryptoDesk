import tempfile
import unittest
from pathlib import Path

from database.trade_history_db import TradeHistoryRepository


class TradeHistoryRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = (
            Path(self.temp_dir.name)
            / "trade-history-test.db"
        )
        self.repository = TradeHistoryRepository(
            db_path=self.db_path
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def _transaction(
        transaction_key,
        coin,
        side,
        total_usdt,
        executed_at_ms,
        pnl_usdt=None,
        pnl_percent=None,
    ):
        return {
            "transaction_key": transaction_key,
            "order_id": transaction_key,
            "instrument_id": f"{coin}-USDT",
            "coin": coin,
            "side": side,
            "quantity": 1.0,
            "price": total_usdt,
            "total_usdt": total_usdt,
            "average_cost": (
                100.0
                if pnl_usdt is not None
                else None
            ),
            "cost_basis_usdt": (
                100.0
                if pnl_usdt is not None
                else None
            ),
            "pnl_usdt": pnl_usdt,
            "pnl_percent": pnl_percent,
            "executed_at_ms": executed_at_ms,
            "executed_at": (
                "2026-08-10T23:00:00+03:00"
            ),
            "source_trade_ids": [transaction_key],
        }

    def test_upsert_preserves_empty_buy_pnl(self):
        item = self._transaction(
            "btc-buy",
            "BTC",
            "buy",
            100.0,
            1000,
        )

        self.repository.upsert_many([item])
        saved = self.repository.list_transactions()

        self.assertEqual(len(saved), 1)
        self.assertIsNone(saved[0]["pnl_usdt"])
        self.assertIsNone(saved[0]["pnl_percent"])

    def test_upsert_updates_existing_transaction(self):
        original = self._transaction(
            "btc-sell",
            "BTC",
            "sell",
            120.0,
            1000,
            pnl_usdt=20.0,
            pnl_percent=20.0,
        )
        updated = dict(original)
        updated["total_usdt"] = 130.0
        updated["pnl_usdt"] = 30.0
        updated["pnl_percent"] = 30.0

        self.repository.upsert_many([original])
        self.repository.upsert_many([updated])

        self.assertEqual(self.repository.count(), 1)
        saved = self.repository.list_transactions()[0]
        self.assertAlmostEqual(saved["pnl_usdt"], 30.0)

    def test_coin_filter_and_numeric_sort(self):
        items = [
            self._transaction(
                "btc-1",
                "BTC",
                "sell",
                100.0,
                1000,
                pnl_usdt=10.0,
                pnl_percent=10.0,
            ),
            self._transaction(
                "eth-1",
                "ETH",
                "sell",
                300.0,
                2000,
                pnl_usdt=50.0,
                pnl_percent=20.0,
            ),
            self._transaction(
                "btc-2",
                "BTC",
                "sell",
                200.0,
                3000,
                pnl_usdt=-20.0,
                pnl_percent=-10.0,
            ),
        ]
        self.repository.upsert_many(items)

        filtered = self.repository.list_transactions(
            coin="btc",
            sort_by="total_usdt",
            descending=False,
        )

        self.assertEqual(
            [item["transaction_key"] for item in filtered],
            ["btc-1", "btc-2"],
        )

    def test_source_trade_ids_round_trip(self):
        item = self._transaction(
            "btc-buy",
            "BTC",
            "buy",
            100.0,
            1000,
        )
        item["source_trade_ids"] = ["1", "2"]

        self.repository.upsert_many([item])
        saved = self.repository.list_transactions()[0]

        self.assertEqual(saved["source_trade_ids"], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
