import base64
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from database import settings_db
from security import dpapi


@unittest.skipIf(
    os.name == "nt",
    "Linux kimlik bilgisi koruma testleri.",
)
class LinuxCredentialProtectionTestCase(
    unittest.TestCase
):
    def test_round_trip_uses_keyring_master_key(self):
        stored_values = {}

        def get_password(service, username):
            return stored_values.get(
                (service, username)
            )

        def set_password(
            service,
            username,
            password,
        ):
            stored_values[
                (service, username)
            ] = password

        with (
            patch(
                "security.dpapi.keyring.get_password",
                side_effect=get_password,
            ),
            patch(
                "security.dpapi.keyring.set_password",
                side_effect=set_password,
            ),
        ):
            original = "API-şifresi-İstanbul-🔐"

            encrypted = dpapi.encrypt(original)
            decrypted = dpapi.decrypt(encrypted)

        self.assertNotEqual(encrypted, original)
        self.assertEqual(decrypted, original)
        self.assertEqual(len(stored_values), 1)

    def test_existing_master_key_is_reused(self):
        master_key = (
            dpapi.Fernet.generate_key().decode(
                "ascii"
            )
        )

        with (
            patch(
                "security.dpapi.keyring.get_password",
                return_value=master_key,
            ),
            patch(
                "security.dpapi.keyring.set_password",
            ) as set_password,
        ):
            dpapi.encrypt("api")
            dpapi.encrypt("secret")

        set_password.assert_not_called()

    def test_missing_master_key_rejects_decryption(
        self,
    ):
        encoded = base64.b64encode(
            b"encrypted-value"
        ).decode()

        with (
            patch(
                "security.dpapi.keyring.get_password",
                return_value=None,
            ),
            self.assertRaises(
                dpapi.CredentialProtectionError
            ),
        ):
            dpapi.decrypt(encoded)

    def test_invalid_ciphertext_is_rejected(self):
        master_key = (
            dpapi.Fernet.generate_key().decode(
                "ascii"
            )
        )
        encoded = base64.b64encode(
            b"invalid-ciphertext"
        ).decode()

        with (
            patch(
                "security.dpapi.keyring.get_password",
                return_value=master_key,
            ),
            self.assertRaises(
                dpapi.CredentialProtectionError
            ),
        ):
            dpapi.decrypt(encoded)


class SettingsCredentialCompatibilityTestCase(
    unittest.TestCase
):
    def test_incompatible_config_returns_empty_values(
        self,
    ):
        with tempfile.TemporaryDirectory() as temp_dir:
            config = (
                Path(temp_dir) / "config.json"
            )
            config.write_text(
                json.dumps(
                    {
                        "api": "windows-data",
                        "secret": "windows-data",
                        "passphrase": "windows-data",
                    }
                ),
                encoding="utf-8",
            )

            with (
                patch.object(
                    settings_db,
                    "CONFIG",
                    config,
                ),
                patch.object(
                    settings_db,
                    "decrypt",
                    side_effect=(
                        dpapi.CredentialProtectionError(
                            "uyumsuz veri"
                        )
                    ),
                ),
            ):
                result = settings_db.load_settings()

        self.assertEqual(result, ("", "", ""))


if __name__ == "__main__":
    unittest.main()
