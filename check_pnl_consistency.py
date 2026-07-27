from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from services.cost_basis_service import CostBasisService
from services.okx_service import OKXService
from services.price_cache import PriceCache


REPORT_DIRECTORY = Path("pnl_audit_reports")
DEFAULT_MAX_PAGES = 20
DEFAULT_PAGE_LIMIT = 100

OKX_SPOT_FIELDS = (
    "ccy",
    "eq",
    "cashBal",
    "availBal",
    "frozenBal",
    "eqUsd",
    "spotBal",
    "openAvgPx",
    "accAvgPx",
    "spotUpl",
    "spotUplRatio",
    "totalPnl",
    "totalPnlRatio",
    "uTime",
)


def safe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None

    if not math.isfinite(number):
        return None

    return number


def value_or_none(mapping: dict[str, Any], key: str) -> float | None:
    return safe_float(mapping.get(key))


def format_number(value: float | None, digits: int = 8) -> str:
    if value is None:
        return "—"

    return f"{value:,.{digits}f}"


def format_percent(value: float | None) -> str:
    if value is None:
        return "—"

    return f"{value:+.4f}%"


def normalize_symbols(raw_symbols: list[str]) -> set[str]:
    symbols: set[str] = set()

    for raw_value in raw_symbols:
        for part in raw_value.split(","):
            symbol = part.strip().upper()

            if symbol:
                symbols.add(symbol)

    return symbols



def okx_response_error(
    response: Any,
    context: str,
) -> str:
    status_code = getattr(response, "status_code", "?")
    code = None
    message = None

    try:
        payload = response.json()
    except Exception:
        payload = None

    if isinstance(payload, dict):
        code = payload.get("code")
        message = payload.get("msg")

    parts = [f"{context}: HTTP {status_code}"]

    if code not in (None, ""):
        parts.append(f"OKX kodu {code}")

    if message:
        parts.append(str(message))

    if not message:
        try:
            body = str(response.text or "").strip()
        except Exception:
            body = ""

        if body:
            parts.append(body[:300])

    return " | ".join(parts)


def fetch_public_spot_prices(
    service: OKXService,
) -> tuple[bool, dict[str, float] | str]:
    path = "/api/v5/market/tickers?instType=SPOT"

    try:
        response = service.session.get(
            service.client.BASE_URL + path,
            timeout=15,
        )

        if response.status_code >= 400:
            return False, okx_response_error(
                response,
                "OKX Spot fiyatları alınamadı",
            )

        payload = response.json()

        if payload.get("code") != "0":
            return False, (
                payload.get("msg")
                or "OKX Spot fiyatları alınamadı."
            )

        prices: dict[str, float] = {}

        for item in payload.get("data", []):
            if not isinstance(item, dict):
                continue

            instrument = str(
                item.get("instId", "")
            ).strip().upper()

            if not instrument.endswith("-USDT"):
                continue

            price = safe_float(item.get("last"))

            if price is None or price <= 0:
                continue

            coin = instrument.removesuffix("-USDT")
            prices[coin] = price

        prices["USDT"] = 1.0
        return True, prices

    except Exception as error:
        return False, f"OKX Spot fiyatları alınamadı: {error}"


def build_trading_assets(
    raw_details: dict[str, dict[str, Any]],
    prices: dict[str, float],
) -> list[dict[str, Any]]:
    assets: list[dict[str, Any]] = []

    for coin, detail in raw_details.items():
        if not isinstance(detail, dict):
            continue

        spot_balance = value_or_none(detail, "spotBal")
        equity = value_or_none(detail, "eq")

        quantity = (
            spot_balance
            if spot_balance is not None and spot_balance > 0
            else equity
        )

        if quantity is None or quantity <= 0:
            continue

        price = 1.0 if coin == "USDT" else prices.get(coin)

        if price is None or price <= 0:
            continue

        available = value_or_none(detail, "availBal")

        assets.append(
            {
                "coin": coin,
                "total": quantity,
                "available": (
                    available
                    if available is not None
                    else quantity
                ),
                "funding_total": 0.0,
                "trading_total": quantity,
                "price": price,
                "usdt_value": quantity * price,
            }
        )

    assets.sort(
        key=lambda item: item.get("usdt_value", 0.0),
        reverse=True,
    )
    return assets


