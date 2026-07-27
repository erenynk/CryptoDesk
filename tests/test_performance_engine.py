import unittest
from dataclasses import FrozenInstanceError
from datetime import UTC, datetime, timedelta, timezone

from services.performance_engine import (
    CashFlow,
    PerformanceEngine,
    PerformanceResult,
)


class PerformanceEngineTestCase(unittest.TestCase):
    def setUp(self):
        self.timezone = timezone(
            timedelta(hours=3)
        )
        self.period_start = datetime(
            2026,
            7,
            21,
            0,
            0,
            tzinfo=self.timezone,
        )
        self.period_end = (
            self.period_start
            + timedelta(days=1)
        )

    def test_cash_flow_is_frozen_and_description_defaults(
        self,
    ):
        flow = CashFlow(
            amount_usdt=100.0,
            timestamp=self.period_start,
        )

        self.assertEqual(flow.description, "")

        with self.assertRaises(
            FrozenInstanceError
        ):
            flow.amount_usdt = 200.0

    def test_result_is_frozen_dataclass(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1100.0,
            period_start=self.period_start,
            period_end=self.period_end,
        )

        self.assertIsInstance(
            result,
            PerformanceResult,
        )

        with self.assertRaises(
            FrozenInstanceError
        ):
            result.pnl_usdt = 0.0

    def test_no_flow_calculates_simple_return(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1100.0,
            period_start=self.period_start,
            period_end=self.period_end,
        )

        self.assertEqual(
            result.start_value_usdt,
            1000.0,
        )
        self.assertEqual(
            result.end_value_usdt,
            1100.0,
        )
        self.assertEqual(result.net_flow_usdt, 0.0)
        self.assertEqual(
            result.weighted_flow_usdt,
            0.0,
        )
        self.assertEqual(result.pnl_usdt, 100.0)
        self.assertEqual(
            result.return_percent,
            10.0,
        )
        self.assertEqual(result.flow_count, 0)

    def test_midpoint_deposit_uses_half_weight(self):
        flow = CashFlow(
            amount_usdt=500.0,
            timestamp=(
                self.period_start
                + timedelta(hours=12)
            ),
            description="deposit",
        )

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1510.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[flow],
        )

        self.assertEqual(
            result.net_flow_usdt,
            500.0,
        )
        self.assertEqual(
            result.weighted_flow_usdt,
            250.0,
        )
        self.assertEqual(result.pnl_usdt, 10.0)
        self.assertEqual(
            result.return_percent,
            0.8,
        )

    def test_midpoint_withdrawal_uses_half_weight(
        self,
    ):
        flow = CashFlow(
            amount_usdt=-200.0,
            timestamp=(
                self.period_start
                + timedelta(hours=12)
            ),
            description="withdrawal",
        )

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=810.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[flow],
        )

        self.assertEqual(
            result.net_flow_usdt,
            -200.0,
        )
        self.assertEqual(
            result.weighted_flow_usdt,
            -100.0,
        )
        self.assertEqual(result.pnl_usdt, 10.0)
        self.assertEqual(
            result.return_percent,
            1.11111111,
        )

    def test_multiple_flows_use_modified_dietz_weights(
        self,
    ):
        flows = [
            CashFlow(
                amount_usdt=300.0,
                timestamp=(
                    self.period_start
                    + timedelta(hours=6)
                ),
            ),
            CashFlow(
                amount_usdt=-100.0,
                timestamp=(
                    self.period_start
                    + timedelta(hours=18)
                ),
            ),
        ]

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1250.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=flows,
        )

        self.assertEqual(
            result.net_flow_usdt,
            200.0,
        )
        self.assertEqual(
            result.weighted_flow_usdt,
            200.0,
        )
        self.assertEqual(result.pnl_usdt, 50.0)
        self.assertEqual(
            result.return_percent,
            4.16666667,
        )
        self.assertEqual(result.flow_count, 2)

    def test_period_boundaries_are_inclusive(self):
        flows = [
            CashFlow(
                amount_usdt=10.0,
                timestamp=self.period_start,
            ),
            CashFlow(
                amount_usdt=20.0,
                timestamp=self.period_end,
            ),
        ]

        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=130.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=flows,
        )

        self.assertEqual(result.flow_count, 2)
        self.assertEqual(
            result.net_flow_usdt,
            30.0,
        )
        self.assertEqual(
            result.weighted_flow_usdt,
            10.0,
        )
        self.assertEqual(result.pnl_usdt, 0.0)
        self.assertEqual(
            result.return_percent,
            0.0,
        )

    def test_out_of_period_flows_are_ignored(self):
        flows = [
            CashFlow(
                amount_usdt=100.0,
                timestamp=(
                    self.period_start
                    - timedelta(seconds=1)
                ),
            ),
            CashFlow(
                amount_usdt=200.0,
                timestamp=(
                    self.period_end
                    + timedelta(seconds=1)
                ),
            ),
        ]

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1010.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=flows,
        )

        self.assertEqual(result.flow_count, 0)
        self.assertEqual(result.net_flow_usdt, 0.0)
        self.assertEqual(result.pnl_usdt, 10.0)
        self.assertEqual(
            result.return_percent,
            1.0,
        )

    def test_non_cash_flow_items_are_ignored(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=110.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[
                {
                    "amount_usdt": 500.0,
                },
                "invalid",
                None,
            ],
        )

        self.assertEqual(result.flow_count, 0)
        self.assertEqual(result.net_flow_usdt, 0.0)
        self.assertEqual(result.pnl_usdt, 10.0)

    def test_zero_nan_and_tiny_flows_are_ignored(
        self,
    ):
        midpoint = (
            self.period_start
            + timedelta(hours=12)
        )
        flows = [
            CashFlow(
                amount_usdt=0.0,
                timestamp=midpoint,
            ),
            CashFlow(
                amount_usdt=float("nan"),
                timestamp=midpoint,
            ),
            CashFlow(
                amount_usdt=(
                    PerformanceEngine.EPSILON
                ),
                timestamp=midpoint,
            ),
            CashFlow(
                amount_usdt=(
                    PerformanceEngine.EPSILON * 2
                ),
                timestamp=midpoint,
            ),
        ]

        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=100.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=flows,
        )

        self.assertEqual(result.flow_count, 1)
        self.assertEqual(
            result.net_flow_usdt,
            PerformanceEngine.EPSILON * 2,
        )

    def test_safe_float_handles_conversion_errors(self):
        for value in (None, "invalid", object()):
            with self.subTest(value=value):
                self.assertEqual(
                    PerformanceEngine._safe_float(value),
                    0.0,
                )

    def test_invalid_start_and_end_values_are_normalized(
        self,
    ):
        result = PerformanceEngine.calculate(
            start_value_usdt=float("nan"),
            end_value_usdt="50",
            period_start=self.period_start,
            period_end=self.period_end,
        )

        self.assertEqual(
            result.start_value_usdt,
            0.0,
        )
        self.assertEqual(
            result.end_value_usdt,
            50.0,
        )
        self.assertEqual(result.pnl_usdt, 50.0)
        self.assertIsNone(
            result.return_percent
        )

    def test_zero_denominator_returns_none(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=0.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[
                CashFlow(
                    amount_usdt=-100.0,
                    timestamp=self.period_start,
                )
            ],
        )

        self.assertEqual(
            result.weighted_flow_usdt,
            -100.0,
        )
        self.assertEqual(result.pnl_usdt, 0.0)
        self.assertIsNone(
            result.return_percent
        )

    def test_negative_denominator_returns_none(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=-100.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[
                CashFlow(
                    amount_usdt=-200.0,
                    timestamp=self.period_start,
                )
            ],
        )

        self.assertEqual(result.pnl_usdt, 0.0)
        self.assertIsNone(
            result.return_percent
        )

    def test_return_is_rounded_to_eight_decimals(self):
        result = PerformanceEngine.calculate(
            start_value_usdt=3.0,
            end_value_usdt=4.0,
            period_start=self.period_start,
            period_end=self.period_end,
        )

        self.assertEqual(
            result.return_percent,
            33.33333333,
        )

    def test_equal_period_boundaries_raise_error(self):
        with self.assertRaisesRegex(
            ValueError,
            (
                "period_end, period_start "
                "değerinden sonra olmalıdır"
            ),
        ):
            PerformanceEngine.calculate(
                start_value_usdt=100.0,
                end_value_usdt=100.0,
                period_start=self.period_start,
                period_end=self.period_start,
            )

    def test_reversed_period_raises_error(self):
        with self.assertRaises(ValueError):
            PerformanceEngine.calculate(
                start_value_usdt=100.0,
                end_value_usdt=100.0,
                period_start=self.period_end,
                period_end=self.period_start,
            )

    def test_naive_period_remains_naive(self):
        start = datetime(
            2026,
            7,
            21,
            0,
            0,
        )
        end = start + timedelta(days=1)

        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=110.0,
            period_start=start,
            period_end=end,
        )

        self.assertIsNone(
            result.period_start.tzinfo
        )
        self.assertIsNone(
            result.period_end.tzinfo
        )

    def test_mixed_period_timezone_is_normalized(
        self,
    ):
        naive_end = datetime(
            2026,
            7,
            22,
            0,
            0,
        )

        result = PerformanceEngine.calculate(
            start_value_usdt=100.0,
            end_value_usdt=110.0,
            period_start=self.period_start,
            period_end=naive_end,
        )

        self.assertEqual(
            result.period_start.tzinfo,
            self.timezone,
        )
        self.assertEqual(
            result.period_end.tzinfo,
            self.timezone,
        )
        self.assertEqual(
            result.period_end.hour,
            0,
        )

    def test_aware_flow_is_converted_to_period_timezone(
        self,
    ):
        midpoint_utc = datetime(
            2026,
            7,
            21,
            9,
            0,
            tzinfo=UTC,
        )

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1510.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=[
                CashFlow(
                    amount_usdt=500.0,
                    timestamp=midpoint_utc,
                )
            ],
        )

        self.assertEqual(result.flow_count, 1)
        self.assertEqual(
            result.weighted_flow_usdt,
            250.0,
        )
        self.assertEqual(
            result.return_percent,
            0.8,
        )

    def test_cash_flow_generator_is_supported(self):
        def generate_flows():
            yield CashFlow(
                amount_usdt=100.0,
                timestamp=self.period_start,
            )
            yield CashFlow(
                amount_usdt=-20.0,
                timestamp=self.period_end,
            )

        result = PerformanceEngine.calculate(
            start_value_usdt=1000.0,
            end_value_usdt=1090.0,
            period_start=self.period_start,
            period_end=self.period_end,
            cash_flows=generate_flows(),
        )

        self.assertEqual(result.flow_count, 2)
        self.assertEqual(
            result.net_flow_usdt,
            80.0,
        )
        self.assertEqual(
            result.weighted_flow_usdt,
            100.0,
        )
        self.assertEqual(result.pnl_usdt, 10.0)
        self.assertEqual(
            result.return_percent,
            0.90909091,
        )


if __name__ == "__main__":
    unittest.main()
