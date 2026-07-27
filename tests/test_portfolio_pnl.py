import unittest

from ui.portfolio import PortfolioPage


class LabelStub:
    def __init__(self):
        self._text = ""
        self._style_sheet = ""

    def setText(self, text):
        self._text = text

    def text(self):
        return self._text

    def setStyleSheet(self, style_sheet):
        self._style_sheet = style_sheet

    def styleSheet(self):
        return self._style_sheet


class PortfolioPnlHarness:
    _set_portfolio_total_pnl_placeholder = (
        PortfolioPage._set_portfolio_total_pnl_placeholder
    )
    _update_portfolio_total_pnl = (
        PortfolioPage._update_portfolio_total_pnl
    )
    _set_trading_total_pnl_placeholder = (
        PortfolioPage._set_trading_total_pnl_placeholder
    )
    _update_trading_total_pnl = (
        PortfolioPage._update_trading_total_pnl
    )

    def __init__(self):
        self.raw_assets_data = []

        self.portfolio_total_pnl_percent_value = LabelStub()
        self.portfolio_total_pnl_usdt_value = LabelStub()

        self.trading_total_pnl_percent_value = LabelStub()
        self.trading_total_pnl_usdt_value = LabelStub()


class PortfolioPnlTestCase(unittest.TestCase):
    def setUp(self):
        self.page = PortfolioPnlHarness()

    def test_portfolio_total_pnl_aggregates_open_positions(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "total": 2.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 200.0,
                "pnl_usdt": -20.0,
            },
            {
                "coin": "USDT",
                "total": 500.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 500.0,
                "pnl_usdt": 100.0,
            },
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "-3.33%",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "-10.00 USDT",
        )

    def test_portfolio_total_pnl_formats_positive_result(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 1000.0,
                "pnl_usdt": 1234.5,
            }
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "+123.45%",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "+1,234.50 USDT",
        )

    def test_portfolio_total_pnl_ignores_zero_balance_assets(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "total": 0.0,
                "cost_basis_available": False,
                "cost_basis_usdt": None,
                "pnl_usdt": None,
            },
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "+10.00%",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "+10.00 USDT",
        )

    def test_portfolio_total_pnl_ignores_unknown_cost_assets(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "total": 1.0,
                "cost_basis_available": True,
                "cost_basis_usdt": 100.0,
                "pnl_usdt": 10.0,
            },
            {
                "coin": "ETH",
                "total": 1.0,
                "cost_basis_available": False,
                "cost_basis_usdt": None,
                "pnl_usdt": None,
            },
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "+10.00%",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "+10.00 USDT",
        )

    def test_portfolio_total_pnl_is_placeholder_when_all_costs_are_unknown(self):
        self.page.raw_assets_data = [
            {
                "coin": "ETH",
                "total": 1.0,
                "cost_basis_available": False,
                "cost_basis_usdt": None,
                "pnl_usdt": None,
            }
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "—",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "—",
        )

    def test_portfolio_total_pnl_is_placeholder_for_usdt_only(self):
        self.page.raw_assets_data = [
            {
                "coin": "USDT",
                "total": 1000.0,
            }
        ]

        self.page._update_portfolio_total_pnl()

        self.assertEqual(
            self.page.portfolio_total_pnl_percent_value.text(),
            "—",
        )
        self.assertEqual(
            self.page.portfolio_total_pnl_usdt_value.text(),
            "—",
        )

    def test_trading_total_pnl_aggregates_only_trading_positions(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "trading_total": 0.4,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 40.0,
                "trading_pnl_usdt": 4.0,
            },
            {
                "coin": "ETH",
                "trading_total": 1.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 100.0,
                "trading_pnl_usdt": -5.0,
            },
            {
                "coin": "LTC",
                "trading_total": 0.0,
                "trading_cost_basis_available": False,
                "trading_cost_basis_usdt": None,
                "trading_pnl_usdt": None,
            },
            {
                "coin": "USDT",
                "trading_total": 500.0,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 500.0,
                "trading_pnl_usdt": 50.0,
            },
        ]

        self.page._update_trading_total_pnl()

        self.assertEqual(
            self.page.trading_total_pnl_percent_value.text(),
            "-0.71%",
        )
        self.assertEqual(
            self.page.trading_total_pnl_usdt_value.text(),
            "-1.00 USDT",
        )

    def test_trading_total_pnl_ignores_unknown_cost_assets(self):
        self.page.raw_assets_data = [
            {
                "coin": "BTC",
                "trading_total": 0.4,
                "trading_cost_basis_available": True,
                "trading_cost_basis_usdt": 40.0,
                "trading_pnl_usdt": 4.0,
            },
            {
                "coin": "ETH",
                "trading_total": 1.0,
                "trading_cost_basis_available": False,
                "trading_cost_basis_usdt": None,
                "trading_pnl_usdt": None,
            },
        ]

        self.page._update_trading_total_pnl()

        self.assertEqual(
            self.page.trading_total_pnl_percent_value.text(),
            "+10.00%",
        )
        self.assertEqual(
            self.page.trading_total_pnl_usdt_value.text(),
            "+4.00 USDT",
        )

    def test_trading_total_pnl_is_placeholder_when_all_costs_are_unknown(self):
        self.page.raw_assets_data = [
            {
                "coin": "ETH",
                "trading_total": 1.0,
                "trading_cost_basis_available": False,
                "trading_cost_basis_usdt": None,
                "trading_pnl_usdt": None,
            }
        ]

        self.page._update_trading_total_pnl()

        self.assertEqual(
            self.page.trading_total_pnl_percent_value.text(),
            "—",
        )
        self.assertEqual(
            self.page.trading_total_pnl_usdt_value.text(),
            "—",
        )

    def test_daily_pnl_usdt_reads_analytics_value(self):
        portfolio = {
            "analytics": {
                "period_changes": {
                    "1d": {
                        "total": {
                            "amount_usdt": 12.345,
                        }
                    }
                }
            }
        }

        result = PortfolioPage._get_daily_pnl_usdt(
            portfolio
        )

        self.assertEqual(result, 12.345)

    def test_daily_pnl_usdt_uses_fallback_field(self):
        portfolio = {
            "daily_pnl_usdt": -7.25,
        }

        result = PortfolioPage._get_daily_pnl_usdt(
            portfolio
        )

        self.assertEqual(result, -7.25)

    def test_daily_pnl_usdt_returns_none_without_valid_value(self):
        portfolio = {
            "analytics": {
                "period_changes": {
                    "1d": {
                        "total": {
                            "amount_usdt": "invalid",
                        }
                    }
                }
            }
        }

        result = PortfolioPage._get_daily_pnl_usdt(
            portfolio
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
