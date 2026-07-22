import base64
import binascii
import unittest
from unittest.mock import patch

from security import dpapi


class DPAPITestCase(unittest.TestCase):
    @patch(
        "security.dpapi.win32crypt.CryptProtectData"
    )
    def test_encrypt_encodes_utf8_and_calls_dpapi(
        self,
        crypt_protect_data,
    ):
        encrypted_bytes = b"encrypted-payload"
        crypt_protect_data.return_value = (
            encrypted_bytes
        )

        result = dpapi.encrypt(
            "Türkçe şifre 🔐"
        )

        crypt_protect_data.assert_called_once_with(
            "Türkçe şifre 🔐".encode("utf-8"),
            None,
            None,
            None,
            None,
            0,
        )
        self.assertEqual(
            result,
            base64.b64encode(
                encrypted_bytes
            ).decode(),
        )

    @patch(
        "security.dpapi.win32crypt.CryptProtectData"
    )
    def test_encrypt_supports_empty_text(
        self,
        crypt_protect_data,
    ):
        crypt_protect_data.return_value = b"empty"

        result = dpapi.encrypt("")

        crypt_protect_data.assert_called_once_with(
            b"",
            None,
            None,
            None,
            None,
            0,
        )
        self.assertEqual(
            result,
            base64.b64encode(b"empty").decode(),
        )

    @patch(
        "security.dpapi.win32crypt.CryptProtectData"
    )
    def test_encrypt_returns_ascii_base64_text(
        self,
        crypt_protect_data,
    ):
        crypt_protect_data.return_value = (
            bytes(range(32))
        )

        result = dpapi.encrypt("secret")

        self.assertIsInstance(result, str)
        result.encode("ascii")
        self.assertEqual(
            base64.b64decode(result),
            bytes(range(32)),
        )

    @patch(
        "security.dpapi.win32crypt.CryptProtectData"
    )
    def test_encrypt_propagates_dpapi_error(
        self,
        crypt_protect_data,
    ):
        crypt_protect_data.side_effect = (
            RuntimeError("protect failed")
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "protect failed",
        ):
            dpapi.encrypt("secret")

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_decrypt_decodes_base64_and_calls_dpapi(
        self,
        crypt_unprotect_data,
    ):
        encrypted_bytes = b"encrypted-payload"
        crypt_unprotect_data.return_value = (
            "description",
            "Türkçe şifre 🔐".encode("utf-8"),
        )
        encoded = base64.b64encode(
            encrypted_bytes
        ).decode()

        result = dpapi.decrypt(encoded)

        crypt_unprotect_data.assert_called_once_with(
            encrypted_bytes,
            None,
            None,
            None,
            0,
        )
        self.assertEqual(
            result,
            "Türkçe şifre 🔐",
        )

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_decrypt_ignores_description_field(
        self,
        crypt_unprotect_data,
    ):
        crypt_unprotect_data.return_value = (
            "ignored description",
            b"plain-text",
        )

        result = dpapi.decrypt(
            base64.b64encode(
                b"cipher-text"
            ).decode()
        )

        self.assertEqual(result, "plain-text")

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_decrypt_supports_empty_plain_text(
        self,
        crypt_unprotect_data,
    ):
        crypt_unprotect_data.return_value = (
            None,
            b"",
        )

        result = dpapi.decrypt(
            base64.b64encode(b"empty").decode()
        )

        self.assertEqual(result, "")

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_decrypt_propagates_dpapi_error(
        self,
        crypt_unprotect_data,
    ):
        crypt_unprotect_data.side_effect = (
            RuntimeError("unprotect failed")
        )

        encoded = base64.b64encode(
            b"cipher-text"
        ).decode()

        with self.assertRaisesRegex(
            RuntimeError,
            "unprotect failed",
        ):
            dpapi.decrypt(encoded)

    def test_decrypt_rejects_invalid_base64_padding(self):
        with self.assertRaises(
            (binascii.Error, ValueError),
        ):
            dpapi.decrypt("a")

    @patch(
        "security.dpapi.win32crypt.CryptUnprotectData"
    )
    def test_decrypt_rejects_invalid_utf8_plain_text(
        self,
        crypt_unprotect_data,
    ):
        crypt_unprotect_data.return_value = (
            None,
            b"\xff\xfe",
        )

        encoded = base64.b64encode(
            b"cipher-text"
        ).decode()

        with self.assertRaises(
            UnicodeDecodeError
        ):
            dpapi.decrypt(encoded)

    def test_mocked_round_trip_preserves_unicode_text(self):
        def protect(
            data,
            description,
            optional_entropy,
            reserved,
            prompt_struct,
            flags,
        ):
            self.assertIsNone(description)
            self.assertIsNone(optional_entropy)
            self.assertIsNone(reserved)
            self.assertIsNone(prompt_struct)
            self.assertEqual(flags, 0)
            return b"prefix:" + data

        def unprotect(
            encrypted,
            optional_entropy,
            reserved,
            prompt_struct,
            flags,
        ):
            self.assertIsNone(optional_entropy)
            self.assertIsNone(reserved)
            self.assertIsNone(prompt_struct)
            self.assertEqual(flags, 0)
            self.assertTrue(
                encrypted.startswith(b"prefix:")
            )
            return (
                None,
                encrypted[len(b"prefix:"):],
            )

        original = (
            "API-şifresi-İstanbul-🔐"
        )

        with (
            patch(
                "security.dpapi.win32crypt"
                ".CryptProtectData",
                side_effect=protect,
            ),
            patch(
                "security.dpapi.win32crypt"
                ".CryptUnprotectData",
                side_effect=unprotect,
            ),
        ):
            encrypted = dpapi.encrypt(original)
            decrypted = dpapi.decrypt(encrypted)

        self.assertNotEqual(encrypted, original)
        self.assertEqual(decrypted, original)


if __name__ == "__main__":
    unittest.main()
