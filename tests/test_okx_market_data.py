import unittest

import requests

from services.okx_service import OKXService


class ResponseStub:
    def __init__(
        self,
        *,
        payload=None,
        error=None,
    ):
        self.payload = payload
        self.error = error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        return self.payload


class SessionStub:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(
            {
                "url": url,
                "kwargs": kwargs,
            }
        )

        if not self.responses:
            raise AssertionError(
                "Beklenmeyen ek HTTP çağrısı yapıldı."
            )

        return self.responses.pop(0)


class ClientStub:
    BASE_URL = "https://www.okx.com"

    @staticmethod
    def _headers(method, path):
        return {
            "X-Test-Method": method,
            "X-Test-Path": path,
        }


class CacheStub:
    def __init__(
        self,
        *,
        prices=None,
        age=0.0,
        available=False,
    ):
        self.prices = dict(prices or {})
        self.age = age
        self.available = available
        self.update_calls = []

    def has(self):
        return self.available

    def get_all(self):
        return self.prices.copy()

    def update(self, prices):
        copied = dict(prices)
        self.prices = copied
        self.available = bool(copied)
        self.age = 0.0
        self.update_calls.append(copied)


class OKXMarketDataTestCase(unittest.TestCase):
    @staticmethod
    def make_service(
        *,
        responses,
        authenticated=True,
    ):
        service = object.__new__(OKXService)
        service.client = (
            ClientStub()
            if authenticated
            else None
        )
        service.session = SessionStub(responses)
        service._spot_symbols = set()
        service._spot_symbols_loaded = False
        service._spot_fills_cache = []
        service._spot_fills_cache_timestamp = 0.0
        return service

    def test_load_prices_uses_fresh_cache_without_http(self):
        service = self.make_service(responses=[])
        cache = CacheStub(
            prices={
                "BTC": 65000.0,
                "ETH": 3500.0,
            },
            age=10.0,
            available=True,
        )

        result = service._load_prices(cache)

        self.assertEqual(
            result,
            {
                "BTC": 65000.0,
                "ETH": 3500.0,
            },
        )
        self.assertEqual(service.session.calls, [])
        self.assertEqual(cache.update_calls, [])

    def test_load_prices_refreshes_expired_cache(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT",
                                "last": "65000.5",
                            },
                            {
                                "instId": "ETH-USDT",
                                "last": "3500.25",
                            },
                        ],
                    }
                )
            ]
        )
        cache = CacheStub(
            prices={
                "BTC": 1.0,
            },
            age=15.0,
            available=True,
        )

        result = service._load_prices(cache)

        self.assertEqual(
            result,
            {
                "BTC": 65000.5,
                "ETH": 3500.25,
            },
        )
        self.assertEqual(
            cache.update_calls,
            [
                {
                    "BTC": 65000.5,
                    "ETH": 3500.25,
                }
            ],
        )
        self.assertEqual(
            len(service.session.calls),
            1,
        )

    def test_load_prices_keeps_only_usdt_pairs(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT",
                                "last": "65000",
                            },
                            {
                                "instId": "BTC-USDC",
                                "last": "65010",
                            },
                            {
                                "instId": "ETH-BTC",
                                "last": "0.05",
                            },
                        ],
                    }
                )
            ]
        )
        cache = CacheStub()

        result = service._load_prices(cache)

        self.assertEqual(
            result,
            {
                "BTC": 65000.0,
            },
        )

    def test_load_prices_returns_empty_without_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )
        cache = CacheStub()

        result = service._load_prices(cache)

        self.assertEqual(result, {})
        self.assertEqual(service.session.calls, [])

    def test_get_spot_balances_requires_api_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_get_spot_balances_merges_accounts_and_values(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "ccy": "BTC",
                                "bal": "0.01",
                                "availBal": "0.009",
                            },
                            {
                                "ccy": "USDT",
                                "bal": "50",
                                "availBal": "50",
                            },
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": [
                                    {
                                        "ccy": "BTC",
                                        "eq": "0.02",
                                        "availBal": "0.015",
                                    },
                                    {
                                        "ccy": "ETH",
                                        "eq": "1",
                                        "availBal": "0.8",
                                    },
                                ]
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT",
                                "last": "60000",
                            },
                            {
                                "instId": "ETH-USDT",
                                "last": "3000",
                            },
                        ],
                    }
                ),
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertTrue(success)
        self.assertEqual(
            result["total_usdt"],
            4850.0,
        )
        self.assertEqual(
            result["funding_usdt"],
            650.0,
        )
        self.assertEqual(
            result["trading_usdt"],
            4200.0,
        )

        assets = result["assets"]

        self.assertEqual(
            [
                asset["coin"]
                for asset in assets
            ],
            ["ETH", "BTC", "USDT"],
        )

        btc = next(
            asset
            for asset in assets
            if asset["coin"] == "BTC"
        )

        self.assertEqual(btc["total"], 0.03)
        self.assertEqual(btc["available"], 0.024)
        self.assertEqual(
            btc["funding_total"],
            0.01,
        )
        self.assertEqual(
            btc["trading_total"],
            0.02,
        )
        self.assertEqual(
            btc["funding_usdt_value"],
            600.0,
        )
        self.assertEqual(
            btc["trading_usdt_value"],
            1200.0,
        )
        self.assertEqual(
            btc["usdt_value"],
            1800.0,
        )

    def test_get_spot_balances_filters_worthless_dust(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "ccy": "DUST",
                                "bal": "0.000001",
                                "availBal": "0.000001",
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": []
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "DUST-USDT",
                                "last": "0.001",
                            }
                        ],
                    }
                ),
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertTrue(success)
        self.assertEqual(result["assets"], [])
        self.assertEqual(
            result["total_usdt"],
            0.0,
        )

    def test_get_spot_balances_keeps_tiny_but_valuable_asset(
        self,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "ccy": "VALUABLE",
                                "bal": "0.000001",
                                "availBal": "0.000001",
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": []
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "VALUABLE-USDT",
                                "last": "20000",
                            }
                        ],
                    }
                ),
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertTrue(success)
        self.assertEqual(
            len(result["assets"]),
            1,
        )
        self.assertEqual(
            result["assets"][0]["coin"],
            "VALUABLE",
        )
        self.assertEqual(
            result["assets"][0]["usdt_value"],
            0.02,
        )

    def test_get_spot_balances_uses_one_dollar_for_usdt(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "ccy": "USDT",
                                "bal": "123.45",
                                "availBal": "120",
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": []
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                ),
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertTrue(success)
        self.assertEqual(
            result["total_usdt"],
            123.45,
        )
        self.assertEqual(
            result["funding_usdt"],
            123.45,
        )
        self.assertEqual(
            result["trading_usdt"],
            0.0,
        )
        self.assertEqual(
            result["assets"][0]["price"],
            1.0,
        )

    def test_get_spot_balances_returns_connection_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    error=requests.RequestException(
                        "connection lost"
                    )
                )
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertFalse(success)
        self.assertIn(
            "connection lost",
            result,
        )


if __name__ == "__main__":
    unittest.main()
