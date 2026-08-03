import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path


APP_TIMEZONE = timezone(timedelta(hours=3))

PERIODS = {
    "1 Gün": timedelta(days=1),
    "7 Gün": timedelta(days=7),
    "30 Gün": timedelta(days=30),
    "90 Gün": timedelta(days=90),
    "1 Yıl": timedelta(days=365),
}


def get_database_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")

    if local_app_data:
        return Path(local_app_data) / "CryptoDesk" / "cryptodesk.db"

    return Path.home() / ".cryptodesk" / "cryptodesk.db"


def parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=APP_TIMEZONE)

    return parsed.astimezone(APP_TIMEZONE)


def format_duration(seconds: float) -> str:
    seconds = max(0, int(seconds))

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)

    parts = []

    if days:
        parts.append(f"{days} gün")
    if hours:
        parts.append(f"{hours} saat")
    if minutes:
        parts.append(f"{minutes} dakika")
    if secs or not parts:
        parts.append(f"{secs} saniye")

    return " ".join(parts)


def main() -> None:
    database_path = get_database_path()

    print("=" * 76)
    print("CryptoDesk Portfolio History Durum Kontrolü")
    print("=" * 76)
    print(f"Veritabanı: {database_path}")

    if not database_path.exists():
        print("\nHATA: Veritabanı dosyası bulunamadı.")
        return

    try:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row

            table = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                  AND name = 'portfolio_history'
                """
            ).fetchone()

            if table is None:
                print("\nHATA: portfolio_history tablosu bulunamadı.")
                return

            rows = connection.execute(
                """
                SELECT
                    id,
                    timestamp,
                    total_usdt,
                    funding_usdt,
                    trading_usdt,
                    asset_count
                FROM portfolio_history
                ORDER BY timestamp ASC
                """
            ).fetchall()

            if not rows:
                print("\nHenüz snapshot kaydı bulunmuyor.")
                return

            first_time = parse_timestamp(rows[0]["timestamp"])
            last_time = parse_timestamp(rows[-1]["timestamp"])
            now = datetime.now(APP_TIMEZONE)

            print(f"\nToplam snapshot: {len(rows)}")
            print(f"İlk kayıt: {first_time.isoformat(timespec='seconds')}")
            print(f"Son kayıt: {last_time.isoformat(timespec='seconds')}")
            print(
                "Toplam geçmiş süresi: "
                f"{format_duration((last_time - first_time).total_seconds())}"
            )

            print("\nSnapshot aralıkları")
            print("-" * 76)

            if len(rows) < 2:
                print("Aralık kontrolü için en az 2 kayıt gerekli.")
            else:
                intervals = []

                for previous, current in zip(rows, rows[1:]):
                    previous_time = parse_timestamp(previous["timestamp"])
                    current_time = parse_timestamp(current["timestamp"])
                    intervals.append(
                        (current_time - previous_time).total_seconds()
                    )

                print(
                    "En kısa aralık: "
                    f"{format_duration(min(intervals))}"
                )
                print(
                    "En uzun aralık: "
                    f"{format_duration(max(intervals))}"
                )
                print(
                    "Ortalama aralık: "
                    f"{format_duration(sum(intervals) / len(intervals))}"
                )

                under_five_minutes = sum(
                    1 for interval in intervals if interval < 300
                )

                print(
                    "5 dakikadan kısa aralık sayısı: "
                    f"{under_five_minutes}"
                )

            print("\nPerformans dönemleri")
            print("-" * 76)

            for label, delta in PERIODS.items():
                target_time = now - delta

                if first_time <= target_time:
                    status = "HAZIR"
                else:
                    remaining = (
                        first_time + delta - now
                    ).total_seconds()
                    status = (
                        "BEKLENİYOR — "
                        f"{format_duration(remaining)} kaldı"
                    )

                print(f"{label:<8}: {status}")

            latest = rows[-1]

            print("\nSon snapshot")
            print("-" * 76)
            print(f"Toplam: {float(latest['total_usdt']):.8f} USDT")
            print(f"Funding: {float(latest['funding_usdt']):.8f} USDT")
            print(f"Trading: {float(latest['trading_usdt']):.8f} USDT")
            print(f"Varlık sayısı: {int(latest['asset_count'])}")

            print("\nGenel sonuç")
            print("-" * 76)

            if len(rows) >= 2:
                print("Portfolio History düzenli kayıt topluyor.")
            else:
                print(
                    "İlk snapshot mevcut. İkinci kayıt için uygulamayı "
                    "en az 5 dakika açık bırak."
                )

    except sqlite3.Error as error:
        print(f"\nSQLite hatası: {error}")


if __name__ == "__main__":
    main()
