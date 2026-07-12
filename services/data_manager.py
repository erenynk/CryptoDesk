from typing import Any

from PySide6.QtCore import QObject, Signal

from services.okx_service import OKXService
from services.portfolio_history_service import PortfolioHistoryService
from services.price_cache import PriceCache


class DataManager(QObject):
    portfolio_updated = Signal(dict)
    portfolio_error = Signal(str)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        super().__init__()

        self._initialized = True

        self.cache = PriceCache()
        self.okx = OKXService()
        self.portfolio_history = PortfolioHistoryService()

        self.portfolio = None
        self.last_error = None
        self.loading = False

    def refresh_client(self):
        self.okx.refresh_client()

    def refresh_portfolio(self):
        if self.loading:
            return False, "Loading"

        self.loading = True

        try:
            ok, result = self.okx.get_spot_balances(self.cache)

            if ok:
                self._save_portfolio_snapshot(result)

                self.portfolio = result
                self.last_error = None
                self.portfolio_updated.emit(result)
            else:
                self.last_error = result
                self.portfolio_error.emit(str(result))

            return ok, result

        except Exception as e:
            self.last_error = str(e)
            self.portfolio_error.emit(str(e))
            return False, str(e)

        finally:
            self.loading = False

    def _save_portfolio_snapshot(self, portfolio: dict[str, Any]) -> None:
        """
        Başarılı portföy yenilemesinden sonra geçmiş kaydı oluşturur.

        Snapshot hataları ana portföy yenilemesini bozmaz. Geçmiş servisinde
        oluşabilecek geçici SQLite hataları kullanıcıya portföy hatası olarak
        yansıtılmaz.
        """
        try:
            total_usdt = self._extract_float(
                portfolio,
                "total_usdt",
                "total_value",
                "total_balance",
                "total",
            )
            funding_usdt = self._extract_float(
                portfolio,
                "funding_usdt",
                "funding_value",
                "funding_balance",
                "funding",
            )
            trading_usdt = self._extract_float(
                portfolio,
                "trading_usdt",
                "trading_value",
                "trading_balance",
                "trading",
            )
            asset_count = self._extract_asset_count(portfolio)

            self.portfolio_history.save_snapshot(
                total_usdt=total_usdt,
                funding_usdt=funding_usdt,
                trading_usdt=trading_usdt,
                asset_count=asset_count,
            )
        except Exception:
            pass

    @staticmethod
    def _extract_float(
        source: dict[str, Any],
        *keys: str,
    ) -> float:
        for key in keys:
            if key not in source:
                continue

            value = source.get(key)

            if isinstance(value, dict):
                for nested_key in (
                    "total_usdt",
                    "value",
                    "balance",
                    "total",
                    "usdt",
                ):
                    if nested_key in value:
                        value = value.get(nested_key)
                        break

            try:
                number = float(value)

                if number == number:
                    return number
            except (TypeError, ValueError, OverflowError):
                continue

        return 0.0

    @staticmethod
    def _extract_asset_count(portfolio: dict[str, Any]) -> int:
        for key in (
            "assets",
            "balances",
            "coins",
            "holdings",
            "items",
        ):
            value = portfolio.get(key)

            if isinstance(value, (list, tuple, set, dict)):
                return len(value)

        for key in (
            "asset_count",
            "coin_count",
            "count",
        ):
            try:
                return max(0, int(portfolio.get(key, 0)))
            except (TypeError, ValueError, OverflowError):
                continue

        return 0

    def get_portfolio(self):
        return self.portfolio

    def get_price(self, coin):
        return self.cache.get(coin)

    def get_prices(self):
        return self.cache.get_all()

    def clear_cache(self):
        self.cache.clear()

    def reconnect(self):
        self.refresh_client()
        self.clear_cache()
