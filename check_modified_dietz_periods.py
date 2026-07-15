from datetime import datetime

from services.data_manager import DataManager


LINE = "=" * 84
SUBLINE = "-" * 84


def format_value(value, suffix=""):
    if isinstance(value, (int, float)):
        return f"{value:+,.4f}{suffix}"

    return "—"


def main():
    print(LINE)
    print("Caspian Modified Dietz Dönem Kontrolü")
    print(LINE)

    manager = DataManager()

    success, result = manager.refresh_portfolio()

    if not success:
        print(f"Portföy yenilenemedi: {result}")
        return

    portfolio = manager.get_portfolio() or {}
    performance = portfolio.get("performance", {})
    breakdown = portfolio.get("performance_breakdown", {})
    analytics = portfolio.get("analytics", {})
    period_changes = analytics.get("period_changes", {})

    print()
    print("Güncel Hesap Değerleri")
    print(SUBLINE)
    print(
        f"Toplam              : "
        f"{float(portfolio.get('total_usdt', 0.0)):,.2f} USDT"
    )
    print(
        f"Funding             : "
        f"{float(portfolio.get('funding_usdt', 0.0)):,.2f} USDT"
    )
    print(
        f"Trading             : "
        f"{float(portfolio.get('trading_usdt', 0.0)):,.2f} USDT"
    )

    for period in ("1d", "7d", "30d", "90d", "1y"):
        print()
        print(period.upper())
        print(SUBLINE)

        total_percent = (
            performance.get(period)
            if isinstance(performance, dict)
            else None
        )
        funding_percent = (
            (breakdown.get("funding") or {}).get(period)
            if isinstance(breakdown, dict)
            else None
        )
        trading_percent = (
            (breakdown.get("trading") or {}).get(period)
            if isinstance(breakdown, dict)
            else None
        )

        print(
            f"Toplam getiri       : "
            f"{format_value(total_percent, '%')}"
        )
        print(
            f"Funding getiri      : "
            f"{format_value(funding_percent, '%')}"
        )
        print(
            f"Trading getiri      : "
            f"{format_value(trading_percent, '%')}"
        )

        period_data = (
            period_changes.get(period, {})
            if isinstance(period_changes, dict)
            else {}
        )

        for account_name, label in (
            ("total", "Toplam"),
            ("funding", "Funding"),
            ("trading", "Trading"),
        ):
            account_data = period_data.get(account_name, {})

            if not isinstance(account_data, dict):
                account_data = {}

            print(
                f"{label:<8} PNL        : "
                f"{format_value(account_data.get('amount_usdt'), ' USDT')}"
            )
            print(
                f"{label:<8} başlangıç  : "
                f"{format_value(account_data.get('baseline_usdt'), ' USDT')}"
            )
            print(
                f"{label:<8} referans   : "
                f"{account_data.get('baseline_timestamp') or '—'}"
            )

    print()
    print(LINE)
    print("Kontrol")
    print(LINE)

    one_day = period_changes.get("1d", {})

    total_pnl = (
        (one_day.get("total") or {}).get("amount_usdt")
        if isinstance(one_day, dict)
        else None
    )
    funding_pnl = (
        (one_day.get("funding") or {}).get("amount_usdt")
        if isinstance(one_day, dict)
        else None
    )
    trading_pnl = (
        (one_day.get("trading") or {}).get("amount_usdt")
        if isinstance(one_day, dict)
        else None
    )

    if all(
        isinstance(value, (int, float))
        for value in (total_pnl, funding_pnl, trading_pnl)
    ):
        difference = total_pnl - (funding_pnl + trading_pnl)

        print(
            f"1d PNL tutarlılık farkı: "
            f"{difference:+,.8f} USDT"
        )

        if abs(difference) <= 0.05:
            print("Sonuç: 1 günlük hesaplar tutarlı.")
        else:
            print(
                "Sonuç: 1 günlük hesaplarda anlamlı fark var."
            )
    else:
        print(
            "Sonuç: 1 günlük karşılaştırma için yeterli veri yok."
        )


if __name__ == "__main__":
    main()
