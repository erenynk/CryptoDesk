import unittest

from services.trade_history_service import TradeHistoryService


class TradeHistoryServiceTestCase(unittest.TestCase):
    def test_buy_pnl_is_empty(self):
        transactions = TradeHistoryService.build_transactions(
            fills=[
                {
                    "instId": "BTC-USDT",
                    "side": "buy",
                    "fillSz": "1",
                    "fillPx": "100",
                    "tradeId": "t1",
                    "ordId": "o1",
                    "ts": "1000",
                }
            ],
            current_assets=[
                {
                    "coin": "BTC",
                    "trading_total": 1.0,
                    "funding_total": 0.0,
                }
            ],
        )

        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["side"], "buy")
        self.assertIsNone(transactions[0]["pnl_usdt"])
        self.assertIsNone(transactions[0]["pnl_percent"])

    def test_sell_uses_weighted_trading_average(self):
        fills = [
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "1",
                "fillPx": "100",
                "tradeId": "t1",
                "ordId": "o1",
                "ts": "1000",
            },
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "1",
                "fillPx": "200",
                "tradeId": "t2",
                "ordId": "o2",
                "ts": "2000",
            },
            {
                "instId": "BTC-USDT",
                "side": "sell",
                "fillSz": "1",
                "fillPx": "250",
                "tradeId": "t3",
                "ordId": "o3",
                "ts": "3000",
            },
        ]

        transactions = TradeHistoryService.build_transactions(
            fills=fills,
            current_assets=[
                {
                    "coin": "BTC",
                    "trading_total": 1.0,
                    "funding_total": 0.0,
                }
            ],
        )
        sell = next(
            item
            for item in transactions
            if item["side"] == "sell"
        )

        self.assertAlmostEqual(sell["average_cost"], 150.0)
        self.assertAlmostEqual(sell["pnl_usdt"], 100.0)
        self.assertAlmostEqual(
            sell["pnl_percent"],
            66.6666666667,
            places=6,
        )

    def test_trading_to_funding_is_not_a_trade(self):
        fills = [
            {
                "instId": "ETH-USDT",
                "side": "buy",
                "fillSz": "2",
                "fillPx": "100",
                "tradeId": "t1",
                "ordId": "o1",
                "ts": "1000",
            },
            {
                "instId": "ETH-USDT",
                "side": "sell",
                "fillSz": "1",
                "fillPx": "150",
                "tradeId": "t2",
                "ordId": "o2",
                "ts": "3000",
            },
        ]
        transfers = [
            {
                "ccy": "ETH",
                "from": "18",
                "to": "6",
                "sz": "1",
                "billId": "b1",
                "ts": "2000",
            }
        ]

        transactions = TradeHistoryService.build_transactions(
            fills=fills,
            transfers=transfers,
            current_assets=[
                {
                    "coin": "ETH",
                    "trading_total": 0.0,
                    "funding_total": 1.0,
                }
            ],
        )

        self.assertEqual(len(transactions), 2)
        sell = next(
            item
            for item in transactions
            if item["side"] == "sell"
        )
        self.assertAlmostEqual(sell["pnl_usdt"], 50.0)
        self.assertAlmostEqual(sell["pnl_percent"], 50.0)

    def test_unknown_funding_cost_keeps_sell_pnl_empty(self):
        fills = [
            {
                "instId": "SOL-USDT",
                "side": "sell",
                "fillSz": "1",
                "fillPx": "150",
                "tradeId": "t1",
                "ordId": "o1",
                "ts": "2000",
            }
        ]
        transfers = [
            {
                "ccy": "SOL",
                "from": "6",
                "to": "18",
                "sz": "1",
                "billId": "b1",
                "ts": "1000",
            }
        ]

        transactions = TradeHistoryService.build_transactions(
            fills=fills,
            transfers=transfers,
            current_assets=[
                {
                    "coin": "SOL",
                    "trading_total": 0.0,
                    "funding_total": 0.0,
                }
            ],
        )

        self.assertEqual(len(transactions), 1)
        self.assertIsNone(transactions[0]["pnl_usdt"])
        self.assertIsNone(transactions[0]["pnl_percent"])

    def test_unknown_initial_trading_cost_keeps_pnl_empty(self):
        transactions = TradeHistoryService.build_transactions(
            fills=[
                {
                    "instId": "BTC-USDT",
                    "side": "sell",
                    "fillSz": "1",
                    "fillPx": "200",
                    "tradeId": "t1",
                    "ordId": "o1",
                    "ts": "1000",
                }
            ],
            current_assets=[
                {
                    "coin": "BTC",
                    "trading_total": 1.0,
                    "funding_total": 0.0,
                }
            ],
        )

        self.assertEqual(len(transactions), 1)
        self.assertIsNone(transactions[0]["pnl_usdt"])
        self.assertIsNone(transactions[0]["pnl_percent"])

    def test_partial_fills_of_same_order_are_aggregated(self):
        fills = [
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "0.4",
                "fillPx": "100",
                "tradeId": "t1",
                "ordId": "o1",
                "ts": "1000",
            },
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "0.6",
                "fillPx": "110",
                "tradeId": "t2",
                "ordId": "o1",
                "ts": "1100",
            },
        ]

        transactions = TradeHistoryService.build_transactions(
            fills=fills,
            current_assets=[
                {
                    "coin": "BTC",
                    "trading_total": 1.0,
                    "funding_total": 0.0,
                }
            ],
        )

        self.assertEqual(len(transactions), 1)
        self.assertAlmostEqual(
            transactions[0]["quantity"],
            1.0,
        )
        self.assertAlmostEqual(
            transactions[0]["total_usdt"],
            106.0,
        )
        self.assertAlmostEqual(
            transactions[0]["price"],
            106.0,
        )
        self.assertEqual(
            transactions[0]["source_trade_ids"],
            ["t1", "t2"],
        )

    def test_non_usdt_pairs_are_ignored(self):
        transactions = TradeHistoryService.build_transactions(
            fills=[
                {
                    "instId": "BTC-USDC",
                    "side": "buy",
                    "fillSz": "1",
                    "fillPx": "100",
                    "tradeId": "t1",
                    "ordId": "o1",
                    "ts": "1000",
                }
            ],
            current_assets=[],
        )

        self.assertEqual(transactions, [])


if __name__ == "__main__":
    unittest.main()
