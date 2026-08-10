import unittest

from tools.apply_trade_history_ui import patch_main_window


class PatchTestCase(unittest.TestCase):
    def test_patch_is_idempotent(self):
        original = (
            "from ui.settings import SettingsPage\n"
            '            ("Portfolio", "portfolio", "#18C98B"),\n'
            '        elif name == "watchlist":\n'
            "        self.watchlist_page = "
            "WatchlistPage(self.data_manager)\n"
            "        self.pages.addWidget(self.watchlist_page)\n"
            "        if portfolio_page is not None:\n"
            "            portfolio_page.shutdown()\n"
        )

        once = patch_main_window(original)
        twice = patch_main_window(once)

        self.assertEqual(once, twice)
        self.assertIn("TradeHistoryPage", once)
        self.assertIn("İşlem Geçmişi", once)
        self.assertIn('elif name == "history":', once)


if __name__ == "__main__":
    unittest.main()
