import time

from services.data_manager import DataManager


LINE = "=" * 76
SUBLINE = "-" * 76


def print_status(title, status):
    print()
    print(title)
    print(SUBLINE)
    print(f"Cache var mı        : {status.get('cached')}")
    print(f"İşlem sayısı        : {status.get('item_count')}")

    age = status.get("age_seconds")

    if isinstance(age, (int, float)):
        print(f"Cache yaşı          : {age:.2f} saniye")
    else:
        print("Cache yaşı          : —")

    print(
        f"TTL                 : "
        f"{status.get('ttl_seconds')} saniye"
    )


def main():
    print(LINE)
    print("Caspian Cost Basis Cache Kontrolü")
    print(LINE)

    manager = DataManager()
    okx = manager.okx

    okx.clear_spot_fills_cache()

    print_status(
        "Başlangıç durumu",
        okx.get_spot_fills_cache_status(),
    )

    print()
    print("İlk çağrı")
    print(SUBLINE)

    started = time.perf_counter()
    success, result = okx.get_spot_fills_history()
    elapsed = time.perf_counter() - started

    print(f"Başarılı            : {success}")
    print(f"Süre                : {elapsed:.3f} saniye")

    if success and isinstance(result, list):
        print(f"İşlem sayısı        : {len(result)}")
    else:
        print(f"Sonuç               : {result}")
        return

    print_status(
        "İlk çağrı sonrası",
        okx.get_spot_fills_cache_status(),
    )

    print()
    print("İkinci çağrı")
    print(SUBLINE)

    started = time.perf_counter()
    success, result = okx.get_spot_fills_history()
    elapsed = time.perf_counter() - started

    print(f"Başarılı            : {success}")
    print(f"Süre                : {elapsed:.6f} saniye")

    if success and isinstance(result, list):
        print(f"İşlem sayısı        : {len(result)}")
    else:
        print(f"Sonuç               : {result}")
        return

    print_status(
        "İkinci çağrı sonrası",
        okx.get_spot_fills_cache_status(),
    )

    print()
    print("Zorunlu yenileme")
    print(SUBLINE)

    started = time.perf_counter()
    success, result = okx.get_spot_fills_history(
        force_refresh=True
    )
    elapsed = time.perf_counter() - started

    print(f"Başarılı            : {success}")
    print(f"Süre                : {elapsed:.3f} saniye")

    if success and isinstance(result, list):
        print(f"İşlem sayısı        : {len(result)}")
    else:
        print(f"Sonuç               : {result}")
        return

    print_status(
        "Zorunlu yenileme sonrası",
        okx.get_spot_fills_cache_status(),
    )

    print()
    print(LINE)
    print("Genel sonuç")
    print(LINE)

    final_status = okx.get_spot_fills_cache_status()

    if (
        final_status.get("cached")
        and final_status.get("item_count", 0) > 0
    ):
        print("Cost basis işlem geçmişi cache sistemi çalışıyor.")
    else:
        print("Cache doğrulanamadı.")


if __name__ == "__main__":
    main()
