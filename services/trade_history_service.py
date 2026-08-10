from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from database.trade_history_db import TradeHistoryRepository


class TradeHistoryService:
    FUNDING_ACCOUNT = "6"
    TRADING_ACCOUNT = "18"
    QUANTITY_TOLERANCE = 1e-10
    RELATIVE_TOLERANCE = 0.0001
    MIN_POSITION_VALUE_USDT = 0.01
    UTC_PLUS_3 = timezone(timedelta(hours=3))

    def __init__(
        self,
        repository: TradeHistoryRepository | None = None,
    ):
        self.repository = repository or TradeHistoryRepository()

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)
            if number != number:
                return 0.0
            if number in (float("inf"), float("-inf")):
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
    def _transfer_quantity(
        cls,
        bill: dict[str, Any],
    ) -> float:
        for key in ("sz", "amt", "amount", "balChg"):
            quantity = abs(cls._safe_float(bill.get(key)))
            if quantity > 0:
                return quantity
        return 0.0

    @classmethod
    def _sell_inventory_quantity(
        cls,
        coin: str,
        fill: dict[str, Any],
    ) -> float:
        quantity = cls._safe_float(fill.get("fillSz"))
        if quantity <= 0:
            return 0.0

        fee = cls._safe_float(fill.get("fee"))
        fee_currency = str(
            fill.get("feeCcy", "")
        ).strip().upper()

        if fee < 0 and fee_currency == coin:
            quantity += abs(fee)

        return quantity

    @staticmethod
    def _new_ledger(
        quantity: float,
        cost_known: bool,
    ) -> dict[str, Any]:
        return {
            "quantity": max(0.0, quantity),
            "cost": 0.0,
            "cost_known": bool(cost_known),
        }

    @classmethod
    def _reset_if_empty(
        cls,
        ledger: dict[str, Any],
    ) -> None:
        if (
            cls._safe_float(ledger.get("quantity"))
            <= cls.QUANTITY_TOLERANCE
        ):
            ledger["quantity"] = 0.0
            ledger["cost"] = 0.0
            ledger["cost_known"] = True

    @classmethod
    def _reset_if_dust(
        cls,
        ledger: dict[str, Any],
        reference_price: float,
    ) -> None:
        quantity = cls._safe_float(ledger.get("quantity"))
        price = cls._safe_float(reference_price)

        if (
            quantity <= cls.QUANTITY_TOLERANCE
            or price <= 0
            or quantity * price >= cls.MIN_POSITION_VALUE_USDT
        ):
            return

        ledger["quantity"] = 0.0
        ledger["cost"] = 0.0
        ledger["cost_known"] = True

    @classmethod
    def _add_buy(
        cls,
        ledger: dict[str, Any],
        quantity: float,
        price: float,
    ) -> None:
        quantity = cls._safe_float(quantity)
        price = cls._safe_float(price)

        if quantity <= 0 or price <= 0:
            return

        ledger["quantity"] = (
            cls._safe_float(ledger.get("quantity"))
            + quantity
        )

        if bool(ledger.get("cost_known")):
            ledger["cost"] = (
                cls._safe_float(ledger.get("cost"))
                + quantity * price
            )

    @classmethod
    def _remove_inventory(
        cls,
        ledger: dict[str, Any],
        quantity: float,
    ) -> tuple[float, float, bool]:
        requested_quantity = cls._safe_float(quantity)
        available_quantity = cls._safe_float(
            ledger.get("quantity")
        )
        cost_known = bool(ledger.get("cost_known"))

        if requested_quantity <= 0 or available_quantity <= 0:
            return 0.0, 0.0, cost_known

        removed_quantity = min(
            requested_quantity,
            available_quantity,
        )
        removed_cost = 0.0

        if cost_known:
            available_cost = cls._safe_float(
                ledger.get("cost")
            )
            average_cost = (
                available_cost / available_quantity
                if available_quantity > cls.QUANTITY_TOLERANCE
                else 0.0
            )
            removed_cost = average_cost * removed_quantity
            ledger["cost"] = max(
                0.0,
                available_cost - removed_cost,
            )

        ledger["quantity"] = max(
            0.0,
            available_quantity - removed_quantity,
        )
        cls._reset_if_empty(ledger)

        complete = (
            abs(removed_quantity - requested_quantity)
            <= cls._allowed_difference(requested_quantity)
        )
        return removed_quantity, removed_cost, (
            cost_known and complete
        )

    @classmethod
    def _add_transfer(
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
        previous_known = bool(ledger.get("cost_known"))

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
    def _current_quantities(
        cls,
        current_assets: list[dict[str, Any]] | None,
    ) -> dict[str, dict[str, float]]:
        result: dict[str, dict[str, float]] = {}

        for asset in current_assets or []:
            coin = str(
                asset.get("coin", "")
            ).strip().upper()

            if not coin or coin == "USDT":
                continue

            result[coin] = {
                "trading": cls._safe_float(
                    asset.get("trading_total")
                ),
                "funding": cls._safe_float(
                    asset.get("funding_total")
                ),
            }

        return result

    @classmethod
    def _normalize_events(
        cls,
        fills: list[dict[str, Any]],
        transfers: list[dict[str, Any]] | None,
    ) -> dict[str, list[dict[str, Any]]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(
            list
        )

        for fill in fills or []:
            coin = cls._extract_coin(fill.get("instId"))
            if not coin:
                continue

            side = str(
                fill.get("side", "")
            ).strip().lower()
            quantity = cls._safe_float(fill.get("fillSz"))
            price = cls._safe_float(fill.get("fillPx"))

            if side not in {"buy", "sell"}:
                continue
            if quantity <= 0 or price <= 0:
                continue

            grouped[coin].append(
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
            if not coin or coin == "USDT":
                continue

            from_account = str(
                bill.get("from", "")
            ).strip()
            to_account = str(
                bill.get("to", "")
            ).strip()

            if {
                from_account,
                to_account,
            } != {
                cls.FUNDING_ACCOUNT,
                cls.TRADING_ACCOUNT,
            }:
                continue

            quantity = cls._transfer_quantity(bill)
            if quantity <= 0:
                continue

            grouped[coin].append(
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

        for coin in grouped:
            grouped[coin].sort(
                key=lambda event: (
                    event["timestamp"],
                    0 if event["kind"] == "fill" else 1,
                    event["sort_id"],
                )
            )

        return grouped

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
                    trading_change += cls._safe_float(
                        payload.get("fillSz")
                    )
                elif side == "sell":
                    trading_change -= cls._sell_inventory_quantity(
                        coin,
                        payload,
                    )
                continue

            from_account = str(
                payload.get("from", "")
            ).strip()
            to_account = str(
                payload.get("to", "")
            ).strip()
            quantity = cls._transfer_quantity(payload)

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

        return (
            max(
                0.0,
                cls._safe_float(current_trading)
                - trading_change,
            ),
            max(
                0.0,
                cls._safe_float(current_funding)
                - funding_change,
            ),
        )

    @classmethod
    def _format_timestamp(cls, timestamp_ms: int) -> str:
        timestamp_seconds = max(0, int(timestamp_ms)) / 1000
        return datetime.fromtimestamp(
            timestamp_seconds,
            tz=cls.UTC_PLUS_3,
        ).isoformat(timespec="seconds")

    @classmethod
    def _record_fill(
        cls,
        groups: dict[tuple[str, str, str], dict[str, Any]],
        coin: str,
        fill: dict[str, Any],
        cost_basis_usdt: float | None,
    ) -> None:
        side = str(fill.get("side", "")).strip().lower()
        instrument_id = str(
            fill.get("instId", "")
        ).strip().upper()
        trade_id = str(
            fill.get("tradeId", "")
        ).strip()
        order_id = str(
            fill.get("ordId", "")
        ).strip() or trade_id
        timestamp = int(cls._safe_float(fill.get("ts")))
        quantity = cls._safe_float(fill.get("fillSz"))
        price = cls._safe_float(fill.get("fillPx"))
        total_usdt = quantity * price

        if not order_id:
            order_id = (
                f"{instrument_id}:{side}:{timestamp}:"
                f"{len(groups)}"
            )

        key = (instrument_id, side, order_id)
        group = groups.get(key)

        if group is None:
            group = {
                "transaction_key": (
                    f"{instrument_id}|{side}|{order_id}"
                ),
                "order_id": order_id,
                "instrument_id": instrument_id,
                "coin": coin,
                "side": side,
                "quantity": 0.0,
                "notional": 0.0,
                "cost_basis_usdt": 0.0,
                "cost_basis_known": True,
                "executed_at_ms": timestamp,
                "source_trade_ids": [],
            }
            groups[key] = group

        group["quantity"] += quantity
        group["notional"] += total_usdt
        group["executed_at_ms"] = max(
            int(group["executed_at_ms"]),
            timestamp,
        )

        if trade_id:
            group["source_trade_ids"].append(trade_id)

        if side == "sell":
            if cost_basis_usdt is None:
                group["cost_basis_known"] = False
            else:
                group["cost_basis_usdt"] += cost_basis_usdt

    @classmethod
    def build_transactions(
        cls,
        fills: list[dict[str, Any]],
        current_assets: list[dict[str, Any]] | None = None,
        transfers: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        grouped_events = cls._normalize_events(
            fills=fills,
            transfers=transfers,
        )
        current = cls._current_quantities(current_assets)

        all_coins = set(grouped_events) | set(current)
        order_groups: dict[
            tuple[str, str, str],
            dict[str, Any],
        ] = {}

        for coin in sorted(all_coins):
            events = grouped_events.get(coin, [])
            current_values = current.get(
                coin,
                {
                    "trading": 0.0,
                    "funding": 0.0,
                },
            )
            (
                initial_trading,
                initial_funding,
            ) = cls._infer_initial_quantities(
                events=events,
                current_trading=current_values["trading"],
                current_funding=current_values["funding"],
                coin=coin,
            )

            trading = cls._new_ledger(
                quantity=initial_trading,
                cost_known=(
                    initial_trading <= cls.QUANTITY_TOLERANCE
                ),
            )
            funding = cls._new_ledger(
                quantity=initial_funding,
                cost_known=(
                    initial_funding <= cls.QUANTITY_TOLERANCE
                ),
            )

            for event in events:
                payload = event["payload"]

                if event["kind"] == "fill":
                    side = str(
                        payload.get("side", "")
                    ).strip().lower()
                    quantity = cls._safe_float(
                        payload.get("fillSz")
                    )
                    price = cls._safe_float(
                        payload.get("fillPx")
                    )

                    if side == "buy":
                        cls._add_buy(
                            trading,
                            quantity,
                            price,
                        )
                        cls._record_fill(
                            order_groups,
                            coin,
                            payload,
                            cost_basis_usdt=None,
                        )
                        continue

                    inventory_quantity = (
                        cls._sell_inventory_quantity(
                            coin,
                            payload,
                        )
                    )
                    (
                        _,
                        removed_cost,
                        cost_known,
                    ) = cls._remove_inventory(
                        trading,
                        inventory_quantity,
                    )
                    cls._record_fill(
                        order_groups,
                        coin,
                        payload,
                        cost_basis_usdt=(
                            removed_cost
                            if cost_known
                            else None
                        ),
                    )
                    cls._reset_if_dust(
                        trading,
                        price,
                    )
                    continue

                from_account = str(
                    payload.get("from", "")
                ).strip()
                to_account = str(
                    payload.get("to", "")
                ).strip()
                quantity = cls._transfer_quantity(payload)

                if (
                    from_account == cls.TRADING_ACCOUNT
                    and to_account == cls.FUNDING_ACCOUNT
                ):
                    (
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    ) = cls._remove_inventory(
                        trading,
                        quantity,
                    )
                    cls._add_transfer(
                        funding,
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    )
                elif (
                    from_account == cls.FUNDING_ACCOUNT
                    and to_account == cls.TRADING_ACCOUNT
                ):
                    (
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    ) = cls._remove_inventory(
                        funding,
                        quantity,
                    )
                    cls._add_transfer(
                        trading,
                        moved_quantity,
                        moved_cost,
                        moved_cost_known,
                    )

        transactions = []
        for group in order_groups.values():
            quantity = cls._safe_float(group["quantity"])
            notional = cls._safe_float(group["notional"])

            if quantity <= 0 or notional <= 0:
                continue

            price = notional / quantity
            side = group["side"]
            average_cost = None
            cost_basis_usdt = None
            pnl_usdt = None
            pnl_percent = None

            if side == "sell" and bool(
                group.get("cost_basis_known")
            ):
                cost_basis_usdt = cls._safe_float(
                    group.get("cost_basis_usdt")
                )

                if cost_basis_usdt > 0:
                    average_cost = cost_basis_usdt / quantity
                    pnl_usdt = notional - cost_basis_usdt
                    pnl_percent = (
                        pnl_usdt / cost_basis_usdt * 100.0
                    )

            executed_at_ms = int(
                group["executed_at_ms"]
            )
            transactions.append(
                {
                    "transaction_key": group[
                        "transaction_key"
                    ],
                    "order_id": group["order_id"],
                    "instrument_id": group[
                        "instrument_id"
                    ],
                    "coin": group["coin"],
                    "side": side,
                    "quantity": quantity,
                    "price": price,
                    "total_usdt": notional,
                    "average_cost": average_cost,
                    "cost_basis_usdt": cost_basis_usdt,
                    "pnl_usdt": pnl_usdt,
                    "pnl_percent": pnl_percent,
                    "executed_at_ms": executed_at_ms,
                    "executed_at": cls._format_timestamp(
                        executed_at_ms
                    ),
                    "source_trade_ids": list(
                        dict.fromkeys(
                            group["source_trade_ids"]
                        )
                    ),
                }
            )

        transactions.sort(
            key=lambda item: (
                item["executed_at_ms"],
                item["transaction_key"],
            ),
            reverse=True,
        )
        return transactions

    def save_transactions(
        self,
        transactions: list[dict[str, Any]],
    ) -> int:
        return self.repository.upsert_many(transactions)

    def get_transactions(
        self,
        coin: str | None = None,
        sort_by: str = "executed_at_ms",
        descending: bool = True,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        return self.repository.list_transactions(
            coin=coin,
            sort_by=sort_by,
            descending=descending,
            limit=limit,
        )

    def sync_from_okx(
        self,
        okx_service: Any,
        current_assets: list[dict[str, Any]] | None,
        force_refresh: bool = False,
    ) -> tuple[bool, list[dict[str, Any]] | str]:
        fills_success, fills_result = (
            okx_service.get_spot_fills_history(
                force_refresh=force_refresh,
            )
        )
        if not fills_success:
            return False, str(fills_result)

        transfer_success, transfer_result = (
            okx_service.get_funding_transfer_bills()
        )
        if not transfer_success:
            return False, str(transfer_result)

        transactions = self.build_transactions(
            fills=list(fills_result),
            current_assets=current_assets,
            transfers=list(transfer_result),
        )
        self.save_transactions(transactions)
        return True, transactions
