import base64
import os
from typing import Any


class _UnavailableWin32Crypt:
    """Windows dışındaki sistemler için DPAPI uyumluluk nesnesi."""

    @staticmethod
    def CryptProtectData(
        *args: Any,
        **kwargs: Any,
    ) -> bytes:
        raise RuntimeError(
            "Windows DPAPI bu platformda kullanılamıyor."
        )

    @staticmethod
    def CryptUnprotectData(
        *args: Any,
        **kwargs: Any,
    ) -> tuple[None, bytes]:
        raise RuntimeError(
            "Windows DPAPI bu platformda kullanılamıyor."
        )


if os.name == "nt":
    import win32crypt
else:
    win32crypt = _UnavailableWin32Crypt()


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
