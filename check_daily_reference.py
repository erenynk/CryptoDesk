from datetime import datetime

from services.daily_reference_service import (
    DailyReferenceService,
)
from services.data_manager import DataManager


LINE = "=" * 84
SUBLINE = "-" * 84


def print_assets(title, assets):
    print()
    print(title)
    print(SUBLINE)

    if not assets:
        print("Varlık yok.")
        return

    for coin, amount in sorted(assets.items()):
        print(f"{coin:<12}: {amount:,.12f}")


def main():
    print(LINE)
    print("Caspian UTC+3 00:00 Referans Kontrolü")
    print(LINE)

    manager = DataManager()

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
    transfers_ok, transfers = (
        manager.okx.get_funding_transfer_bills()
    )
    deposits_ok, deposits = (
        manager.okx.get_deposit_history()
    )
    withdrawals_ok, withdrawals = (
        manager.okx.get_withdrawal_history()
    )

    checks = (
        ("Spot fills", fills_ok, fills),
        ("İç transferler", transfers_ok, transfers),
        ("Yatırmalar", deposits_ok, deposits),
        ("Çekmeler", withdrawals_ok, withdrawals),
    )

    for label, success, result in checks:
        if not success:
            print(f"{label} alınamadı: {result}")
            return

    service = DailyReferenceService(
        okx_service=manager.okx,
        app_timezone=(
            manager.portfolio_history.APP_TIMEZONE
        ),
    )
    result = service.reconstruct(
        portfolio=portfolio,
        fills=fills,
        transfer_bills=transfers,
        deposits=deposits,
        withdrawals=withdrawals,
        reference_time=datetime.now(
            manager.portfolio_history.APP_TIMEZONE
        ),
    )

    print()
    print("Dönem")
    print(SUBLINE)
    print(f"Başlangıç          : {result.period_start}")
    print(f"Bitiş              : {result.period_end}")
    print(f"Uygulanan hareket  : {result.event_count}")

    print()
    print("00:00 Hesap Değerleri")
    print(SUBLINE)
    print(
        f"Funding            : "
        f"{result.funding_usdt:,.8f} USDT"
    )
    print(
        f"Trading            : "
        f"{result.trading_usdt:,.8f} USDT"
    )
    print(
        f"Toplam             : "
        f"{result.total_usdt:,.8f} USDT"
    )

    print_assets(
        "00:00 Funding Varlıkları",
        result.funding_assets,
    )
    print_assets(
        "00:00 Trading Varlıkları",
        result.trading_assets,
    )

    print()
    print("Atlanan Hareketler")
    print(SUBLINE)
    print(f"Toplam             : {len(result.skipped_events)}")

    for event in result.skipped_events[:20]:
        print(event)


if __name__ == "__main__":
    main()
