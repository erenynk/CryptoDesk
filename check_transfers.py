from datetime import datetime

from services.data_manager import DataManager


LINE = "=" * 76
SUBLINE = "-" * 76


def safe_float(value):
    try:
        number = float(value)

        if number != number:
            return 0.0

        return number
    except (TypeError, ValueError, OverflowError):
        return 0.0


def format_timestamp(timestamp_ms, timezone_info):
    try:
        value = safe_float(timestamp_ms)

        if value <= 0:
            return "—"

        return datetime.fromtimestamp(
            value / 1000,
            tz=timezone_info,
        ).strftime("%d.%m.%Y %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return "—"


def transfer_direction(item):
    from_account = str(item.get("from", "")).strip()
    to_account = str(item.get("to", "")).strip()

    if from_account == "18" and to_account == "6":
        return "Trading -> Funding"

    if from_account == "6" and to_account == "18":
        return "Funding -> Trading"

    return f"{from_account or '?'} -> {to_account or '?'}"


def transfer_amount(item):
    amount = abs(safe_float(item.get("balChg")))

    if amount <= 0:
        amount = abs(safe_float(item.get("sz")))

    return amount


def main():
    print(LINE)
    print("Caspian Transfer Kontrolü")
    print(LINE)

    manager = DataManager()
    okx = manager.okx
    transfer_service = manager.transfer_service
    timezone_info = manager.portfolio_history.APP_TIMEZONE

    success, result = okx.get_funding_transfer_bills()

    print()
    print("Transfer sorgusu")
    print(SUBLINE)
    print(f"Başarılı            : {success}")

    if not success:
        print(f"Hata                : {result}")
        return

    if not isinstance(result, list):
        print("Hata                : Transfer sonucu liste değil.")
        return

    print(f"Toplam transfer     : {len(result)}")

    print()
    print("Son 10 Transfer")
    print(SUBLINE)

    recent_items = sorted(
        result,
        key=lambda item: safe_float(item.get("ts")),
        reverse=True,
    )[:10]

    if not recent_items:
        print("Transfer kaydı bulunamadı.")
    else:
        for item in recent_items:
            currency = str(
                item.get("ccy", "")
            ).strip().upper() or "—"

            amount = transfer_amount(item)
            direction = transfer_direction(item)
            timestamp = format_timestamp(
                item.get("ts"),
                timezone_info,
            )

            print(f"Tarih               : {timestamp}")
            print(f"Varlık              : {currency}")
            print(f"Miktar              : {amount:,.8f}")
            print(f"Yön                 : {direction}")
            print(f"Type                : {item.get('type')}")
            print(f"SubType             : {item.get('subType')}")
            print(f"From                : {item.get('from')}")
            print(f"To                  : {item.get('to')}")
            print(SUBLINE)

    prices = manager.cache.get_all()

    if not isinstance(prices, dict):
        prices = {}

    adjustments = (
        transfer_service.calculate_period_adjustments(
            bills=result,
            prices=prices,
            reference_time=datetime.now(timezone_info),
        )
    )

    print()
    print("Dönemsel Net Transfer Düzeltmeleri")
    print(SUBLINE)

    for period in ("1d", "7d", "30d", "90d", "1y"):
        funding_value = safe_float(
            adjustments.get(period, 0.0)
        )
        trading_value = -funding_value

        print(
            f"{period:<4} Funding       : "
            f"{funding_value:+,.2f} USDT"
        )
        print(
            f"{period:<4} Trading       : "
            f"{trading_value:+,.2f} USDT"
        )

    print()
    print(LINE)
    print("Genel sonuç")
    print(LINE)

    if not result:
        print(
            "Transfer kaydı bulunamadı. Sorun OKX sorgusu, API izni "
            "veya endpoint uyumluluğunda olabilir."
        )
        return

    one_day_adjustment = safe_float(
        adjustments.get("1d", 0.0)
    )

    if one_day_adjustment == 0:
        print(
            "Transferler bulundu ancak 1 günlük net düzeltme 0.00 USDT. "
            "Son transferlerin yön, type, from ve to alanlarını kontrol et."
        )
    else:
        print(
            "Transfer kayıtları ve 1 günlük düzeltme başarıyla üretildi."
        )


if __name__ == "__main__":
    main()
