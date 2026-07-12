import os
import sqlite3
from pathlib import Path


def get_database_path() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA")

    if local_app_data:
        return Path(local_app_data) / "CryptoDesk" / "cryptodesk.db"

    return Path.home() / ".cryptodesk" / "cryptodesk.db"


def main() -> None:
    database_path = get_database_path()

    print("=" * 72)
    print("CryptoDesk Portfolio History Kontrolü")
    print("=" * 72)
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
                print(
                    "Uygulamayı güncel dosyalarla en az bir kez çalıştır."
                )
                return

            count_row = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM portfolio_history
                """
            ).fetchone()

            snapshot_count = int(count_row["total"])

            print("\nTablo durumu: OK")
            print(f"Toplam snapshot: {snapshot_count}")

            if snapshot_count == 0:
                print("\nHenüz snapshot kaydı yok.")
                print(
                    "Uygulamayı aç, portföyün başarıyla yenilenmesini bekle "
                    "ve bu kontrolü tekrar çalıştır."
                )
                return

            first_row = connection.execute(
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
                LIMIT 1
                """
            ).fetchone()

            last_row = connection.execute(
                """
                SELECT
                    id,
                    timestamp,
                    total_usdt,
                    funding_usdt,
                    trading_usdt,
                    asset_count
                FROM portfolio_history
                ORDER BY timestamp DESC
                LIMIT 1
                """
            ).fetchone()

            print("\nİlk snapshot")
            print("-" * 72)
            print(f"ID: {first_row['id']}")
            print(f"Zaman: {first_row['timestamp']}")
            print(f"Toplam: {first_row['total_usdt']:.8f} USDT")
            print(f"Funding: {first_row['funding_usdt']:.8f} USDT")
            print(f"Trading: {first_row['trading_usdt']:.8f} USDT")
            print(f"Varlık sayısı: {first_row['asset_count']}")

            print("\nSon snapshot")
            print("-" * 72)
            print(f"ID: {last_row['id']}")
            print(f"Zaman: {last_row['timestamp']}")
            print(f"Toplam: {last_row['total_usdt']:.8f} USDT")
            print(f"Funding: {last_row['funding_usdt']:.8f} USDT")
            print(f"Trading: {last_row['trading_usdt']:.8f} USDT")
            print(f"Varlık sayısı: {last_row['asset_count']}")

            invalid_rows = connection.execute(
                """
                SELECT COUNT(*) AS total
                FROM portfolio_history
                WHERE total_usdt < 0
                   OR funding_usdt < 0
                   OR trading_usdt < 0
                   OR asset_count < 0
                """
            ).fetchone()

            invalid_count = int(invalid_rows["total"])

            print("\nVeri kontrolü")
            print("-" * 72)
            print(f"Geçersiz kayıt sayısı: {invalid_count}")

            if invalid_count == 0:
                print("Sonuç: Portfolio History altyapısı çalışıyor.")
            else:
                print(
                    "UYARI: Geçersiz değer içeren snapshot kayıtları bulundu."
                )

    except sqlite3.Error as error:
        print(f"\nSQLite hatası: {error}")


if __name__ == "__main__":
    main()
