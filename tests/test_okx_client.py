import base64
import hmac
import unittest
from datetime import UTC, datetime
from hashlib import sha256
from unittest.mock import Mock, patch

import requests

from api.okx_client import OKXClient


class OKXClientTestCase(unittest.TestCase):
    def setUp(self):
        self.client = OKXClient(
            api_key="test-api-key",
            secret_key="test-secret-key",
            passphrase="test-passphrase",
        )
        self.fixed_time = datetime(
            2026,
            7,
            22,
            14,
            30,
            45,
            123000,
            tzinfo=UTC,
        )
        self.timestamp = "2026-07-22T14:30:45.123Z"

    @staticmethod
    def expected_signature(
        secret_key,
        timestamp,
        method,
        path,
        body="",
    ):
        message = (
            f"{timestamp}{method}{path}{body}"
        )

        return base64.b64encode(
            hmac.new(
                secret_key.encode(),
                message.encode(),
                sha256,
            ).digest()
        ).decode()

    def build_headers(
        self,
        method,
        path,
        body="",
    ):
        with patch(
            "api.okx_client.datetime"
        ) as mocked_datetime:
            mocked_datetime.now.return_value = (
                self.fixed_time
            )

            headers = self.client._headers(
                method,
                path,
                body,
            )

            mocked_datetime.now.assert_called_once_with(
                UTC
            )

        return headers

    def test_constructor_stores_credentials(self):
        self.assertEqual(
            self.client.api_key,
            "test-api-key",
        )
        self.assertEqual(
            self.client.secret_key,
            "test-secret-key",
        )
        self.assertEqual(
            self.client.passphrase,
            "test-passphrase",
        )

    def test_headers_include_required_okx_fields(self):
        headers = self.build_headers(
            "GET",
            "/api/v5/account/config",
        )

        self.assertEqual(
            headers["OK-ACCESS-KEY"],
            "test-api-key",
        )
        self.assertEqual(
            headers["OK-ACCESS-TIMESTAMP"],
            self.timestamp,
        )
        self.assertEqual(
            headers["OK-ACCESS-PASSPHRASE"],
            "test-passphrase",
        )
        self.assertEqual(
            headers["Content-Type"],
            "application/json",
        )
        self.assertIn(
            "OK-ACCESS-SIGN",
            headers,
        )
        self.assertEqual(len(headers), 5)

    def test_timestamp_uses_milliseconds_and_z_suffix(
        self,
    ):
        headers = self.build_headers(
            "GET",
            "/api/v5/account/config",
        )

        self.assertEqual(
            headers["OK-ACCESS-TIMESTAMP"],
            "2026-07-22T14:30:45.123Z",
        )
        self.assertNotIn(
            "+00:00",
            headers["OK-ACCESS-TIMESTAMP"],
        )

    def test_get_signature_uses_empty_body(self):
        path = "/api/v5/account/config"

        headers = self.build_headers(
            "GET",
            path,
        )

        expected = self.expected_signature(
            secret_key="test-secret-key",
            timestamp=self.timestamp,
            method="GET",
            path=path,
            body="",
        )

        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            expected,
        )

    def test_query_string_is_included_in_signature(self):
        path = (
            "/api/v5/trade/fills-history"
            "?instType=SPOT&limit=100"
        )

        headers = self.build_headers(
            "GET",
            path,
        )

        expected = self.expected_signature(
            secret_key="test-secret-key",
            timestamp=self.timestamp,
            method="GET",
            path=path,
        )

        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            expected,
        )

    def test_post_signature_includes_exact_body(self):
        path = "/api/v5/trade/order"
        body = (
            '{"instId":"BTC-USDT",'
            '"tdMode":"cash",'
            '"side":"buy"}'
        )

        headers = self.build_headers(
            "POST",
            path,
            body,
        )

        expected = self.expected_signature(
            secret_key="test-secret-key",
            timestamp=self.timestamp,
            method="POST",
            path=path,
            body=body,
        )

        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            expected,
        )

    def test_signature_changes_when_body_changes(self):
        path = "/api/v5/trade/order"

        first_headers = self.build_headers(
            "POST",
            path,
            '{"side":"buy"}',
        )
        second_headers = self.build_headers(
            "POST",
            path,
            '{"side":"sell"}',
        )

        self.assertNotEqual(
            first_headers["OK-ACCESS-SIGN"],
            second_headers["OK-ACCESS-SIGN"],
        )

    def test_signature_supports_utf8_secret_and_body(
        self,
    ):
        client = OKXClient(
            api_key="anahtar",
            secret_key="gizli-şifre",
            passphrase="parola",
        )
        path = "/api/v5/trade/order"
        body = '{"not":"Türkçe açıklama"}'

        with patch(
            "api.okx_client.datetime"
        ) as mocked_datetime:
            mocked_datetime.now.return_value = (
                self.fixed_time
            )
            headers = client._headers(
                "POST",
                path,
                body,
            )

        expected = self.expected_signature(
            secret_key="gizli-şifre",
            timestamp=self.timestamp,
            method="POST",
            path=path,
            body=body,
        )

        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            expected,
        )

    @patch("api.okx_client.requests.get")
    def test_connection_uses_expected_request(
        self,
        requests_get,
    ):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {
            "code": "0",
            "data": [
                {
                    "uid": "123",
                }
            ],
        }
        requests_get.return_value = response

        fixed_headers = {
            "OK-ACCESS-KEY": "test-api-key",
            "OK-ACCESS-SIGN": "signature",
            "OK-ACCESS-TIMESTAMP": self.timestamp,
            "OK-ACCESS-PASSPHRASE": (
                "test-passphrase"
            ),
            "Content-Type": "application/json",
        }

        with patch.object(
            self.client,
            "_headers",
            return_value=fixed_headers,
        ) as headers_mock:
            status_code, payload = (
                self.client.test_connection()
            )

        self.assertEqual(status_code, 200)
        self.assertEqual(
            payload,
            {
                "code": "0",
                "data": [
                    {
                        "uid": "123",
                    }
                ],
            },
        )
        headers_mock.assert_called_once_with(
            "GET",
            "/api/v5/account/config",
        )
        requests_get.assert_called_once_with(
            (
                "https://www.okx.com"
                "/api/v5/account/config"
            ),
            headers=fixed_headers,
            timeout=10,
        )
        response.json.assert_called_once_with()

    @patch("api.okx_client.requests.get")
    def test_connection_returns_api_error_payload(
        self,
        requests_get,
    ):
        response = Mock()
        response.status_code = 401
        response.json.return_value = {
            "code": "50113",
            "msg": "Invalid signature",
        }
        requests_get.return_value = response

        with patch.object(
            self.client,
            "_headers",
            return_value={},
        ):
            status_code, payload = (
                self.client.test_connection()
            )

        self.assertEqual(status_code, 401)
        self.assertEqual(
            payload,
            {
                "code": "50113",
                "msg": "Invalid signature",
            },
        )

    @patch("api.okx_client.requests.get")
    def test_connection_propagates_request_exception(
        self,
        requests_get,
    ):
        requests_get.side_effect = (
            requests.RequestException(
                "connection lost"
            )
        )

        with (
            patch.object(
                self.client,
                "_headers",
                return_value={},
            ),
            self.assertRaisesRegex(
                requests.RequestException,
                "connection lost",
            ),
        ):
            self.client.test_connection()

    @patch("api.okx_client.requests.get")
    def test_connection_propagates_json_error(
        self,
        requests_get,
    ):
        response = Mock()
        response.status_code = 200
        response.json.side_effect = ValueError(
            "invalid json"
        )
        requests_get.return_value = response

        with (
            patch.object(
                self.client,
                "_headers",
                return_value={},
            ),
            self.assertRaisesRegex(
                ValueError,
                "invalid json",
            ),
        ):
            self.client.test_connection()


if __name__ == "__main__":
    unittest.main()
