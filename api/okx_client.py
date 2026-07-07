import base64
import hmac
import json
from datetime import datetime, UTC
from hashlib import sha256

import requests


class OKXClient:
    BASE_URL = "https://www.okx.com"

    def __init__(self, api_key, secret_key, passphrase):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase

    def _headers(self, method, path, body=""):
        timestamp = datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")

        message = f"{timestamp}{method}{path}{body}"

        signature = base64.b64encode(
            hmac.new(
                self.secret_key.encode(),
                message.encode(),
                sha256,
            ).digest()
        ).decode()

        return {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
        }

    def test_connection(self):
        path = "/api/v5/account/config"

        response = requests.get(
            self.BASE_URL + path,
            headers=self._headers("GET", path),
            timeout=10,
        )

        return response.status_code, response.json()