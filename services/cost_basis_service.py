from collections import defaultdict
from typing import Any


class CostBasisService:
    """
    OKX Spot gerçekleşmiş işlemlerinden açık pozisyon maliyeti üretir.

    Eski gerçekleşmiş PNL tutulmaz. Pozisyon tamamen kapandığında veya
    yalnızca ekonomik değeri olmayan bir artık kaldığında maliyet döngüsü
    sıfırlanır. Sonraki alış yeni bir pozisyon olarak hesaplanır.
    """

    RESET_AMOUNT_THRESHOLD = 0.00005
    RESET_VALUE_THRESHOLD_USDT = 0.01
    QUANTITY_TOLERANCE = 1e-10

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    @classmethod
    def _is_dust(
        cls,
        quantity: float,
        price: float,
    ) -> bool:
        quantity = abs(cls._safe_float(quantity))
        price = max(0.0, cls._safe_float(price))
        value = quantity * price

        return (
            quantity < cls.RESET_AMOUNT_THRESHOLD
            and value < cls.RESET_VALUE_THRESHOLD_USDT
        )

    @staticmethod
    def _extract_coin(inst_id: str) -> str | None:
        normalized = str(inst_id or "").strip().upper()

        if not normalized.endswith("-USDT"):
            return None

        coin = normalized.removesuffix("-USDT").strip()
        return coin or None

    @classmethod
    def calculate(
        cls,
        fills: list[dict[str, Any]],
        current_assets: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        current_by_coin = {}

        for asset in current_assets:
            coin = str(asset.get("coin", "")).strip().upper()

            if not coin or coin == "USDT":
                continue

            current_by_coin[coin] = {
                "quantity": cls._safe_float(asset.get("total")),
                "price": cls._safe_float(asset.get("price")),
            }

        grouped_fills = defaultdict(list)

        for fill in fills:
            coin = cls._extract_coin(fill.get("instId"))

            if coin is None or coin not in current_by_coin:
                continue

            side = str(fill.get("side", "")).strip().lower()

            if side not in {"buy", "sell"}:
                continue

            grouped_fills[coin].append(fill)

        results = {}

        for coin, current in current_by_coin.items():
            current_quantity = current["quantity"]
            current_price = current["price"]

            if current_quantity <= 0 or cls._is_dust(
                current_quantity,
                current_price,
            ):
                continue

            fills_for_coin = sorted(
                grouped_fills.get(coin, []),
                key=lambda item: (
                    int(cls._safe_float(item.get("ts"))),
                    str(item.get("tradeId", "")),
                ),
            )

            quantity = 0.0
            total_cost = 0.0
            has_valid_cycle = False
            history_incomplete = False

            for fill in fills_for_coin:
                side = str(fill.get("side", "")).strip().lower()
                fill_size = cls._safe_float(fill.get("fillSz"))
                fill_price = cls._safe_float(fill.get("fillPx"))
                fee = cls._safe_float(fill.get("fee"))
                fee_currency = str(
                    fill.get("feeCcy", "")
                ).strip().upper()

                if fill_size <= 0 or fill_price <= 0:
                    continue

                if side == "buy":
                    received_quantity = fill_size
                    quote_cost = fill_size * fill_price

                    if fee < 0:
                        if fee_currency == coin:
                            received_quantity = max(
                                0.0,
                                received_quantity + fee,
                            )
                        elif fee_currency == "USDT":
                            quote_cost += abs(fee)

                    if received_quantity <= 0:
                        continue

                    quantity += received_quantity
                    total_cost += quote_cost
                    has_valid_cycle = True
                    continue

                sold_quantity = fill_size

                if fee < 0 and fee_currency == coin:
                    sold_quantity += abs(fee)

                if quantity <= cls.QUANTITY_TOLERANCE:
                    history_incomplete = True
                    quantity = 0.0
                    total_cost = 0.0
                    has_valid_cycle = False
                    continue

                average_cost = (
                    total_cost / quantity
                    if quantity > cls.QUANTITY_TOLERANCE
                    else 0.0
                )
                removed_quantity = min(
                    sold_quantity,
                    quantity,
                )

                quantity -= removed_quantity
                total_cost -= average_cost * removed_quantity

                if quantity < 0:
                    quantity = 0.0

                if total_cost < 0:
                    total_cost = 0.0

                if cls._is_dust(quantity, fill_price):
                    quantity = 0.0
                    total_cost = 0.0
                    has_valid_cycle = False
                    history_incomplete = False

            if not has_valid_cycle or quantity <= cls.QUANTITY_TOLERANCE:
                continue

            difference = current_quantity - quantity
            allowed_difference = max(
                cls.QUANTITY_TOLERANCE,
                current_quantity * 0.0001,
            )

            if difference > allowed_difference:
                # Mevcut bakiye işlem geçmişinden büyükse eski alış,
                # yatırma veya eksik geçmiş vardır. Tahmini PNL üretme.
                continue

            if difference < -allowed_difference:
                # Mevcut bakiye hesaplanan miktardan küçükse maliyeti
                # kalan miktara oransal indir. Bu, transfer/çekim gibi
                # miktar azaltan hareketlerde ortalama maliyeti korur.
                ratio = (
                    current_quantity / quantity
                    if quantity > 0
                    else 0.0
                )
                quantity = current_quantity
                total_cost *= max(0.0, min(1.0, ratio))

            if history_incomplete:
                continue

            average_price = (
                total_cost / quantity
                if quantity > cls.QUANTITY_TOLERANCE
                else 0.0
            )

            if average_price <= 0 or current_price <= 0:
                continue

            current_value = current_quantity * current_price
            cost_basis_usdt = current_quantity * average_price
            pnl_usdt = current_value - cost_basis_usdt
            pnl_percent = (
                pnl_usdt / cost_basis_usdt * 100
                if cost_basis_usdt > 0
                else None
            )

            results[coin] = {
                "average_price": average_price,
                "cost_basis_usdt": cost_basis_usdt,
                "pnl_usdt": pnl_usdt,
                "pnl_percent": pnl_percent,
                "cost_basis_available": True,
            }

        return results

    @staticmethod
    def attach_to_assets(
        assets: list[dict[str, Any]],
        cost_basis: dict[str, dict[str, Any]],
    ) -> None:
        for asset in assets:
            coin = str(asset.get("coin", "")).strip().upper()
            result = cost_basis.get(coin)

            if result is None:
                asset["average_price"] = None
                asset["cost_basis_usdt"] = None
                asset["pnl_usdt"] = None
                asset["pnl_percent"] = None
                asset["cost_basis_available"] = False
                continue

            asset.update(result)
