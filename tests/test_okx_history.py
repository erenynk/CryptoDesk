import unittest
from unittest.mock import patch

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


class OKXHistoryTestCase(unittest.TestCase):
    @staticmethod
    def make_service(
        *,
        responses=None,
        authenticated=True,
    ):
        service = object.__new__(OKXService)
        service.client = (
            ClientStub()
            if authenticated
            else None
        )
        service.session = SessionStub(
            responses or []
        )
        service._spot_symbols = set()
        service._spot_symbols_loaded = False
        service._spot_fills_cache = []
        service._spot_fills_cache_timestamp = 0.0
        return service

    def test_spot_fills_requires_api_client(self):
        service = self.make_service(
            authenticated=False
        )

        success, result = (
            service.get_spot_fills_history()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    @patch(
        "services.okx_service.time.monotonic",
        side_effect=[
            1000.0,
            1000.0,
        ],
    )
    def test_spot_fills_reads_and_caches_result(
        self,
        mocked_monotonic,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "billId": "2",
                                "tradeId": "20",
                                "instId": "ETH-USDT",
                            },
                            {
                                "billId": "1",
                                "tradeId": "10",
                                "instId": "BTC-USDT",
                            },
                        ],
                    }
                )
            ]
        )

        success, result = (
            service.get_spot_fills_history(
                page_limit=100
            )
        )

        self.assertTrue(success)
        self.assertEqual(len(result), 2)
        self.assertEqual(
            service._spot_fills_cache,
            result,
        )
        self.assertEqual(
            service._spot_fills_cache_timestamp,
            1000.0,
        )
        self.assertEqual(
            len(service.session.calls),
            1,
        )
        self.assertEqual(
            mocked_monotonic.call_count,
            2,
        )

    @patch(
        "services.okx_service.time.monotonic",
        return_value=1030.0,
    )
    def test_spot_fills_uses_fresh_cache_copy(
        self,
        mocked_monotonic,
    ):
        service = self.make_service()
        service._spot_fills_cache = [
            {
                "billId": "1",
                "tradeId": "10",
                "instId": "BTC-USDT",
            }
        ]
        service._spot_fills_cache_timestamp = 1000.0

        success, result = (
            service.get_spot_fills_history()
        )

        self.assertTrue(success)
        self.assertEqual(
            result,
            service._spot_fills_cache,
        )
        self.assertIsNot(
            result,
            service._spot_fills_cache,
        )

        result[0]["billId"] = "changed"

        self.assertEqual(
            service._spot_fills_cache[0][
                "billId"
            ],
            "1",
        )
        self.assertEqual(
            service.session.calls,
            [],
        )
        mocked_monotonic.assert_called_once_with()

    @patch(
        "services.okx_service.time.monotonic",
        side_effect=[
            1100.0,
            1100.0,
        ],
    )
    def test_force_refresh_bypasses_fills_cache(
        self,
        mocked_monotonic,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "billId": "2",
                                "tradeId": "20",
                                "instId": "ETH-USDT",
                            }
                        ],
                    }
                )
            ]
        )
        service._spot_fills_cache = [
            {
                "billId": "1",
                "tradeId": "10",
                "instId": "BTC-USDT",
            }
        ]
        service._spot_fills_cache_timestamp = 1090.0

        success, result = (
            service.get_spot_fills_history(
                force_refresh=True
            )
        )

        self.assertTrue(success)
        self.assertEqual(
            result[0]["billId"],
            "2",
        )
        self.assertEqual(
            len(service.session.calls),
            1,
        )
        self.assertEqual(
            mocked_monotonic.call_count,
            2,
        )

    def test_spot_fills_paginates_and_removes_duplicates(
        self,
    ):
        first_page = [
            {
                "billId": "3",
                "tradeId": "30",
                "instId": "SOL-USDT",
            },
            {
                "billId": "2",
                "tradeId": "20",
                "instId": "ETH-USDT",
            },
        ]
        second_page = [
            {
                "billId": "2",
                "tradeId": "20",
                "instId": "ETH-USDT",
            },
            {
                "billId": "1",
                "tradeId": "10",
                "instId": "BTC-USDT",
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
            ["3", "2", "1"],
        )
        self.assertEqual(
            len(service.session.calls),
            2,
        )
        self.assertIn(
            "after=2",
            service.session.calls[1]["url"],
        )

    def test_spot_fills_returns_api_error(self):
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
            service.get_spot_fills_history(
                force_refresh=True
            )
        )

        self.assertFalse(success)
        self.assertEqual(result, "Rate limit")

    def test_spot_fills_returns_connection_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    error=requests.RequestException(
                        "connection lost"
                    )
                )
            ]
        )

        success, result = (
            service.get_spot_fills_history(
                force_refresh=True
            )
        )

        self.assertFalse(success)
        self.assertIn(
            "OKX işlem geçmişi bağlantı hatası:",
            result,
        )
        self.assertIn(
            "connection lost",
            result,
        )

    def test_deposit_history_uses_correct_endpoint(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                )
            ]
        )

        success, result = (
            service.get_deposit_history()
        )

        self.assertTrue(success)
        self.assertEqual(result, [])
        self.assertIn(
            "/api/v5/asset/deposit-history",
            service.session.calls[0]["url"],
        )

    def test_withdrawal_history_uses_correct_endpoint(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [],
                    }
                )
            ]
        )

        success, result = (
            service.get_withdrawal_history()
        )

        self.assertTrue(success)
        self.assertEqual(result, [])
        self.assertIn(
            "/api/v5/asset/withdrawal-history",
            service.session.calls[0]["url"],
        )

    def test_asset_history_paginates_deduplicates_and_sorts(
        self,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "depId": "2",
                                "wdId": "",
                                "txId": "tx2",
                                "ts": "2000",
                                "ccy": "ETH",
                                "amt": "2",
                            },
                            {
                                "depId": "1",
                                "wdId": "",
                                "txId": "tx1",
                                "ts": "1000",
                                "ccy": "BTC",
                                "amt": "1",
                            },
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "depId": "1",
                                "wdId": "",
                                "txId": "tx1",
                                "ts": "1000",
                                "ccy": "BTC",
                                "amt": "1",
                            },
                            {
                                "depId": "3",
                                "wdId": "",
                                "txId": "tx3",
                                "ts": "3000",
                                "ccy": "SOL",
                                "amt": "3",
                            },
                        ],
                    }
                ),
            ]
        )

        success, result = (
            service.get_deposit_history(
                max_pages=2,
                page_limit=2,
            )
        )

        self.assertTrue(success)
        self.assertEqual(
            [
                item["depId"]
                for item in result
            ],
            ["1", "2", "3"],
        )
        self.assertEqual(
            len(service.session.calls),
            2,
        )
        self.assertIn(
            "after=1",
            service.session.calls[1]["url"],
        )

    def test_asset_history_returns_api_error(self):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "51000",
                        "msg": "Bad request",
                    }
                )
            ]
        )

        success, result = (
            service.get_deposit_history()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Bad request",
        )

    def test_historical_price_returns_one_for_stablecoin(
        self,
    ):
        service = self.make_service(
            authenticated=False
        )

        for coin in ("USDT", "usd"):
            with self.subTest(coin=coin):
                success, result = (
                    service.get_historical_spot_price(
                        coin,
                        1000,
                    )
                )

                self.assertTrue(success)
                self.assertEqual(result, 1.0)

        self.assertEqual(
            service.session.calls,
            [],
        )

    def test_historical_price_rejects_empty_asset(self):
        service = self.make_service(
            authenticated=False
        )

        success, result = (
            service.get_historical_spot_price(
                "   ",
                1000,
            )
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Geçersiz varlık.",
        )

    def test_historical_price_selects_nearest_valid_candle(
        self,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            [
                                "900",
                                "0",
                                "0",
                                "0",
                                "95",
                            ],
                            [
                                "1010",
                                "0",
                                "0",
                                "0",
                                "101",
                            ],
                            [
                                "1005",
                                "0",
                                "0",
                                "0",
                                "100",
                            ],
                            [
                                "bad",
                                "0",
                                "0",
                                "0",
                                "99",
                            ],
                        ],
                    }
                )
            ],
            authenticated=False,
        )

        success, result = (
            service.get_historical_spot_price(
                "btc",
                1000,
            )
        )

        self.assertTrue(success)
        self.assertEqual(result, 100.0)
        self.assertIn(
            "instId=BTC-USDT",
            service.session.calls[0]["url"],
        )

    def test_historical_price_tries_second_window(self):
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
                            [
                                "1000",
                                "0",
                                "0",
                                "0",
                                "123.45",
                            ]
                        ],
                    }
                ),
            ],
            authenticated=False,
        )

        success, result = (
            service.get_historical_spot_price(
                "eth",
                1000,
            )
        )

        self.assertTrue(success)
        self.assertEqual(result, 123.45)
        self.assertEqual(
            len(service.session.calls),
            2,
        )

    def test_historical_price_returns_not_found(self):
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
                        "data": [],
                    }
                ),
            ],
            authenticated=False,
        )

        success, result = (
            service.get_historical_spot_price(
                "sol",
                1000,
            )
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            (
                "SOL-USDT için tarihsel fiyat "
                "bulunamadı."
            ),
        )

    def test_transfer_bills_requires_api_client(self):
        service = self.make_service(
            authenticated=False
        )

        success, result = (
            service.get_funding_transfer_bills()
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "API bilgileri bulunamadi.",
        )

    def test_transfer_bills_filter_deduplicate_and_sort(
        self,
    ):
        service = self.make_service(
            responses=[
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "billId": "2",
                                "from": "18",
                                "to": "6",
                                "ts": "2000",
                            },
                            {
                                "billId": "ignored",
                                "from": "18",
                                "to": "18",
                                "ts": "1500",
                            },
                        ],
                    }
                ),
                ResponseStub(
                    payload={
                        "code": "0",
                        "data": [
                            {
                                "billId": "1",
                                "from": "6",
                                "to": "18",
                                "ts": "1000",
                            },
                            {
                                "billId": "2",
                                "from": "18",
                                "to": "6",
                                "ts": "2000",
                            },
                        ],
                    }
                ),
            ]
        )

        success, result = (
            service.get_funding_transfer_bills(
                page_limit=100,
            )
        )

        self.assertTrue(success)
        self.assertEqual(
            [
                item["billId"]
                for item in result
            ],
            ["1", "2"],
        )
        self.assertEqual(
            len(service.session.calls),
            2,
        )
        self.assertIn(
            "/api/v5/account/bills?",
            service.session.calls[0]["url"],
        )
        self.assertIn(
            "/api/v5/account/bills-archive?",
            service.session.calls[1]["url"],
        )

    def test_transfer_bills_returns_api_error(self):
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
            service.get_funding_transfer_bills()
        )

        self.assertFalse(success)
        self.assertEqual(result, "Rate limit")


if __name__ == "__main__":
    unittest.main()
