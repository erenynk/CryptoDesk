from services.portfolio_history_service import PortfolioHistoryService


PERIODS = (
    ("1 Gün", "1d"),
    ("7 Gün", "7d"),
    ("30 Gün", "30d"),
    ("90 Gün", "90d"),
    ("1 Yıl", "1y"),
)


def main() -> None:
    service = PortfolioHistoryService()

    print("=" * 76)
    print("CryptoDesk Portfolio History Zaman Serisi Kontrolü")
    print("=" * 76)
    print(f"Veritabanı: {service.db_path}")

    available_periods = service.get_available_history_periods()

    print("\nDönem kullanılabilirliği")
    print("-" * 76)

    for label, key in PERIODS:
        status = "HAZIR" if available_periods.get(key) else "BEKLENİYOR"
        print(f"{label:<8}: {status}")

    print("\nZaman serileri")
    print("-" * 76)

    for label, key in PERIODS:
        series = service.get_history_series(
            period=key,
            max_points=500,
        )

        print(f"\n{label} ({key})")
        print(f"Kayıt sayısı: {len(series)}")

        if not series:
            print("Veri yok.")
            continue

        first = series[0]
        last = series[-1]

        print(f"İlk zaman: {first['timestamp']}")
        print(f"Son zaman: {last['timestamp']}")
        print(f"İlk toplam: {first['total_usdt']:.8f} USDT")
        print(f"Son toplam: {last['total_usdt']:.8f} USDT")

    print("\nÖrnekleme kontrolü")
    print("-" * 76)

    full_series = service.get_history_series(
        period="1y",
        max_points=500,
    )
    limited_series = service.get_history_series(
        period="1y",
        max_points=2,
    )

    print(f"1Y / 500 nokta sınırı: {len(full_series)} kayıt")
    print(f"1Y / 2 nokta sınırı: {len(limited_series)} kayıt")

    if len(full_series) > 2 and len(limited_series) == 2:
        same_first = (
            full_series[0]["id"] == limited_series[0]["id"]
        )
        same_last = (
            full_series[-1]["id"] == limited_series[-1]["id"]
        )

        print(
            "İlk kayıt korundu: "
            f"{'EVET' if same_first else 'HAYIR'}"
        )
        print(
            "Son kayıt korundu: "
            f"{'EVET' if same_last else 'HAYIR'}"
        )
    else:
        print(
            "Örnekleme doğrulaması için henüz yeterli kayıt yok."
        )

    print("\nGenel sonuç")
    print("-" * 76)
    print("Zaman serisi servisi erişilebilir durumda.")


if __name__ == "__main__":
    main()
