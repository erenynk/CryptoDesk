import unittest
from datetime import UTC, datetime, timedelta
from unittest.mock import Mock, call, patch

from services.account_performance_service import (
    AccountPerformanceService,
)
from services.performance_engine import CashFlow


class AccountPerformanceServiceTestCase(
    unittest.TestCase
):
    def setUp(self):
        self.okx = Mock()
        self.history = Mock()
        self.history.APP_TIMEZONE = UTC
        self.history.PERFORMANCE_PERIODS = (
            "1d",
            "7d",
            "30d",
            "90d",
            "1y",
        )
        self.service = AccountPerformanceService(
            okx_service=self.okx,
            history_service=self.history,
        )

        self.period_start = datetime(
            2026,
            7,
            21,
            12,
            0,
            tzinfo=UTC,
        )
        self.period_end = datetime(
            2026,
            7,
            22,
            12,
            0,
            tzinfo=UTC,
        )

    @staticmethod
    def timestamp_ms(value):
        return int(value.timestamp() * 1000)

    @patch(
        "services.account_performance_service."
        "ExternalFlowService"
    )
    def test_constructor_wires_dependencies(
        self,
        external_flow_class,
    ):
        okx = Mock()
        history = Mock()
        history.APP_TIMEZONE = UTC

        service = AccountPerformanceService(
            okx_service=okx,
            history_service=history,
        )

        self.assertIs(service.okx, okx)
        self.assertIs(service.history, history)
        external_flow_class.assert_called_once_with(
            okx_service=okx,
            app_timezone=UTC,
        )
        self.assertIs(
            service.external_flows,
            external_flow_class.return_value,
        )

    def test_safe_float_normalizes_invalid_values(self):
        cases = (
            ("12.5", 12.5),
            (5, 5.0),
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

    def test_bill_datetime_converts_milliseconds(self):
        expected = datetime(
            2026,
            7,
            22,
            10,
            15,
            30,
            tzinfo=UTC,
        )

        result = self.service._bill_datetime(
            {
                "ts": str(
                    self.timestamp_ms(expected)
                ),
            }
        )

        self.assertEqual(result, expected)

    def test_bill_datetime_rejects_invalid_values(self):
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
                    self.service._bill_datetime(
                        {
                            "ts": value,
                        }
                    )
                )

    def test_historical_value_uses_one_for_stablecoins(
        self,
    ):
        for coin in ("USDT", "usd"):
            with self.subTest(coin=coin):
                result = (
                    self.service._historical_value(
                        coin=coin,
                        amount=25.5,
                        timestamp_ms=123456,
                    )
                )

                self.assertEqual(result, 25.5)

        self.okx.get_historical_spot_price.assert_not_called()

    def test_historical_value_uses_okx_price(self):
        self.okx.get_historical_spot_price.return_value = (
            True,
            "2500.5",
        )

        result = self.service._historical_value(
            coin=" eth ",
            amount=2.0,
            timestamp_ms=123456,
        )

        self.assertEqual(result, 5001.0)
        self.okx.get_historical_spot_price.assert_called_once_with(
            coin="ETH",
            timestamp_ms=123456,
        )

    def test_historical_value_rejects_failed_or_invalid_price(
        self,
    ):
        responses = (
            (False, "not found"),
            (True, 0),
            (True, -1),
            (True, "invalid"),
        )

        for response in responses:
            with self.subTest(response=response):
                self.okx.reset_mock()
                self.okx.get_historical_spot_price.return_value = (
                    response
                )

                result = (
                    self.service._historical_value(
                        coin="BTC",
                        amount=1.0,
                        timestamp_ms=123456,
                    )
                )

                self.assertIsNone(result)

    def test_internal_transfer_trading_to_funding(
        self,
    ):
        transfer_time = (
            self.period_start
            + timedelta(hours=3)
        )
        bills = [
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "-125.5",
                "ts": str(
                    self.timestamp_ms(transfer_time)
                ),
            }
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(len(funding), 1)
        self.assertEqual(len(trading), 1)
        self.assertEqual(
            funding[0].amount_usdt,
            125.5,
        )
        self.assertEqual(
            trading[0].amount_usdt,
            -125.5,
        )
        self.assertEqual(
            funding[0].description,
            "trading_to_funding:USDT:125.5",
        )
        self.assertEqual(
            funding[0].timestamp,
            transfer_time,
        )

    def test_internal_transfer_funding_to_trading(
        self,
    ):
        transfer_time = (
            self.period_start
            + timedelta(hours=4)
        )
        self.okx.get_historical_spot_price.return_value = (
            True,
            3000.0,
        )
        bills = [
            {
                "type": "1",
                "from": "6",
                "to": "18",
                "ccy": "eth",
                "balChg": "2",
                "ts": str(
                    self.timestamp_ms(transfer_time)
                ),
            }
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(
            funding[0].amount_usdt,
            -6000.0,
        )
        self.assertEqual(
            trading[0].amount_usdt,
            6000.0,
        )
        self.assertEqual(
            trading[0].description,
            "funding_to_trading:ETH:2.0",
        )
        self.okx.get_historical_spot_price.assert_called_once_with(
            coin="ETH",
            timestamp_ms=self.timestamp_ms(
                transfer_time
            ),
        )

    def test_internal_transfer_uses_size_fallback(
        self,
    ):
        transfer_time = (
            self.period_start
            + timedelta(hours=5)
        )
        bills = [
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "0",
                "sz": "-75",
                "ts": str(
                    self.timestamp_ms(transfer_time)
                ),
            }
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(
            funding[0].amount_usdt,
            75.0,
        )
        self.assertEqual(
            trading[0].amount_usdt,
            -75.0,
        )

    def test_internal_transfer_filters_irrelevant_bills(
        self,
    ):
        inside_time = (
            self.period_start
            + timedelta(hours=1)
        )
        before_time = (
            self.period_start
            - timedelta(seconds=1)
        )
        after_time = (
            self.period_end
            + timedelta(seconds=1)
        )
        bills = [
            {
                "type": "2",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "1",
                "ts": str(
                    self.timestamp_ms(inside_time)
                ),
            },
            {
                "type": "1",
                "from": "18",
                "to": "18",
                "ccy": "USDT",
                "balChg": "1",
                "ts": str(
                    self.timestamp_ms(inside_time)
                ),
            },
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "1",
                "ts": str(
                    self.timestamp_ms(before_time)
                ),
            },
            {
                "type": "1",
                "from": "6",
                "to": "18",
                "ccy": "USDT",
                "balChg": "1",
                "ts": str(
                    self.timestamp_ms(after_time)
                ),
            },
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "1",
                "ts": "invalid",
            },
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(funding, [])
        self.assertEqual(trading, [])
        self.assertEqual(skipped, [])
        self.okx.get_historical_spot_price.assert_not_called()

    def test_internal_transfer_records_missing_price(
        self,
    ):
        transfer_time = (
            self.period_start
            + timedelta(hours=6)
        )
        self.okx.get_historical_spot_price.return_value = (
            False,
            "price unavailable",
        )
        bills = [
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "BTC",
                "balChg": "0.5",
                "ts": str(
                    self.timestamp_ms(transfer_time)
                ),
            }
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(funding, [])
        self.assertEqual(trading, [])
        self.assertEqual(
            skipped,
            [
                {
                    "type": "internal_transfer",
                    "coin": "BTC",
                    "amount": 0.5,
                    "reason": (
                        "historical_price_unavailable"
                    ),
                }
            ],
        )

    def test_internal_transfer_flows_are_sorted(self):
        late = (
            self.period_start
            + timedelta(hours=10)
        )
        early = (
            self.period_start
            + timedelta(hours=2)
        )
        bills = [
            {
                "type": "1",
                "from": "18",
                "to": "6",
                "ccy": "USDT",
                "balChg": "10",
                "ts": str(self.timestamp_ms(late)),
            },
            {
                "type": "1",
                "from": "6",
                "to": "18",
                "ccy": "USDT",
                "balChg": "20",
                "ts": str(self.timestamp_ms(early)),
            },
        ]

        funding, trading, skipped = (
            self.service.build_internal_transfer_flows(
                bills=bills,
                period_start=self.period_start,
                period_end=self.period_end,
            )
        )

        self.assertEqual(skipped, [])
        self.assertEqual(
            [flow.timestamp for flow in funding],
            [early, late],
        )
        self.assertEqual(
            [flow.timestamp for flow in trading],
            [early, late],
        )

    @patch(
        "services.account_performance_service."
        "PerformanceEngine.calculate"
    )
    def test_calculate_period_routes_cash_flows(
        self,
        calculate,
    ):
        self.history._storage_to_datetime.return_value = (
            self.period_start
        )
        external_early = CashFlow(
            amount_usdt=100.0,
            timestamp=(
                self.period_start
                + timedelta(hours=1)
            ),
            description="deposit",
        )
        external_late = CashFlow(
            amount_usdt=-25.0,
            timestamp=(
                self.period_start
                + timedelta(hours=8)
            ),
            description="withdrawal",
        )
        funding_internal = CashFlow(
            amount_usdt=50.0,
            timestamp=(
                self.period_start
                + timedelta(hours=4)
            ),
            description="internal-funding",
        )
        trading_internal = CashFlow(
            amount_usdt=-50.0,
            timestamp=(
                self.period_start
                + timedelta(hours=4)
            ),
            description="internal-trading",
        )

        self.service.external_flows = Mock()
        self.service.external_flows.build_cash_flows.return_value = (
            [external_late, external_early],
            [
                {
                    "reason": "external skipped",
                }
            ],
        )
        self.service.build_internal_transfer_flows = (
            Mock(
                return_value=(
                    [funding_internal],
                    [trading_internal],
                    [
                        {
                            "reason": "transfer skipped",
                        }
                    ],
                )
            )
        )
        calculate.side_effect = (
            "total-result",
            "funding-result",
            "trading-result",
        )

        snapshot = {
            "timestamp": "stored-time",
            "total_usdt": 1000.0,
            "funding_usdt": 400.0,
            "trading_usdt": 600.0,
        }
        portfolio = {
            "total_usdt": 1100.0,
            "funding_usdt": 450.0,
            "trading_usdt": 650.0,
        }

        result = self.service._calculate_period(
            portfolio=portfolio,
            reference_snapshot=snapshot,
            period_end=self.period_end,
            deposits=[{"id": "deposit"}],
            withdrawals=[{"id": "withdrawal"}],
            transfer_bills=[{"id": "transfer"}],
        )

        self.history._storage_to_datetime.assert_called_once_with(
            "stored-time"
        )
        self.service.external_flows.build_cash_flows.assert_called_once_with(
            deposits=[{"id": "deposit"}],
            withdrawals=[{"id": "withdrawal"}],
            period_start=self.period_start,
            period_end=self.period_end,
        )
        self.service.build_internal_transfer_flows.assert_called_once_with(
            bills=[{"id": "transfer"}],
            period_start=self.period_start,
            period_end=self.period_end,
        )

        self.assertEqual(
            calculate.call_args_list,
            [
                call(
                    start_value_usdt=1000.0,
                    end_value_usdt=1100.0,
                    period_start=self.period_start,
                    period_end=self.period_end,
                    cash_flows=[
                        external_late,
                        external_early,
                    ],
                ),
                call(
                    start_value_usdt=400.0,
                    end_value_usdt=450.0,
                    period_start=self.period_start,
                    period_end=self.period_end,
                    cash_flows=[
                        external_early,
                        funding_internal,
                        external_late,
                    ],
                ),
                call(
                    start_value_usdt=600.0,
                    end_value_usdt=650.0,
                    period_start=self.period_start,
                    period_end=self.period_end,
                    cash_flows=[
                        trading_internal,
                    ],
                ),
            ],
        )
        self.assertEqual(
            result["total"],
            "total-result",
        )
        self.assertEqual(
            result["funding"],
            "funding-result",
        )
        self.assertEqual(
            result["trading"],
            "trading-result",
        )
        self.assertEqual(
            result["skipped"],
            [
                {
                    "reason": "external skipped",
                },
                {
                    "reason": "transfer skipped",
                },
            ],
        )

    def test_calculate_period_integrates_modified_dietz(
        self,
    ):
        self.history._storage_to_datetime.return_value = (
            self.period_start
        )
        self.service.external_flows = Mock()
        self.service.external_flows.build_cash_flows.return_value = (
            [],
            [],
        )
        self.service.build_internal_transfer_flows = (
            Mock(
                return_value=(
                    [],
                    [],
                    [],
                )
            )
        )

        result = self.service._calculate_period(
            portfolio={
                "total_usdt": 1100.0,
                "funding_usdt": 420.0,
                "trading_usdt": 680.0,
            },
            reference_snapshot={
                "timestamp": "stored-time",
                "total_usdt": 1000.0,
                "funding_usdt": 400.0,
                "trading_usdt": 600.0,
            },
            period_end=self.period_end,
            deposits=[],
            withdrawals=[],
            transfer_bills=[],
        )

        self.assertEqual(
            result["total"].pnl_usdt,
            100.0,
        )
        self.assertEqual(
            result["total"].return_percent,
            10.0,
        )
        self.assertEqual(
            result["funding"].pnl_usdt,
            20.0,
        )
        self.assertEqual(
            result["funding"].return_percent,
            5.0,
        )
        self.assertEqual(
            result["trading"].pnl_usdt,
            80.0,
        )
        self.assertEqual(
            result["trading"].return_percent,
            13.33333333,
        )

    def test_calculate_periods_fetches_history_once_and_delegates(
        self,
    ):
        deposits = [{"depId": "1"}]
        withdrawals = [{"wdId": "2"}]
        transfers = [{"billId": "3"}]

        self.okx.get_deposit_history.return_value = (
            True,
            deposits,
        )
        self.okx.get_withdrawal_history.return_value = (
            True,
            withdrawals,
        )
        self.okx.get_funding_transfer_bills.return_value = (
            True,
            transfers,
        )
        self.service._calculate_period = Mock(
            side_effect=[
                {
                    "period": "1d",
                },
                {
                    "period": "30d",
                },
            ]
        )

        snapshot_1d = {
            "timestamp": "one-day",
        }
        snapshot_30d = {
            "timestamp": "thirty-day",
        }
        references = {
            "1d": snapshot_1d,
            "7d": None,
            "30d": snapshot_30d,
        }
        portfolio = {
            "total_usdt": 1000.0,
        }

        result = self.service.calculate_periods(
            portfolio=portfolio,
            reference_snapshots=references,
            period_end=self.period_end,
        )

        self.assertEqual(
            result,
            {
                "1d": {
                    "period": "1d",
                },
                "7d": None,
                "30d": {
                    "period": "30d",
                },
                "90d": None,
                "1y": None,
            },
        )
        self.assertEqual(
            self.service._calculate_period.call_args_list,
            [
                call(
                    portfolio=portfolio,
                    reference_snapshot=snapshot_1d,
                    period_end=self.period_end,
                    deposits=deposits,
                    withdrawals=withdrawals,
                    transfer_bills=transfers,
                ),
                call(
                    portfolio=portfolio,
                    reference_snapshot=snapshot_30d,
                    period_end=self.period_end,
                    deposits=deposits,
                    withdrawals=withdrawals,
                    transfer_bills=transfers,
                ),
            ],
        )
        self.okx.get_deposit_history.assert_called_once_with()
        self.okx.get_withdrawal_history.assert_called_once_with()
        self.okx.get_funding_transfer_bills.assert_called_once_with()

    def test_calculate_periods_raises_on_deposit_error(
        self,
    ):
        self.okx.get_deposit_history.return_value = (
            False,
            "deposit failed",
        )
        self.okx.get_withdrawal_history.return_value = (
            True,
            [],
        )
        self.okx.get_funding_transfer_bills.return_value = (
            True,
            [],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "deposit failed",
        ):
            self.service.calculate_periods(
                portfolio={},
                reference_snapshots={},
                period_end=self.period_end,
            )

    def test_calculate_periods_raises_on_withdrawal_error(
        self,
    ):
        self.okx.get_deposit_history.return_value = (
            True,
            [],
        )
        self.okx.get_withdrawal_history.return_value = (
            False,
            "withdrawal failed",
        )
        self.okx.get_funding_transfer_bills.return_value = (
            True,
            [],
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "withdrawal failed",
        ):
            self.service.calculate_periods(
                portfolio={},
                reference_snapshots={},
                period_end=self.period_end,
            )

    def test_calculate_periods_raises_on_transfer_error(
        self,
    ):
        self.okx.get_deposit_history.return_value = (
            True,
            [],
        )
        self.okx.get_withdrawal_history.return_value = (
            True,
            [],
        )
        self.okx.get_funding_transfer_bills.return_value = (
            False,
            "transfer failed",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "transfer failed",
        ):
            self.service.calculate_periods(
                portfolio={},
                reference_snapshots={},
                period_end=self.period_end,
            )

    def test_calculate_periods_propagates_period_error(
        self,
    ):
        self.okx.get_deposit_history.return_value = (
            True,
            [],
        )
        self.okx.get_withdrawal_history.return_value = (
            True,
            [],
        )
        self.okx.get_funding_transfer_bills.return_value = (
            True,
            [],
        )
        self.service._calculate_period = Mock(
            side_effect=ValueError(
                "invalid period"
            )
        )

        with self.assertRaisesRegex(
            ValueError,
            "invalid period",
        ):
            self.service.calculate_periods(
                portfolio={},
                reference_snapshots={
                    "1d": {
                        "timestamp": "stored-time",
                    }
                },
                period_end=self.period_end,
            )


if __name__ == "__main__":
    unittest.main()
