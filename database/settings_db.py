import json
from pathlib import Path

from security.dpapi import encrypt, decrypt


CONFIG = Path("config.json")


def save_settings(api, secret, passphrase):

    data = {
        "api": encrypt(api),
        "secret": encrypt(secret),
        "passphrase": encrypt(passphrase),
    }

    CONFIG.write_text(
        json.dumps(data, indent=4),
        encoding="utf-8",
    )


def load_settings():

    if not CONFIG.exists():
        return "", "", ""

    data = json.loads(CONFIG.read_text(encoding="utf-8"))

    return (
        decrypt(data["api"]),
        decrypt(data["secret"]),
        decrypt(data["passphrase"]),
    )