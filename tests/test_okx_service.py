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


if __name__ == "__main__":
    unittest.main()
