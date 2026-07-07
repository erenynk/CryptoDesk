import base64
import win32crypt


def encrypt(text: str) -> str:
    data = text.encode("utf-8")

    encrypted = win32crypt.CryptProtectData(
        data,
        None,
        None,
        None,
        None,
        0
    )

    return base64.b64encode(encrypted).decode()


def decrypt(text: str) -> str:
    encrypted = base64.b64decode(text)

    decrypted = win32crypt.CryptUnprotectData(
        encrypted,
        None,
        None,
        None,
        0
    )[1]

    return decrypted.decode()