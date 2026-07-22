from datetime import datetime, timedelta
from typing import Any

from PySide6.QtCore import QObject, Signal

from database.settings_db import get_app_setting
from services.account_performance_service import AccountPerformanceService
from services.cost_basis_service import CostBasisService
from services.okx_service import OKXService
from services.portfolio_history_service import PortfolioHistoryService
from services.price_cache import PriceCache


class DataManager(QObject):
    portfolio_updated = Signal(dict)
    portfolio_error = Signal(str)

    HISTORY_MAINTENANCE_INTERVAL = timedelta(hours=24)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized"):
            return

        super().__init__()

        self._initialized = True

        self.cache = PriceCache()
        self.okx = OKXService()
        self.cost_basis = CostBasisService()
        self.portfolio_history = PortfolioHistoryService()
        self.account_performance = AccountPerformanceService(
            okx_service=self.okx,
            history_service=self.portfolio_history,
        )

        self.portfolio = None
        self.last_error = None
        self.loading = False
        self._last_history_maintenance = None
        self._portfolio_history_enabled = bool(
            get_app_setting(
                "portfolio_history_enabled",
                True,
            )
        )

        self._run_history_maintenance_if_needed()

    def refresh_client(self):
        self.okx.refresh_client()

    def refresh_portfolio(self):
        if self.loading:
            return False, "Loading"

        self.loading = True

        try:
            ok, result = self.okx.get_spot_balances(self.cache)

            if ok:
                self._attach_cost_basis_data(result)
                self._attach_history_data(result)
                self._attach_modified_dietz_performance(result)
                self._run_history_maintenance_if_needed()

                self.portfolio = result
                self.last_error = None
                self.portfolio_updated.emit(result)
            else:
                self.last_error = result
                self.portfolio_error.emit(str(result))

            return ok, result

        except Exception as e:
            self.last_error = str(e)
            self.portfolio_error.emit(str(e))
            return False, str(e)

        finally:
            self.loading = False

    def _attach_cost_basis_data(
        self,
        portfolio: dict[str, Any],
    ) -> None:
        """
        Açık Spot pozisyonlarına doğrulanmış ortalama maliyet ve PNL ekler.

        İşlem geçmişi yetersiz veya bakiye geçmişle uyuşmuyorsa tahmini
        değer üretmez; ilgili asset alanları None olarak bırakılır.
        """
        assets = portfolio.get("assets", [])

        if not isinstance(assets, list):
            return

        try:
            fills_success, fills = (
                self.okx.get_spot_fills_history()
            )
            transfers_success, transfers = (
                self.okx.get_funding_transfer_bills()
            )

            if not fills_success or not isinstance(fills, list):
                CostBasisService.attach_to_assets(
                    assets,
                    {},
                )
                return

            if (
                not transfers_success
                or not isinstance(transfers, list)
            ):
                transfers = []

            calculated = self.cost_basis.calculate(
                fills=fills,
                transfers=transfers,
                current_assets=assets,
            )
            self.cost_basis.attach_to_assets(
                assets,
                calculated,
            )

        except Exception:
            CostBasisService.attach_to_assets(
                assets,
                {},
            )

    def _attach_history_data(
        self,
        portfolio: dict[str, Any],
    ) -> None:
        """
        Güncel portföy snapshot'ını kaydeder ve tüketici ekranlar için
        performans veri yapısını hazırlar.

        Dönemsel performansların tek hesaplama kaynağı
        AccountPerformanceService / Modified Dietz motorudur.
        """
        total_usdt = self._safe_float(
            portfolio.get("total_usdt", 0.0)
        )
        funding_usdt = self._safe_float(
            portfolio.get("funding_usdt", 0.0)
        )
        trading_usdt = self._safe_float(
            portfolio.get("trading_usdt", 0.0)
        )

        assets = portfolio.get("assets", [])
        asset_count = (
            len(assets)
            if isinstance(assets, list)
            else 0
        )

        if self._portfolio_history_enabled:
            try:
                self.portfolio_history.save_snapshot(
                    total_usdt=total_usdt,
                    funding_usdt=funding_usdt,
                    trading_usdt=trading_usdt,
                    asset_count=asset_count,
                )
            except Exception:
                pass

        empty = self._empty_performance()

        portfolio["performance"] = empty.copy()
        portfolio["performance_breakdown"] = {
            "total": empty.copy(),
            "funding": empty.copy(),
            "trading": empty.copy(),
        }

        try:
            portfolio["analytics"] = (
                self.portfolio_history
                .calculate_portfolio_analytics(
                    current_total_usdt=total_usdt,
                    current_funding_usdt=funding_usdt,
                    current_trading_usdt=trading_usdt,
                )
            )
        except Exception:
            portfolio["analytics"] = (
                self._empty_analytics()
            )

    def _attach_modified_dietz_performance(
        self,
        portfolio: dict[str, Any],
    ) -> None:
        """
        Toplam, Funding ve Trading performanslarını tüm desteklenen
        dönemlerde aynı Modified Dietz motoruyla hesaplar.
        """
        calculation_time = datetime.now(
            self.portfolio_history.APP_TIMEZONE
        )
        references = (
            self.portfolio_history
            .get_performance_reference_snapshots(
                reference_time=calculation_time
            )
        )

        try:
            period_results = (
                self.account_performance.calculate_periods(
                    portfolio=portfolio,
                    reference_snapshots=references,
                    period_end=calculation_time,
                )
            )

            performance = portfolio.get("performance")
            breakdown = portfolio.get(
                "performance_breakdown"
            )
            analytics = portfolio.get("analytics")

            if not isinstance(performance, dict):
                performance = self._empty_performance()
                portfolio["performance"] = performance

            if not isinstance(breakdown, dict):
                breakdown = {
                    "total": self._empty_performance(),
                    "funding": self._empty_performance(),
                    "trading": self._empty_performance(),
                }
                portfolio["performance_breakdown"] = breakdown

            for period_key in (
                "1d",
                "7d",
                "30d",
                "90d",
                "1y",
            ):
                result = period_results.get(period_key)

                if not isinstance(result, dict):
                    performance[period_key] = None

                    for account_name in (
                        "total",
                        "funding",
                        "trading",
                    ):
                        group = breakdown.get(account_name)

                        if isinstance(group, dict):
                            group[period_key] = None

                    continue

                for account_name in (
                    "total",
                    "funding",
                    "trading",
                ):
                    account_result = result[account_name]
                    return_percent = (
                        account_result.return_percent
                    )

                    group = breakdown.get(account_name)

                    if isinstance(group, dict):
                        group[period_key] = return_percent

                    if account_name == "total":
                        performance[period_key] = return_percent

                if isinstance(analytics, dict):
                    period_changes = analytics.get(
                        "period_changes"
                    )

                    if isinstance(period_changes, dict):
                        period_data = period_changes.get(
                            period_key
                        )

                        if isinstance(period_data, dict):
                            for account_name in (
                                "total",
                                "funding",
                                "trading",
                            ):
                                account_data = period_data.get(
                                    account_name
                                )

                                if not isinstance(
                                    account_data,
                                    dict,
                                ):
                                    continue

                                account_result = result[
                                    account_name
                                ]
                                account_data["amount_usdt"] = (
                                    account_result.pnl_usdt
                                )
                                account_data["percent"] = (
                                    account_result.return_percent
                                )
                                account_data["baseline_usdt"] = (
                                    account_result
                                    .start_value_usdt
                                )
                                account_data[
                                    "baseline_timestamp"
                                ] = result[
                                    "reference_snapshot"
                                ].get("timestamp")

        except Exception:
            # Eski snapshot hesabını göstermek yerine yanlış veri
            # üretmemek için tüm dönemleri kullanılamaz bırak.
            empty = self._empty_performance()
            portfolio["performance"] = empty.copy()
            portfolio["performance_breakdown"] = {
                "total": empty.copy(),
                "funding": empty.copy(),
                "trading": empty.copy(),
            }

    def _run_history_maintenance_if_needed(self) -> None:
        if not self._portfolio_history_enabled:
            return

        now = datetime.now(
            self.portfolio_history.APP_TIMEZONE
        )

        if self._last_history_maintenance is not None:
            elapsed = now - self._last_history_maintenance

            if elapsed < self.HISTORY_MAINTENANCE_INTERVAL:
                return

        try:
            self.portfolio_history.optimize_history()
            self._last_history_maintenance = now
        except Exception:
            pass

    def apply_app_settings(self, settings: dict[str, Any]) -> None:
        """
        Çalışma zamanı uygulama tercihlerini uygular.
        """
        if not isinstance(settings, dict):
            return

        self._portfolio_history_enabled = bool(
            settings.get(
                "portfolio_history_enabled",
                True,
            )
        )

        if self._portfolio_history_enabled:
            self._run_history_maintenance_if_needed()

    def get_portfolio_history(
        self,
        period: str,
        max_points: int = 500,
    ) -> list[dict[str, Any]]:
        try:
            return self.portfolio_history.get_history_series(
                period=period,
                max_points=max_points,
            )
        except Exception:
            return []

    def get_available_history_periods(self) -> dict[str, bool]:
        try:
            return (
                self.portfolio_history
                .get_available_history_periods()
            )
        except Exception:
            return {
                "1d": False,
                "7d": False,
                "30d": False,
                "90d": False,
                "1y": False,
            }

    def get_portfolio_analytics(self) -> dict[str, Any]:
        """
        Son portföy yenilemesinde oluşturulan analiz verisini döndürür.
        """
        if not isinstance(self.portfolio, dict):
            return self._empty_analytics()

        analytics = self.portfolio.get("analytics")

        if not isinstance(analytics, dict):
            return self._empty_analytics()

        return analytics

    @staticmethod
    def _empty_analytics() -> dict[str, Any]:
        empty_account_change = {
            "amount_usdt": None,
            "percent": None,
            "baseline_usdt": None,
            "baseline_timestamp": None,
        }

        period_changes = {}

        for period in ("1d", "7d", "30d", "90d", "1y"):
            period_changes[period] = {
                "total": empty_account_change.copy(),
                "funding": empty_account_change.copy(),
                "trading": empty_account_change.copy(),
            }

        empty_summary_group = {
            "highest_usdt": None,
            "lowest_usdt": None,
            "average_usdt": None,
        }

        return {
            "period_changes": period_changes,
            "summary": {
                "snapshot_count": 0,
                "first_timestamp": None,
                "last_timestamp": None,
                "total": empty_summary_group.copy(),
                "funding": empty_summary_group.copy(),
                "trading": empty_summary_group.copy(),
            },
        }

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)

            if number != number:
                return 0.0

            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    @staticmethod
    def _empty_performance() -> dict[str, None]:
        return {
            "1d": None,
            "7d": None,
            "30d": None,
            "90d": None,
            "1y": None,
        }

    def get_portfolio(self):
        return self.portfolio

    def get_price(self, coin):
        return self.cache.get(coin)

    def get_prices(self):
        return self.cache.get_all()

    def clear_cache(self):
        self.cache.clear()

    def reconnect(self):
        self.refresh_client()
        self.clear_cache()
