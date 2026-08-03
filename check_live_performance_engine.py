from datetime import datetime

from services.data_manager import DataManager
from services.external_flow_service import ExternalFlowService
from services.performance_engine import PerformanceEngine


LINE = "=" * 76
SUBLINE = "-" * 76


def main():
    print(LINE)
    print("Caspian Canlı Modified Dietz Kontrolü")
    print(LINE)

    manager = DataManager()
    timezone_info = manager.portfolio_history.APP_TIMEZONE
    period_end = datetime.now(timezone_info)

    references = (
        manager.portfolio_history
        .get_performance_reference_snapshots(
            reference_time=period_end
        )
    )
    snapshot = references.get("1d")

    if not isinstance(snapshot, dict):
        print("1 günlük geçerli referans snapshot bulunamadı.")
        return

    period_start = (
        manager.portfolio_history
        ._storage_to_datetime(
            snapshot["timestamp"]
        )
    )

    balance_ok, portfolio = (
        manager.okx.get_spot_balances(
            manager.cache
        )
    )

    if not balance_ok:
        print(f"Portföy alınamadı: {portfolio}")
        return

    deposit_ok, deposits = (
        manager.okx.get_deposit_history()
    )
    withdrawal_ok, withdrawals = (
        manager.okx.get_withdrawal_history()
    )

    if not deposit_ok:
        print(f"Yatırma geçmişi alınamadı: {deposits}")
        return

    if not withdrawal_ok:
        print(f"Çekme geçmişi alınamadı: {withdrawals}")
        return

    flow_service = ExternalFlowService(
        okx_service=manager.okx,
        app_timezone=timezone_info,
    )
    flows, skipped = flow_service.build_cash_flows(
        deposits=deposits,
        withdrawals=withdrawals,
        period_start=period_start,
        period_end=period_end,
    )

    result = PerformanceEngine.calculate(
        start_value_usdt=snapshot["total_usdt"],
        end_value_usdt=portfolio["total_usdt"],
        period_start=period_start,
        period_end=period_end,
        cash_flows=flows,
    )

    print()
    print("Dönem")
    print(SUBLINE)
    print(f"Başlangıç          : {period_start}")
    print(f"Bitiş              : {period_end}")

    print()
    print("Para Akışları")
    print(SUBLINE)

    if not flows:
        print("Dönem içinde tamamlanmış harici akış yok.")
    else:
        for flow in flows:
            print(
                f"{flow.timestamp} | "
                f"{flow.amount_usdt:+,.2f} USDT | "
                f"{flow.description}"
            )

    print()
    print("Modified Dietz Sonucu")
    print(SUBLINE)
    print(
        f"Başlangıç değeri   : "
        f"{result.start_value_usdt:,.2f} USDT"
    )
    print(
        f"Bitiş değeri       : "
        f"{result.end_value_usdt:,.2f} USDT"
    )
    print(
        f"Net akış           : "
        f"{result.net_flow_usdt:+,.2f} USDT"
    )
    print(
        f"Ağırlıklı akış     : "
        f"{result.weighted_flow_usdt:+,.2f} USDT"
    )
    print(
        f"Gerçek PNL         : "
        f"{result.pnl_usdt:+,.2f} USDT"
    )

    if result.return_percent is None:
        print("Getiri             : —")
    else:
        print(
            f"Getiri             : "
            f"{result.return_percent:+.4f}%"
        )

    print()
    print("Atlanan Kayıtlar")
    print(SUBLINE)
    print(f"Toplam             : {len(skipped)}")

    for item in skipped[:10]:
        record = item["item"]
        print(
            f"{item['type']} | "
            f"{record.get('ccy')} | "
            f"{record.get('amt')} | "
            f"{item['reason']}"
        )


if __name__ == "__main__":
    main()
