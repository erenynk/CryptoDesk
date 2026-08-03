from datetime import datetime

from services.daily_reference_service import (
    DailyReferenceService,
)
from services.data_manager import DataManager


LINE = "=" * 88
SUBLINE = "-" * 88


def safe_float(value):
    try:
        number = float(value)
        return 0.0 if number != number else number
    except (TypeError, ValueError, OverflowError):
        return 0.0


def current_price(manager, coin):
    symbol = str(coin or "").strip().upper()

    if symbol in {"USDT", "USD"}:
        return 1.0

    return safe_float(manager.get_price(symbol))


def historical_price(manager, coin, timestamp_ms):
    symbol = str(coin or "").strip().upper()

    if symbol in {"USDT", "USD"}:
        return 1.0

    success, result = manager.okx.get_historical_spot_price(
        coin=symbol,
        timestamp_ms=timestamp_ms,
    )

    if not success:
        return None

    price = safe_float(result)
    return price if price > 0 else None


def main():
    print(LINE)
    print("Caspian OKX Uyumlu Bugünkü Trading PNL Kontrolü")
    print(LINE)

    manager = DataManager()
    timezone_info = manager.portfolio_history.APP_TIMEZONE
    period_end = datetime.now(timezone_info)

    balance_ok, portfolio = manager.okx.get_spot_balances(
        manager.cache
    )
    fills_ok, fills = manager.okx.get_spot_fills_history(
        force_refresh=True
    )
    transfers_ok, transfers = (
        manager.okx.get_funding_transfer_bills()
    )
    deposits_ok, deposits = manager.okx.get_deposit_history()
    withdrawals_ok, withdrawals = (
        manager.okx.get_withdrawal_history()
    )

    checks = (
        ("Portföy", balance_ok, portfolio),
        ("Spot fills", fills_ok, fills),
        ("İç transferler", transfers_ok, transfers),
        ("Yatırmalar", deposits_ok, deposits),
        ("Çekmeler", withdrawals_ok, withdrawals),
    )

    for label, success, result in checks:
        if not success:
            print(f"{label} alınamadı: {result}")
            return

    reference_service = DailyReferenceService(
        okx_service=manager.okx,
        app_timezone=timezone_info,
    )
    reference = reference_service.reconstruct(
        portfolio=portfolio,
        fills=fills,
        transfer_bills=transfers,
        deposits=deposits,
        withdrawals=withdrawals,
        reference_time=period_end,
    )

    timestamp_ms = int(
        reference.period_start.timestamp() * 1000
    )

    start_value = 0.0
    current_value = 0.0
    failed = []

    print()
    print("00:00 Trading Varlık Sepeti")
    print(SUBLINE)

    for coin, amount in sorted(
        reference.trading_assets.items()
    ):
        safe_amount = safe_float(amount)

        if abs(safe_amount) <= 1e-12:
            continue

        open_price = historical_price(
            manager,
            coin,
            timestamp_ms,
        )
        last_price = current_price(manager, coin)

        if (
            open_price is None
            or open_price <= 0
            or last_price <= 0
        ):
            failed.append(coin)
            continue

        open_value = safe_amount * open_price
        last_value = safe_amount * last_price
        pnl = last_value - open_value

        start_value += open_value
        current_value += last_value

        print(
            f"{coin:<10} "
            f"miktar={safe_amount:,.12f} | "
            f"00:00={open_price:,.12f} | "
            f"şimdi={last_price:,.12f} | "
            f"PNL={pnl:+,.8f} USDT"
        )

    pnl_usdt = current_value - start_value
    pnl_percent = (
        (pnl_usdt / start_value) * 100
        if start_value > 0
        else None
    )

    print()
    print("Sonuç")
    print(SUBLINE)
    print(
        f"00:00 sepet değeri : "
        f"{start_value:,.8f} USDT"
    )
    print(
        f"Şimdiki sepet değeri: "
        f"{current_value:,.8f} USDT"
    )
    print(
        f"Bugünkü PNL        : "
        f"{pnl_usdt:+,.8f} USDT"
    )

    if pnl_percent is None:
        print("Bugünkü PNL %      : —")
    else:
        print(
            f"Bugünkü PNL %      : "
            f"{pnl_percent:+.4f}%"
        )

    print()
    print("Kontrol Notu")
    print(SUBLINE)
    print(
        "Bu hesap yalnızca 00:00'da Trading hesabında bulunan "
        "varlıkların fiyat değişimini kullanır."
    )
    print(
        "Bugün alınan SUI, SOL ve NEAR bu sepete dahil edilmez."
    )

    if failed:
        print(
            "Fiyatı alınamayan varlıklar: "
            + ", ".join(failed)
        )
    else:
        print("Fiyatı alınamayan varlık yok.")


if __name__ == "__main__":
    main()