def fetch_raw_trading_details(
    service: OKXService,
) -> tuple[bool, dict[str, dict[str, Any]] | str]:
    if service.client is None:
        return False, "API bilgileri bulunamadı."

    path = "/api/v5/account/balance"

    try:
        response = service.session.get(
            service.client.BASE_URL + path,
            headers=service.client._headers("GET", path),
            timeout=15,
        )

        if response.status_code >= 400:
            return False, okx_response_error(
                response,
                "OKX Trading bakiye ayrıntıları alınamadı",
            )

        payload = response.json()

        if payload.get("code") != "0":
            return False, (
                payload.get("msg")
                or "OKX Trading bakiye ayrıntıları alınamadı."
            )

        data = payload.get("data", [])
        details = (
            data[0].get("details", [])
            if isinstance(data, list) and data
            else []
        )

        if not isinstance(details, list):
            return False, "OKX Trading bakiye ayrıntıları geçersiz."

        result: dict[str, dict[str, Any]] = {}

        for detail in details:
            if not isinstance(detail, dict):
                continue

            coin = str(detail.get("ccy", "")).strip().upper()

            if not coin:
                continue

            result[coin] = {
                field: detail.get(field)
                for field in OKX_SPOT_FIELDS
            }

        return True, result

    except Exception as error:
        return False, f"OKX Trading bakiye ayrıntıları alınamadı: {error}"


def fill_coin(fill: dict[str, Any]) -> str:
    instrument = str(fill.get("instId", "")).strip().upper()

    if not instrument.endswith("-USDT"):
        return ""

    return instrument.removesuffix("-USDT").strip()


