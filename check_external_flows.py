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


def format_time(timestamp_ms, timezone_info):
    value = safe_float(timestamp_ms)

    if value <= 0:
        return "—"

    try:
        return datetime.fromtimestamp(
            value / 1000,
            tz=timezone_info,
        ).strftime("%d.%m.%Y %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return "—"


def print_items(title, items, timezone_info):
    print()
    print(title)
    print(SUBLINE)
    print(f"Toplam kayıt        : {len(items)}")

    if not items:
        print("Kayıt bulunamadı.")
        return

    print()
    print("Son 10 kayıt")
    print(SUBLINE)

    recent = sorted(
        items,
        key=lambda item: safe_float(item.get("ts")),
        reverse=True,
    )[:10]

    for item in recent:
        print(
            f"Tarih               : "
            f"{format_time(item.get('ts'), timezone_info)}"
        )
        print(
            f"Varlık              : "
            f"{str(item.get('ccy', '')).upper() or '—'}"
        )
        print(
            f"Miktar              : "
            f"{safe_float(item.get('amt')):,.8f}"
        )
        print(f"State               : {item.get('state')}")
        print(f"DepId               : {item.get('depId')}")
        print(f"WdId                : {item.get('wdId')}")
        print(f"TxId                : {item.get('txId')}")
        print(f"Chain               : {item.get('chain')}")
        print(f"Fee                 : {item.get('fee')}")
        print(SUBLINE)


def main():
    print(LINE)
    print("Caspian Harici Para Akışı Kontrolü")
    print(LINE)

    manager = DataManager()
    okx = manager.okx
    timezone_info = manager.portfolio_history.APP_TIMEZONE

    deposit_ok, deposits = okx.get_deposit_history()
    withdrawal_ok, withdrawals = okx.get_withdrawal_history()

    print()
    print("Sorgu durumu")
    print(SUBLINE)
    print(f"Yatırma geçmişi     : {deposit_ok}")
    print(f"Çekme geçmişi       : {withdrawal_ok}")

    if not deposit_ok:
        print(f"Yatırma hatası      : {deposits}")
        deposits = []

    if not withdrawal_ok:
        print(f"Çekme hatası        : {withdrawals}")
        withdrawals = []

    if not isinstance(deposits, list):
        deposits = []

    if not isinstance(withdrawals, list):
        withdrawals = []

    print_items(
        "Yatırma Geçmişi",
        deposits,
        timezone_info,
    )
    print_items(
        "Çekme Geçmişi",
        withdrawals,
        timezone_info,
    )

    states = {
        "deposit": sorted({
            str(item.get("state"))
            for item in deposits
        }),
        "withdrawal": sorted({
            str(item.get("state"))
            for item in withdrawals
        }),
    }

    print()
    print(LINE)
    print("Durum kodları özeti")
    print(LINE)
    print(f"Deposit state'leri  : {states['deposit']}")
    print(f"Withdraw state'leri : {states['withdrawal']}")
    print()
    print(
        "Bu aşamada kayıtlar performans motoruna bağlanmadı. "
        "Önce tamamlanmış işlem state kodlarını doğrulayacağız."
    )


if __name__ == "__main__":
    main()
