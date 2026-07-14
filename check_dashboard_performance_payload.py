from services.data_manager import DataManager


EXPECTED_PERIOD_KEYS = (
    "1d",
    "7d",
    "30d",
    "90d",
    "1y",
)


def main() -> None:
    manager = DataManager()

    print("=" * 72)
    print("Dashboard Performance Payload Kontrolü")
    print("=" * 72)

    success, result = manager.refresh_portfolio()

    if not success:
        print(f"Portföy yenilenemedi: {result}")
        return

    portfolio = manager.get_portfolio()

    if not isinstance(portfolio, dict):
        print("HATA: Portföy verisi sözlük formatında değil.")
        return

    performance = portfolio.get("performance")
    breakdown = portfolio.get("performance_breakdown")
    analytics = portfolio.get("analytics")

    print("\nAna alanlar")
    print("-" * 72)

    required_fields = (
        "total_usdt",
        "funding_usdt",
        "trading_usdt",
        "assets",
        "performance",
    )

    all_fields_ok = True

    for field in required_fields:
        exists = field in portfolio
        print(f"{field:<24}: {'OK' if exists else 'EKSİK'}")
        all_fields_ok = all_fields_ok and exists

    print("\nDashboard performans anahtarları")
    print("-" * 72)

    performance_ok = isinstance(performance, dict)

    if not performance_ok:
        print("HATA: performance alanı sözlük değil.")
    else:
        for key in EXPECTED_PERIOD_KEYS:
            exists = key in performance
            value = performance.get(key)

            valid_type = (
                value is None
                or isinstance(value, (int, float))
            )

            status = (
                "OK"
                if exists and valid_type
                else "HATALI"
            )

            print(f"{key:<6}: {status} | Değer: {value}")
            performance_ok = (
                performance_ok
                and exists
                and valid_type
            )

    print("\nAyrıntılı performans")
    print("-" * 72)

    breakdown_ok = isinstance(breakdown, dict)

    if not breakdown_ok:
        print("HATA: performance_breakdown alanı sözlük değil.")
    else:
        for group in ("total", "funding", "trading"):
            group_data = breakdown.get(group)
            group_ok = isinstance(group_data, dict)

            if group_ok:
                group_ok = all(
                    key in group_data
                    for key in EXPECTED_PERIOD_KEYS
                )

            print(f"{group:<10}: {'OK' if group_ok else 'HATALI'}")
            breakdown_ok = breakdown_ok and group_ok

    print("\nAnalytics")
    print("-" * 72)

    analytics_ok = isinstance(analytics, dict)

    if not analytics_ok:
        print("HATA: analytics alanı sözlük değil.")
    else:
        period_changes_ok = isinstance(
            analytics.get("period_changes"),
            dict,
        )
        summary_ok = isinstance(
            analytics.get("summary"),
            dict,
        )

        print(
            "period_changes:",
            "OK" if period_changes_ok else "HATALI",
        )
        print(
            "summary:",
            "OK" if summary_ok else "HATALI",
        )

        analytics_ok = period_changes_ok and summary_ok

    print("\nGenel sonuç")
    print("-" * 72)

    if (
        all_fields_ok
        and performance_ok
        and breakdown_ok
        and analytics_ok
    ):
        print(
            "Dashboard performans veri yapısı eksiksiz "
            "ve uyumlu."
        )
    else:
        print(
            "En az bir alan eksik veya hatalı. "
            "Çıktıyı kontrol et."
        )


if __name__ == "__main__":
    main()
