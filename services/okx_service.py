import requests

from api.okx_client import OKXClient
from database.settings_db import load_settings


class OKXService:
    MIN_DISPLAY_AMOUNT = 0.00005
    MIN_MEANINGFUL_USDT_VALUE = 0.01

    def __init__(self):
        self.client = None
        self.refresh_client()
        self.session = requests.Session()

        self._spot_symbols = set()
        self._spot_symbols_loaded = False

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

    @staticmethod
    def _safe_float(value):
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number

        except (TypeError, ValueError, OverflowError):
            return 0.0

    @classmethod
    def _is_meaningful_asset(
        cls,
        total_amount,
        usdt_value,
    ):
        """
        Gerçek bakiyeleri korur, anlamsız hesaplama artıklarını eler.

        Miktar 0.00005 veya üzerindeyse doğrudan anlamlı kabul edilir.
        Miktar daha küçük olsa bile USDT değeri en az 0.01 ise korunur.
        Böylece çok küçük miktarda fakat değerli coinler gizlenmez.
        """
        amount = cls._safe_float(total_amount)
        value = cls._safe_float(usdt_value)

        if amount <= 0:
            return False

        return (
            amount >= cls.MIN_DISPLAY_AMOUNT
            or value >= cls.MIN_MEANINGFUL_USDT_VALUE
        )

    def _load_prices(self, cache):
        if self.client is None:
            return {}

        if cache.has() and cache.age < 15:
            return cache.get_all()

        ticker_path = "/api/v5/market/tickers?instType=SPOT"

        response = self.session.get(
            self.client.BASE_URL + ticker_path,
            timeout=10,
        )
        response.raise_for_status()

        prices = {}
        data = response.json()

        if data.get("code") == "0":
            for item in data["data"]:
                instrument = item["instId"]

                if instrument.endswith("-USDT"):
                    symbol = instrument.split("-")[0]
                    prices[symbol] = float(item["last"])

        cache.update(prices)
        return prices

    def get_spot_balances(self, cache):
        if not self.client:
            return False, "API bilgileri bulunamadi."

        try:
            balances = {}
            funding_amounts = {}
            trading_amounts = {}

            funding_path = "/api/v5/asset/balances"

            response = self.session.get(
                self.client.BASE_URL + funding_path,
                headers=self.client._headers(
                    "GET",
                    funding_path,
                ),
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") == "0":
                for asset in data.get("data", []):
                    balance = self._safe_float(
                        asset.get("bal")
                    )

                    if balance <= 0:
                        continue

                    coin = str(
                        asset.get("ccy", "")
                    ).strip().upper()

                    if not coin:
                        continue

                    available = self._safe_float(
                        asset.get("availBal")
                    )

                    funding_amounts[coin] = balance
                    balances[coin] = {
                        "total": balance,
                        "available": available,
                    }

            account_path = "/api/v5/account/balance"

            response = self.session.get(
                self.client.BASE_URL + account_path,
                headers=self.client._headers(
                    "GET",
                    account_path,
                ),
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("code") == "0":
                account_data = data.get("data", [])
                details = (
                    account_data[0].get("details", [])
                    if account_data
                    else []
                )

                for asset in details:
                    quantity = self._safe_float(
                        asset.get("eq")
                    )

                    if quantity <= 0:
                        continue

                    coin = str(
                        asset.get("ccy", "")
                    ).strip().upper()

                    if not coin:
                        continue

                    available = self._safe_float(
                        asset.get("availBal")
                    )
                    trading_amounts[coin] = quantity

                    if coin in balances:
                        balances[coin]["total"] += quantity
                        balances[coin]["available"] += available
                    else:
                        balances[coin] = {
                            "total": quantity,
                            "available": available,
                        }

            prices = self._load_prices(cache)

            assets = []
            total_usdt = 0.0
            funding_total = 0.0
            trading_total = 0.0

            for coin, balance_data in balances.items():
                price = (
                    1.0
                    if coin == "USDT"
                    else self._safe_float(
                        prices.get(coin, 0.0)
                    )
                )
                total_amount = self._safe_float(
                    balance_data.get("total")
                )
                available_amount = self._safe_float(
                    balance_data.get("available")
                )
                usdt_value = total_amount * price

                if not self._is_meaningful_asset(
                    total_amount=total_amount,
                    usdt_value=usdt_value,
                ):
                    continue

                total_usdt += usdt_value

                assets.append(
                    {
                        "coin": coin,
                        "total": total_amount,
                        "available": available_amount,
                        "price": price,
                        "usdt_value": usdt_value,
                    }
                )

            for coin, amount in funding_amounts.items():
                price = (
                    1.0
                    if coin == "USDT"
                    else self._safe_float(
                        prices.get(coin, 0.0)
                    )
                )
                funding_total += amount * price

            for coin, amount in trading_amounts.items():
                price = (
                    1.0
                    if coin == "USDT"
                    else self._safe_float(
                        prices.get(coin, 0.0)
                    )
                )
                trading_total += amount * price

            assets.sort(
                key=lambda item: item["usdt_value"],
                reverse=True,
            )

            return True, {
                "total_usdt": total_usdt,
                "funding_usdt": funding_total,
                "trading_usdt": trading_total,
                "assets": assets,
            }

        except Exception as e:
            return False, str(e)

    def get_spot_fills_history(
        self,
        max_pages: int = 20,
        page_limit: int = 100,
    ):
        """
        OKX'in erişilebilir Spot işlem geçmişini sayfalı olarak döndürür.

        OKX fills-history uç noktası son 3 aylık işlemleri sağlar.
        Bu aralık açık pozisyon maliyetini doğrulamaya yetmiyorsa
        CostBasisService PNL üretmez.
        """
        if not self.client:
            return False, "API bilgileri bulunamadi."

        path = "/api/v5/trade/fills-history"
        all_fills = []
        after = None
        seen_ids = set()

        try:
            for _ in range(max(1, max_pages)):
                query_parts = [
                    "instType=SPOT",
                    f"limit={max(1, min(page_limit, 100))}",
                ]

                if after:
                    query_parts.append(f"after={after}")

                request_path = path + "?" + "&".join(query_parts)

                response = self.session.get(
                    self.client.BASE_URL + request_path,
                    headers=self.client._headers(
                        "GET",
                        request_path,
                    ),
                    timeout=15,
                )
                response.raise_for_status()

                payload = response.json()

                if payload.get("code") != "0":
                    return False, payload.get(
                        "msg",
                        "OKX işlem geçmişi alınamadı.",
                    )

                page = payload.get("data", [])

                if not isinstance(page, list) or not page:
                    break

                new_count = 0

                for fill in page:
                    unique_id = (
                        str(fill.get("billId", "")),
                        str(fill.get("tradeId", "")),
                        str(fill.get("instId", "")),
                    )

                    if unique_id in seen_ids:
                        continue

                    seen_ids.add(unique_id)
                    all_fills.append(fill)
                    new_count += 1

                if new_count == 0 or len(page) < page_limit:
                    break

                last_item = page[-1]
                after = (
                    str(last_item.get("billId", "")).strip()
                    or str(last_item.get("tradeId", "")).strip()
                )

                if not after:
                    break

            return True, all_fills

        except requests.RequestException as error:
            return False, f"OKX işlem geçmişi bağlantı hatası: {error}"

        except (TypeError, ValueError) as error:
            return False, f"OKX işlem geçmişi okunamadı: {error}"

    def get_spot_symbols(
        self,
        force_refresh: bool = False,
    ) -> tuple[bool, set[str] | str]:
        if self._spot_symbols_loaded and not force_refresh:
            return True, self._spot_symbols.copy()

        path = "/api/v5/public/instruments?instType=SPOT"

        try:
            response = self.session.get(
                self.client.BASE_URL + path
                if self.client is not None
                else "https://www.okx.com" + path,
                timeout=10,
            )
            response.raise_for_status()

            payload = response.json()

            if payload.get("code") != "0":
                return False, payload.get(
                    "msg",
                    "OKX spot varlıkları alınamadı.",
                )

            symbols = set()

            for instrument in payload.get("data", []):
                if instrument.get("quoteCcy") != "USDT":
                    continue

                if instrument.get("state") != "live":
                    continue

                base_currency = (
                    instrument.get("baseCcy", "")
                    .strip()
                    .upper()
                )

                if base_currency:
                    symbols.add(base_currency)

            self._spot_symbols = symbols
            self._spot_symbols_loaded = True

            return True, symbols.copy()

        except requests.RequestException as error:
            return False, f"OKX bağlantı hatası: {error}"

        except (TypeError, ValueError):
            return False, "OKX varlık listesi okunamadı."

    def is_spot_symbol_available(
        self,
        symbol: str,
    ) -> tuple[bool, bool | str]:
        normalized_symbol = symbol.strip().upper()

        if not normalized_symbol:
            return True, False

        success, result = self.get_spot_symbols()

        if not success:
            return False, str(result)

        return True, normalized_symbol in result
