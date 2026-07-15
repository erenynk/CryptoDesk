import time

import requests

from api.okx_client import OKXClient
from database.settings_db import load_settings


class OKXService:
    MIN_DISPLAY_AMOUNT = 0.00005
    MIN_MEANINGFUL_USDT_VALUE = 0.01
    FILLS_CACHE_TTL_SECONDS = 60

    def __init__(self):
        self.client = None
        self.refresh_client()
        self.session = requests.Session()

        self._spot_symbols = set()
        self._spot_symbols_loaded = False

        self._spot_fills_cache = []
        self._spot_fills_cache_timestamp = 0.0

    def refresh_client(self):
        api, secret, passphrase = load_settings()

        if api and secret and passphrase:
            self.client = OKXClient(api, secret, passphrase)
        else:
            self.client = None

        if hasattr(self, "_spot_fills_cache"):
            self.clear_spot_fills_cache()

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
                        "funding_total": balance,
                        "trading_total": 0.0,
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
                        balances[coin]["trading_total"] += quantity
                    else:
                        balances[coin] = {
                            "total": quantity,
                            "available": available,
                            "funding_total": 0.0,
                            "trading_total": quantity,
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

                funding_amount = self._safe_float(
                    balance_data.get("funding_total")
                )
                trading_amount = self._safe_float(
                    balance_data.get("trading_total")
                )

                assets.append(
                    {
                        "coin": coin,
                        "total": total_amount,
                        "available": available_amount,
                        "funding_total": funding_amount,
                        "trading_total": trading_amount,
                        "funding_usdt_value": funding_amount * price,
                        "trading_usdt_value": trading_amount * price,
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

    def clear_spot_fills_cache(self):
        self._spot_fills_cache = []
        self._spot_fills_cache_timestamp = 0.0

    def get_spot_fills_cache_status(self):
        if not self._spot_fills_cache:
            return {
                "cached": False,
                "item_count": 0,
                "age_seconds": None,
                "ttl_seconds": self.FILLS_CACHE_TTL_SECONDS,
            }

        age = max(
            0.0,
            time.monotonic()
            - self._spot_fills_cache_timestamp,
        )

        return {
            "cached": True,
            "item_count": len(self._spot_fills_cache),
            "age_seconds": age,
            "ttl_seconds": self.FILLS_CACHE_TTL_SECONDS,
        }

    def get_spot_fills_history(
        self,
        max_pages: int = 20,
        page_limit: int = 100,
        force_refresh: bool = False,
    ):
        """
        OKX'in erişilebilir Spot işlem geçmişini sayfalı olarak döndürür.

        OKX fills-history uç noktası son 3 aylık işlemleri sağlar.
        Bu aralık açık pozisyon maliyetini doğrulamaya yetmiyorsa
        CostBasisService PNL üretmez.
        """
        if not self.client:
            return False, "API bilgileri bulunamadi."

        now = time.monotonic()
        cache_age = now - self._spot_fills_cache_timestamp

        if (
            not force_refresh
            and self._spot_fills_cache
            and cache_age < self.FILLS_CACHE_TTL_SECONDS
        ):
            return True, [
                fill.copy()
                for fill in self._spot_fills_cache
            ]

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

            self._spot_fills_cache = [
                fill.copy()
                for fill in all_fills
            ]
            self._spot_fills_cache_timestamp = (
                time.monotonic()
            )

            return True, [
                fill.copy()
                for fill in self._spot_fills_cache
            ]

        except requests.RequestException as error:
            return False, f"OKX işlem geçmişi bağlantı hatası: {error}"

        except (TypeError, ValueError) as error:
            return False, f"OKX işlem geçmişi okunamadı: {error}"

    def _get_asset_history(
        self,
        endpoint: str,
        max_pages: int = 20,
        page_limit: int = 100,
    ):
        """
        OKX Funding varlık hareketlerini sayfalı olarak okur.

        Bu yardımcı metot yatırma ve çekme geçmişi için kullanılır.
        """
        if not self.client:
            return False, "API bilgileri bulunamadi."

        all_items = []
        seen_ids = set()
        after = None

        try:
            for _ in range(max(1, max_pages)):
                query_parts = [
                    f"limit={max(1, min(page_limit, 100))}",
                ]

                if after:
                    query_parts.append(f"after={after}")

                request_path = (
                    endpoint
                    + "?"
                    + "&".join(query_parts)
                )

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
                        "OKX varlık geçmişi alınamadı.",
                    )

                page = payload.get("data", [])

                if not isinstance(page, list) or not page:
                    break

                new_count = 0

                for item in page:
                    unique_id = (
                        str(item.get("depId", "")),
                        str(item.get("wdId", "")),
                        str(item.get("txId", "")),
                        str(item.get("ts", "")),
                        str(item.get("ccy", "")),
                        str(item.get("amt", "")),
                    )

                    if unique_id in seen_ids:
                        continue

                    seen_ids.add(unique_id)
                    all_items.append(item)
                    new_count += 1

                if new_count == 0 or len(page) < page_limit:
                    break

                last_item = page[-1]
                after = (
                    str(last_item.get("depId", "")).strip()
                    or str(last_item.get("wdId", "")).strip()
                    or str(last_item.get("ts", "")).strip()
                )

                if not after:
                    break

            all_items.sort(
                key=lambda item: (
                    int(self._safe_float(item.get("ts"))),
                    str(item.get("depId", "")),
                    str(item.get("wdId", "")),
                )
            )

            return True, all_items

        except requests.RequestException as error:
            return (
                False,
                f"OKX varlık geçmişi bağlantı hatası: {error}",
            )
        except (TypeError, ValueError) as error:
            return (
                False,
                f"OKX varlık geçmişi okunamadı: {error}",
            )

    def get_deposit_history(
        self,
        max_pages: int = 20,
        page_limit: int = 100,
    ):
        return self._get_asset_history(
            endpoint="/api/v5/asset/deposit-history",
            max_pages=max_pages,
            page_limit=page_limit,
        )

    def get_withdrawal_history(
        self,
        max_pages: int = 20,
        page_limit: int = 100,
    ):
        return self._get_asset_history(
            endpoint="/api/v5/asset/withdrawal-history",
            max_pages=max_pages,
            page_limit=page_limit,
        )

    def get_historical_spot_price(
        self,
        coin: str,
        timestamp_ms: int,
    ):
        """
        Belirtilen zamana en yakın 1 dakikalık USDT spot kapanış
        fiyatını döndürür.
        """
        normalized_coin = str(coin or "").strip().upper()

        if normalized_coin in {"USDT", "USD"}:
            return True, 1.0

        if not normalized_coin:
            return False, "Geçersiz varlık."

        base_url = (
            self.client.BASE_URL
            if self.client is not None
            else "https://www.okx.com"
        )
        instrument = f"{normalized_coin}-USDT"
        target = int(timestamp_ms)

        attempts = (
            (
                target + 5 * 60 * 1000,
                target - 5 * 60 * 1000,
            ),
            (
                target + 60 * 60 * 1000,
                target - 60 * 60 * 1000,
            ),
        )

        try:
            for after_value, before_value in attempts:
                path = (
                    "/api/v5/market/history-candles"
                    f"?instId={instrument}"
                    "&bar=1m"
                    f"&after={after_value}"
                    f"&before={before_value}"
                    "&limit=100"
                )

                response = self.session.get(
                    base_url + path,
                    timeout=10,
                )
                response.raise_for_status()

                payload = response.json()

                if payload.get("code") != "0":
                    continue

                candles = payload.get("data", [])

                if not isinstance(candles, list) or not candles:
                    continue

                nearest = None
                nearest_distance = None

                for candle in candles:
                    if not isinstance(candle, list) or len(candle) < 5:
                        continue

                    candle_time = int(
                        self._safe_float(candle[0])
                    )
                    close_price = self._safe_float(
                        candle[4]
                    )

                    if candle_time <= 0 or close_price <= 0:
                        continue

                    distance = abs(candle_time - target)

                    if (
                        nearest_distance is None
                        or distance < nearest_distance
                    ):
                        nearest = close_price
                        nearest_distance = distance

                if nearest is not None:
                    return True, nearest

            return (
                False,
                f"{instrument} için tarihsel fiyat bulunamadı.",
            )

        except requests.RequestException as error:
            return (
                False,
                f"OKX tarihsel fiyat bağlantı hatası: {error}",
            )
        except (TypeError, ValueError) as error:
            return (
                False,
                f"OKX tarihsel fiyat okunamadı: {error}",
            )

    def get_funding_transfer_bills(
        self,
        max_pages: int = 20,
        page_limit: int = 100,
    ):
        """
        Funding ve Trading hesapları arasındaki transfer kayıtlarını
        Trading account bills uç noktalarından döndürür.

        Account bills kayıtları transfer yönünü açıkça `from` ve `to`
        alanlarında taşır:
        - 6: Funding
        - 18: Trading
        """
        if not self.client:
            return False, "API bilgileri bulunamadi."

        endpoints = (
            "/api/v5/account/bills",
            "/api/v5/account/bills-archive",
        )
        all_bills = []
        seen_bill_ids = set()

        try:
            for endpoint in endpoints:
                after = None

                for _ in range(max(1, max_pages)):
                    query_parts = [
                        "type=1",
                        f"limit={max(1, min(page_limit, 100))}",
                    ]

                    if after:
                        query_parts.append(f"after={after}")

                    request_path = (
                        endpoint
                        + "?"
                        + "&".join(query_parts)
                    )

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
                            "OKX transfer geçmişi alınamadı.",
                        )

                    page = payload.get("data", [])

                    if not isinstance(page, list) or not page:
                        break

                    new_count = 0

                    for bill in page:
                        from_account = str(
                            bill.get("from", "")
                        ).strip()
                        to_account = str(
                            bill.get("to", "")
                        ).strip()

                        if (
                            {from_account, to_account}
                            != {"6", "18"}
                        ):
                            continue

                        bill_id = str(
                            bill.get("billId", "")
                        ).strip()

                        if not bill_id or bill_id in seen_bill_ids:
                            continue

                        seen_bill_ids.add(bill_id)
                        all_bills.append(bill)
                        new_count += 1

                    if len(page) < page_limit:
                        break

                    after = str(
                        page[-1].get("billId", "")
                    ).strip()

                    if not after:
                        break

            all_bills.sort(
                key=lambda item: (
                    int(self._safe_float(item.get("ts"))),
                    str(item.get("billId", "")),
                )
            )

            return True, all_bills

        except requests.RequestException as error:
            return (
                False,
                f"OKX transfer geçmişi bağlantı hatası: {error}",
            )
        except (TypeError, ValueError) as error:
            return (
                False,
                f"OKX transfer geçmişi okunamadı: {error}",
            )

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
