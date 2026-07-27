import math
import unittest
from datetime import datetime, timedelta, timezone

from services.transfer_service import TransferService


class RaisesOverflow:
    def __float__(self):
        raise OverflowError("overflow")


class TransferServiceTestCase(unittest.TestCase):
    APP_TIMEZONE = timezone(timedelta(hours=3))
    NOW = datetime(
        2026,
        7,
        23,
        12,
        0,
        0,
        tzinfo=APP_TIMEZONE,
    )

    def setUp(self):
        self.service = TransferService(
            self.APP_TIMEZONE
        )

    @staticmethod
    def timestamp_ms(value):
        return str(
            int(value.timestamp() * 1000)
        )

    def make_bill(
        self,
        *,
        when=None,
        from_account="18",
        to_account="6",
        currency="USDT",
        balance_change="100",
        size="0",
        bill_type="1",
    ):
        return {
            "type": bill_type,
            "from": from_account,
            "to": to_account,
            "ccy": currency,
            "balChg": balance_change,
            "sz": size,
            "ts": self.timestamp_ms(
                when or self.NOW
            ),
        }

    def all_references(self):
        return {
            period: self.NOW - duration
            for period, duration in (
                self.service.PERIODS.items()
            )
        }

    def test_period_constants(self):
        self.assertEqual(
            self.service.PERIODS,
            {
                "1d": timedelta(days=1),
                "7d": timedelta(days=7),
                "30d": timedelta(days=30),
                "90d": timedelta(days=90),
                "1y": timedelta(days=365),
            },
        )

    def test_safe_float_accepts_numeric_values(self):
        cases = (
            (10, 10.0),
            (-2.5, -2.5),
            ("3.25", 3.25),
            (True, 1.0),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.service._safe_float(value),
                    expected,
                )

    def test_safe_float_rejects_invalid_values_and_nan(self):
        cases = (
            None,
            "",
            "invalid",
            object(),
            RaisesOverflow(),
            float("nan"),
        )

        for value in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    self.service._safe_float(value),
                    0.0,
                )

    def test_safe_float_preserves_infinity(self):
        self.assertTrue(
            math.isinf(
                self.service._safe_float(
                    float("inf")
                )
            )
        )

    def test_bill_datetime_converts_timestamp(self):
        expected = self.NOW - timedelta(hours=2)
        bill = {
            "ts": self.timestamp_ms(expected)
        }

        result = self.service._bill_datetime(
            bill
        )

        self.assertEqual(result, expected)
        self.assertIs(
            result.tzinfo,
            self.APP_TIMEZONE,
        )

    def test_bill_datetime_rejects_missing_nonpositive_and_invalid(self):
        bills = (
            {},
            {
                "ts": "0",
            },
            {
                "ts": "-1000",
            },
            {
                "ts": "invalid",
            },
            {
                "ts": float("inf"),
            },
        )

        for bill in bills:
            with self.subTest(bill=bill):
                self.assertIsNone(
                    self.service._bill_datetime(
                        bill
                    )
                )

    def test_reference_adjustments_return_zero_without_bills(self):
        result = (
            self.service
            .calculate_reference_adjustments(
                bills=[],
                prices={},
                reference_times={},
                current_time=self.NOW,
            )
        )

        self.assertEqual(
            result,
            {
                period: 0.0
                for period in self.service.PERIODS
            },
        )

    def test_reference_adjustments_normalize_naive_times(self):
        bill_time = (
            self.NOW - timedelta(hours=1)
        ).replace(tzinfo=None)
        current_time = self.NOW.replace(
            tzinfo=None
        )
        references = {
            "1d": (
                self.NOW
                - timedelta(days=1)
            ).replace(tzinfo=None),
            "7d": None,
        }

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=[
                    self.make_bill(
                        when=bill_time.replace(
                            tzinfo=self.APP_TIMEZONE
                        )
                    )
                ],
                prices={},
                reference_times=references,
                current_time=current_time,
            )
        )

        self.assertEqual(result["1d"], 100.0)
        self.assertEqual(result["7d"], 0.0)
        self.assertEqual(result["30d"], 0.0)

    def test_reference_adjustments_convert_aware_times_to_app_timezone(self):
        utc = timezone.utc
        current_utc = self.NOW.astimezone(
            utc
        )
        bill_time = self.NOW - timedelta(
            hours=2
        )
        references = {
            period: (
                self.NOW - duration
            ).astimezone(utc)
            for period, duration in (
                self.service.PERIODS.items()
            )
        }

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=[
                    self.make_bill(
                        when=bill_time
                    )
                ],
                prices={},
                reference_times=references,
                current_time=current_utc,
            )
        )

        self.assertTrue(
            all(
                value == 100.0
                for value in result.values()
            )
        )

    def test_reference_adjustments_apply_direction_and_asset_price(self):
        when = self.NOW - timedelta(
            hours=12
        )
        bills = [
            self.make_bill(
                when=when,
                from_account="18",
                to_account="6",
                currency="btc",
                balance_change="-0.5",
            ),
            self.make_bill(
                when=when,
                from_account="6",
                to_account="18",
                currency="ETH",
                balance_change="2",
            ),
        ]

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=bills,
                prices={
                    "BTC": 60000.0,
                    "ETH": 3000.0,
                },
                reference_times=self.all_references(),
                current_time=self.NOW,
            )
        )

        expected = 24000.0
        self.assertTrue(
            all(
                value == expected
                for value in result.values()
            )
        )

    def test_reference_adjustments_use_size_when_balance_change_is_zero(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                hours=1
            ),
            balance_change="0",
            size="-2.5",
        )

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=[bill],
                prices={},
                reference_times=self.all_references(),
                current_time=self.NOW,
            )
        )

        self.assertTrue(
            all(
                value == 2.5
                for value in result.values()
            )
        )

    def test_reference_adjustments_respect_reference_boundaries(self):
        one_day_reference = (
            self.NOW - timedelta(days=1)
        )
        bills = [
            self.make_bill(
                when=one_day_reference,
                balance_change="10",
            ),
            self.make_bill(
                when=self.NOW,
                balance_change="20",
            ),
        ]

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=bills,
                prices={},
                reference_times=self.all_references(),
                current_time=self.NOW,
            )
        )

        self.assertEqual(result["1d"], 20.0)
        self.assertEqual(result["7d"], 30.0)

    def test_reference_adjustments_skip_unsupported_bills(self):
        valid_time = self.NOW - timedelta(
            hours=1
        )
        bills = [
            self.make_bill(
                when=valid_time,
                bill_type="2",
            ),
            self.make_bill(
                when=valid_time,
                from_account="6",
                to_account="6",
            ),
            {
                **self.make_bill(
                    when=valid_time
                ),
                "ts": "invalid",
            },
            self.make_bill(
                when=self.NOW
                + timedelta(seconds=1)
            ),
            self.make_bill(
                when=valid_time,
                currency=" ",
            ),
            self.make_bill(
                when=valid_time,
                balance_change="0",
                size="0",
            ),
            self.make_bill(
                when=valid_time,
                currency="BTC",
            ),
            self.make_bill(
                when=valid_time,
                currency="ETH",
            ),
        ]

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=bills,
                prices={
                    "BTC": 0,
                    "ETH": float("nan"),
                },
                reference_times=self.all_references(),
                current_time=self.NOW,
            )
        )

        self.assertTrue(
            all(
                value == 0.0
                for value in result.values()
            )
        )

    def test_reference_adjustments_round_to_eight_decimals(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                hours=1
            ),
            currency="BTC",
            balance_change="0.333333333",
        )

        result = (
            self.service
            .calculate_reference_adjustments(
                bills=[bill],
                prices={
                    "BTC": 3.0,
                },
                reference_times=self.all_references(),
                current_time=self.NOW,
            )
        )

        self.assertEqual(
            result["1d"],
            1.0,
        )

    def test_period_adjustments_return_zero_without_bills(self):
        result = (
            self.service
            .calculate_period_adjustments(
                bills=[],
                prices={},
                reference_time=self.NOW,
            )
        )

        self.assertEqual(
            result,
            {
                period: 0.0
                for period in self.service.PERIODS
            },
        )

    def test_period_adjustments_normalize_naive_reference_time(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                hours=1
            )
        )

        result = (
            self.service
            .calculate_period_adjustments(
                bills=[bill],
                prices={},
                reference_time=(
                    self.NOW.replace(
                        tzinfo=None
                    )
                ),
            )
        )

        self.assertTrue(
            all(
                value == 100.0
                for value in result.values()
            )
        )

    def test_period_adjustments_convert_aware_reference_time(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                hours=1
            )
        )

        result = (
            self.service
            .calculate_period_adjustments(
                bills=[bill],
                prices={},
                reference_time=(
                    self.NOW.astimezone(
                        timezone.utc
                    )
                ),
            )
        )

        self.assertTrue(
            all(
                value == 100.0
                for value in result.values()
            )
        )

    def test_period_adjustments_apply_direction_and_price(self):
        when = self.NOW - timedelta(
            hours=1
        )
        bills = [
            self.make_bill(
                when=when,
                from_account="18",
                to_account="6",
                currency="BTC",
                balance_change="-0.25",
            ),
            self.make_bill(
                when=when,
                from_account="6",
                to_account="18",
                currency="ETH",
                balance_change="1",
            ),
        ]

        result = (
            self.service
            .calculate_period_adjustments(
                bills=bills,
                prices={
                    "BTC": 60000.0,
                    "ETH": 3000.0,
                },
                reference_time=self.NOW,
            )
        )

        self.assertTrue(
            all(
                value == 12000.0
                for value in result.values()
            )
        )

    def test_period_adjustments_apply_inclusive_age_boundaries(self):
        bills = [
            self.make_bill(
                when=self.NOW,
                balance_change="10",
            ),
            self.make_bill(
                when=(
                    self.NOW
                    - timedelta(days=1)
                ),
                balance_change="20",
            ),
            self.make_bill(
                when=(
                    self.NOW
                    - timedelta(days=1)
                    - timedelta(milliseconds=1)
                ),
                balance_change="40",
            ),
        ]

        result = (
            self.service
            .calculate_period_adjustments(
                bills=bills,
                prices={},
                reference_time=self.NOW,
            )
        )

        self.assertEqual(result["1d"], 30.0)
        self.assertEqual(result["7d"], 70.0)

    def test_period_adjustments_use_size_fallback(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                minutes=5
            ),
            balance_change="invalid",
            size="-1.25",
        )

        result = (
            self.service
            .calculate_period_adjustments(
                bills=[bill],
                prices={},
                reference_time=self.NOW,
            )
        )

        self.assertTrue(
            all(
                value == 1.25
                for value in result.values()
            )
        )

    def test_period_adjustments_skip_unsupported_bills(self):
        valid_time = self.NOW - timedelta(
            hours=1
        )
        bills = [
            self.make_bill(
                when=valid_time,
                bill_type="3",
            ),
            self.make_bill(
                when=valid_time,
                from_account="18",
                to_account="18",
            ),
            {
                **self.make_bill(
                    when=valid_time
                ),
                "ts": "",
            },
            self.make_bill(
                when=self.NOW
                + timedelta(seconds=1)
            ),
            self.make_bill(
                when=valid_time,
                currency="",
            ),
            self.make_bill(
                when=valid_time,
                balance_change="0",
                size="bad",
            ),
            self.make_bill(
                when=valid_time,
                currency="BTC",
            ),
        ]

        result = (
            self.service
            .calculate_period_adjustments(
                bills=bills,
                prices={
                    "BTC": -1,
                },
                reference_time=self.NOW,
            )
        )

        self.assertTrue(
            all(
                value == 0.0
                for value in result.values()
            )
        )

    def test_period_adjustments_only_apply_to_matching_windows(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                days=45
            ),
            balance_change="12",
        )

        result = (
            self.service
            .calculate_period_adjustments(
                bills=[bill],
                prices={},
                reference_time=self.NOW,
            )
        )

        self.assertEqual(result["1d"], 0.0)
        self.assertEqual(result["7d"], 0.0)
        self.assertEqual(result["30d"], 0.0)
        self.assertEqual(result["90d"], 12.0)
        self.assertEqual(result["1y"], 12.0)

    def test_period_adjustments_round_to_eight_decimals(self):
        bill = self.make_bill(
            when=self.NOW - timedelta(
                hours=1
            ),
            currency="BTC",
            balance_change="0.1",
        )

        result = (
            self.service
            .calculate_period_adjustments(
                bills=[bill],
                prices={
                    "BTC": 0.333333333,
                },
                reference_time=self.NOW,
            )
        )

        self.assertEqual(
            result["1d"],
            0.03333333,
        )


if __name__ == "__main__":
    unittest.main()
