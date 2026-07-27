import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.portfolio_history_service import PortfolioHistoryService


APP_TIMEZONE = timezone(timedelta(hours=3))


def create_service() -> tuple[PortfolioHistoryService, Path]:
    temp_dir = Path(tempfile.mkdtemp(prefix="cryptodesk_history_test_"))
    db_path = temp_dir / "test_history.db"

    service = PortfolioHistoryService(
        db_path=db_path,
        snapshot_interval_seconds=0,
    )

    return service, db_path


def print_result(
    title: str,
    actual,
    expected,
) -> bool:
    passed = actual == expected
    status = "BAŞARILI" if passed else "HATALI"

    print(f"{title:<52}: {status}")
    print(f"  Beklenen: {expected}")
    print(f"  Gerçek:   {actual}")

    return passed


def main() -> None:
    service, db_path = create_service()

    print("=" * 76)
    print("CryptoDesk Performans Boşluk Kuralı Testi")
    print("=" * 76)
    print(f"Geçici veritabanı: {db_path}")

    reference_time = datetime(
        2026,
        7,
        20,
        12,
        0,
        0,
        tzinfo=APP_TIMEZONE,
    )

    results = []

    print("\nSenaryo 1 — Hedef tarihe yakın geçerli kayıt")
    print("-" * 76)

    service.save_snapshot(
        total_usdt=1000.0,
        funding_usdt=400.0,
        trading_usdt=600.0,
        timestamp=reference_time - timedelta(days=1, hours=1),
        force=True,
    )

    performance = service.calculate_performance(
        current_total_usdt=1100.0,
        reference_time=reference_time,
        value_field="total_usdt",
    )

    results.append(
        print_result(
            "1 günlük performans hesaplandı",
            performance["1d"],
            10.0,
        )
    )

    service.clear_history()

    print("\nSenaryo 2 — Hedef tarihten sonraki kayıt kullanılmamalı")
    print("-" * 76)

    service.save_snapshot(
        total_usdt=1000.0,
        funding_usdt=400.0,
        trading_usdt=600.0,
        timestamp=reference_time - timedelta(hours=23),
        force=True,
    )

    performance = service.calculate_performance(
        current_total_usdt=1100.0,
        reference_time=reference_time,
        value_field="total_usdt",
    )

    results.append(
        print_result(
            "Gelecekteki referans reddedildi",
            performance["1d"],
            None,
        )
    )

    service.clear_history()

    print("\nSenaryo 3 — Çok eski kayıt reddedilmeli")
    print("-" * 76)

    service.save_snapshot(
        total_usdt=1000.0,
        funding_usdt=400.0,
        trading_usdt=600.0,
        timestamp=reference_time - timedelta(days=2),
        force=True,
    )

    performance = service.calculate_performance(
        current_total_usdt=1100.0,
        reference_time=reference_time,
        value_field="total_usdt",
    )

    results.append(
        print_result(
            "1 günlük dönem için 2 günlük kayıt reddedildi",
            performance["1d"],
            None,
        )
    )

    service.clear_history()

    print("\nSenaryo 4 — Funding ve Trading ayrı hesaplanmalı")
    print("-" * 76)

    service.save_snapshot(
        total_usdt=1000.0,
        funding_usdt=400.0,
        trading_usdt=600.0,
        timestamp=reference_time - timedelta(days=1, hours=1),
        force=True,
    )

    breakdown = service.calculate_performance_breakdown(
        current_total_usdt=1100.0,
        current_funding_usdt=420.0,
        current_trading_usdt=680.0,
        reference_time=reference_time,
    )

    results.append(
        print_result(
            "Toplam performans",
            breakdown["total"]["1d"],
            10.0,
        )
    )
    results.append(
        print_result(
            "Funding performansı",
            breakdown["funding"]["1d"],
            5.0,
        )
    )
    results.append(
        print_result(
            "Trading performansı",
            breakdown["trading"]["1d"],
            13.33,
        )
    )

    print("\nGenel sonuç")
    print("-" * 76)

    if all(results):
        print("Tüm performans boşluk kuralları doğru çalışıyor.")
    else:
        print("En az bir test başarısız oldu.")


if __name__ == "__main__":
    main()
