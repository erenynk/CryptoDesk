import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import requests

import services.okx_service as okx_service_module
from services.okx_service import OKXService


class ResponseStub:
    def __init__(
        self,
        *,
        payload=None,
        error=None,
        json_error=None,
    ):
        self.payload = payload
        self.error = error
        self.json_error = json_error

    def raise_for_status(self):
        if self.error is not None:
            raise self.error

    def json(self):
        if self.json_error is not None:
            raise self.json_error

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

    def __init__(self):
        self.header_calls = []

    def _headers(self, method, path):
        self.header_calls.append((method, path))
        return {
            "Authorization": "stub",
        }


class CacheStub:
    def __init__(
        self,
        *,
        values=None,
        has_value=False,
        age=0,
    ):
        self.values = dict(values or {})
        self.has_value = has_value
        self.age = age
        self.update_calls = []

    def has(self):
        return self.has_value

    def get_all(self):
        return self.values.copy()

    def update(self, prices):
        self.update_calls.append(
            dict(prices)
        )
        self.values = dict(prices)
        self.has_value = True


class OKXServiceTestCase(unittest.TestCase):
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

    @staticmethod
    def success_payload(instruments):
        return {
            "code": "0",
            "data": instruments,
        }

    def test_get_spot_symbols_keeps_only_live_usdt_pairs(self):
        payload = self.success_payload(
            [
                {
                    "baseCcy": "BTC",
                    "quoteCcy": "USDT",
                    "state": "live",
                },
                {
                    "baseCcy": "ETH",
                    "quoteCcy": "USDT",
                    "state": "live",
                },
                {
                    "baseCcy": "BTC",
                    "quoteCcy": "USDC",
                    "state": "live",
                },
                {
                    "baseCcy": "LTC",
                    "quoteCcy": "USDT",
                    "state": "suspend",
                },
                {
                    "baseCcy": "   ",
                    "quoteCcy": "USDT",
                    "state": "live",
                },
            ]
        )
        service = self.make_service(
            responses=[
                ResponseStub(payload=payload)
            ]
        )

        success, result = service.get_spot_symbols()

        self.assertTrue(success)
        self.assertEqual(result, {"BTC", "ETH"})
        self.assertTrue(service._spot_symbols_loaded)
        self.assertEqual(
            service._spot_symbols,
            {"BTC", "ETH"},
        )
        self.assertEqual(
            len(service.session.calls),
            1,
        )

    def test_get_spot_symbols_normalizes_base_currency(self):
        payload = self.success_payload(
            [
                {
                    "baseCcy": " btc ",
                    "quoteCcy": "USDT",
                    "state": "live",
                }
            ]
        )
        service = self.make_service(
            responses=[
                ResponseStub(payload=payload)
            ]
        )

        success, result = service.get_spot_symbols()

        self.assertTrue(success)
        self.assertEqual(result, {"BTC"})

    def test_get_spot_symbols_uses_cached_copy(self):
        payload = self.success_payload(
            [
                {
                    "baseCcy": "BTC",
                    "quoteCcy": "USDT",
                    "state": "live",
                }
            ]
        )
        service = self.make_service(
            responses=[
                ResponseStub(payload=payload)
            ]
        )

        first_success, first_result = (
            service.get_spot_symbols()
        )
        first_result.add("FAKE")

        second_success, second_result = (
            service.get_spot_symbols()
        )

        self.assertTrue(first_success)
        self.assertTrue(second_success)
        self.assertEqual(second_result, {"BTC"})
        self.assertEqual(
            len(service.session.calls),
            1,
        )

    def test_force_refresh_reloads_symbol_list(self):
        first_payload = self.success_payload(
            [
                {
                    "baseCcy": "BTC",
                    "quoteCcy": "USDT",
                    "state": "live",
                }
            ]
        )
        second_payload = self.success_payload(
            [
                {
                    "baseCcy": "ETH",
                    "quoteCcy": "USDT",
                    "state": "live",
                }
            ]
        )
        service = self.make_service(
            responses=[
                ResponseStub(payload=first_payload),
                ResponseStub(payload=second_payload),
            ]
        )

        first_success, first_result = (
            service.get_spot_symbols()
        )
        second_success, second_result = (
            service.get_spot_symbols(
                force_refresh=True
            )
        )

        self.assertTrue(first_success)
        self.assertEqual(first_result, {"BTC"})
        self.assertTrue(second_success)
        self.assertEqual(second_result, {"ETH"})
        self.assertEqual(
            len(service.session.calls),
            2,
        )

    def test_public_endpoint_works_without_api_client(self):
        payload = self.success_payload([])
        service = self.make_service(
            responses=[
                ResponseStub(payload=payload)
            ],
            authenticated=False,
        )

        success, result = service.get_spot_symbols()

        self.assertTrue(success)
        self.assertEqual(result, set())
        self.assertEqual(
            service.session.calls[0]["url"],
            (
                "https://www.okx.com"
                "/api/v5/public/instruments"
                "?instType=SPOT"
            ),
        )

    def test_get_spot_symbols_returns_api_error_message(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "50011",
                        "msg": "Rate limit",
                    }
                )
            ]
        )

        success, result = service.get_spot_symbols()

        self.assertFalse(success)
        self.assertEqual(result, "Rate limit")
        self.assertFalse(
            service._spot_symbols_loaded
        )

    def test_get_spot_symbols_handles_connection_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    error=requests.RequestException(
                        "connection lost"
                    )
                )
            ]
        )

        success, result = service.get_spot_symbols()

        self.assertFalse(success)
        self.assertIn(
            "OKX bağlantı hatası:",
            result,
        )
        self.assertIn(
            "connection lost",
            result,
        )

    def test_get_spot_symbols_handles_invalid_data(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": None,
                    }
                )
            ]
        )

        success, result = service.get_spot_symbols()

        self.assertFalse(success)
        self.assertEqual(
            result,
            "OKX varlık listesi okunamadı.",
        )

    def test_is_spot_symbol_available_normalizes_input(self):
        service = self.make_service(responses=[])
        service._spot_symbols = {"BTC", "ETH"}
        service._spot_symbols_loaded = True

        success, result = (
            service.is_spot_symbol_available(
                " btc "
            )
        )

        self.assertTrue(success)
        self.assertTrue(result)
        self.assertEqual(
            len(service.session.calls),
            0,
        )

    def test_is_spot_symbol_available_rejects_unknown_symbol(self):
        service = self.make_service(responses=[])
        service._spot_symbols = {"BTC", "ETH"}
        service._spot_symbols_loaded = True

        success, result = (
            service.is_spot_symbol_available(
                "RANDOMCOIN"
            )
        )

        self.assertTrue(success)
        self.assertFalse(result)

    def test_is_spot_symbol_available_rejects_empty_input(self):
        service = self.make_service(responses=[])

        success, result = (
            service.is_spot_symbol_available("   ")
        )

        self.assertTrue(success)
        self.assertFalse(result)
        self.assertEqual(
            len(service.session.calls),
            0,
        )

    def test_is_spot_symbol_available_propagates_load_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "50011",
                        "msg": "Rate limit",
                    }
                )
            ]
        )

        success, result = (
            service.is_spot_symbol_available("BTC")
        )

        self.assertFalse(success)
        self.assertEqual(result, "Rate limit")

    def test_meaningful_asset_accepts_amount_threshold(self):
        self.assertTrue(
            OKXService._is_meaningful_asset(
                total_amount=0.00005,
                usdt_value=0.001,
            )
        )

    def test_meaningful_asset_accepts_value_threshold(self):
        self.assertTrue(
            OKXService._is_meaningful_asset(
                total_amount=0.000001,
                usdt_value=0.01,
            )
        )

    def test_meaningful_asset_rejects_dust_below_both_limits(self):
        self.assertFalse(
            OKXService._is_meaningful_asset(
                total_amount=0.000001,
                usdt_value=0.009,
            )
        )

    def test_meaningful_asset_rejects_zero_or_negative_amount(self):
        for amount in (0, -1):
            with self.subTest(amount=amount):
                self.assertFalse(
                    OKXService._is_meaningful_asset(
                        total_amount=amount,
                        usdt_value=100,
                    )
                )


    def test_constructor_loads_client_session_and_caches(self):
        client = object()
        session = object()

        with (
            patch.object(
                okx_service_module,
                "load_settings",
                return_value=(
                    "api",
                    "secret",
                    "passphrase",
                ),
            ),
            patch.object(
                okx_service_module,
                "OKXClient",
                return_value=client,
            ) as client_factory,
            patch.object(
                okx_service_module.requests,
                "Session",
                return_value=session,
            ) as session_factory,
        ):
            service = OKXService()

        self.assertIs(service.client, client)
        self.assertIs(service.session, session)
        self.assertEqual(
            service._spot_symbols,
            set(),
        )
        self.assertFalse(
            service._spot_symbols_loaded
        )
        self.assertEqual(
            service._spot_fills_cache,
            [],
        )
        self.assertEqual(
            service._spot_fills_cache_timestamp,
            0.0,
        )
        client_factory.assert_called_once_with(
            "api",
            "secret",
            "passphrase",
        )
        session_factory.assert_called_once_with()

    def test_refresh_client_without_credentials_clears_cache(self):
        service = self.make_service(
            responses=[]
        )
        service._spot_fills_cache = [
            {
                "tradeId": "1",
            }
        ]
        service._spot_fills_cache_timestamp = 10.0

        with patch.object(
            okx_service_module,
            "load_settings",
            return_value=(
                "",
                "",
                "",
            ),
        ):
            service.refresh_client()

        self.assertIsNone(service.client)
        self.assertEqual(
            service._spot_fills_cache,
            [],
        )
        self.assertEqual(
            service._spot_fills_cache_timestamp,
            0.0,
        )

    def test_refresh_client_creates_authenticated_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )
        created_client = object()

        with (
            patch.object(
                okx_service_module,
                "load_settings",
                return_value=(
                    "api",
                    "secret",
                    "passphrase",
                ),
            ),
            patch.object(
                okx_service_module,
                "OKXClient",
                return_value=created_client,
            ) as client_factory,
        ):
            service.refresh_client()

        self.assertIs(
            service.client,
            created_client,
        )
        client_factory.assert_called_once_with(
            "api",
            "secret",
            "passphrase",
        )

    def test_check_connection_requires_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = service.check_connection()

        self.assertFalse(success)
        self.assertEqual(
            result,
            (
                "API bilgileri veritabaninda "
                "bulunamadi."
            ),
        )

    def test_check_connection_returns_account_permissions(self):
        service = self.make_service(
            responses=[]
        )
        service.client.test_connection = Mock(
            return_value=(
                200,
                {
                    "code": "0",
                    "data": [
                        {
                            "uid": "123",
                            "perm": (
                                "read,trade,withdraw"
                            ),
                        }
                    ],
                },
            )
        )

        success, result = service.check_connection()

        self.assertTrue(success)
        self.assertEqual(
            result,
            {
                "uid": "123",
                "permissions": {
                    "read": True,
                    "trade": True,
                    "withdraw": True,
                },
            },
        )

    def test_check_connection_uses_defaults_for_sparse_account(self):
        service = self.make_service(
            responses=[]
        )
        service.client.test_connection = Mock(
            return_value=(
                200,
                {
                    "code": "0",
                    "data": [{}],
                },
            )
        )

        success, result = service.check_connection()

        self.assertTrue(success)
        self.assertEqual(
            result["uid"],
            "Bilinmiyor",
        )
        self.assertEqual(
            result["permissions"],
            {
                "read": False,
                "trade": False,
                "withdraw": False,
            },
        )

    def test_check_connection_returns_api_error_and_default(self):
        cases = (
            (
                {
                    "code": "500",
                    "msg": "Denied",
                },
                "Denied",
            ),
            (
                {
                    "code": "500",
                },
                "OKX Hatasi",
            ),
        )

        for payload, expected in cases:
            with self.subTest(payload=payload):
                service = self.make_service(
                    responses=[]
                )
                service.client.test_connection = Mock(
                    return_value=(
                        400,
                        payload,
                    )
                )

                success, result = (
                    service.check_connection()
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    expected,
                )

    def test_check_connection_contains_exception(self):
        service = self.make_service(
            responses=[]
        )
        service.client.test_connection = Mock(
            side_effect=RuntimeError(
                "connection failed"
            )
        )

        success, result = service.check_connection()

        self.assertFalse(success)
        self.assertEqual(
            result,
            "connection failed",
        )

    def test_safe_float_handles_nan_and_invalid_values(self):
        self.assertEqual(
            OKXService._safe_float("nan"),
            0.0,
        )

        for value in (
            None,
            "invalid",
            object(),
        ):
            with self.subTest(value=value):
                self.assertEqual(
                    OKXService._safe_float(value),
                    0.0,
                )

        self.assertEqual(
            OKXService._safe_float("12.5"),
            12.5,
        )

    def test_load_prices_returns_empty_without_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )
        cache = CacheStub()

        result = service._load_prices(cache)

        self.assertEqual(result, {})
        self.assertEqual(
            service.session.calls,
            [],
        )

    def test_load_prices_uses_fresh_cache(self):
        service = self.make_service(
            responses=[]
        )
        cache = CacheStub(
            values={
                "BTC": 100.0,
            },
            has_value=True,
            age=14.9,
        )

        result = service._load_prices(cache)

        self.assertEqual(
            result,
            {
                "BTC": 100.0,
            },
        )
        self.assertEqual(
            service.session.calls,
            [],
        )

    def test_load_prices_fetches_and_filters_usdt_tickers(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "instId": "BTC-USDT",
                                "last": "100",
                            },
                            {
                                "instId": "ETH-USDC",
                                "last": "50",
                            },
                            {
                                "instId": "LTC-USDT",
                                "last": "25.5",
                            },
                        ],
                    }
                )
            ]
        )
        cache = CacheStub(
            has_value=True,
            age=15,
        )

        result = service._load_prices(cache)

        self.assertEqual(
            result,
            {
                "BTC": 100.0,
                "LTC": 25.5,
            },
        )
        self.assertEqual(
            cache.update_calls,
            [
                {
                    "BTC": 100.0,
                    "LTC": 25.5,
                }
            ],
        )
        self.assertEqual(
            service.session.calls[0]["kwargs"],
            {
                "timeout": 10,
            },
        )

    def test_load_prices_caches_empty_api_result(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                    }
                )
            ]
        )
        cache = CacheStub()

        result = service._load_prices(cache)

        self.assertEqual(result, {})
        self.assertEqual(
            cache.update_calls,
            [{}],
        )

    def test_get_spot_balances_requires_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = (
            service.get_spot_balances(
                CacheStub()
            )
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_get_spot_balances_combines_accounts_and_sorts_assets(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "ccy": "BTC",
                                "bal": "1",
                                "availBal": "0.8",
                            },
                            {
                                "ccy": "USDT",
                                "bal": "20",
                                "availBal": "15",
                            },
                            {
                                "ccy": "ZERO",
                                "bal": "0",
                                "availBal": "0",
                            },
                            {
                                "ccy": " ",
                                "bal": "1",
                                "availBal": "1",
                            },
                            {
                                "ccy": "DUST",
                                "bal": "0.000001",
                                "availBal": "0.000001",
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
                                        "eq": "0.5",
                                        "availBal": "0.4",
                                    },
                                    {
                                        "ccy": "ETH",
                                        "eq": "2",
                                        "availBal": "1.5",
                                    },
                                    {
                                        "ccy": "ZERO",
                                        "eq": "-1",
                                        "availBal": "0",
                                    },
                                    {
                                        "ccy": " ",
                                        "eq": "1",
                                        "availBal": "1",
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
                                "last": "100",
                            },
                            {
                                "instId": "ETH-USDT",
                                "last": "25",
                            },
                            {
                                "instId": "DUST-USDT",
                                "last": "1",
                            },
                        ],
                    }
                ),
            ]
        )
        cache = CacheStub()

        success, result = (
            service.get_spot_balances(cache)
        )

        self.assertTrue(success)
        self.assertAlmostEqual(
            result["total_usdt"],
            220.0,
        )
        self.assertAlmostEqual(
            result["funding_usdt"],
            120.000001,
        )
        self.assertAlmostEqual(
            result["trading_usdt"],
            100.0,
        )
        self.assertEqual(
            [
                item["coin"]
                for item in result["assets"]
            ],
            [
                "BTC",
                "ETH",
                "USDT",
            ],
        )

        btc = result["assets"][0]
        self.assertEqual(btc["total"], 1.5)
        self.assertAlmostEqual(
            btc["available"],
            1.2,
        )
        self.assertEqual(
            btc["funding_total"],
            1.0,
        )
        self.assertEqual(
            btc["trading_total"],
            0.5,
        )
        self.assertEqual(
            btc["funding_usdt_value"],
            100.0,
        )
        self.assertEqual(
            btc["trading_usdt_value"],
            50.0,
        )
        self.assertEqual(
            btc["usdt_value"],
            150.0,
        )

        self.assertEqual(
            len(service.session.calls),
            3,
        )
        self.assertEqual(
            service.client.header_calls,
            [
                (
                    "GET",
                    "/api/v5/asset/balances",
                ),
                (
                    "GET",
                    "/api/v5/account/balance",
                ),
            ],
        )

    def test_get_spot_balances_handles_empty_account_data(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
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
            result,
            {
                "total_usdt": 0.0,
                "funding_usdt": 0.0,
                "trading_usdt": 0.0,
                "assets": [],
            },
        )

    def test_get_spot_balances_contains_http_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    error=requests.RequestException(
                        "balance unavailable"
                    )
                )
            ]
        )

        success, result = service.get_spot_balances(
            CacheStub()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "balance unavailable",
        )

    def test_clear_and_empty_spot_fills_cache_status(self):
        service = self.make_service(
            responses=[]
        )
        service._spot_fills_cache = [
            {
                "tradeId": "1",
            }
        ]
        service._spot_fills_cache_timestamp = 5.0

        service.clear_spot_fills_cache()

        self.assertEqual(
            service._spot_fills_cache,
            [],
        )
        self.assertEqual(
            service._spot_fills_cache_timestamp,
            0.0,
        )
        self.assertEqual(
            service.get_spot_fills_cache_status(),
            {
                "cached": False,
                "item_count": 0,
                "age_seconds": None,
                "ttl_seconds": 60,
            },
        )

    def test_spot_fills_cache_status_reports_age(self):
        service = self.make_service(
            responses=[]
        )
        service._spot_fills_cache = [
            {
                "tradeId": "1",
            },
            {
                "tradeId": "2",
            },
        ]
        service._spot_fills_cache_timestamp = 110.0

        with patch.object(
            okx_service_module.time,
            "monotonic",
            return_value=100.0,
        ):
            status = (
                service
                .get_spot_fills_cache_status()
            )

        self.assertEqual(
            status,
            {
                "cached": True,
                "item_count": 2,
                "age_seconds": 0.0,
                "ttl_seconds": 60,
            },
        )

    def test_get_spot_fills_history_requires_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = (
            service.get_spot_fills_history()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_get_spot_fills_history_uses_cached_copies(self):
        service = self.make_service(
            responses=[]
        )
        service._spot_fills_cache = [
            {
                "tradeId": "1",
            }
        ]
        service._spot_fills_cache_timestamp = 100.0

        with patch.object(
            okx_service_module.time,
            "monotonic",
            return_value=120.0,
        ):
            success, result = (
                service.get_spot_fills_history()
            )

        self.assertTrue(success)
        self.assertEqual(
            result,
            [
                {
                    "tradeId": "1",
                }
            ],
        )
        self.assertIsNot(
            result[0],
            service._spot_fills_cache[0],
        )
        result[0]["tradeId"] = "changed"
        self.assertEqual(
            service._spot_fills_cache[0][
                "tradeId"
            ],
            "1",
        )

    def test_get_spot_fills_history_paginates_deduplicates_and_caches(self):
        first_page = [
            {
                "billId": "3",
                "tradeId": "t3",
                "instId": "BTC-USDT",
            },
            {
                "billId": "2",
                "tradeId": "t2",
                "instId": "ETH-USDT",
            },
        ]
        second_page = [
            first_page[1].copy(),
            {
                "billId": "1",
                "tradeId": "t1",
                "instId": "LTC-USDT",
            },
        ]
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": first_page,
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": second_page,
                    }
                ),
            ]
        )

        with patch.object(
            okx_service_module.time,
            "monotonic",
            side_effect=[
                100.0,
                101.0,
            ],
        ):
            success, result = (
                service.get_spot_fills_history(
                    max_pages=2,
                    page_limit=2,
                    force_refresh=True,
                )
            )

        self.assertTrue(success)
        self.assertEqual(
            [
                item["billId"]
                for item in result
            ],
            [
                "3",
                "2",
                "1",
            ],
        )
        self.assertEqual(
            service._spot_fills_cache_timestamp,
            101.0,
        )
        self.assertIn(
            "after=2",
            service.session.calls[1]["url"],
        )
        self.assertEqual(
            service.session.calls[0]["kwargs"][
                "timeout"
            ],
            15,
        )

    def test_get_spot_fills_history_stops_on_empty_duplicate_and_missing_cursor(self):
        cases = (
            (
                [
                    ResponseStub(
                        payload={
                            "code": "0",
                            "data": [],
                        }
                    )
                ],
                1,
            ),
            (
                [
                    ResponseStub(
                        payload={
                            "code": "0",
                            "data": [
                                {
                                    "billId": "1",
                                    "tradeId": "1",
                                    "instId": "BTC-USDT",
                                }
                            ],
                        }
                    ),
                    ResponseStub(
                        payload={
                            "code": "0",
                            "data": [
                                {
                                    "billId": "1",
                                    "tradeId": "1",
                                    "instId": "BTC-USDT",
                                }
                            ],
                        }
                    ),
                ],
                2,
            ),
            (
                [
                    ResponseStub(
                        payload={
                            "code": "0",
                            "data": [
                                {
                                    "billId": "",
                                    "tradeId": "",
                                    "instId": "BTC-USDT",
                                }
                            ],
                        }
                    )
                ],
                1,
            ),
        )

        for responses, expected_calls in cases:
            with self.subTest(
                expected_calls=expected_calls
            ):
                service = self.make_service(
                    responses=responses
                )

                success, _ = (
                    service.get_spot_fills_history(
                        max_pages=3,
                        page_limit=1,
                        force_refresh=True,
                    )
                )

                self.assertTrue(success)
                self.assertEqual(
                    len(service.session.calls),
                    expected_calls,
                )

    def test_get_spot_fills_history_returns_api_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                        "msg": "fills denied",
                    }
                )
            ]
        )

        success, result = (
            service.get_spot_fills_history(
                force_refresh=True
            )
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "fills denied",
        )

    def test_get_spot_fills_history_handles_request_and_parse_errors(self):
        cases = (
            (
                ResponseStub(
                    error=requests.RequestException(
                        "network"
                    )
                ),
                (
                    "OKX işlem geçmişi "
                    "bağlantı hatası: network"
                ),
            ),
            (
                ResponseStub(
                    json_error=ValueError(
                        "invalid json"
                    )
                ),
                (
                    "OKX işlem geçmişi "
                    "okunamadı: invalid json"
                ),
            ),
        )

        for response, expected in cases:
            with self.subTest(expected=expected):
                service = self.make_service(
                    responses=[
                        response
                    ]
                )

                success, result = (
                    service.get_spot_fills_history(
                        force_refresh=True
                    )
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    expected,
                )

    def test_asset_history_requires_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = service._get_asset_history(
            "/history"
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_asset_history_paginates_deduplicates_and_sorts(self):
        first_page = [
            {
                "depId": "2",
                "wdId": "",
                "txId": "tx2",
                "ts": "200",
                "ccy": "BTC",
                "amt": "1",
            },
            {
                "depId": "1",
                "wdId": "",
                "txId": "tx1",
                "ts": "100",
                "ccy": "ETH",
                "amt": "2",
            },
        ]
        second_page = [
            first_page[1].copy(),
            {
                "depId": "",
                "wdId": "3",
                "txId": "tx3",
                "ts": "150",
                "ccy": "LTC",
                "amt": "3",
            },
        ]
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": first_page,
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": second_page,
                    }
                ),
            ]
        )

        success, result = service._get_asset_history(
            "/history",
            max_pages=2,
            page_limit=2,
        )

        self.assertTrue(success)
        self.assertEqual(
            [
                item["ts"]
                for item in result
            ],
            [
                "100",
                "150",
                "200",
            ],
        )
        self.assertIn(
            "after=1",
            service.session.calls[1]["url"],
        )

    def test_asset_history_stops_on_empty_duplicate_and_missing_cursor(self):
        cases = (
            [
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                )
            ],
            [
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "depId": "1",
                                "ts": "1",
                            }
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "depId": "1",
                                "ts": "1",
                            }
                        ],
                    }
                ),
            ],
            [
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "depId": "",
                                "wdId": "",
                                "ts": "",
                            }
                        ],
                    }
                )
            ],
        )

        expected_calls = (
            1,
            2,
            1,
        )

        for responses, call_count in zip(
            cases,
            expected_calls,
        ):
            with self.subTest(
                call_count=call_count
            ):
                service = self.make_service(
                    responses=responses
                )

                success, _ = (
                    service._get_asset_history(
                        "/history",
                        max_pages=3,
                        page_limit=1,
                    )
                )

                self.assertTrue(success)
                self.assertEqual(
                    len(service.session.calls),
                    call_count,
                )

    def test_asset_history_returns_api_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                        "msg": "history denied",
                    }
                )
            ]
        )

        success, result = service._get_asset_history(
            "/history"
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "history denied",
        )

    def test_asset_history_handles_request_and_parse_errors(self):
        cases = (
            (
                ResponseStub(
                    error=requests.RequestException(
                        "network"
                    )
                ),
                (
                    "OKX varlık geçmişi "
                    "bağlantı hatası: network"
                ),
            ),
            (
                ResponseStub(
                    json_error=TypeError(
                        "bad json"
                    )
                ),
                (
                    "OKX varlık geçmişi "
                    "okunamadı: bad json"
                ),
            ),
        )

        for response, expected in cases:
            with self.subTest(expected=expected):
                service = self.make_service(
                    responses=[
                        response
                    ]
                )

                success, result = (
                    service._get_asset_history(
                        "/history"
                    )
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    expected,
                )

    def test_deposit_and_withdrawal_history_delegate(self):
        service = self.make_service(
            responses=[]
        )

        with patch.object(
            service,
            "_get_asset_history",
            return_value=(
                True,
                [],
            ),
        ) as get_history:
            deposit_result = (
                service.get_deposit_history(
                    max_pages=2,
                    page_limit=3,
                )
            )
            withdrawal_result = (
                service.get_withdrawal_history(
                    max_pages=4,
                    page_limit=5,
                )
            )

        self.assertEqual(
            deposit_result,
            (
                True,
                [],
            ),
        )
        self.assertEqual(
            withdrawal_result,
            (
                True,
                [],
            ),
        )
        self.assertEqual(
            get_history.call_args_list,
            [
                call(
                    endpoint=(
                        "/api/v5/asset/"
                        "deposit-history"
                    ),
                    max_pages=2,
                    page_limit=3,
                ),
                call(
                    endpoint=(
                        "/api/v5/asset/"
                        "withdrawal-history"
                    ),
                    max_pages=4,
                    page_limit=5,
                ),
            ],
        )

    def test_historical_price_returns_stablecoin_value(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        for coin in (
            "usdt",
            " USD ",
        ):
            with self.subTest(coin=coin):
                self.assertEqual(
                    service.get_historical_spot_price(
                        coin,
                        1000,
                    ),
                    (
                        True,
                        1.0,
                    ),
                )

    def test_historical_price_rejects_empty_coin(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        self.assertEqual(
            service.get_historical_spot_price(
                " ",
                1000,
            ),
            (
                False,
                "Geçersiz varlık.",
            ),
        )

    def test_historical_price_selects_nearest_valid_candle(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            "invalid",
                            [
                                "0",
                                "1",
                                "1",
                                "1",
                                "5",
                            ],
                            [
                                "900",
                                "1",
                                "1",
                                "1",
                                "0",
                            ],
                            [
                                "850",
                                "1",
                                "1",
                                "1",
                                "25",
                            ],
                            [
                                "990",
                                "1",
                                "1",
                                "1",
                                "30",
                            ],
                            [
                                "1010",
                                "1",
                                "1",
                                "1",
                                "40",
                            ],
                        ],
                    }
                ),
            ],
            authenticated=False,
        )

        success, result = (
            service.get_historical_spot_price(
                " btc ",
                1000,
            )
        )

        self.assertTrue(success)
        self.assertEqual(result, 30.0)
        self.assertEqual(
            len(service.session.calls),
            2,
        )
        self.assertTrue(
            service.session.calls[0]["url"].startswith(
                (
                    "https://www.okx.com"
                    "/api/v5/market/"
                    "history-candles"
                    "?instId=BTC-USDT"
                )
            )
        )

    def test_historical_price_returns_not_found_for_empty_attempts(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": None,
                    }
                ),
            ]
        )

        success, result = (
            service.get_historical_spot_price(
                "ETH",
                1000,
            )
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            (
                "ETH-USDT için tarihsel fiyat "
                "bulunamadı."
            ),
        )

    def test_historical_price_handles_request_and_parse_errors(self):
        cases = (
            (
                ResponseStub(
                    error=requests.RequestException(
                        "network"
                    )
                ),
                (
                    "OKX tarihsel fiyat "
                    "bağlantı hatası: network"
                ),
            ),
            (
                ResponseStub(
                    json_error=ValueError(
                        "bad json"
                    )
                ),
                (
                    "OKX tarihsel fiyat "
                    "okunamadı: bad json"
                ),
            ),
        )

        for response, expected in cases:
            with self.subTest(expected=expected):
                service = self.make_service(
                    responses=[
                        response
                    ]
                )

                success, result = (
                    service.get_historical_spot_price(
                        "BTC",
                        1000,
                    )
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    expected,
                )

    def test_transfer_bills_require_client(self):
        service = self.make_service(
            responses=[],
            authenticated=False,
        )

        success, result = (
            service.get_funding_transfer_bills()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_transfer_bills_filter_deduplicate_paginate_and_sort(self):
        current_first = [
            {
                "billId": "3",
                "from": "6",
                "to": "18",
                "ts": "300",
            },
            {
                "billId": "2",
                "from": "18",
                "to": "6",
                "ts": "200",
            },
        ]
        current_second = [
            {
                "billId": "2",
                "from": "18",
                "to": "6",
                "ts": "200",
            },
            {
                "billId": "x",
                "from": "18",
                "to": "18",
                "ts": "250",
            },
        ]
        archive_first = [
            {
                "billId": "",
                "from": "6",
                "to": "18",
                "ts": "150",
            },
            {
                "billId": "1",
                "from": "6",
                "to": "18",
                "ts": "100",
            },
        ]
        archive_second = [
            {
                "billId": "0",
                "from": "18",
                "to": "6",
                "ts": "50",
            },
        ]
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": current_first,
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": current_second,
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": archive_first,
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": archive_second,
                    }
                ),
            ]
        )

        success, result = (
            service.get_funding_transfer_bills(
                max_pages=2,
                page_limit=2,
            )
        )

        self.assertTrue(success)
        self.assertEqual(
            [
                item["billId"]
                for item in result
            ],
            [
                "0",
                "1",
                "2",
                "3",
            ],
        )
        self.assertIn(
            "after=2",
            service.session.calls[1]["url"],
        )
        self.assertIn(
            "after=1",
            service.session.calls[3]["url"],
        )

    def test_transfer_bills_stop_on_empty_short_and_missing_cursor(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "billId": "",
                                "from": "6",
                                "to": "18",
                                "ts": "1",
                            }
                        ],
                    }
                ),
            ]
        )

        success, result = (
            service.get_funding_transfer_bills(
                max_pages=3,
                page_limit=1,
            )
        )

        self.assertTrue(success)
        self.assertEqual(result, [])
        self.assertEqual(
            len(service.session.calls),
            2,
        )

    def test_transfer_bills_returns_api_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "500",
                        "msg": "bills denied",
                    }
                )
            ]
        )

        success, result = (
            service.get_funding_transfer_bills()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "bills denied",
        )

    def test_transfer_bills_handles_request_and_parse_errors(self):
        cases = (
            (
                ResponseStub(
                    error=requests.RequestException(
                        "network"
                    )
                ),
                (
                    "OKX transfer geçmişi "
                    "bağlantı hatası: network"
                ),
            ),
            (
                ResponseStub(
                    json_error=TypeError(
                        "bad json"
                    )
                ),
                (
                    "OKX transfer geçmişi "
                    "okunamadı: bad json"
                ),
            ),
        )

        for response, expected in cases:
            with self.subTest(expected=expected):
                service = self.make_service(
                    responses=[
                        response
                    ]
                )

                success, result = (
                    service
                    .get_funding_transfer_bills()
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    expected,
                )


    def test_optional_float_rejects_invalid_and_nonfinite_values(self):
        self.assertIsNone(OKXService._optional_float(None))
        self.assertIsNone(OKXService._optional_float(""))
        self.assertIsNone(OKXService._optional_float("invalid"))
        self.assertIsNone(OKXService._optional_float(float("nan")))
        self.assertIsNone(OKXService._optional_float(float("inf")))
        self.assertEqual(
            OKXService._optional_float("-1.25"),
            -1.25,
        )

    def test_get_spot_balances_exposes_okx_native_trading_pnl(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": [
                                    {
                                        "ccy": "DOGE",
                                        "eq": "100",
                                        "availBal": "80",
                                        "spotBal": "100",
                                        "openAvgPx": "0.10",
                                        "spotUpl": "2.00",
                                        "spotUplRatio": "0.20",
                                    }
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
                                "instId": "DOGE-USDT",
                                "last": "0.12",
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
        self.assertEqual(len(result["assets"]), 1)
        asset = result["assets"][0]
        self.assertEqual(
            asset["okx_trading_spot_balance"],
            100.0,
        )
        self.assertEqual(
            asset["okx_trading_average_price"],
            0.10,
        )
        self.assertEqual(
            asset["okx_trading_pnl_usdt"],
            2.0,
        )
        self.assertEqual(
            asset["okx_trading_pnl_percent"],
            20.0,
        )
        self.assertTrue(
            asset["okx_trading_pnl_available"]
        )

    def test_get_spot_balances_marks_incomplete_native_pnl_unavailable(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "details": [
                                    {
                                        "ccy": "SUI",
                                        "eq": "1",
                                        "availBal": "1",
                                        "spotBal": "",
                                        "openAvgPx": "",
                                        "spotUpl": "",
                                        "spotUplRatio": "",
                                    }
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
                                "instId": "SUI-USDT",
                                "last": "1.00",
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
        asset = result["assets"][0]
        self.assertIsNone(
            asset["okx_trading_spot_balance"]
        )
        self.assertIsNone(
            asset["okx_trading_average_price"]
        )
        self.assertIsNone(
            asset["okx_trading_pnl_usdt"]
        )
        self.assertIsNone(
            asset["okx_trading_pnl_percent"]
        )
        self.assertFalse(
            asset["okx_trading_pnl_available"]
        )



if __name__ == "__main__":
    unittest.main()
