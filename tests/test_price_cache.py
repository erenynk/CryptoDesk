import math
import unittest
from threading import Thread
from unittest.mock import patch

from services.price_cache import PriceCache


class PriceCacheTestCase(unittest.TestCase):
    def test_new_cache_is_empty(self):
        cache = PriceCache()

        self.assertFalse(cache.has())
        self.assertEqual(cache.get_all(), {})
        self.assertEqual(cache.last_update, 0)
        self.assertTrue(math.isinf(cache.age))

    @patch(
        "services.price_cache.time",
        return_value=1000.0,
    )
    def test_update_stores_prices_and_timestamp(
        self,
        mocked_time,
    ):
        cache = PriceCache()

        cache.update(
            {
                "BTC": 65000.0,
                "ETH": 3500.0,
            }
        )

        self.assertTrue(cache.has())
        self.assertEqual(
            cache.get_all(),
            {
                "BTC": 65000.0,
                "ETH": 3500.0,
            },
        )
        self.assertEqual(cache.last_update, 1000.0)
        mocked_time.assert_called_once_with()

    def test_update_copies_input_dictionary(self):
        cache = PriceCache()
        source = {
            "BTC": 65000.0,
        }

        cache.update(source)
        source["BTC"] = 1.0
        source["ETH"] = 3500.0

        self.assertEqual(
            cache.get_all(),
            {
                "BTC": 65000.0,
            },
        )

    def test_update_replaces_previous_prices(self):
        cache = PriceCache()

        cache.update(
            {
                "BTC": 65000.0,
                "ETH": 3500.0,
            }
        )
        cache.update(
            {
                "SOL": 150.0,
            }
        )

        self.assertEqual(
            cache.get_all(),
            {
                "SOL": 150.0,
            },
        )
        self.assertEqual(cache.get("BTC"), 0.0)

    def test_get_is_case_insensitive(self):
        cache = PriceCache()
        cache.update(
            {
                "BTC": 65000.0,
            }
        )

        self.assertEqual(cache.get("btc"), 65000.0)
        self.assertEqual(cache.get("BtC"), 65000.0)
        self.assertEqual(cache.get("BTC"), 65000.0)

    def test_get_returns_requested_default(self):
        cache = PriceCache()

        self.assertEqual(cache.get("BTC"), 0.0)
        self.assertIsNone(
            cache.get(
                "BTC",
                default=None,
            )
        )
        self.assertEqual(
            cache.get(
                "BTC",
                default=-1.0,
            ),
            -1.0,
        )

    def test_get_all_returns_independent_copy(self):
        cache = PriceCache()
        cache.update(
            {
                "BTC": 65000.0,
            }
        )

        result = cache.get_all()
        result["BTC"] = 1.0
        result["ETH"] = 3500.0

        self.assertEqual(
            cache.get_all(),
            {
                "BTC": 65000.0,
            },
        )

    def test_clear_removes_prices_and_resets_timestamp(self):
        cache = PriceCache()
        cache.update(
            {
                "BTC": 65000.0,
            }
        )

        cache.clear()

        self.assertFalse(cache.has())
        self.assertEqual(cache.get_all(), {})
        self.assertEqual(cache.last_update, 0)
        self.assertTrue(math.isinf(cache.age))

    @patch(
        "services.price_cache.time",
        side_effect=[
            1000.0,
            1007.5,
        ],
    )
    def test_age_uses_elapsed_seconds(
        self,
        mocked_time,
    ):
        cache = PriceCache()

        cache.update(
            {
                "BTC": 65000.0,
            }
        )

        self.assertEqual(cache.age, 7.5)
        self.assertEqual(mocked_time.call_count, 2)

    def test_empty_update_marks_cache_as_empty_but_updated(self):
        cache = PriceCache()

        with patch(
            "services.price_cache.time",
            return_value=2000.0,
        ):
            cache.update({})

        self.assertFalse(cache.has())
        self.assertEqual(cache.get_all(), {})
        self.assertEqual(cache.last_update, 2000.0)

    def test_concurrent_reads_and_writes_do_not_raise(self):
        cache = PriceCache()
        errors = []

        def writer(start):
            try:
                for index in range(200):
                    cache.update(
                        {
                            "BTC": float(
                                start + index
                            ),
                            "ETH": float(index),
                        }
                    )
            except Exception as error:
                errors.append(error)

        def reader():
            try:
                for _ in range(400):
                    cache.get("btc")
                    cache.get_all()
                    cache.has()
                    cache.last_update
                    cache.age
            except Exception as error:
                errors.append(error)

        threads = [
            Thread(target=writer, args=(0,)),
            Thread(target=writer, args=(1000,)),
            Thread(target=reader),
            Thread(target=reader),
        ]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=5)

        self.assertFalse(errors)
        self.assertTrue(
            all(
                not thread.is_alive()
                for thread in threads
            )
        )
        self.assertTrue(cache.has())
        self.assertIn("BTC", cache.get_all())
        self.assertIn("ETH", cache.get_all())


if __name__ == "__main__":
    unittest.main()
