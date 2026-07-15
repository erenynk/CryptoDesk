from __future__ import annotations

from datetime import datetime
from typing import Any

from services.external_flow_service import ExternalFlowService
from services.performance_engine import CashFlow, PerformanceEngine


class AccountPerformanceService:
    """
    Toplam, Funding ve Trading hesaplarının 1 günlük performansını
    aynı Modified Dietz motoruyla hesaplar.
    """

    def __init__(
        self,
        okx_service,
        history_service,
    ):
        self.okx = okx_service
        self.history = history_service
        self.external_flows = ExternalFlowService(
            okx_service=okx_service,
            app_timezone=history_service.APP_TIMEZONE,
        )

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    def _bill_datetime(
        self,
        bill: dict[str, Any],
    ) -> datetime | None:
        timestamp_ms = int(
            self._safe_float(bill.get("ts"))
        )

        if timestamp_ms <= 0:
            return None

        try:
            return datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=self.history.APP_TIMEZONE,
            )
        except (OSError, OverflowError, ValueError):
            return None

    def _historical_value(
        self,
        coin: str,
        amount: float,
        timestamp_ms: int,
    ) -> float | None:
        normalized_coin = str(coin or "").strip().upper()

        if normalized_coin in {"USDT", "USD"}:
            return amount

        success, price = self.okx.get_historical_spot_price(
            coin=normalized_coin,
            timestamp_ms=timestamp_ms,
        )

        if not success:
            return None

        safe_price = self._safe_float(price)

        if safe_price <= 0:
            return None

        return amount * safe_price

    def build_internal_transfer_flows(
        self,
        bills: list[dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[list[CashFlow], list[CashFlow], list[dict[str, Any]]]:
        funding_flows: list[CashFlow] = []
        trading_flows: list[CashFlow] = []
        skipped: list[dict[str, Any]] = []

        for bill in bills:
            if str(bill.get("type", "")).strip() != "1":
                continue

            from_account = str(
                bill.get("from", "")
            ).strip()
            to_account = str(
                bill.get("to", "")
            ).strip()

            if {from_account, to_account} != {"6", "18"}:
                continue

            flow_time = self._bill_datetime(bill)

            if (
                flow_time is None
                or flow_time < period_start
                or flow_time > period_end
            ):
                continue

            coin = str(
                bill.get("ccy", "")
            ).strip().upper()
            amount = abs(
                self._safe_float(bill.get("balChg"))
            )

            if amount <= 0:
                amount = abs(
                    self._safe_float(bill.get("sz"))
                )

            timestamp_ms = int(
                self._safe_float(bill.get("ts"))
            )

            value_usdt = self._historical_value(
                coin=coin,
                amount=amount,
                timestamp_ms=timestamp_ms,
            )

            if value_usdt is None:
                skipped.append({
                    "type": "internal_transfer",
                    "coin": coin,
                    "amount": amount,
                    "reason": "historical_price_unavailable",
                })
                continue

            if from_account == "18" and to_account == "6":
                funding_amount = value_usdt
                trading_amount = -value_usdt
                direction = "trading_to_funding"
            else:
                funding_amount = -value_usdt
                trading_amount = value_usdt
                direction = "funding_to_trading"

            funding_flows.append(
                CashFlow(
                    amount_usdt=funding_amount,
                    timestamp=flow_time,
                    description=f"{direction}:{coin}:{amount}",
                )
            )
            trading_flows.append(
                CashFlow(
                    amount_usdt=trading_amount,
                    timestamp=flow_time,
                    description=f"{direction}:{coin}:{amount}",
                )
            )

        funding_flows.sort(key=lambda flow: flow.timestamp)
        trading_flows.sort(key=lambda flow: flow.timestamp)

        return funding_flows, trading_flows, skipped

    def _calculate_period(
        self,
        portfolio: dict[str, Any],
        reference_snapshot: dict[str, Any],
        period_end: datetime,
        deposits: list[dict[str, Any]],
        withdrawals: list[dict[str, Any]],
        transfer_bills: list[dict[str, Any]],
    ) -> dict[str, Any]:
        period_start = self.history._storage_to_datetime(
            reference_snapshot["timestamp"]
        )

        external_flows, external_skipped = (
            self.external_flows.build_cash_flows(
                deposits=deposits,
                withdrawals=withdrawals,
                period_start=period_start,
                period_end=period_end,
            )
        )

        funding_internal, trading_internal, transfer_skipped = (
            self.build_internal_transfer_flows(
                bills=transfer_bills,
                period_start=period_start,
                period_end=period_end,
            )
        )

        funding_flows = external_flows + funding_internal
        funding_flows.sort(key=lambda flow: flow.timestamp)

        total_result = PerformanceEngine.calculate(
            start_value_usdt=reference_snapshot["total_usdt"],
            end_value_usdt=portfolio.get("total_usdt", 0.0),
            period_start=period_start,
            period_end=period_end,
            cash_flows=external_flows,
        )
        funding_result = PerformanceEngine.calculate(
            start_value_usdt=reference_snapshot["funding_usdt"],
            end_value_usdt=portfolio.get("funding_usdt", 0.0),
            period_start=period_start,
            period_end=period_end,
            cash_flows=funding_flows,
        )
        trading_result = PerformanceEngine.calculate(
            start_value_usdt=reference_snapshot["trading_usdt"],
            end_value_usdt=portfolio.get("trading_usdt", 0.0),
            period_start=period_start,
            period_end=period_end,
            cash_flows=trading_internal,
        )

        return {
            "period_start": period_start,
            "period_end": period_end,
            "reference_snapshot": reference_snapshot,
            "total": total_result,
            "funding": funding_result,
            "trading": trading_result,
            "external_flows": external_flows,
            "funding_internal_flows": funding_internal,
            "trading_internal_flows": trading_internal,
            "skipped": external_skipped + transfer_skipped,
        }

    def calculate_periods(
        self,
        portfolio: dict[str, Any],
        reference_snapshots: dict[
            str,
            dict[str, Any] | None,
        ],
        period_end: datetime,
    ) -> dict[str, dict[str, Any] | None]:
        deposit_ok, deposits = self.okx.get_deposit_history()
        withdrawal_ok, withdrawals = (
            self.okx.get_withdrawal_history()
        )
        transfer_ok, transfer_bills = (
            self.okx.get_funding_transfer_bills()
        )

        if not deposit_ok:
            raise RuntimeError(str(deposits))

        if not withdrawal_ok:
            raise RuntimeError(str(withdrawals))

        if not transfer_ok:
            raise RuntimeError(str(transfer_bills))

        results: dict[str, dict[str, Any] | None] = {}

        for period_key in self.history.PERFORMANCE_PERIODS:
            snapshot = reference_snapshots.get(period_key)

            if not isinstance(snapshot, dict):
                results[period_key] = None
                continue

            results[period_key] = self._calculate_period(
                portfolio=portfolio,
                reference_snapshot=snapshot,
                period_end=period_end,
                deposits=deposits,
                withdrawals=withdrawals,
                transfer_bills=transfer_bills,
            )

        return results
