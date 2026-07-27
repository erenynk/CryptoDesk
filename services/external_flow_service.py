from __future__ import annotations

from datetime import datetime
from typing import Any

from services.performance_engine import CashFlow


class ExternalFlowService:
    """
    OKX yatırma ve çekme geçmişini PerformanceEngine CashFlow
    kayıtlarına dönüştürür.
    """

    COMPLETED_STATE = "2"

    def __init__(self, okx_service, app_timezone):
        self.okx = okx_service
        self.app_timezone = app_timezone
        self._price_cache: dict[tuple[str, int], float] = {}

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    def _timestamp_to_datetime(
        self,
        timestamp_ms: Any,
    ) -> datetime | None:
        value = int(self._safe_float(timestamp_ms))

        if value <= 0:
            return None

        try:
            return datetime.fromtimestamp(
                value / 1000,
                tz=self.app_timezone,
            )
        except (OSError, OverflowError, ValueError):
            return None

    def _price_at(
        self,
        coin: str,
        timestamp_ms: int,
    ) -> float | None:
        normalized_coin = str(coin or "").strip().upper()

        if normalized_coin in {"USDT", "USD"}:
            return 1.0

        # Aynı dakika için tekrar API çağrısı yapma.
        minute_bucket = timestamp_ms // 60000
        cache_key = (normalized_coin, minute_bucket)

        if cache_key in self._price_cache:
            return self._price_cache[cache_key]

        success, result = self.okx.get_historical_spot_price(
            coin=normalized_coin,
            timestamp_ms=timestamp_ms,
        )

        if not success:
            return None

        price = self._safe_float(result)

        if price <= 0:
            return None

        self._price_cache[cache_key] = price
        return price

    def build_cash_flows(
        self,
        deposits: list[dict[str, Any]],
        withdrawals: list[dict[str, Any]],
        period_start: datetime,
        period_end: datetime,
    ) -> tuple[list[CashFlow], list[dict[str, Any]]]:
        flows: list[CashFlow] = []
        skipped: list[dict[str, Any]] = []

        records = [
            ("deposit", item)
            for item in deposits
        ] + [
            ("withdrawal", item)
            for item in withdrawals
        ]

        for flow_type, item in records:
            if str(item.get("state", "")).strip() != self.COMPLETED_STATE:
                continue

            flow_time = self._timestamp_to_datetime(
                item.get("ts")
            )

            if flow_time is None:
                skipped.append({
                    "type": flow_type,
                    "reason": "invalid_timestamp",
                    "item": item,
                })
                continue

            if flow_time < period_start or flow_time > period_end:
                continue

            coin = str(
                item.get("ccy", "")
            ).strip().upper()
            amount = abs(
                self._safe_float(
                    item.get("amt")
                )
            )

            if not coin or amount <= 0:
                skipped.append({
                    "type": flow_type,
                    "reason": "invalid_amount_or_coin",
                    "item": item,
                })
                continue

            timestamp_ms = int(
                self._safe_float(
                    item.get("ts")
                )
            )
            price = self._price_at(
                coin=coin,
                timestamp_ms=timestamp_ms,
            )

            if price is None:
                skipped.append({
                    "type": flow_type,
                    "reason": "historical_price_unavailable",
                    "item": item,
                })
                continue

            amount_usdt = amount * price

            if flow_type == "withdrawal":
                amount_usdt = -amount_usdt

            flows.append(
                CashFlow(
                    amount_usdt=amount_usdt,
                    timestamp=flow_time,
                    description=(
                        f"{flow_type}:{coin}:{amount}"
                    ),
                )
            )

        flows.sort(key=lambda flow: flow.timestamp)
        return flows, skipped
