from datetime import datetime, timedelta, timezone

from services.performance_engine import (
    CashFlow,
    PerformanceEngine,
)


APP_TIMEZONE = timezone(timedelta(hours=3))


def run_case(
    title,
    start_value,
    end_value,
    start_time,
    end_time,
    flows,
):
    result = PerformanceEngine.calculate(
        start_value_usdt=start_value,
        end_value_usdt=end_value,
        period_start=start_time,
        period_end=end_time,
        cash_flows=flows,
    )

    print("=" * 72)
    print(title)
    print("=" * 72)
    print(f"Başlangıç değeri : {result.start_value_usdt:,.2f} USDT")
    print(f"Bitiş değeri     : {result.end_value_usdt:,.2f} USDT")
    print(f"Net akış         : {result.net_flow_usdt:+,.2f} USDT")
    print(f"Ağırlıklı akış   : {result.weighted_flow_usdt:+,.2f} USDT")
    print(f"PNL              : {result.pnl_usdt:+,.2f} USDT")

    if result.return_percent is None:
        print("Getiri           : —")
    else:
        print(f"Getiri           : {result.return_percent:+.4f}%")

    print(f"Akış sayısı      : {result.flow_count}")
    print()


def main():
    end_time = datetime.now(APP_TIMEZONE)
    start_time = end_time - timedelta(days=1)

    run_case(
        title="Akışsız portföy",
        start_value=1000.0,
        end_value=1010.0,
        start_time=start_time,
        end_time=end_time,
        flows=[],
    )

    run_case(
        title="Gün ortasında 500 USDT giriş",
        start_value=1000.0,
        end_value=1510.0,
        start_time=start_time,
        end_time=end_time,
        flows=[
            CashFlow(
                amount_usdt=500.0,
                timestamp=start_time + timedelta(hours=12),
                description="Deposit",
            )
        ],
    )

    run_case(
        title="Gün ortasında 200 USDT çıkış",
        start_value=1000.0,
        end_value=810.0,
        start_time=start_time,
        end_time=end_time,
        flows=[
            CashFlow(
                amount_usdt=-200.0,
                timestamp=start_time + timedelta(hours=12),
                description="Withdraw",
            )
        ],
    )


if __name__ == "__main__":
    main()
