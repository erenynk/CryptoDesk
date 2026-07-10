from threading import RLock
from time import time


class PriceCache:
    """
    Bellekte fiyat cache'i.

    Amaç:
    - Aynı fiyatları tekrar tekrar API'den çekmemek.
    - Dashboard, Portfolio ve Watchlist'in aynı veriyi kullanmasını sağlamak.
    """

    def __init__(self):
        self._lock = RLock()
        self._prices = {}
        self._last_update = 0

    def clear(self):
        with self._lock:
            self._prices.clear()
            self._last_update = 0

    def update(self, prices: dict):
        """
        prices örneği:

        {
            "BTC": 109243.5,
            "ETH": 3890.2,
            ...
        }
        """
        with self._lock:
            self._prices = dict(prices)
            self._last_update = time()

    def get(self, coin: str, default=0.0):
        with self._lock:
            return self._prices.get(coin.upper(), default)

    def get_all(self):
        with self._lock:
            return dict(self._prices)

    def has(self):
        with self._lock:
            return bool(self._prices)

    @property
    def last_update(self):
        with self._lock:
            return self._last_update

    @property
    def age(self):
        with self._lock:
            if self._last_update == 0:
                return float("inf")
            return time() - self._last_update