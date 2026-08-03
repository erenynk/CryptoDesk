import base64
import os
from threading import Lock
from typing import Any


class CredentialProtectionError(RuntimeError):
    """Kimlik bilgilerinin korunması sırasında oluşan hata."""


if os.name == "nt":
    import win32crypt
else:
    import keyring
    from cryptography.fernet import Fernet, InvalidToken
    from keyring.errors import KeyringError

    class _LinuxCredentialProtector:
        """KDE Wallet anahtarıyla Linux kimlik bilgisi koruması."""

        SERVICE_NAME = "io.github.erenynk.CryptoDesk"
        MASTER_KEY_NAME = "credential-master-key-v1"

        _key_lock = Lock()

        @classmethod
        def _get_master_key(
            cls,
            create: bool,
        ) -> bytes:
            try:
                stored_key = keyring.get_password(
                    cls.SERVICE_NAME,
                    cls.MASTER_KEY_NAME,
                )

                if stored_key:
                    key = stored_key.encode("ascii")
                    Fernet(key)
                    return key

                if not create:
                    raise CredentialProtectionError(
                        "Linux kimlik bilgisi anahtarı bulunamadı."
                    )

                key = Fernet.generate_key()

                keyring.set_password(
                    cls.SERVICE_NAME,
                    cls.MASTER_KEY_NAME,
                    key.decode("ascii"),
                )

                return key

            except CredentialProtectionError:
                raise
            except (
                KeyringError,
                UnicodeError,
                ValueError,
            ) as exc:
                raise CredentialProtectionError(
                    "KDE Wallet kimlik bilgisi anahtarına "
                    "erişilemedi."
                ) from exc

        @classmethod
        def CryptProtectData(
            cls,
            data: bytes,
            *args: Any,
            **kwargs: Any,
        ) -> bytes:
            with cls._key_lock:
                key = cls._get_master_key(
                    create=True,
                )

            try:
                return Fernet(key).encrypt(
                    bytes(data)
                )
            except (TypeError, ValueError) as exc:
                raise CredentialProtectionError(
                    "Kimlik bilgisi şifrelenemedi."
                ) from exc

        @classmethod
        def CryptUnprotectData(
            cls,
            encrypted: bytes,
            *args: Any,
            **kwargs: Any,
        ) -> tuple[None, bytes]:
            with cls._key_lock:
                key = cls._get_master_key(
                    create=False,
                )

            try:
                decrypted = Fernet(key).decrypt(
                    bytes(encrypted)
                )
            except InvalidToken as exc:
                raise CredentialProtectionError(
                    "Şifreli kimlik bilgisi bu sistemle "
                    "uyumlu değil veya bozulmuş."
                ) from exc

            return None, decrypted

    win32crypt = _LinuxCredentialProtector()


def encrypt(text: str) -> str:
    data = text.encode("utf-8")

    encrypted = win32crypt.CryptProtectData(
        data,
        None,
        None,
        None,
        None,
        0,
    )

    return base64.b64encode(encrypted).decode()


def decrypt(text: str) -> str:
    encrypted = base64.b64decode(text)

    decrypted = win32crypt.CryptUnprotectData(
        encrypted,
        None,
        None,
        None,
        0,
    )[1]

    return decrypted.decode()
