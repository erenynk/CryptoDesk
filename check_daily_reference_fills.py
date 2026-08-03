from datetime import datetime

from services.data_manager import DataManager


LINE = "=" * 92
SUBLINE = "-" * 92


def safe_float(value):
    try:
        number = float(value)
        return 0.0 if number != number else number
    except (TypeError, ValueError, OverflowError):
        return 0.0


def event_time(item, timezone_info):
    timestamp_ms = int(
        safe_float(
            item.get("ts", item.get("fillTime"))
        )
    )

    if timestamp_ms <= 0:
        return None

    try:
        return datetime.fromtimestamp(
            timestamp_ms / 1000,
            tz=timezone_info,
        )
    except (OSError, OverflowError, ValueError):
        return None


def get_current_trading_assets(portfolio):
    result = {}

    for asset in portfolio.get("assets", []):
        if not isinstance(asset, dict):
            continue

        coin = str(
            asset.get("coin", "")
        ).strip().upper()
        amount = safe_float(
            asset.get("trading_total", 0.0)
        )

        if coin and abs(amount) > 1e-12:
            result[coin] = amount

    return result


def apply_delta(balances, coin, delta):
    symbol = str(coin or "").strip().upper()

    if not symbol:
        return

    updated = safe_float(
        balances.get(symbol, 0.0)
    ) + safe_float(delta)

    if abs(updated) <= 1e-12:
        balances.pop(symbol, None)
    else:
        balances[symbol] = updated


def print_balances(title, balances):
    print()
    print(title)
    print(SUBLINE)

    if not balances:
        print("Varlık yok.")
        return

    for coin, amount in sorted(balances.items()):
        print(f"{coin:<12}: {amount:,.12f}")


