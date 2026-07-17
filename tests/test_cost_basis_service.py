import unittest

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


if __name__ == "__main__":
    unittest.main()