def group_fills(
    fills: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for fill in fills:
        if not isinstance(fill, dict):
            continue

        coin = fill_coin(fill)

        if coin:
            result[coin].append(fill)

    return dict(result)


def group_movements(
    records: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for record in records:
        if not isinstance(record, dict):
            continue

        coin = str(record.get("ccy", "")).strip().upper()

        if coin:
            result[coin].append(record)

    return dict(result)


def timestamp_text(value: Any) -> str | None:
    timestamp = safe_float(value)

    if timestamp is None or timestamp <= 0:
        return None

    try:
        return datetime.fromtimestamp(
            timestamp / 1000,
            tz=UTC,
        ).isoformat()
    except (OSError, OverflowError, ValueError):
        return None


def summarize_fills(
    coin: str,
    fills: list[dict[str, Any]],
) -> dict[str, Any]:
    buy_quantity = 0.0
    sell_quantity = 0.0
    buy_quote_cost = 0.0
    sell_quote_value = 0.0
    fee_totals: dict[str, float] = defaultdict(float)
    timestamps: list[float] = []
    buy_count = 0
    sell_count = 0

    for fill in fills:
        side = str(fill.get("side", "")).strip().lower()
        size = safe_float(fill.get("fillSz")) or 0.0
        price = safe_float(fill.get("fillPx")) or 0.0
        fee = safe_float(fill.get("fee")) or 0.0
        fee_currency = str(
            fill.get("feeCcy", "")
        ).strip().upper()
        timestamp = safe_float(fill.get("ts"))

        if timestamp is not None and timestamp > 0:
            timestamps.append(timestamp)

        if fee_currency and fee != 0:
            fee_totals[fee_currency] += fee

        if side == "buy":
            buy_count += 1
            quantity, quote_cost = CostBasisService._buy_values(
                coin,
                fill,
            )
            buy_quantity += quantity
            buy_quote_cost += quote_cost
        elif side == "sell":
            sell_count += 1
            removed_quantity = CostBasisService._sell_quantity(
                coin,
                fill,
            )
            sell_quantity += removed_quantity
            sell_quote_value += size * price

    return {
        "fill_count": len(fills),
        "buy_fill_count": buy_count,
        "sell_fill_count": sell_count,
        "buy_quantity": buy_quantity,
        "sell_quantity": sell_quantity,
        "net_fill_quantity": buy_quantity - sell_quantity,
        "buy_quote_cost_usdt": buy_quote_cost,
        "sell_quote_value_usdt": sell_quote_value,
        "fee_totals": dict(sorted(fee_totals.items())),
        "first_fill_at": (
            timestamp_text(min(timestamps))
            if timestamps
            else None
        ),
        "last_fill_at": (
            timestamp_text(max(timestamps))
            if timestamps
            else None
        ),
    }


def sum_movement_amount(
    records: list[dict[str, Any]],
) -> float:
    total = 0.0

    for record in records:
        amount = safe_float(record.get("amt"))

        if amount is None:
            amount = safe_float(record.get("sz"))

        if amount is not None:
            total += abs(amount)

    return total


def calculate_difference_percent(
    caspian_value: float | None,
    okx_value: float | None,
) -> float | None:
    if (
        caspian_value is None
        or okx_value is None
        or abs(okx_value) <= 1e-18
    ):
        return None

    return (caspian_value - okx_value) / abs(okx_value) * 100


def calculate_difference(
    caspian_value: float | None,
    okx_value: float | None,
) -> float | None:
    if caspian_value is None or okx_value is None:
        return None

    return caspian_value - okx_value


def result_value(
    result: dict[str, Any] | None,
    key: str,
) -> float | None:
    if not isinstance(result, dict):
        return None

    return safe_float(result.get(key))


def infer_okx_price(
    okx_detail: dict[str, Any],
) -> float | None:
    balance = value_or_none(okx_detail, "spotBal")
    average = value_or_none(okx_detail, "openAvgPx")
    pnl = value_or_none(okx_detail, "spotUpl")

    if (
        balance is None
        or average is None
        or pnl is None
        or balance <= 0
    ):
        return None

    return average + pnl / balance


def build_diagnostics(
    *,
    coin: str,
    asset: dict[str, Any],
    okx_detail: dict[str, Any],
    fill_summary: dict[str, Any],
    deposits: list[dict[str, Any]],
    withdrawals: list[dict[str, Any]],
    transfers: list[dict[str, Any]],
    caspian_trading_result: dict[str, Any] | None,
) -> list[str]:
    diagnostics: list[str] = []
    current_total = safe_float(asset.get("total")) or 0.0
    funding_total = safe_float(asset.get("funding_total")) or 0.0
    trading_total = safe_float(asset.get("trading_total")) or 0.0
    net_fill_quantity = safe_float(
        fill_summary.get("net_fill_quantity")
    ) or 0.0
    estimated_opening_quantity = current_total - net_fill_quantity
    allowed_difference = CostBasisService._allowed_difference(
        current_total
    )

    if funding_total > allowed_difference:
        diagnostics.append(
            "OKX spot PNL alanları Trading bakiyesini temsil eder; "
            "Caspian toplam satırı Funding bakiyesini de içerir."
        )

    if deposits:
        diagnostics.append(
            "Harici deposit geçmişi var. OKX average cost, deposit "
            "anındaki fiyatı maliyete katabilir; mevcut Caspian ledger "
            "deposit maliyetini işlemiyor."
        )

    if withdrawals:
        diagnostics.append(
            "Harici withdrawal geçmişi var. Mevcut Caspian ledger "
            "withdrawal hareketini açık maliyet zincirinde işlemiyor."
        )

    if abs(estimated_opening_quantity) > allowed_difference:
        diagnostics.append(
            "Erişilebilir fill geçmişi güncel toplam bakiyeyi tek başına "
            "açıklamıyor. Üç aydan eski işlem, deposit, Earn/bot veya "
            "başka bir kaynak olabilir."
        )

    fee_totals = fill_summary.get("fee_totals", {})

    if isinstance(fee_totals, dict) and fee_totals:
        non_quote_fees = [
            currency
            for currency, amount in fee_totals.items()
            if currency != "USDT" and abs(amount) > 0
        ]

        if non_quote_fees:
            diagnostics.append(
                "Coin cinsinden komisyon bulundu: "
                + ", ".join(sorted(non_quote_fees))
                + ". Net miktar ile fillSz ayrımı kontrol edilmeli."
            )

    okx_average = value_or_none(okx_detail, "openAvgPx")
    caspian_average = result_value(
        caspian_trading_result,
        "average_price",
    )

    if okx_average is not None and caspian_average is not None:
        average_difference = calculate_difference_percent(
            caspian_average,
            okx_average,
        )

        if (
            average_difference is not None
            and abs(average_difference) >= 0.05
        ):
            diagnostics.append(
                "Ortalama maliyet farkı fiyat farkından bağımsız olarak "
                "anlamlı görünüyor."
            )

    if caspian_trading_result is None and trading_total > allowed_difference:
        diagnostics.append(
            "Caspian Trading maliyetini doğrulayamıyor; PNL üretmemeli."
        )

    if not transfers and funding_total > allowed_difference:
        diagnostics.append(
            "Funding bakiyesi var fakat erişilebilir hesaplar arası "
            "transfer kaydı yok. Funding maliyeti doğrulanamayabilir."
        )

    if not diagnostics:
        diagnostics.append(
            "Belirgin deposit, withdrawal, eksik geçmiş veya hesap "
            "ayrımı sinyali bulunmadı. Fiyat zamanı ve komisyon etkisi "
            "öncelikli karşılaştırılmalı."
        )

    return diagnostics


def build_report_rows(
    *,
    assets: list[dict[str, Any]],
    cost_basis: dict[str, dict[str, Any]],
    raw_details: dict[str, dict[str, Any]],
    fills_by_coin: dict[str, list[dict[str, Any]]],
    transfers_by_coin: dict[str, list[dict[str, Any]]],
    deposits_by_coin: dict[str, list[dict[str, Any]]],
    withdrawals_by_coin: dict[str, list[dict[str, Any]]],
    selected_symbols: set[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for asset in assets:
        if not isinstance(asset, dict):
            continue

        coin = str(asset.get("coin", "")).strip().upper()

        if not coin or coin == "USDT":
            continue

        if selected_symbols and coin not in selected_symbols:
            continue

        coin_result = cost_basis.get(coin, {})
        total_result = (
            coin_result.get("total")
            if isinstance(coin_result, dict)
            else None
        )
        funding_result = (
            coin_result.get("funding")
            if isinstance(coin_result, dict)
            else None
        )
        trading_result = (
            coin_result.get("trading")
            if isinstance(coin_result, dict)
            else None
        )
        okx_detail = raw_details.get(coin, {})
        fills = fills_by_coin.get(coin, [])
        transfers = transfers_by_coin.get(coin, [])
        deposits = deposits_by_coin.get(coin, [])
        withdrawals = withdrawals_by_coin.get(coin, [])
        fill_summary = summarize_fills(coin, fills)

        current_price = safe_float(asset.get("price"))
        okx_implied_price = infer_okx_price(okx_detail)
        caspian_trading_average = result_value(
            trading_result,
            "average_price",
        )
        caspian_trading_pnl = result_value(
            trading_result,
            "pnl_usdt",
        )
        caspian_trading_pnl_percent = result_value(
            trading_result,
            "pnl_percent",
        )
        okx_open_average = value_or_none(
            okx_detail,
            "openAvgPx",
        )
        okx_spot_pnl = value_or_none(
            okx_detail,
            "spotUpl",
        )
        okx_spot_pnl_ratio = value_or_none(
            okx_detail,
            "spotUplRatio",
        )
        okx_spot_pnl_percent = (
            okx_spot_pnl_ratio * 100
            if okx_spot_pnl_ratio is not None
            else None
        )
        current_total = safe_float(asset.get("total")) or 0.0
        net_fill_quantity = safe_float(
            fill_summary.get("net_fill_quantity")
        ) or 0.0

        row = {
            "coin": coin,
            "current_price": current_price,
            "okx_implied_price": okx_implied_price,
            "price_difference": calculate_difference(
                current_price,
                okx_implied_price,
            ),
            "price_difference_percent": calculate_difference_percent(
                current_price,
                okx_implied_price,
            ),
            "total_quantity": safe_float(asset.get("total")),
            "funding_quantity": safe_float(
                asset.get("funding_total")
            ),
            "trading_quantity": safe_float(
                asset.get("trading_total")
            ),
            "okx_spot_balance": value_or_none(
                okx_detail,
                "spotBal",
            ),
            "caspian_total_average": result_value(
                total_result,
                "average_price",
            ),
            "caspian_total_pnl_usdt": result_value(
                total_result,
                "pnl_usdt",
            ),
            "caspian_total_pnl_percent": result_value(
                total_result,
                "pnl_percent",
            ),
            "caspian_funding_average": result_value(
                funding_result,
                "average_price",
            ),
            "caspian_funding_pnl_usdt": result_value(
                funding_result,
                "pnl_usdt",
            ),
            "caspian_funding_pnl_percent": result_value(
                funding_result,
                "pnl_percent",
            ),
            "caspian_trading_average": caspian_trading_average,
            "caspian_trading_pnl_usdt": caspian_trading_pnl,
            "caspian_trading_pnl_percent": (
                caspian_trading_pnl_percent
            ),
            "okx_open_average": okx_open_average,
            "okx_accumulated_average": value_or_none(
                okx_detail,
                "accAvgPx",
            ),
            "okx_spot_pnl_usdt": okx_spot_pnl,
            "okx_spot_pnl_percent": okx_spot_pnl_percent,
            "okx_total_pnl_usdt": value_or_none(
                okx_detail,
                "totalPnl",
            ),
            "okx_total_pnl_ratio_raw": value_or_none(
                okx_detail,
                "totalPnlRatio",
            ),
            "trading_average_difference": calculate_difference(
                caspian_trading_average,
                okx_open_average,
            ),
            "trading_average_difference_percent": (
                calculate_difference_percent(
                    caspian_trading_average,
                    okx_open_average,
                )
            ),
            "trading_pnl_difference_usdt": calculate_difference(
                caspian_trading_pnl,
                okx_spot_pnl,
            ),
            "trading_pnl_percent_difference_points": (
                calculate_difference(
                    caspian_trading_pnl_percent,
                    okx_spot_pnl_percent,
                )
            ),
            "fill_count": fill_summary["fill_count"],
            "buy_fill_count": fill_summary["buy_fill_count"],
            "sell_fill_count": fill_summary["sell_fill_count"],
            "buy_quantity": fill_summary["buy_quantity"],
            "sell_quantity": fill_summary["sell_quantity"],
            "net_fill_quantity": net_fill_quantity,
            "estimated_opening_quantity": (
                current_total - net_fill_quantity
            ),
            "buy_quote_cost_usdt": fill_summary[
                "buy_quote_cost_usdt"
            ],
            "sell_quote_value_usdt": fill_summary[
                "sell_quote_value_usdt"
            ],
            "fee_totals": fill_summary["fee_totals"],
            "first_fill_at": fill_summary["first_fill_at"],
            "last_fill_at": fill_summary["last_fill_at"],
            "transfer_count": len(transfers),
            "deposit_count": len(deposits),
            "deposit_amount": sum_movement_amount(deposits),
            "withdrawal_count": len(withdrawals),
            "withdrawal_amount": sum_movement_amount(withdrawals),
            "okx_raw_fields": okx_detail,
        }
        row["diagnostics"] = build_diagnostics(
            coin=coin,
            asset=asset,
            okx_detail=okx_detail,
            fill_summary=fill_summary,
            deposits=deposits,
            withdrawals=withdrawals,
            transfers=transfers,
            caspian_trading_result=trading_result,
        )
        rows.append(row)

    rows.sort(
        key=lambda item: abs(
            safe_float(
                item.get("trading_pnl_difference_usdt")
            )
            or 0.0
        ),
        reverse=True,
    )
    return rows


def csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
        )

    return value


def write_reports(
    rows: list[dict[str, Any]],
    metadata: dict[str, Any],
) -> tuple[Path, Path]:
    REPORT_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = REPORT_DIRECTORY / f"pnl_audit_{timestamp}.json"
    csv_path = REPORT_DIRECTORY / f"pnl_audit_{timestamp}.csv"

    json_path.write_text(
        json.dumps(
            {
                "metadata": metadata,
                "assets": rows,
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    fieldnames = sorted(
        {
            key
            for row in rows
            for key in row
        }
    )

    with csv_path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )
        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    key: csv_value(row.get(key))
                    for key in fieldnames
                }
            )

    return json_path, csv_path


def print_summary(rows: list[dict[str, Any]]) -> None:
    if not rows:
        print("Karşılaştırılacak varlık bulunamadı.")
        return

    print()
    print(
        "Coin      Caspian Avg       OKX Avg           Avg Fark %    "
        "Caspian PNL     OKX PNL         PNL Fark"
    )
    print("-" * 108)

    for row in rows:
        print(
            f"{row['coin']:<9} "
            f"{format_number(row.get('caspian_trading_average'), 8):>16} "
            f"{format_number(row.get('okx_open_average'), 8):>16} "
            f"{format_percent(row.get('trading_average_difference_percent')):>12} "
            f"{format_number(row.get('caspian_trading_pnl_usdt'), 4):>15} "
            f"{format_number(row.get('okx_spot_pnl_usdt'), 4):>15} "
            f"{format_number(row.get('trading_pnl_difference_usdt'), 4):>12}"
        )

    print()
    print("Tanı notları:")

    for row in rows:
        print(f"\n{row['coin']}:")

        for note in row.get("diagnostics", []):
            print(f"  - {note}")


def require_success(
    name: str,
    result: tuple[bool, Any],
    *,
    optional: bool = False,
) -> Any:
    success, payload = result

    if success:
        return payload

    if optional:
        print(
            f"Uyarı: {name} alınamadı: {payload}",
            file=sys.stderr,
        )
        return []

    raise RuntimeError(f"{name} alınamadı: {payload}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Caspian maliyet/PNL hesaplarını OKX'in Trading hesabındaki "
            "openAvgPx, spotUpl ve spotUplRatio alanlarıyla salt okunur "
            "olarak karşılaştırır."
        )
    )
    parser.add_argument(
        "symbols",
        nargs="*",
        help=(
            "İsteğe bağlı coin listesi. Örnek: DOGE BTC veya "
            "DOGE,BTC. Boş bırakılırsa tüm coinler denetlenir."
        ),
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=DEFAULT_MAX_PAGES,
        help="Geçmiş uç noktaları için en fazla sayfa sayısı.",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=DEFAULT_PAGE_LIMIT,
        help="Her geçmiş sayfasındaki en fazla kayıt sayısı.",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    selected_symbols = normalize_symbols(arguments.symbols)
    max_pages = max(1, arguments.max_pages)
    page_limit = max(1, min(arguments.page_limit, 100))

    print("Caspian PNL denetimi başlatılıyor.")
    print("Bu araç yalnızca GET istekleri yapar; emir veya transfer oluşturmaz.")
    print("Karşılaştırma Trading hesabı üzerinden yapılır.")

    service = OKXService()

    if service.client is None:
        print(
            "API bilgileri bulunamadı. Önce Caspian ayarlarından OKX "
            "kimlik bilgilerini kaydedin.",
            file=sys.stderr,
        )
        return 1

    try:
        connection_success, connection_info = service.check_connection()

        if connection_success and isinstance(connection_info, dict):
            permissions = connection_info.get("permissions", {})
            read_permission = bool(
                permissions.get("read")
                if isinstance(permissions, dict)
                else False
            )
            print(
                "API bağlantısı doğrulandı. "
                f"Read izni: {'var' if read_permission else 'yok'}"
            )
        else:
            print(
                "Uyarı: API bağlantı kontrolü doğrulanamadı: "
                f"{connection_info}",
                file=sys.stderr,
            )

        raw_details = require_success(
            "OKX Trading PNL alanları",
            fetch_raw_trading_details(service),
        )
        prices = require_success(
            "Spot fiyatları",
            fetch_public_spot_prices(service),
        )
        assets = build_trading_assets(
            raw_details,
            prices,
        )

        if not assets:
            raise RuntimeError(
                "Trading hesabında karşılaştırılacak varlık bulunamadı."
            )

        fills = require_success(
            "Spot fill geçmişi",
            service.get_spot_fills_history(
                max_pages=max_pages,
                page_limit=page_limit,
                force_refresh=True,
            ),
        )
        transfers = require_success(
            "Funding/Trading transfer geçmişi",
            service.get_funding_transfer_bills(
                max_pages=max_pages,
                page_limit=page_limit,
            ),
            optional=True,
        )
        deposits = require_success(
            "Deposit geçmişi",
            service.get_deposit_history(
                max_pages=max_pages,
                page_limit=page_limit,
            ),
            optional=True,
        )
        withdrawals = require_success(
            "Withdrawal geçmişi",
            service.get_withdrawal_history(
                max_pages=max_pages,
                page_limit=page_limit,
            ),
            optional=True,
        )

        calculated = CostBasisService.calculate(
            fills=fills,
            current_assets=assets,
            transfers=transfers,
        )

        rows = build_report_rows(
            assets=assets,
            cost_basis=calculated,
            raw_details=raw_details,
            fills_by_coin=group_fills(fills),
            transfers_by_coin=group_movements(transfers),
            deposits_by_coin=group_movements(deposits),
            withdrawals_by_coin=group_movements(withdrawals),
            selected_symbols=selected_symbols,
        )
        trading_total_usdt = sum(
            (safe_float(asset.get("usdt_value")) or 0.0)
            for asset in assets
        )
        metadata = {
            "generated_at": datetime.now(UTC).isoformat(),
            "selected_symbols": sorted(selected_symbols),
            "max_pages": max_pages,
            "page_limit": page_limit,
            "fill_count": len(fills),
            "transfer_count": len(transfers),
            "deposit_count": len(deposits),
            "withdrawal_count": len(withdrawals),
            "portfolio_total_usdt": trading_total_usdt,
            "portfolio_funding_usdt": None,
            "portfolio_trading_usdt": trading_total_usdt,
            "portfolio_mode": "trading_only",
            "comparison_scope": (
                "OKX openAvgPx/spotUpl Trading hesabına aittir. "
                "Caspian Trading sonucu ile karşılaştırılmıştır. "
                "Funding /api/v5/asset/balances uç noktası denetim "
                "için zorunlu değildir."
            ),
        }
        json_path, csv_path = write_reports(rows, metadata)

        print_summary(rows)
        print()
        print(f"JSON raporu: {json_path.resolve()}")
        print(f"CSV raporu:  {csv_path.resolve()}")
        return 0

    except Exception as error:
        print(f"PNL denetimi başarısız: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
