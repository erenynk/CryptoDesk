import unittest
from unittest.mock import patch

from services import watchlist_service


class WatchlistServiceTestCase(unittest.TestCase):
    def test_normalize_symbol_handles_empty_values(self):
        self.assertEqual(
            watchlist_service.normalize_symbol(""),
            "",
        )
        self.assertEqual(
            watchlist_service.normalize_symbol(None),
            "",
        )
        self.assertEqual(
            watchlist_service.normalize_symbol("   "),
            "",
        )

    def test_normalize_symbol_uppercases_and_trims(self):
        self.assertEqual(
            watchlist_service.normalize_symbol(
                "  btc  "
            ),
            "BTC",
        )

    def test_normalize_symbol_converts_aliases(self):
        aliases = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "solana": "SOL",
            "litecoin": "LTC",
            "ripple": "XRP",
            "dogecoin": "DOGE",
        }

        for source, expected in aliases.items():
            with self.subTest(source=source):
                self.assertEqual(
                    watchlist_service.normalize_symbol(
                        source
                    ),
                    expected,
                )

    def test_normalize_symbol_removes_quote_pair_suffix(self):
        pairs = (
            "BTC-USDT",
            "BTC/USDT",
            "BTC_USDT",
        )

        for pair in pairs:
            with self.subTest(pair=pair):
                self.assertEqual(
                    watchlist_service.normalize_symbol(
                        pair
                    ),
                    "BTC",
                )

    def test_unknown_symbol_is_only_normalized_here(self):
        self.assertEqual(
            watchlist_service.normalize_symbol(
                " unknowncoin/usdt "
            ),
            "UNKNOWNCOIN",
        )

    @patch(
        "services.watchlist_service.add_watchlist_symbol"
    )
    def test_add_symbol_rejects_empty_symbol(
        self,
        add_watchlist_symbol,
    ):
        result = watchlist_service.add_symbol(
            "   ",
            100.0,
        )

        self.assertFalse(result)
        add_watchlist_symbol.assert_not_called()

    @patch(
        "services.watchlist_service.add_watchlist_symbol"
    )
    def test_add_symbol_normalizes_and_forwards_price(
        self,
        add_watchlist_symbol,
    ):
        add_watchlist_symbol.return_value = True

        result = watchlist_service.add_symbol(
            "ethereum/usdt",
            2500.0,
        )

        self.assertTrue(result)
        add_watchlist_symbol.assert_called_once_with(
            "ETH",
            2500.0,
        )

    @patch(
        "services.watchlist_service.add_watchlist_symbol"
    )
    def test_add_symbol_propagates_duplicate_rejection(
        self,
        add_watchlist_symbol,
    ):
        add_watchlist_symbol.return_value = False

        result = watchlist_service.add_symbol(
            "BTC",
            100.0,
        )

        self.assertFalse(result)
        add_watchlist_symbol.assert_called_once_with(
            "BTC",
            100.0,
        )

    @patch(
        "services.watchlist_service.remove_watchlist_symbol"
    )
    def test_remove_symbol_rejects_empty_symbol(
        self,
        remove_watchlist_symbol,
    ):
        result = watchlist_service.remove_symbol("")

        self.assertFalse(result)
        remove_watchlist_symbol.assert_not_called()

    @patch(
        "services.watchlist_service.remove_watchlist_symbol"
    )
    def test_remove_symbol_normalizes_before_delete(
        self,
        remove_watchlist_symbol,
    ):
        remove_watchlist_symbol.return_value = True

        result = watchlist_service.remove_symbol(
            "bitcoin-usdt"
        )

        self.assertTrue(result)
        remove_watchlist_symbol.assert_called_once_with(
            "BTC"
        )

    @patch(
        "services.watchlist_service.get_watchlist_items"
    )
    def test_get_items_delegates_to_database(
        self,
        get_watchlist_items,
    ):
        expected = [
            {
                "symbol": "BTC",
                "added_price": 100.0,
            }
        ]
        get_watchlist_items.return_value = expected

        self.assertIs(
            watchlist_service.get_items(),
            expected,
        )


if __name__ == "__main__":
    unittest.main()
