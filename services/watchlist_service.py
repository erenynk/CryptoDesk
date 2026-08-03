from database.settings_db import (
    add_watchlist_symbol,
    get_watchlist_items,
    remove_watchlist_symbol,
)


ALIASES = {
    "BITCOIN": "BTC",
    "ETHEREUM": "ETH",
    "SOLANA": "SOL",
    "SOLAN": "SOL",
    "LITECOIN": "LTC",
    "RIPPLE": "XRP",
    "CARDANO": "ADA",
    "DOGECOIN": "DOGE",
    "POLKADOT": "DOT",
    "AVALANCHE": "AVAX",
    "CHAINLINK": "LINK",
    "TRON": "TRX",
    "TONCOIN": "TON",
}


def normalize_symbol(symbol: str) -> str:
    text = str(symbol or "").strip().upper()

    if not text:
        return ""

    for separator in ("-", "/", "_"):
        if separator in text:
            text = text.split(separator, 1)[0]

    text = text.strip()

    return ALIASES.get(text, text)


def add_symbol(
    symbol: str,
    current_price: float | None = None,
) -> bool:
    normalized = normalize_symbol(symbol)

    if not normalized:
        return False

    return add_watchlist_symbol(
        normalized,
        current_price,
    )


def remove_symbol(symbol: str) -> bool:
    normalized = normalize_symbol(symbol)

    if not normalized:
        return False

    return remove_watchlist_symbol(normalized)


def get_items() -> list[dict]:
    return get_watchlist_items()