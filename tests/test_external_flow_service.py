import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from services.external_flow_service import (
    ExternalFlowService,
)
from services.performance_engine import CashFlow


class ExternalFlowServiceTestCase(unittest.TestCase):
    def setUp(self):
        self.okx = Mock()
        self.app_timezone = timezone(
            timedelta(hours=3)
        )
        self.service = ExternalFlowService(
            okx_service=self.okx,
            app_timezone=self.app_timezone,
        )
        self.period_start = datetime(
            2026,
            7,
            21,
            0,
            0,
            tzinfo=self.app_timezone,
        )
        self.period_end = datetime(
            2026,
            7,
            22,
            0,
            0,
            tzinfo=self.app_timezone,
        )

    @staticmethod
    def timestamp_ms(value: datetime) -> int:
        return int(value.timestamp() * 1000)

    def test_constructor_stores_dependencies_and_empty_cache(
        self,
    ):
        self.assertIs(self.service.okx, self.okx)
        self.assertEqual(
            self.service.app_timezone,
            self.app_timezone,
        )
        self.assertEqual(
            self.service._price_cache,
            {},
        )

    def test_safe_float_normalizes_invalid_values(self):
        cases = (
            ("12.5", 12.5),
            (10, 10.0),
            (None, 0.0),
            ("invalid", 0.0),
            (float("nan"), 0.0),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.service._safe_float(value),
                    expected,
                )

    def test_timestamp_to_datetime_converts_milliseconds(
        self,
    ):
        expected = datetime(
            2026,
            7,
            21,
            14,
            30,
            15,
            tzinfo=self.app_timezone,
        )

        result = self.service._timestamp_to_datetime(
            self.timestamp_ms(expected)
        )

        self.assertEqual(result, expected)

    def test_timestamp_to_datetime_rejects_invalid_values(
        self,
    ):
        invalid_values = (
            None,
            "",
            "invalid",
            "0",
            "-1000",
            "1e40",
        )

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertIsNone(
                    self.service._timestamp_to_datetime(
                        value
                    )
                )

    def test_price_at_returns_one_for_stablecoins(self):
        for coin in ("USDT", " usd "):
            with self.subTest(coin=coin):
                self.assertEqual(
                    self.service._price_at(
                        coin=coin,
                        timestamp_ms=123456,
                    ),
                    1.0,
                )

        self.okx.get_historical_spot_price.assert_not_called()

    def test_price_at_normalizes_coin_and_caches_same_minute(
        self,
    ):
        self.okx.get_historical_spot_price.return_value = (
            True,
            "2500.5",
        )
        first_timestamp = 1_000_000
        second_timestamp = 1_000_050

        first = self.service._price_at(
            coin=" eth ",
            timestamp_ms=first_timestamp,
        )
        second = self.service._price_at(
            coin="ETH",
            timestamp_ms=second_timestamp,
        )

        self.assertEqual(first, 2500.5)
        self.assertEqual(second, 2500.5)
        self.okx.get_historical_spot_price.assert_called_once_with(
            coin="ETH",
            timestamp_ms=first_timestamp,
        )
        self.assertEqual(
            self.service._price_cache,
            {
                (
                    "ETH",
                    first_timestamp // 60000,
                ): 2500.5,
            },
        )

    def test_price_at_uses_separate_cache_buckets(
        self,
    ):
        self.okx.get_historical_spot_price.side_effect = (
            (True, 100.0),
            (True, 110.0),
            (True, 200.0),
        )

        first_timestamp = 1_000_000
        next_minute = first_timestamp + 60_000

        first = self.service._price_at(
            coin="BTC",
            timestamp_ms=first_timestamp,
        )
        second = self.service._price_at(
            coin="BTC",
            timestamp_ms=next_minute,
        )
        third = self.service._price_at(
            coin="ETH",
            timestamp_ms=first_timestamp,
        )

        self.assertEqual(
            (first, second, third),
            (100.0, 110.0, 200.0),
        )
        self.assertEqual(
            self.okx.get_historical_spot_price.call_count,
            3,
        )

    def test_price_at_rejects_failed_or_invalid_prices(
        self,
    ):
        responses = (
            (False, "not found"),
            (True, 0),
            (True, -1),
            (True, "invalid"),
        )

        for index, response in enumerate(responses):
            with self.subTest(response=response):
                self.okx.reset_mock()
                self.service._price_cache.clear()
                self.okx.get_historical_spot_price.return_value = (
                    response
                )

                result = self.service._price_at(
                    coin="BTC",
                    timestamp_ms=(
                        1_000_000
                        + index * 60_000
                    ),
                )

                self.assertIsNone(result)
                self.assertEqual(
                    self.service._price_cache,
                    {},
                )

    def test_build_cash_flows_creates_positive_deposit(
        self,
    ):
        flow_time = (
            self.period_start
            + timedelta(hours=2)
        )
        item = {
            "state": "2",
            "ts": str(
                self.timestamp_ms(flow_time)
            ),
            "ccy": " usdt ",
            "amt": "-125.5",
        }

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=[item],
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(len(flows), 1)
        self.assertIsInstance(flows[0], CashFlow)
        self.assertEqual(
            flows[0].amount_usdt,
            125.5,
        )
        self.assertEqual(
            flows[0].timestamp,
            flow_time,
        )
        self.assertEqual(
            flows[0].description,
            "deposit:USDT:125.5",
        )

    def test_build_cash_flows_creates_negative_withdrawal(
        self,
    ):
        flow_time = (
            self.period_start
            + timedelta(hours=4)
        )
        timestamp = self.timestamp_ms(flow_time)
        self.okx.get_historical_spot_price.return_value = (
            True,
            3000.0,
        )
        item = {
            "state": "2",
            "ts": str(timestamp),
            "ccy": "eth",
            "amt": "2",
        }

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=[],
                withdrawals=[item],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(
            flows[0].amount_usdt,
            -6000.0,
        )
        self.assertEqual(
            flows[0].description,
            "withdrawal:ETH:2.0",
        )
        self.okx.get_historical_spot_price.assert_called_once_with(
            coin="ETH",
            timestamp_ms=timestamp,
        )

    def test_incomplete_records_are_ignored(self):
        flow_time = (
            self.period_start
            + timedelta(hours=1)
        )
        records = [
            {
                "state": "0",
                "ts": str(
                    self.timestamp_ms(flow_time)
                ),
                "ccy": "USDT",
                "amt": "10",
            },
            {
                "state": "1",
                "ts": str(
                    self.timestamp_ms(flow_time)
                ),
                "ccy": "USDT",
                "amt": "20",
            },
        ]

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=records,
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(flows, [])
        self.assertEqual(skipped, [])
        self.okx.get_historical_spot_price.assert_not_called()

    def test_invalid_timestamp_is_recorded_as_skipped(
        self,
    ):
        item = {
            "state": "2",
            "ts": "invalid",
            "ccy": "USDT",
            "amt": "10",
        }

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=[item],
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(flows, [])
        self.assertEqual(
            skipped,
            [
                {
                    "type": "deposit",
                    "reason": "invalid_timestamp",
                    "item": item,
                }
            ],
        )

    def test_out_of_period_records_are_ignored(self):
        before = (
            self.period_start
            - timedelta(seconds=1)
        )
        after = (
            self.period_end
            + timedelta(seconds=1)
        )
        records = [
            {
                "state": "2",
                "ts": str(
                    self.timestamp_ms(before)
                ),
                "ccy": "USDT",
                "amt": "10",
            },
            {
                "state": "2",
                "ts": str(
                    self.timestamp_ms(after)
                ),
                "ccy": "USDT",
                "amt": "20",
            },
        ]

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=records,
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(flows, [])
        self.assertEqual(skipped, [])

    def test_invalid_amount_or_coin_is_recorded(
        self,
    ):
        flow_time = (
            self.period_start
            + timedelta(hours=3)
        )
        timestamp = str(
            self.timestamp_ms(flow_time)
        )
        items = [
            {
                "state": "2",
                "ts": timestamp,
                "ccy": "",
                "amt": "10",
            },
            {
                "state": "2",
                "ts": timestamp,
                "ccy": "USDT",
                "amt": "0",
            },
            {
                "state": "2",
                "ts": timestamp,
                "ccy": "USDT",
                "amt": "invalid",
            },
        ]

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=items,
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(flows, [])
        self.assertEqual(len(skipped), 3)
        self.assertTrue(
            all(
                item["reason"]
                == "invalid_amount_or_coin"
                for item in skipped
            )
        )

    def test_missing_historical_price_is_recorded(
        self,
    ):
        flow_time = (
            self.period_start
            + timedelta(hours=5)
        )
        item = {
            "state": "2",
            "ts": str(
                self.timestamp_ms(flow_time)
            ),
            "ccy": "BTC",
            "amt": "0.5",
        }
        self.okx.get_historical_spot_price.return_value = (
            False,
            "price unavailable",
        )

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=[item],
                withdrawals=[],
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(flows, [])
        self.assertEqual(
            skipped,
            [
                {
                    "type": "deposit",
                    "reason": (
                        "historical_price_unavailable"
                    ),
                    "item": item,
                }
            ],
        )

    def test_flows_are_sorted_and_boundaries_are_inclusive(
        self,
    ):
        middle = (
            self.period_start
            + timedelta(hours=12)
        )
        deposits = [
            {
                "state": "2",
                "ts": str(
                    self.timestamp_ms(middle)
                ),
                "ccy": "USDT",
                "amt": "20",
            },
            {
                "state": "2",
                "ts": str(
                    self.timestamp_ms(
                        self.period_start
                    )
                ),
                "ccy": "USDT",
                "amt": "10",
            },
        ]
        withdrawals = [
            {
                "state": "2",
                "ts": str(
                    self.timestamp_ms(
                        self.period_end
                    )
                ),
                "ccy": "USDT",
                "amt": "5",
            }
        ]

        flows, skipped = (
            self.service.build_cash_flows(
                deposits=deposits,
                withdrawals=withdrawals,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(
            [flow.timestamp for flow in flows],
            [
                self.period_start,
                middle,
                self.period_end,
            ],
        )
        self.assertEqual(
            [
                flow.amount_usdt
                for flow in flows
            ],
            [
                10.0,
                20.0,
                -5.0,
            ],
        )


if __name__ == "__main__":
    unittest.main()
