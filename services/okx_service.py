import requests

from api.okx_client import OKXClient
from database.settings_db import load_settings


class OKXService:
    def __init__(self):
        self.client = None
        self.refresh_client()
        self.session = requests.Session()

    def refresh_client(self):
        api, secret, passphrase = load_settings()

        if api and secret and passphrase:
            self.client = OKXClient(api, secret, passphrase)
        else:
            self.client = None

    def check_connection(self):
        if not self.client:
            return False, "API bilgileri veritabaninda bulunamadi."

        try:
            status, data = self.client.test_connection()

            if status == 200 and data.get("code") == "0":
                account = data.get("data", [{}])[0]

                uid = account.get("uid", "Bilinmiyor")
                perm = account.get("perm", "")

                permissions = {
                    "read": "read" in perm,
                    "trade": "trade" in perm,
                    "withdraw": "withdraw" in perm,
                }

                return True, {
                    "uid": uid,
                    "permissions": permissions,
                }

            return False, data.get("msg", "OKX Hatasi")

        except Exception as e:
            return False, str(e)

    # ---------------------------------------------------------
    # INTERNAL
    # ---------------------------------------------------------

    def _load_prices(self, cache):
        if self.client is None:
            return {}
        
        
        """
        Tüm spot fiyatlarını tek sefer çeker.
        """

        if cache.has() and cache.age < 15:
            return cache.get_all()

        ticker_path = "/api/v5/market/tickers?instType=SPOT"

        r = self.session.get(
            self.client.BASE_URL + ticker_path,
            timeout=10,
        )
        r.raise_for_status()

        prices = {}

        data = r.json()

        if data.get("code") == "0":

            for item in data["data"]:
            

                inst = item["instId"]

                if inst.endswith("-USDT"):
                    symbol = inst.split("-")[0]
                    prices[symbol] = float(item["last"])

        cache.update(prices)

        return prices

    # ---------------------------------------------------------
    # PORTFOLIO
    # ---------------------------------------------------------

    def get_spot_balances(self, cache):
        if not self.client:
            return False, "API bilgileri bulunamadi."

        try:

            balances = {}

            #
            # FUNDING
            #

            funding_path = "/api/v5/asset/balances"

            r = self.session.get(
                self.client.BASE_URL + funding_path,
                headers=self.client._headers("GET", funding_path),
                timeout=10,
            )
            r.raise_for_status()

            data = r.json()

            if data.get("code") == "0":

                

                for asset in r.json()["data"]:

                    bal = float(asset["bal"])

                    if bal <= 0:
                        continue

                    balances[asset["ccy"]] = {
                        "total": bal,
                        "available": float(asset["availBal"]),
                    }

            #
            # TRADING
            #

            account_path = "/api/v5/account/balance"

            r = self.session.get(
                self.client.BASE_URL + account_path,
                headers=self.client._headers("GET", account_path),
                timeout=10,
            )
            r.raise_for_status()

            data = r.json()

            if data.get("code") == "0":

                

                details = data["data"][0]["details"]

                for asset in details:

                    qty = float(asset["eq"])

                    if qty <= 0:
                        continue

                    coin = asset["ccy"]

                    if coin in balances:

                        balances[coin]["total"] += qty
                        balances[coin]["available"] += float(asset["availBal"])

                    else:

                        balances[coin] = {
                            "total": qty,
                            "available": float(asset["availBal"]),
                        }

            #
            # PRICE CACHE
            #

            prices = self._load_prices(cache)

            assets = []

            total = 0.0

            for coin, data in balances.items():

                if coin == "USDT":
                    price = 1.0
                else:
                    price = prices.get(coin, 0)

                usdt = data["total"] * price

                total += usdt

                assets.append(
                    {
                        "coin": coin,
                        "total": data["total"],
                        "available": data["available"],
                        "price": price,
                        "usdt_value": usdt,
                    }
                )

            assets.sort(
                key=lambda x: x["usdt_value"],
                reverse=True,
            )

            return True, {
                "total_usdt": total,
                "assets": assets,
            }

        except Exception as e:
            return False, str(e)