from collections import defaultdict
from typing import Any


class CostBasisService:
    """
    Spot işlemleri ile Funding/Trading transferlerini kronolojik olarak
    işleyerek hesap bazlı ortalama maliyet ve PNL üretir.

    Temel kurallar:
    - Spot alış ve satışlar Trading hesabında gerçekleşir.
    - Hesaplar arası transferlerde bilinen maliyet miktarla birlikte taşınır.
    - Geçmişin başlangıcındaki bakiye miktarı geriye doğru hesaplanır.
    - Başlangıç maliyeti bilinmiyorsa maliyet tahmin edilmez.
    - Bir hesabın bakiyesi sıfıra indiğinde eski maliyet geçmişi sıfırlanır.
    - Satış sonrası kalan toplam değeri 0.01 USDT'nin altındaki bakiye
      kapanmış pozisyon kabul edilir ve maliyet geçmişi sıfırlanır.
    - Sıfırlamadan sonraki alışlarla yeni maliyet bağımsız olarak oluşur.
    """

    QUANTITY_TOLERANCE = 1e-10
    RELATIVE_TOLERANCE = 0.0001
    MIN_POSITION_VALUE_USDT = 0.01

    FUNDING_ACCOUNT = "6"
    TRADING_ACCOUNT = "18"

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
    def _allowed_difference(cls, quantity: float) -> float:
        return max(
            cls.QUANTITY_TOLERANCE,
            abs(cls._safe_float(quantity))
            * cls.RELATIVE_TOLERANCE,
        )

    @staticmethod
    def _extract_coin(inst_id: Any) -> str | None:
        normalized = str(inst_id or "").strip().upper()

        if not normalized.endswith("-USDT"):
            return None

        coin = normalized.removesuffix("-USDT").strip()
        return coin or None

    @classmethod
    def _buy_values(
        cls,
        coin: str,
        fill: dict[str, Any],
    ) -> tuple[float, float]:
        fill_size = cls._safe_float(fill.get("fillSz"))
        fill_price = cls._safe_float(fill.get("fillPx"))
        fee = cls._safe_float(fill.get("fee"))
        fee_currency = str(
            fill.get("feeCcy", "")
        ).strip().upper()

        if fill_size <= 0 or fill_price <= 0:
            return 0.0, 0.0

        received_quantity = fill_size
        quote_cost = fill_size * fill_price

        return received_quantity, quote_cost

    @classmethod
    def _sell_quantity(
        cls,
        coin: str,
        fill: dict[str, Any],
    ) -> float:
        fill_size = cls._safe_float(fill.get("fillSz"))
        fee = cls._safe_float(fill.get("fee"))
        fee_currency = str(
            fill.get("feeCcy", "")
        ).strip().upper()

        if fill_size <= 0:
            return 0.0

        removed_quantity = fill_size

        if fee < 0 and fee_currency == coin:
            removed_quantity += abs(fee)

        return removed_quantity

    @classmethod
    def _transfer_quantity(
        cls,
        bill: dict[str, Any],
    ) -> float:
        for key in ("sz", "amt", "amount", "balChg"):
            quantity = abs(cls._safe_float(bill.get(key)))

            if quantity > 0:
                return quantity

        return 0.0

    @staticmethod
    def _new_ledger(
        quantity: float = 0.0,
        cost: float = 0.0,
        cost_known: bool = True,
    ) -> dict[str, Any]:
        return {
            "quantity": max(0.0, quantity),
            "cost": max(0.0, cost),
            "cost_known": bool(cost_known),
        }

    @classmethod
    def _reset_if_empty(
        cls,
        ledger: dict[str, Any],
    ) -> None:
        if cls._safe_float(
            ledger.get("quantity")
        ) <= cls.QUANTITY_TOLERANCE:
            ledger["quantity"] = 0.0
            ledger["cost"] = 0.0
            ledger["cost_known"] = True

    @classmethod
    def _reset_if_dust(
        cls,
        ledger: dict[str, Any],
        reference_price: float,
    ) -> bool:
        quantity = cls._safe_float(
            ledger.get("quantity")
        )
        reference_price = cls._safe_float(
            reference_price
        )

        if (
            quantity <= cls.QUANTITY_TOLERANCE
            or reference_price <= 0
            or quantity * reference_price
            >= cls.MIN_POSITION_VALUE_USDT
        ):
            return False

        ledger["quantity"] = 0.0
        ledger["cost"] = 0.0
        ledger["cost_known"] = True
        return True

    @classmethod
    def _add_known_cost(
        cls,
        ledger: dict[str, Any],
        quantity: float,
        cost: float,
    ) -> None:
        quantity = cls._safe_float(quantity)
        cost = cls._safe_float(cost)

        if quantity <= 0 or cost < 0:
            return

        ledger["quantity"] = (
            cls._safe_float(ledger.get("quantity"))
            + quantity
        )

        if bool(ledger.get("cost_known")):
            ledger["cost"] = (
                cls._safe_float(ledger.get("cost"))
                + cost
            )

    @classmethod
    def _add_transferred(
        cls,
        ledger: dict[str, Any],
        quantity: float,
        cost: float,
        cost_known: bool,
    ) -> None:
        quantity = cls._safe_float(quantity)
        cost = cls._safe_float(cost)

        if quantity <= 0:
            return

        previous_quantity = cls._safe_float(
            ledger.get("quantity")
        )
        previous_known = bool(
            ledger.get("cost_known")
        )

        ledger["quantity"] = previous_quantity + quantity

        if previous_quantity <= cls.QUANTITY_TOLERANCE:
            ledger["cost_known"] = bool(cost_known)
            ledger["cost"] = cost if cost_known else 0.0
            return

        if previous_known and cost_known:
            ledger["cost"] = (
                cls._safe_float(ledger.get("cost"))
                + cost
            )
            return

        ledger["cost_known"] = False
        ledger["cost"] = 0.0

    @classmethod
    def _remove(
        cls,
        ledger: dict[str, Any],
        quantity: float,
    ) -> tuple[float, float, bool]:
        quantity = cls._safe_float(quantity)
        available_quantity = cls._safe_float(
            ledger.get("quantity")
        )
        cost_known = bool(
            ledger.get("cost_known")
        )

        if quantity <= 0 or available_quantity <= 0:
            return 0.0, 0.0, cost_known

        removed_quantity = min(
            quantity,
            available_quantity,
        )
        removed_cost = 0.0

        if cost_known:
            available_cost = cls._safe_float(
                ledger.get("cost")
            )
            average_cost = (
                available_cost / available_quantity
                if available_quantity
                > cls.QUANTITY_TOLERANCE
                else 0.0
            )
            removed_cost = (
                average_cost * removed_quantity
            )
            ledger["cost"] = max(
                0.0,
                available_cost - removed_cost,
            )

        ledger["quantity"] = max(
            0.0,
            available_quantity - removed_quantity,
        )
        cls._reset_if_empty(ledger)

        return (
            removed_quantity,
            removed_cost,
            cost_known,
        )

    @classmethod
    def _infer_initial_quantities(
        cls,
        events: list[dict[str, Any]],
        current_trading: float,
        current_funding: float,
        coin: str,
    ) -> tuple[float, float]:
        trading_change = 0.0
        funding_change = 0.0

        for event in events:
            payload = event["payload"]

            if event["kind"] == "fill":
                side = str(
                    payload.get("side", "")
                ).strip().lower()

                if side == "buy":
                    quantity, _ = cls._buy_values(
                        coin,
                        payload,
                    )
                    trading_change += quantity
                elif side == "sell":
                    trading_change -= (
                        cls._sell_quantity(
                            coin,
                            payload,
                        )
                    )

                continue

            from_account = str(
                payload.get("from", "")
            ).strip()
            to_account = str(
                payload.get("to", "")
            ).strip()
            quantity = cls._transfer_quantity(
                payload
            )

            if (
                from_account == cls.TRADING_ACCOUNT
                and to_account == cls.FUNDING_ACCOUNT
            ):
                trading_change -= quantity
                funding_change += quantity
            elif (
                from_account == cls.FUNDING_ACCOUNT
                and to_account == cls.TRADING_ACCOUNT
            ):
                funding_change -= quantity
                trading_change += quantity

        initial_trading = max(
            0.0,
            cls._safe_float(current_trading)
            - trading_change,
        )
        initial_funding = max(
            0.0,
            cls._safe_float(current_funding)
            - funding_change,
        )

        return initial_trading, initial_funding

    @classmethod
    def _synchronize_quantity(
        cls,
        ledger: dict[str, Any],
        current_quantity: float,
        current_price: float = 0.0,
        preserve_dust_difference: bool = False,
    ) -> None:
        current_quantity = max(
            0.0,
            cls._safe_float(current_quantity),
        )
        ledger_quantity = cls._safe_float(
            ledger.get("quantity")
        )
        current_price = cls._safe_float(
            current_price
        )
        quantity_difference = abs(
            ledger_quantity - current_quantity
        )

        allowed_difference = cls._allowed_difference(
            current_quantity
        )

        if (
            preserve_dust_difference
            and (
                quantity_difference <= allowed_difference
                or (
                    current_price > 0
                    and quantity_difference * current_price
                    < cls.MIN_POSITION_VALUE_USDT
                )
            )
        ):
            cls._reset_if_empty(ledger)
            return

        if quantity_difference <= allowed_difference:
            ledger["quantity"] = current_quantity
            cls._reset_if_empty(ledger)
            return

        if (
            bool(ledger.get("cost_known"))
            and ledger_quantity
            > cls.QUANTITY_TOLERANCE
        ):
            average_cost = (
                cls._safe_float(ledger.get("cost"))
                / ledger_quantity
            )
            ledger["quantity"] = current_quantity
            ledger["cost"] = (
                average_cost * current_quantity
            )
            cls._reset_if_empty(ledger)
            return

        ledger["quantity"] = current_quantity
        cls._reset_if_empty(ledger)

    @classmethod
    def _build_result(
        cls,
        ledger: dict[str, Any],
        current_price: float,
    ) -> dict[str, Any] | None:
        quantity = cls._safe_float(
            ledger.get("quantity")
        )
        total_cost = cls._safe_float(
            ledger.get("cost")
        )
        current_price = cls._safe_float(current_price)
        cost_known = bool(
            ledger.get("cost_known")
        )

        if (
            not cost_known
            or quantity <= cls.QUANTITY_TOLERANCE
            or total_cost <= 0
            or current_price <= 0
        ):
            return None

        average_price = total_cost / quantity
        current_value = quantity * current_price
        pnl_usdt = current_value - total_cost
        pnl_percent = pnl_usdt / total_cost * 100

        return {
            "average_price": average_price,
            "cost_basis_usdt": total_cost,
            "pnl_usdt": pnl_usdt,
            "pnl_percent": pnl_percent,
            "cost_basis_available": True,
        }

    @classmethod
    def _reconstruct_open_average(
        cls,
        fills: list[dict[str, Any]],
        coin: str,
        current_quantity: float,
    ) -> float | None:
        """
        Güncel açık miktarın alış maliyetini işlem geçmişinden geriye doğru
        yeniden kurar.

        Satışların önce en eski envanteri tükettiği kabul edilir. Bu nedenle
        geçmiş geriye doğru okunurken satış miktarı ihtiyaç duyulan envantere
        eklenir, alışlar ise en yeni alıştan eskiye doğru bu ihtiyacı karşılar.

        OKX portföy yüzdesiyle uyum için işlem ücreti ortalama alış fiyatına
        eklenmez. Ücretin baz varlıkla alınması yalnızca gerçek bakiyeyi azaltır;
        fill fiyatını değiştirmez.
        """
        required_quantity = max(
            0.0,
            cls._safe_float(current_quantity),
        )

        if required_quantity <= cls.QUANTITY_TOLERANCE:
            return None

        relevant_fills = []

        for fill in fills:
            if cls._extract_coin(fill.get("instId")) != coin:
                continue

            side = str(
                fill.get("side", "")
            ).strip().lower()
            quantity = cls._safe_float(fill.get("fillSz"))
            price = cls._safe_float(fill.get("fillPx"))
            timestamp = int(cls._safe_float(fill.get("ts")))

            if side not in {"buy", "sell"} or quantity <= 0:
                continue

            if side == "buy" and price <= 0:
                continue

            relevant_fills.append(
                (
                    timestamp,
                    str(fill.get("tradeId", "")),
                    side,
                    quantity,
                    price,
                )
            )

        relevant_fills.sort(
            key=lambda item: (item[0], item[1]),
            reverse=True,
        )

        reconstructed_quantity = 0.0
        reconstructed_cost = 0.0

        for _, _, side, quantity, price in relevant_fills:
            if side == "sell":
                required_quantity += quantity
                continue

            used_quantity = min(
                required_quantity,
                quantity,
            )

            if used_quantity <= 0:
                continue

            reconstructed_quantity += used_quantity
            reconstructed_cost += used_quantity * price
            required_quantity -= used_quantity

            if required_quantity <= cls._allowed_difference(
                current_quantity
            ):
                required_quantity = 0.0
                break

        if (
            required_quantity > cls._allowed_difference(current_quantity)
            or reconstructed_quantity <= cls.QUANTITY_TOLERANCE
            or reconstructed_cost <= 0
        ):
            return None

        return reconstructed_cost / reconstructed_quantity

    @classmethod
    def _latest_buy_average(
        cls,
        fills: list[dict[str, Any]],
        coin: str,
    ) -> float | None:
        """
        Ledger veya açık miktar rekonstrüksiyonu sonuç üretemediğinde,
        en son alış emrindeki fill'lerin ağırlıklı ortalama fiyatını döndürür.

        Aynı ordId altında parçalı gerçekleşen fill'ler tek alış emri olarak
        değerlendirilir. OKX portföy gösterimiyle uyum için işlem ücretleri
        ortalama fiyata eklenmez.
        """
        buy_fills: list[tuple[int, str, float, float]] = []

        for fill in fills:
            if cls._extract_coin(fill.get("instId")) != coin:
                continue

            side = str(
                fill.get("side", "")
            ).strip().lower()

            if side != "buy":
                continue

            quantity = cls._safe_float(fill.get("fillSz"))
            price = cls._safe_float(fill.get("fillPx"))

            if quantity <= 0 or price <= 0:
                continue

            timestamp = int(cls._safe_float(fill.get("ts")))
            order_id = str(fill.get("ordId", "")).strip()

            if not order_id:
                order_id = str(fill.get("tradeId", "")).strip()

            buy_fills.append(
                (
                    timestamp,
                    order_id,
                    quantity,
                    price,
                )
            )

        if not buy_fills:
            return None

        latest_timestamp, latest_order_id, _, _ = max(
            buy_fills,
            key=lambda item: (
                item[0],
                item[1],
            ),
        )

        total_quantity = 0.0
        total_cost = 0.0

        for timestamp, order_id, quantity, price in buy_fills:
            if order_id != latest_order_id:
                continue

            total_quantity += quantity
            total_cost += quantity * price

        if (
            total_quantity <= cls.QUANTITY_TOLERANCE
            or total_cost <= 0
        ):
            return None

        return total_cost / total_quantity

    @classmethod
    def _build_fallback_result(
        cls,
        quantity: float,
        current_price: float,
        average_price: float | None,
    ) -> dict[str, Any] | None:
        quantity = cls._safe_float(quantity)
        current_price = cls._safe_float(current_price)
        average_price = cls._safe_float(average_price)

        if (
            quantity <= cls.QUANTITY_TOLERANCE
            or current_price <= 0
            or average_price <= 0
        ):
            return None

        total_cost = quantity * average_price
        current_value = quantity * current_price
        pnl_usdt = current_value - total_cost
        pnl_percent = pnl_usdt / total_cost * 100

        return {
            "average_price": average_price,
            "cost_basis_usdt": total_cost,
            "pnl_usdt": pnl_usdt,
            "pnl_percent": pnl_percent,
            "cost_basis_available": True,
        }

    @classmethod
    def calculate(
        cls,
        fills: list[dict[str, Any]],
        current_assets: list[dict[str, Any]],
        transfers: list[dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        current_by_coin = {}

        for asset in current_assets:
            coin = str(
                asset.get("coin", "")
            ).strip().upper()

            if not coin or coin == "USDT":
                continue

            current_price = cls._safe_float(
                asset.get("price")
            )
            current_total = cls._safe_float(
                asset.get("total")
            )
            current_funding = cls._safe_float(
                asset.get("funding_total")
            )
            current_trading = cls._safe_float(
                asset.get("trading_total")
            )

            if (
                current_price > 0
                and current_total * current_price
                < cls.MIN_POSITION_VALUE_USDT
            ):
                current_total = 0.0
                current_funding = 0.0
                current_trading = 0.0

            current_by_coin[coin] = {
                "total": current_total,
                "funding": current_funding,
                "trading": current_trading,
                "price": current_price,
            }

        grouped_events = defaultdict(list)

        for fill in fills:
            coin = cls._extract_coin(
                fill.get("instId")
            )

            if coin not in current_by_coin:
                continue

            side = str(
                fill.get("side", "")
            ).strip().lower()

            if side not in {"buy", "sell"}:
                continue

            grouped_events[coin].append(
                {
                    "kind": "fill",
                    "timestamp": int(
                        cls._safe_float(fill.get("ts"))
                    ),
                    "sort_id": str(
                        fill.get("tradeId", "")
                    ),
                    "payload": fill,
                }
            )

        for bill in transfers or []:
            coin = str(
                bill.get("ccy", "")
            ).strip().upper()

            if coin not in current_by_coin:
                continue

            from_account = str(
                bill.get("from", "")
            ).strip()
            to_account = str(
                bill.get("to", "")
            ).strip()

            if (
                {from_account, to_account}
                != {
                    cls.FUNDING_ACCOUNT,
                    cls.TRADING_ACCOUNT,
                }
            ):
                continue

            quantity = cls._transfer_quantity(bill)

            if quantity <= 0:
                continue

            grouped_events[coin].append(
                {
                    "kind": "transfer",
                    "timestamp": int(
                        cls._safe_float(bill.get("ts"))
                    ),
                    "sort_id": str(
                        bill.get("billId", "")
                    ),
                    "payload": bill,
                }
            )

        results = {}

        for coin, current in current_by_coin.items():
            events = sorted(
                grouped_events.get(coin, []),
                key=lambda event: (
                    event["timestamp"],
                    0 if event["kind"] == "fill" else 1,
                    event["sort_id"],
                ),
            )

            (
                initial_trading,
                initial_funding,
            ) = cls._infer_initial_quantities(
                events=events,
                current_trading=current["trading"],
                current_funding=current["funding"],
                coin=coin,
            )

            dust_position_reset = False

            trading = cls._new_ledger(
                quantity=initial_trading,
                cost=0.0,
                cost_known=(
                    initial_trading
                    <= cls.QUANTITY_TOLERANCE
                ),
            )
            funding = cls._new_ledger(
                quantity=initial_funding,
                cost=0.0,
                cost_known=(
                    initial_funding
                    <= cls.QUANTITY_TOLERANCE
                ),
            )

            for event in events:
                payload = event["payload"]

                if event["kind"] == "fill":
                    side = str(
                        payload.get("side", "")
                    ).strip().lower()

                    if side == "buy":
                        quantity, cost = cls._buy_values(
                            coin,
                            payload,
                        )
                        cls._add_known_cost(
                            trading,
                            quantity,
                            cost,
                        )
                    else:
                        quantity = cls._sell_quantity(
                            coin,
                            payload,
                        )
                        cls._remove(
                            trading,
                            quantity,
                        )

                        if cls._reset_if_dust(
                            trading,
                            cls._safe_float(
                                payload.get("fillPx")
                            ),
                        ):
                            dust_position_reset = True

                    continue

                from_account = str(
                    payload.get("from", "")
                ).strip()
                to_account = str(
                    payload.get("to", "")
                ).strip()
                quantity = cls._transfer_quantity(
                    payload
                )

                if (
                    from_account
                    == cls.TRADING_ACCOUNT
                    and to_account
                    == cls.FUNDING_ACCOUNT
                ):
                    (
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    ) = cls._remove(
                        trading,
                        quantity,
                    )
                    cls._add_transferred(
                        funding,
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    )

                elif (
                    from_account
                    == cls.FUNDING_ACCOUNT
                    and to_account
                    == cls.TRADING_ACCOUNT
                ):
                    (
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    ) = cls._remove(
                        funding,
                        quantity,
                    )
                    cls._add_transferred(
                        trading,
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    )

            cls._synchronize_quantity(
                trading,
                current["trading"],
                current["price"],
                dust_position_reset,
            )
            cls._synchronize_quantity(
                funding,
                current["funding"],
                current["price"],
                dust_position_reset,
            )

            total_quantity = (
                cls._safe_float(
                    trading.get("quantity")
                )
                + cls._safe_float(
                    funding.get("quantity")
                )
            )
            total_cost_known = (
                bool(trading.get("cost_known"))
                and bool(funding.get("cost_known"))
            )
            total_cost = (
                cls._safe_float(trading.get("cost"))
                + cls._safe_float(funding.get("cost"))
            )

            total = cls._new_ledger(
                quantity=total_quantity,
                cost=total_cost,
                cost_known=total_cost_known,
            )

            total_result = cls._build_result(
                total,
                current["price"],
            )
            funding_result = cls._build_result(
                funding,
                current["price"],
            )
            trading_result = cls._build_result(
                trading,
                current["price"],
            )

            reconstructed_average = (
                cls._reconstruct_open_average(
                    fills=fills,
                    coin=coin,
                    current_quantity=current["total"],
                )
            )

            resolved_average = reconstructed_average

            if total_result is None:
                total_result = cls._build_fallback_result(
                    current["total"],
                    current["price"],
                    resolved_average,
                )

            if funding_result is None:
                funding_result = cls._build_fallback_result(
                    current["funding"],
                    current["price"],
                    resolved_average,
                )

            if trading_result is None:
                trading_result = cls._build_fallback_result(
                    current["trading"],
                    current["price"],
                    resolved_average,
                )

            results[coin] = {
                "total": total_result,
                "funding": funding_result,
                "trading": trading_result,
            }

        return results

    @staticmethod
    def _attach_result(
        asset: dict[str, Any],
        prefix: str,
        result: dict[str, Any] | None,
    ) -> None:
        field_map = {
            "average_price": f"{prefix}average_price",
            "cost_basis_usdt": f"{prefix}cost_basis_usdt",
            "pnl_usdt": f"{prefix}pnl_usdt",
            "pnl_percent": f"{prefix}pnl_percent",
            "cost_basis_available": (
                f"{prefix}cost_basis_available"
            ),
        }

        if result is None:
            asset[field_map["average_price"]] = None
            asset[field_map["cost_basis_usdt"]] = None
            asset[field_map["pnl_usdt"]] = None
            asset[field_map["pnl_percent"]] = None
            asset[
                field_map["cost_basis_available"]
            ] = False
            return

        for source_key, target_key in field_map.items():
            asset[target_key] = result.get(source_key)

    @classmethod
    def attach_to_assets(
        cls,
        assets: list[dict[str, Any]],
        cost_basis: dict[str, dict[str, Any]],
    ) -> None:
        for asset in assets:
            coin = str(
                asset.get("coin", "")
            ).strip().upper()
            result = cost_basis.get(coin, {})

            total_result = (
                result.get("total")
                if isinstance(result, dict)
                else None
            )
            funding_result = (
                result.get("funding")
                if isinstance(result, dict)
                else None
            )
            trading_result = (
                result.get("trading")
                if isinstance(result, dict)
                else None
            )

            cls._attach_result(
                asset,
                "",
                total_result,
            )
            cls._attach_result(
                asset,
                "funding_",
                funding_result,
            )
            cls._attach_result(
                asset,
                "trading_",
                trading_result,
            )
