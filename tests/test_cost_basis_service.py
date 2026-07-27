import unittest
from unittest.mock import patch

from services.cost_basis_service import CostBasisService


class CostBasisServiceTestCase(unittest.TestCase):
    @staticmethod
    def make_fill(
        *,
        coin="BTC",
        side,
        size,
        price,
        timestamp,
        trade_id,
        order_id=None,
        fee=0.0,
        fee_currency="USDT",
    ):
        return {
            "instId": f"{coin}-USDT",
            "side": side,
            "fillSz": str(size),
            "fillPx": str(price),
            "ts": str(timestamp),
            "tradeId": str(trade_id),
            "ordId": str(
                order_id
                if order_id is not None
                else trade_id
            ),
            "fee": str(fee),
            "feeCcy": fee_currency,
        }

    @staticmethod
    def make_asset(
        *,
        coin="BTC",
        price,
        total,
        trading_total=None,
        funding_total=None,
    ):
        if trading_total is None:
            trading_total = total

        if funding_total is None:
            funding_total = total - trading_total

        return {
            "coin": coin,
            "price": float(price),
            "total": float(total),
            "trading_total": float(trading_total),
            "funding_total": float(funding_total),
        }

    @staticmethod
    def make_transfer(
        *,
        coin="BTC",
        quantity,
        from_account,
        to_account,
        timestamp,
        bill_id,
    ):
        return {
            "ccy": coin,
            "sz": str(quantity),
            "from": str(from_account),
            "to": str(to_account),
            "ts": str(timestamp),
            "billId": str(bill_id),
        }

    def calculate_one(
        self,
        *,
        fills,
        asset,
        transfers=None,
    ):
        result = CostBasisService.calculate(
            fills=fills,
            current_assets=[asset],
            transfers=transfers or [],
        )

        return result[asset["coin"]]

    def assert_result(
        self,
        result,
        *,
        average_price,
        cost_basis_usdt,
        pnl_usdt,
        pnl_percent,
        places=8,
    ):
        self.assertIsNotNone(result)
        self.assertTrue(result["cost_basis_available"])
        self.assertAlmostEqual(
            result["average_price"],
            average_price,
            places=places,
        )
        self.assertAlmostEqual(
            result["cost_basis_usdt"],
            cost_basis_usdt,
            places=places,
        )
        self.assertAlmostEqual(
            result["pnl_usdt"],
            pnl_usdt,
            places=places,
        )
        self.assertAlmostEqual(
            result["pnl_percent"],
            pnl_percent,
            places=places,
        )

    def test_single_buy_calculates_open_position_pnl(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            )
        ]
        asset = self.make_asset(
            price=110,
            total=1,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=100,
            pnl_usdt=10,
            pnl_percent=10,
        )
        self.assert_result(
            result["trading"],
            average_price=100,
            cost_basis_usdt=100,
            pnl_usdt=10,
            pnl_percent=10,
        )
        self.assertIsNone(result["funding"])

    def test_multiple_buys_use_weighted_average(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="buy",
                size=1,
                price=200,
                timestamp=2,
                trade_id=2,
            ),
        ]
        asset = self.make_asset(
            price=180,
            total=2,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=150,
            cost_basis_usdt=300,
            pnl_usdt=60,
            pnl_percent=20,
        )

    def test_partial_sell_keeps_remaining_average_cost(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="sell",
                size=0.4,
                price=120,
                timestamp=2,
                trade_id=2,
            ),
        ]
        asset = self.make_asset(
            price=110,
            total=0.6,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=60,
            pnl_usdt=6,
            pnl_percent=10,
        )

    def test_full_close_then_new_buy_starts_new_cost_cycle(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="sell",
                size=1,
                price=120,
                timestamp=2,
                trade_id=2,
            ),
            self.make_fill(
                side="buy",
                size=0.5,
                price=150,
                timestamp=3,
                trade_id=3,
            ),
        ]
        asset = self.make_asset(
            price=165,
            total=0.5,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=150,
            cost_basis_usdt=75,
            pnl_usdt=7.5,
            pnl_percent=10,
        )

    def test_position_below_one_cent_is_closed_as_dust(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="sell",
                size=0.99995,
                price=100,
                timestamp=2,
                trade_id=2,
            ),
        ]
        asset = self.make_asset(
            price=100,
            total=0.00005,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assertIsNone(result["total"])
        self.assertIsNone(result["trading"])
        self.assertIsNone(result["funding"])

    def test_position_equal_to_one_cent_remains_open(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="sell",
                size=0.9999,
                price=100,
                timestamp=2,
                trade_id=2,
            ),
        ]
        asset = self.make_asset(
            price=100,
            total=0.0001,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=0.01,
            pnl_usdt=0,
            pnl_percent=0,
        )

    def test_trading_to_funding_transfer_carries_cost(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            )
        ]
        transfers = [
            self.make_transfer(
                quantity=0.6,
                from_account=CostBasisService.TRADING_ACCOUNT,
                to_account=CostBasisService.FUNDING_ACCOUNT,
                timestamp=2,
                bill_id=1,
            )
        ]
        asset = self.make_asset(
            price=110,
            total=1,
            trading_total=0.4,
            funding_total=0.6,
        )

        result = self.calculate_one(
            fills=fills,
            transfers=transfers,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=100,
            pnl_usdt=10,
            pnl_percent=10,
        )
        self.assert_result(
            result["trading"],
            average_price=100,
            cost_basis_usdt=40,
            pnl_usdt=4,
            pnl_percent=10,
        )
        self.assert_result(
            result["funding"],
            average_price=100,
            cost_basis_usdt=60,
            pnl_usdt=6,
            pnl_percent=10,
        )

    def test_round_trip_transfer_preserves_account_costs(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            )
        ]
        transfers = [
            self.make_transfer(
                quantity=1,
                from_account=CostBasisService.TRADING_ACCOUNT,
                to_account=CostBasisService.FUNDING_ACCOUNT,
                timestamp=2,
                bill_id=1,
            ),
            self.make_transfer(
                quantity=0.4,
                from_account=CostBasisService.FUNDING_ACCOUNT,
                to_account=CostBasisService.TRADING_ACCOUNT,
                timestamp=3,
                bill_id=2,
            ),
        ]
        asset = self.make_asset(
            price=90,
            total=1,
            trading_total=0.4,
            funding_total=0.6,
        )

        result = self.calculate_one(
            fills=fills,
            transfers=transfers,
            asset=asset,
        )

        self.assert_result(
            result["trading"],
            average_price=100,
            cost_basis_usdt=40,
            pnl_usdt=-4,
            pnl_percent=-10,
        )
        self.assert_result(
            result["funding"],
            average_price=100,
            cost_basis_usdt=60,
            pnl_usdt=-6,
            pnl_percent=-10,
        )

    def test_usdt_fee_does_not_increase_average_price(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
                fee=-1,
                fee_currency="USDT",
            )
        ]
        asset = self.make_asset(
            price=110,
            total=1,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=100,
            pnl_usdt=10,
            pnl_percent=10,
        )

    def test_base_asset_fee_reduces_quantity_not_entry_price(self):
        fills = [
            self.make_fill(
                coin="ETH",
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
                fee=-0.001,
                fee_currency="ETH",
            )
        ]
        asset = self.make_asset(
            coin="ETH",
            price=110,
            total=0.999,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assert_result(
            result["total"],
            average_price=100,
            cost_basis_usdt=99.9,
            pnl_usdt=9.99,
            pnl_percent=10,
        )

    def test_partial_fills_in_same_order_use_weighted_price(self):
        fills = [
            self.make_fill(
                coin="ETH",
                side="buy",
                size=0.4,
                price=100,
                timestamp=1,
                trade_id=1,
                order_id=10,
            ),
            self.make_fill(
                coin="ETH",
                side="buy",
                size=0.6,
                price=110,
                timestamp=1,
                trade_id=2,
                order_id=10,
            ),
        ]
        asset = self.make_asset(
            coin="ETH",
            price=120,
            total=1,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        expected_average = 106
        expected_cost = 106
        expected_pnl = 14
        expected_percent = expected_pnl / expected_cost * 100

        self.assert_result(
            result["total"],
            average_price=expected_average,
            cost_basis_usdt=expected_cost,
            pnl_usdt=expected_pnl,
            pnl_percent=expected_percent,
        )

    def test_unknown_starting_cost_does_not_guess_without_history(self):
        asset = self.make_asset(
            price=110,
            total=1,
        )

        result = self.calculate_one(
            fills=[],
            asset=asset,
        )

        self.assertIsNone(result["total"])
        self.assertIsNone(result["trading"])
        self.assertIsNone(result["funding"])

    def test_buy_after_partial_sell_uses_remaining_weighted_cost(self):
        fills = [
            self.make_fill(
                coin="DOGE",
                side="buy",
                size=100,
                price=0.10,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                coin="DOGE",
                side="sell",
                size=50,
                price=0.12,
                timestamp=2,
                trade_id=2,
            ),
            self.make_fill(
                coin="DOGE",
                side="buy",
                size=100,
                price=0.20,
                timestamp=3,
                trade_id=3,
            ),
        ]
        asset = self.make_asset(
            coin="DOGE",
            price=0.18,
            total=150,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        expected_average = 25 / 150
        expected_cost = 25
        expected_pnl = 2
        expected_percent = 8

        self.assert_result(
            result["total"],
            average_price=expected_average,
            cost_basis_usdt=expected_cost,
            pnl_usdt=expected_pnl,
            pnl_percent=expected_percent,
        )
        self.assert_result(
            result["trading"],
            average_price=expected_average,
            cost_basis_usdt=expected_cost,
            pnl_usdt=expected_pnl,
            pnl_percent=expected_percent,
        )

    def test_incomplete_history_does_not_apply_latest_buy_to_old_balance(self):
        fills = [
            self.make_fill(
                coin="DOGE",
                side="buy",
                size=100,
                price=0.20,
                timestamp=3,
                trade_id=3,
            )
        ]
        asset = self.make_asset(
            coin="DOGE",
            price=0.18,
            total=1100,
        )

        result = self.calculate_one(
            fills=fills,
            asset=asset,
        )

        self.assertIsNone(result["total"])
        self.assertIsNone(result["trading"])
        self.assertIsNone(result["funding"])

    def test_attach_to_assets_writes_total_and_account_fields(self):
        assets = [
            self.make_asset(
                price=110,
                total=1,
                trading_total=0.4,
                funding_total=0.6,
            )
        ]
        cost_basis = {
            "BTC": {
                "total": {
                    "average_price": 100.0,
                    "cost_basis_usdt": 100.0,
                    "pnl_usdt": 10.0,
                    "pnl_percent": 10.0,
                    "cost_basis_available": True,
                },
                "trading": {
                    "average_price": 100.0,
                    "cost_basis_usdt": 40.0,
                    "pnl_usdt": 4.0,
                    "pnl_percent": 10.0,
                    "cost_basis_available": True,
                },
                "funding": {
                    "average_price": 100.0,
                    "cost_basis_usdt": 60.0,
                    "pnl_usdt": 6.0,
                    "pnl_percent": 10.0,
                    "cost_basis_available": True,
                },
            }
        }

        CostBasisService.attach_to_assets(
            assets,
            cost_basis,
        )

        asset = assets[0]

        self.assertEqual(asset["average_price"], 100.0)
        self.assertEqual(asset["pnl_usdt"], 10.0)
        self.assertTrue(asset["cost_basis_available"])

        self.assertEqual(
            asset["trading_cost_basis_usdt"],
            40.0,
        )
        self.assertEqual(
            asset["trading_pnl_usdt"],
            4.0,
        )
        self.assertTrue(
            asset["trading_cost_basis_available"]
        )

        self.assertEqual(
            asset["funding_cost_basis_usdt"],
            60.0,
        )
        self.assertEqual(
            asset["funding_pnl_usdt"],
            6.0,
        )
        self.assertTrue(
            asset["funding_cost_basis_available"]
        )


    def test_safe_float_and_symbol_helpers_handle_invalid_values(self):
        self.assertEqual(
            CostBasisService._safe_float(float("nan")),
            0.0,
        )
        self.assertEqual(
            CostBasisService._safe_float(object()),
            0.0,
        )
        self.assertIsNone(
            CostBasisService._extract_coin("BTC-USDC")
        )
        self.assertIsNone(
            CostBasisService._extract_coin("-USDT")
        )
        self.assertEqual(
            CostBasisService._extract_coin(" eth-usdt "),
            "ETH",
        )

    def test_fill_and_transfer_helpers_reject_invalid_values(self):
        self.assertEqual(
            CostBasisService._buy_values(
                "BTC",
                {
                    "fillSz": "0",
                    "fillPx": "100",
                },
            ),
            (0.0, 0.0),
        )
        self.assertEqual(
            CostBasisService._buy_values(
                "BTC",
                {
                    "fillSz": "1",
                    "fillPx": "0",
                },
            ),
            (0.0, 0.0),
        )
        self.assertEqual(
            CostBasisService._sell_quantity(
                "BTC",
                {
                    "fillSz": "0",
                },
            ),
            0.0,
        )
        self.assertEqual(
            CostBasisService._sell_quantity(
                "BTC",
                {
                    "fillSz": "1",
                    "fee": "-0.01",
                    "feeCcy": "BTC",
                },
            ),
            1.01,
        )
        self.assertEqual(
            CostBasisService._transfer_quantity({}),
            0.0,
        )
        self.assertEqual(
            CostBasisService._transfer_quantity(
                {
                    "sz": "0",
                    "amt": "-2",
                }
            ),
            2.0,
        )

    def test_ledger_helpers_cover_known_and_unknown_cost_paths(self):
        known = CostBasisService._new_ledger(
            quantity=1,
            cost=10,
            cost_known=True,
        )
        CostBasisService._add_known_cost(
            known,
            0,
            5,
        )
        self.assertEqual(
            known,
            {
                "quantity": 1,
                "cost": 10,
                "cost_known": True,
            },
        )

        CostBasisService._add_transferred(
            known,
            1,
            20,
            True,
        )
        self.assertEqual(known["quantity"], 2)
        self.assertEqual(known["cost"], 30)
        self.assertTrue(known["cost_known"])

        unknown = CostBasisService._new_ledger(
            quantity=1,
            cost=0,
            cost_known=False,
        )
        CostBasisService._add_transferred(
            unknown,
            1,
            20,
            True,
        )
        self.assertEqual(unknown["quantity"], 2)
        self.assertEqual(unknown["cost"], 0)
        self.assertFalse(unknown["cost_known"])

        empty = CostBasisService._new_ledger()
        CostBasisService._add_transferred(
            empty,
            1,
            0,
            False,
        )
        self.assertEqual(empty["quantity"], 1)
        self.assertEqual(empty["cost"], 0)
        self.assertFalse(empty["cost_known"])

        unchanged = dict(empty)
        CostBasisService._add_transferred(
            empty,
            0,
            10,
            True,
        )
        self.assertEqual(empty, unchanged)

        self.assertEqual(
            CostBasisService._remove(
                CostBasisService._new_ledger(),
                1,
            ),
            (0.0, 0.0, True),
        )

    def test_reconstruct_open_average_filters_invalid_fills(self):
        fills = [
            self.make_fill(
                coin="ETH",
                side="buy",
                size=1,
                price=50,
                timestamp=5,
                trade_id=5,
            ),
            {
                "instId": "BTC-USDT",
                "side": "invalid",
                "fillSz": "1",
                "fillPx": "100",
                "ts": "4",
                "tradeId": "4",
            },
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "0",
                "fillPx": "100",
                "ts": "3",
                "tradeId": "3",
            },
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "1",
                "fillPx": "0",
                "ts": "2",
                "tradeId": "2",
            },
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
        ]

        self.assertEqual(
            CostBasisService._reconstruct_open_average(
                fills,
                "BTC",
                1,
            ),
            100,
        )
        self.assertIsNone(
            CostBasisService._reconstruct_open_average(
                fills,
                "BTC",
                0,
            )
        )

    def test_reconstruct_open_average_handles_sell_inventory(self):
        fills = [
            self.make_fill(
                side="buy",
                size=2,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            self.make_fill(
                side="sell",
                size=1,
                price=120,
                timestamp=2,
                trade_id=2,
            ),
        ]

        self.assertEqual(
            CostBasisService._reconstruct_open_average(
                fills,
                "BTC",
                1,
            ),
            100,
        )

    def test_reconstruct_open_average_defensive_zero_use_path(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            )
        ]

        with patch(
            "builtins.min",
            return_value=0,
        ):
            result = (
                CostBasisService
                ._reconstruct_open_average(
                    fills,
                    "BTC",
                    1,
                )
            )

        self.assertIsNone(result)

    def test_latest_buy_average_uses_latest_order_partial_fills(self):
        fills = [
            self.make_fill(
                coin="ETH",
                side="buy",
                size=10,
                price=1,
                timestamp=20,
                trade_id=20,
            ),
            self.make_fill(
                side="sell",
                size=1,
                price=90,
                timestamp=30,
                trade_id=30,
            ),
            {
                "instId": "BTC-USDT",
                "side": "buy",
                "fillSz": "0",
                "fillPx": "100",
                "ts": "40",
                "tradeId": "40",
                "ordId": "40",
            },
            self.make_fill(
                side="buy",
                size=1,
                price=80,
                timestamp=1,
                trade_id=1,
                order_id=1,
            ),
            self.make_fill(
                side="buy",
                size=0.4,
                price=100,
                timestamp=2,
                trade_id=2,
                order_id=10,
            ),
            self.make_fill(
                side="buy",
                size=0.6,
                price=110,
                timestamp=3,
                trade_id=3,
                order_id=10,
            ),
        ]

        self.assertEqual(
            CostBasisService._latest_buy_average(
                fills,
                "BTC",
            ),
            106,
        )

    def test_latest_buy_average_uses_trade_id_and_handles_no_buys(self):
        fill = self.make_fill(
            side="buy",
            size=2,
            price=125,
            timestamp=1,
            trade_id=7,
        )
        fill["ordId"] = ""

        self.assertEqual(
            CostBasisService._latest_buy_average(
                [fill],
                "BTC",
            ),
            125,
        )
        self.assertIsNone(
            CostBasisService._latest_buy_average(
                [
                    self.make_fill(
                        side="sell",
                        size=1,
                        price=100,
                        timestamp=1,
                        trade_id=1,
                    )
                ],
                "BTC",
            )
        )

    def test_latest_buy_average_rejects_degenerate_total(self):
        fills = [
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            )
        ]

        original_tolerance = (
            CostBasisService.QUANTITY_TOLERANCE
        )
        try:
            CostBasisService.QUANTITY_TOLERANCE = 2
            self.assertIsNone(
                CostBasisService._latest_buy_average(
                    fills,
                    "BTC",
                )
            )
        finally:
            CostBasisService.QUANTITY_TOLERANCE = (
                original_tolerance
            )

    def test_calculate_ignores_unrelated_assets_fills_and_transfers(self):
        assets = [
            self.make_asset(
                coin="USDT",
                price=1,
                total=100,
            ),
            {
                "coin": "",
                "price": 1,
                "total": 1,
                "trading_total": 1,
                "funding_total": 0,
            },
            self.make_asset(
                coin="BTC",
                price=110,
                total=1,
            ),
        ]
        fills = [
            self.make_fill(
                coin="ETH",
                side="buy",
                size=1,
                price=100,
                timestamp=1,
                trade_id=1,
            ),
            {
                "instId": "BTC-USDT",
                "side": "invalid",
                "fillSz": "1",
                "fillPx": "100",
                "ts": "2",
                "tradeId": "2",
            },
            self.make_fill(
                side="buy",
                size=1,
                price=100,
                timestamp=3,
                trade_id=3,
            ),
        ]
        transfers = [
            self.make_transfer(
                coin="ETH",
                quantity=1,
                from_account=CostBasisService.TRADING_ACCOUNT,
                to_account=CostBasisService.FUNDING_ACCOUNT,
                timestamp=4,
                bill_id=1,
            ),
            self.make_transfer(
                quantity=1,
                from_account="1",
                to_account="2",
                timestamp=5,
                bill_id=2,
            ),
            {
                "ccy": "BTC",
                "sz": "0",
                "from": CostBasisService.TRADING_ACCOUNT,
                "to": CostBasisService.FUNDING_ACCOUNT,
                "ts": "6",
                "billId": "3",
            },
        ]

        result = CostBasisService.calculate(
            fills=fills,
            current_assets=assets,
            transfers=transfers,
        )

        self.assertEqual(set(result), {"BTC"})
        self.assert_result(
            result["BTC"]["total"],
            average_price=100,
            cost_basis_usdt=100,
            pnl_usdt=10,
            pnl_percent=10,
        )

    def test_attach_to_assets_clears_missing_and_invalid_results(self):
        assets = [
            self.make_asset(
                coin="BTC",
                price=100,
                total=1,
            ),
            self.make_asset(
                coin="ETH",
                price=100,
                total=1,
            ),
        ]

        CostBasisService.attach_to_assets(
            assets,
            {
                "BTC": "invalid",
            },
        )

        for asset in assets:
            for key in (
                "average_price",
                "cost_basis_usdt",
                "pnl_usdt",
                "pnl_percent",
                "funding_average_price",
                "funding_cost_basis_usdt",
                "funding_pnl_usdt",
                "funding_pnl_percent",
                "trading_average_price",
                "trading_cost_basis_usdt",
                "trading_pnl_usdt",
                "trading_pnl_percent",
            ):
                self.assertIsNone(asset[key])

            self.assertFalse(
                asset["cost_basis_available"]
            )
            self.assertFalse(
                asset[
                    "funding_cost_basis_available"
                ]
            )
            self.assertFalse(
                asset[
                    "trading_cost_basis_available"
                ]
            )


if __name__ == "__main__":
    unittest.main()
