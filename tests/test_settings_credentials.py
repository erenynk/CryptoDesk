import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import call, patch

from database import settings_db


class SettingsCredentialsTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_directory.name)
        self.config_patcher = patch.object(
            settings_db,
            "CONFIG",
            self.temp_path / "test_config.json",
        )
        self.config_patcher.start()

    def tearDown(self):
        self.config_patcher.stop()
        self.temp_directory.cleanup()

    @staticmethod
    def protect_stub(
        data,
        description,
        optional_entropy,
        reserved,
        prompt_struct,
        flags,
    ):
        if description is not None:
            raise AssertionError(
                "DPAPI description None olmalı."
            )
        if optional_entropy is not None:
            raise AssertionError(
                "DPAPI entropy None olmalı."
            )
        if reserved is not None:
            raise AssertionError(
                "DPAPI reserved None olmalı."
            )
        if prompt_struct is not None:
            raise AssertionError(
                "DPAPI prompt None olmalı."
            )
        if flags != 0:
            raise AssertionError(
                "DPAPI flags 0 olmalı."
            )

        return b"protected:" + data

    @staticmethod
    def unprotect_stub(
        encrypted,
        optional_entropy,
        reserved,
        prompt_struct,
        flags,
    ):
        if optional_entropy is not None:
            raise AssertionError(
                "DPAPI entropy None olmalı."
            )
        if reserved is not None:
            raise AssertionError(
                "DPAPI reserved None olmalı."
            )
        if prompt_struct is not None:
            raise AssertionError(
                "DPAPI prompt None olmalı."
            )
        if flags != 0:
            raise AssertionError(
                "DPAPI flags 0 olmalı."
            )
        if not encrypted.startswith(b"protected:"):
            raise AssertionError(
                "Beklenen test şifreleme öneki yok."
            )

        return (
            None,
            encrypted[len(b"protected:"):],
        )

    @patch(
        "security.dpapi.win32crypt.CryptProtectData"
    )
    def test_save_settings_encrypts_every_field(
        self,
        crypt_protect_data,
    ):
        crypt_protect_data.side_effect = (
            self.protect_stub
        )

        settings_db.save_settings(
            "api-key",
            "secret-key",
            "passphrase",
        )

        crypt_protect_data.assert_has_calls(
            [
                call(
                    b"api-key",
                    None,
                    None,
                    None,
                    None,
                    0,
                ),
                call(
                    b"secret-key",
                    None,
                    None,
                    None,
                    None,
                    0,
                ),
                call(
                    b"passphrase",
                    None,
                    None,
                    None,
                    None,
                    0,
                ),
            ]
        )
        self.assertEqual(
            crypt_protect_data.call_count,
            3,
        )

        stored_text = (
            settings_db.CONFIG.read_text(
                encoding="utf-8"
            )
        )
        stored = json.loads(stored_text)

        self.assertEqual(
            set(stored),
            {
                "api",
                "secret",
                "passphrase",
            },
        )
        self.assertEqual(
            base64.b64decode(stored["api"]),
            b"protected:api-key",
        )
        self.assertEqual(
            base64.b64decode(stored["secret"]),
            b"protected:secret-key",
        )
        self.assertEqual(
            base64.b64decode(
                stored["passphrase"]
            ),
            b"protected:passphrase",
        )
        self.assertNotEqual(
            stored["api"],
            "api-key",
        )
        self.assertNotEqual(
            stored["secret"],
            "secret-key",
        )
        self.assertNotEqual(
            stored["passphrase"],
            "passphrase",
        )

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_load_settings_decrypts_fields_in_order(
        self,
        crypt_unprotect_data,
    ):
        encrypted_values = {
            "api": b"cipher-api",
            "secret": b"cipher-secret",
            "passphrase": b"cipher-passphrase",
        }
        settings_db.CONFIG.write_text(
            json.dumps(
                {
                    key: base64.b64encode(
                        value
                    ).decode()
                    for key, value in (
                        encrypted_values.items()
                    )
                }
            ),
            encoding="utf-8",
        )

        plain_values = {
            b"cipher-api": b"api-key",
            b"cipher-secret": b"secret-key",
            b"cipher-passphrase": (
                b"passphrase"
            ),
        }

        def unprotect(
            encrypted,
            optional_entropy,
            reserved,
            prompt_struct,
            flags,
        ):
            return (
                None,
                plain_values[encrypted],
            )

        crypt_unprotect_data.side_effect = (
            unprotect
        )

        result = settings_db.load_settings()

        self.assertEqual(
            result,
            (
                "api-key",
                "secret-key",
                "passphrase",
            ),
        )
        self.assertEqual(
            [
                item.args[0]
                for item in (
                    crypt_unprotect_data.call_args_list
                )
            ],
            [
                b"cipher-api",
                b"cipher-secret",
                b"cipher-passphrase",
            ],
        )

    def test_unicode_credentials_round_trip(self):
        original = (
            "api-İstanbul",
            "gizli-şifre-🔐",
            "parola-çğıöşü",
        )

        with (
            patch(
                "security.dpapi.win32crypt"
                ".CryptProtectData",
                side_effect=self.protect_stub,
            ),
            patch(
                "security.dpapi.win32crypt"
                ".CryptUnprotectData",
                side_effect=self.unprotect_stub,
            ),
        ):
            settings_db.save_settings(*original)
            result = settings_db.load_settings()

        self.assertEqual(result, original)

    def test_empty_credentials_round_trip(self):
        original = ("", "", "")

        with (
            patch(
                "security.dpapi.win32crypt"
                ".CryptProtectData",
                side_effect=self.protect_stub,
            ),
            patch(
                "security.dpapi.win32crypt"
                ".CryptUnprotectData",
                side_effect=self.unprotect_stub,
            ),
        ):
            settings_db.save_settings(*original)
            result = settings_db.load_settings()

        self.assertEqual(result, original)

    def test_save_settings_overwrites_old_config(self):
        settings_db.CONFIG.write_text(
            json.dumps(
                {
                    "old": "value",
                }
            ),
            encoding="utf-8",
        )

        with patch(
            "security.dpapi.win32crypt"
            ".CryptProtectData",
            side_effect=self.protect_stub,
        ):
            settings_db.save_settings(
                "new-api",
                "new-secret",
                "new-passphrase",
            )

        stored = json.loads(
            settings_db.CONFIG.read_text(
                encoding="utf-8"
            )
        )

        self.assertNotIn("old", stored)
        self.assertEqual(
            set(stored),
            {
                "api",
                "secret",
                "passphrase",
            },
        )

    def test_encrypt_failure_preserves_existing_config(
        self,
    ):
        original_text = json.dumps(
            {
                "existing": "config",
            }
        )
        settings_db.CONFIG.write_text(
            original_text,
            encoding="utf-8",
        )

        def protect_with_failure(
            data,
            description,
            optional_entropy,
            reserved,
            prompt_struct,
            flags,
        ):
            if data == b"secret-key":
                raise RuntimeError(
                    "protect failed"
                )

            return self.protect_stub(
                data,
                description,
                optional_entropy,
                reserved,
                prompt_struct,
                flags,
            )

        with (
            patch(
                "security.dpapi.win32crypt"
                ".CryptProtectData",
                side_effect=protect_with_failure,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "protect failed",
            ),
        ):
            settings_db.save_settings(
                "api-key",
                "secret-key",
                "passphrase",
            )

        self.assertEqual(
            settings_db.CONFIG.read_text(
                encoding="utf-8"
            ),
            original_text,
        )

    def test_save_settings_propagates_write_error(
        self,
    ):
        with (
            patch(
                "security.dpapi.win32crypt"
                ".CryptProtectData",
                side_effect=self.protect_stub,
            ),
            patch.object(
                Path,
                "write_text",
                side_effect=OSError(
                    "disk full"
                ),
            ),
            self.assertRaisesRegex(
                OSError,
                "disk full",
            ),
        ):
            settings_db.save_settings(
                "api-key",
                "secret-key",
                "passphrase",
            )

    def test_load_settings_returns_empty_for_missing_key(
        self,
    ):
        settings_db.CONFIG.write_text(
            json.dumps(
                {
                    "api": base64.b64encode(
                        b"cipher-api"
                    ).decode(),
                    "secret": base64.b64encode(
                        b"cipher-secret"
                    ).decode(),
                }
            ),
            encoding="utf-8",
        )

        with patch.object(
            settings_db,
            "decrypt",
            return_value="decrypted",
        ) as decrypt_mock:
            result = settings_db.load_settings()

        self.assertEqual(
            result,
            ("", "", ""),
        )
        self.assertEqual(
            decrypt_mock.call_count,
            2,
        )

    def test_load_settings_returns_empty_for_non_object_json(
        self,
    ):
        settings_db.CONFIG.write_text(
            json.dumps(
                [
                    "api",
                    "secret",
                    "passphrase",
                ]
            ),
            encoding="utf-8",
        )

        self.assertEqual(
            settings_db.load_settings(),
            ("", "", ""),
        )

    def test_load_settings_returns_empty_when_read_fails(
        self,
    ):
        settings_db.CONFIG.touch()

        with patch.object(
            Path,
            "read_text",
            side_effect=OSError(
                "read failed"
            ),
        ):
            result = settings_db.load_settings()

        self.assertEqual(
            result,
            ("", "", ""),
        )


if __name__ == "__main__":
    unittest.main()
