from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable


@dataclass(frozen=True)
class CashFlow:
    """
    Portföy dışından gelen veya portföy dışına çıkan para hareketi.

    amount_usdt:
        Pozitif  -> portföye giriş
        Negatif  -> portföyden çıkış

    timestamp:
        Hareketin gerçekleştiği zaman.
    """

    amount_usdt: float
    timestamp: datetime
    description: str = ""


@dataclass(frozen=True)
class PerformanceResult:
    start_value_usdt: float
    end_value_usdt: float
    net_flow_usdt: float
    weighted_flow_usdt: float
    pnl_usdt: float
    return_percent: float | None
    period_start: datetime
    period_end: datetime
    flow_count: int


class PerformanceEngine:
    """
    Modified Dietz tabanlı performans hesaplayıcı.

    Formül:
        Getiri =
        (Bitiş Değeri - Başlangıç Değeri - Net Akış)
        /
        (Başlangıç Değeri + Ağırlıklı Akış)

    İç transferler bu motora gönderilmez.
    Yalnızca portföy dışından gelen/giden gerçek para akışları gönderilir.
    """

    EPSILON = 1e-12

    @staticmethod
    def _safe_float(value) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    @staticmethod
    def _normalize_datetime(
        value: datetime,
        reference_timezone,
    ) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=reference_timezone)

        return value.astimezone(reference_timezone)

    @classmethod
    def calculate(
        cls,
        start_value_usdt: float,
        end_value_usdt: float,
        period_start: datetime,
        period_end: datetime,
        cash_flows: Iterable[CashFlow] = (),
    ) -> PerformanceResult:
        if period_start.tzinfo is None and period_end.tzinfo is None:
            timezone_info = None
        else:
            timezone_info = (
                period_start.tzinfo
                or period_end.tzinfo
            )

        if timezone_info is not None:
            start_time = cls._normalize_datetime(
                period_start,
                timezone_info,
            )
            end_time = cls._normalize_datetime(
                period_end,
                timezone_info,
            )
        else:
            start_time = period_start
            end_time = period_end

        duration_seconds = (
            end_time - start_time
        ).total_seconds()

        if duration_seconds <= 0:
            raise ValueError(
                "period_end, period_start değerinden sonra olmalıdır."
            )

        start_value = cls._safe_float(start_value_usdt)
        end_value = cls._safe_float(end_value_usdt)

        normalized_flows = []

        for flow in cash_flows:
            if not isinstance(flow, CashFlow):
                continue

            flow_time = flow.timestamp

            if timezone_info is not None:
                flow_time = cls._normalize_datetime(
                    flow_time,
                    timezone_info,
                )

            if flow_time < start_time or flow_time > end_time:
                continue

            amount = cls._safe_float(
                flow.amount_usdt
            )

            if abs(amount) <= cls.EPSILON:
                continue

            normalized_flows.append(
                CashFlow(
                    amount_usdt=amount,
                    timestamp=flow_time,
                    description=flow.description,
                )
            )

        net_flow = sum(
            flow.amount_usdt
            for flow in normalized_flows
        )

        weighted_flow = 0.0

        for flow in normalized_flows:
            remaining_seconds = (
                end_time - flow.timestamp
            ).total_seconds()

            weight = max(
                0.0,
                min(
                    1.0,
                    remaining_seconds
                    / duration_seconds,
                ),
            )

            weighted_flow += (
                flow.amount_usdt * weight
            )

        pnl_usdt = (
            end_value
            - start_value
            - net_flow
        )

        denominator = (
            start_value
            + weighted_flow
        )

        if denominator <= cls.EPSILON:
            return_percent = None
        else:
            return_percent = (
                pnl_usdt
                / denominator
            ) * 100

        return PerformanceResult(
            start_value_usdt=start_value,
            end_value_usdt=end_value,
            net_flow_usdt=net_flow,
            weighted_flow_usdt=weighted_flow,
            pnl_usdt=pnl_usdt,
            return_percent=(
                round(return_percent, 8)
                if return_percent is not None
                else None
            ),
            period_start=start_time,
            period_end=end_time,
            flow_count=len(normalized_flows),
        )
