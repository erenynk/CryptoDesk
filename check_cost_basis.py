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


def format_amount(value):
    return f"{safe_float(value):,.8f}".rstrip("0").rstrip(".")


def format_usdt(value):
    return f"{safe_float(value):+,.2f} USDT"


def main():
    print(LINE)
    print("Caspian Cost Basis / PNL Kontrolü")
    print(LINE)

    manager = DataManager()
    success, result = manager.refresh_portfolio()

    if not success:
        print(f"Portföy yenilenemedi: {result}")
        return

    portfolio = manager.get_portfolio() or {}
    assets = portfolio.get("assets", [])

    if not isinstance(assets, list):
        print("HATA: assets alanı liste formatında değil.")
        return

    verified_count = 0
    missing_count = 0
    total_open_pnl = 0.0

    for asset in assets:
        coin = str(asset.get("coin", "")).strip().upper()

        if not coin or coin == "USDT":
            continue

        quantity = safe_float(asset.get("total"))
        current_price = safe_float(asset.get("price"))
        current_value = safe_float(asset.get("usdt_value"))

        available = bool(
            asset.get("cost_basis_available", False)
        )

        average_price = asset.get("average_price")
        cost_basis_usdt = asset.get("cost_basis_usdt")
        pnl_usdt = asset.get("pnl_usdt")
        pnl_percent = asset.get("pnl_percent")

        print()
        print(coin)
        print(SUBLINE)
        print(f"Miktar              : {format_amount(quantity)}")
        print(f"Anlık fiyat         : {current_price:,.8f} USDT")
        print(f"Güncel değer        : {current_value:,.2f} USDT")

        if (
            available
            and isinstance(average_price, (int, float))
            and isinstance(cost_basis_usdt, (int, float))
            and isinstance(pnl_usdt, (int, float))
            and isinstance(pnl_percent, (int, float))
        ):
            verified_count += 1
            total_open_pnl += float(pnl_usdt)

            print(
                f"Ortalama maliyet    : "
                f"{float(average_price):,.8f} USDT"
            )
            print(
                f"Maliyet toplamı     : "
                f"{float(cost_basis_usdt):,.2f} USDT"
            )
            print(
                f"Açık PNL            : "
                f"{float(pnl_usdt):+,.2f} USDT"
            )
            print(
                f"Açık PNL %          : "
                f"{float(pnl_percent):+.2f}%"
            )
            print("Durum               : DOĞRULANDI")
        else:
            missing_count += 1
            print("Ortalama maliyet    : —")
            print("Maliyet toplamı     : —")
            print("Açık PNL            : —")
            print("Açık PNL %          : —")
            print(
                "Durum               : "
                "İŞLEM GEÇMİŞİ YETERSİZ / EŞLEŞME YOK"
            )

    print()
    print(LINE)
    print("Özet")
    print(LINE)
    print(f"Toplam coin         : {verified_count + missing_count}")
    print(f"Doğrulanan          : {verified_count}")
    print(f"Doğrulanamayan      : {missing_count}")
    print(f"Toplam açık PNL     : {format_usdt(total_open_pnl)}")

    if missing_count == 0:
        print("Genel sonuç         : Tüm açık pozisyonlar doğrulandı.")
    else:
        print(
            "Genel sonuç         : Bazı pozisyonlarda yeterli "
            "işlem geçmişi yok."
        )


if __name__ == "__main__":
    main()
