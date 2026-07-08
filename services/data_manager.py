from PySide6.QtCore import QObject, Signal

from services.okx_service import OKXService
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
                self.portfolio = result
                self.last_error = None
                self.portfolio_updated.emit(result)
            else:
                self.last_error = result
                self.portfolio_error.emit(str(result))

            return ok, result

        finally:
            self.loading = False

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