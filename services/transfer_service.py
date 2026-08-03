from datetime import datetime, timedelta
from typing import Any


class TransferService:
    """
    Funding hesabındaki iç transfer hareketlerini dönemsel USDT
    düzeltmelerine dönüştürür.

    Pozitif değer Funding hesabına net giriş, negatif değer Funding
    hesabından net çıkış anlamına gelir. Trading hesabı için aynı
    hareketin işareti tersidir.
    """

    PERIODS = {
        "1d": timedelta(days=1),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
        "90d": timedelta(days=90),
        "1y": timedelta(days=365),
    }

    def __init__(self, app_timezone):
        self.app_timezone = app_timezone

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
        timestamp_ms = self._safe_float(
            bill.get("ts")
        )

        if timestamp_ms <= 0:
            return None

        try:
            return datetime.fromtimestamp(
                timestamp_ms / 1000,
                tz=self.app_timezone,
            )
        except (OSError, OverflowError, ValueError):
            return None

    def calculate_reference_adjustments(
        self,
        bills: list[dict[str, Any]],
        prices: dict[str, float],
        reference_times: dict[str, datetime | None],
        current_time: datetime,
    ) -> dict[str, float]:
        """
        Her dönem için seçilen gerçek snapshot zamanı ile şu an
        arasındaki Funding net transferini USDT cinsinden hesaplar.

        Böylece sabit 24 saatlik pencere yerine performans hesabında
        kullanılan snapshot ile aynı zaman aralığı kullanılır.
        """
        normalized_current = (
            current_time
            if current_time.tzinfo is not None
            else current_time.replace(
                tzinfo=self.app_timezone
            )
        ).astimezone(self.app_timezone)

        normalized_references: dict[str, datetime | None] = {}

        for period in self.PERIODS:
            value = reference_times.get(period)

            if value is None:
                normalized_references[period] = None
                continue

            normalized_references[period] = (
                value
                if value.tzinfo is not None
                else value.replace(
                    tzinfo=self.app_timezone
                )
            ).astimezone(self.app_timezone)

        adjustments = {
            period: 0.0
            for period in self.PERIODS
        }

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

            bill_time = self._bill_datetime(bill)

            if bill_time is None or bill_time > normalized_current:
                continue

            currency = str(
                bill.get("ccy", "")
            ).strip().upper()

            if not currency:
                continue

            amount = abs(
                self._safe_float(
                    bill.get("balChg")
                )
            )

            if amount <= 0:
                amount = abs(
                    self._safe_float(
                        bill.get("sz")
                    )
                )

            if amount <= 0:
                continue

            price = (
                1.0
                if currency == "USDT"
                else self._safe_float(
                    prices.get(currency, 0.0)
                )
            )

            if price <= 0:
                continue

            transfer_value_usdt = amount * price

            if from_account == "18" and to_account == "6":
                funding_change = transfer_value_usdt
            else:
                funding_change = -transfer_value_usdt

            for period, reference_time in (
                normalized_references.items()
            ):
                if reference_time is None:
                    continue

                if reference_time < bill_time <= normalized_current:
                    adjustments[period] += funding_change

        return {
            period: round(value, 8)
            for period, value in adjustments.items()
        }

    def calculate_period_adjustments(
        self,
        bills: list[dict[str, Any]],
        prices: dict[str, float],
        reference_time: datetime,
    ) -> dict[str, float]:
        """
        Her dönem için Funding hesabına net transfer girişini USDT
        cinsinden hesaplar.

        Funding asset bill kayıtlarındaki balChg:
        - pozitif: Funding hesabına giriş
        - negatif: Funding hesabından çıkış
        """
        normalized_time = (
            reference_time
            if reference_time.tzinfo is not None
            else reference_time.replace(
                tzinfo=self.app_timezone
            )
        )
        normalized_time = normalized_time.astimezone(
            self.app_timezone
        )

        adjustments = {
            period: 0.0
            for period in self.PERIODS
        }

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

            bill_time = self._bill_datetime(bill)

            if bill_time is None or bill_time > normalized_time:
                continue

            currency = str(
                bill.get("ccy", "")
            ).strip().upper()

            if not currency:
                continue

            amount = abs(
                self._safe_float(
                    bill.get("balChg")
                )
            )

            if amount <= 0:
                amount = abs(
                    self._safe_float(
                        bill.get("sz")
                    )
                )

            if amount <= 0:
                continue

            price = (
                1.0
                if currency == "USDT"
                else self._safe_float(
                    prices.get(currency, 0.0)
                )
            )

            if price <= 0:
                continue

            transfer_value_usdt = amount * price

            # Funding'e giriş pozitif, Funding'den çıkış negatif.
            if from_account == "18" and to_account == "6":
                funding_change = transfer_value_usdt
            else:
                funding_change = -transfer_value_usdt

            age = normalized_time - bill_time

            for period, duration in self.PERIODS.items():
                if timedelta(0) <= age <= duration:
                    adjustments[period] += funding_change

        return {
            period: round(value, 8)
            for period, value in adjustments.items()
        }