def main():
    print(LINE)
    print("Caspian Günlük Trading Fill Geri Sarma Kontrolü")
    print(LINE)

    manager = DataManager()
    timezone_info = manager.portfolio_history.APP_TIMEZONE
    period_end = datetime.now(timezone_info)
    period_start = period_end.replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )

    balance_ok, portfolio = (
        manager.okx.get_spot_balances(
            manager.cache
        )
    )

    if not balance_ok:
        print(f"Portföy alınamadı: {portfolio}")
        return

    fills_ok, fills = (
        manager.okx.get_spot_fills_history(
            force_refresh=True
        )
    )

    if not fills_ok:
        print(f"Spot fills alınamadı: {fills}")
        return

    today_fills = []

    for fill in fills:
        if not isinstance(fill, dict):
            continue

        fill_time = event_time(
            fill,
            timezone_info,
        )

        if (
            fill_time is not None
            and period_start <= fill_time <= period_end
        ):
            today_fills.append(
                (fill_time, fill)
            )

    today_fills.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    trading = get_current_trading_assets(
        portfolio
    )

    print()
    print("Dönem")
    print(SUBLINE)
    print(f"Başlangıç          : {period_start}")
    print(f"Bitiş              : {period_end}")
    print(f"Bugünkü fill sayısı: {len(today_fills)}")

    print_balances(
        "Güncel Trading Varlıkları",
        trading,
    )

    print()
    print("Fill Geri Sarma Adımları")
    print(SUBLINE)

    if not today_fills:
        print("Bugün spot fill kaydı bulunamadı.")
    else:
        for index, (fill_time, fill) in enumerate(
            today_fills,
            start=1,
        ):
            instrument = str(
                fill.get("instId", "")
            ).strip().upper()
            side = str(
                fill.get("side", "")
            ).strip().lower()
            size = abs(
                safe_float(
                    fill.get(
                        "fillSz",
                        fill.get("sz"),
                    )
                )
            )
            price = safe_float(
                fill.get(
                    "fillPx",
                    fill.get("px"),
                )
            )
            fee = safe_float(
                fill.get("fee")
            )
            fee_coin = str(
                fill.get("feeCcy", "")
            ).strip().upper()

            print()
            print(f"[{index}] {fill_time}")
            print(f"Parite             : {instrument}")
            print(f"Yön                : {side}")
            print(f"Fill miktarı       : {size:,.12f}")
            print(f"Fill fiyatı        : {price:,.12f}")
            print(
                f"Brüt USDT değeri   : "
                f"{size * price:,.12f}"
            )
            print(f"Komisyon           : {fee:,.12f}")
            print(f"Komisyon coini     : {fee_coin or '—'}")
            print(f"Bill ID            : {fill.get('billId')}")
            print(f"Trade ID           : {fill.get('tradeId')}")

            if not instrument.endswith("-USDT"):
                print(
                    "Durum              : "
                    "Desteklenmeyen parite, atlandı."
                )
                continue

            base_coin = instrument.removesuffix(
                "-USDT"
            )
            quote_value = size * price

            before_base = safe_float(
                trading.get(base_coin, 0.0)
            )
            before_usdt = safe_float(
                trading.get("USDT", 0.0)
            )
            before_fee = (
                safe_float(
                    trading.get(fee_coin, 0.0)
                )
                if fee_coin
                else None
            )

            if side == "buy":
                apply_delta(
                    trading,
                    base_coin,
                    -size,
                )
                apply_delta(
                    trading,
                    "USDT",
                    quote_value,
                )
            elif side == "sell":
                apply_delta(
                    trading,
                    base_coin,
                    size,
                )
                apply_delta(
                    trading,
                    "USDT",
                    -quote_value,
                )
            else:
                print(
                    "Durum              : "
                    "Geçersiz yön, atlandı."
                )
                continue

            if fee_coin and abs(fee) > 1e-12:
                apply_delta(
                    trading,
                    fee_coin,
                    -fee,
                )

            after_base = safe_float(
                trading.get(base_coin, 0.0)
            )
            after_usdt = safe_float(
                trading.get("USDT", 0.0)
            )
            after_fee = (
                safe_float(
                    trading.get(fee_coin, 0.0)
                )
                if fee_coin
                else None
            )

            print(
                f"{base_coin} önce/sonra  : "
                f"{before_base:,.12f} -> "
                f"{after_base:,.12f}"
            )
            print(
                f"USDT önce/sonra    : "
                f"{before_usdt:,.12f} -> "
                f"{after_usdt:,.12f}"
            )

            if (
                fee_coin
                and fee_coin not in {
                    base_coin,
                    "USDT",
                }
            ):
                print(
                    f"{fee_coin} önce/sonra : "
                    f"{before_fee:,.12f} -> "
                    f"{after_fee:,.12f}"
                )

            print("Durum              : Uygulandı")

    print_balances(
        "Geri Sarılmış 00:00 Trading Varlıkları",
        trading,
    )

    print()
    print("00:00 Tarihsel Değerleme")
    print(SUBLINE)

    timestamp_ms = int(
        period_start.timestamp() * 1000
    )
    total_usdt = 0.0
    failed = []

    for coin, amount in sorted(trading.items()):
        if coin in {"USDT", "USD"}:
            price = 1.0
        else:
            success, result = (
                manager.okx.get_historical_spot_price(
                    coin=coin,
                    timestamp_ms=timestamp_ms,
                )
            )

            if not success:
                failed.append(
                    (coin, amount, result)
                )
                continue

            price = safe_float(result)

        value = amount * price
        total_usdt += value

        print(
            f"{coin:<10} "
            f"miktar={amount:,.12f} | "
            f"fiyat={price:,.12f} | "
            f"değer={value:,.8f} USDT"
        )

    print(SUBLINE)
    print(
        f"00:00 Trading değeri: "
        f"{total_usdt:,.8f} USDT"
    )

    print()
    print("Değerlenemeyen Varlıklar")
    print(SUBLINE)

    if not failed:
        print("Yok.")
    else:
        for coin, amount, reason in failed:
            print(
                f"{coin} | {amount} | {reason}"
            )


if __name__ == "__main__":
    main()
