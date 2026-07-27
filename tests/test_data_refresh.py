import unittest

from services.data_manager import DataManager
from services.data_worker import PortfolioRefreshWorker
from ui.dashboard import DashboardPage


class SignalStub:
    def __init__(self):
        self.calls = []

    def emit(self, *args):
        self.calls.append(args)


class OKXStub:
    def __init__(
        self,
        *,
        success=True,
        result=None,
        error=None,
    ):
        self.success = success
        self.result = (
            result
            if result is not None
            else {
                "total_usdt": 100.0,
                "funding_usdt": 40.0,
                "trading_usdt": 60.0,
                "assets": [],
            }
        )
        self.error = error
        self.call_count = 0

    def get_spot_balances(self, cache):
        self.call_count += 1

        if self.error is not None:
            raise self.error

        return self.success, self.result


class DataManagerHarness:
    refresh_portfolio = DataManager.refresh_portfolio

    def __init__(
        self,
        *,
        okx,
        portfolio=None,
    ):
        self.okx = okx
        self.cache = object()
        self.portfolio = portfolio
        self.last_error = None
        self.loading = False

        self.portfolio_updated = SignalStub()
        self.portfolio_error = SignalStub()

        self.pipeline_calls = []

    def _attach_cost_basis_data(self, portfolio):
        self.pipeline_calls.append(
            ("cost_basis", portfolio)
        )

    def _attach_history_data(self, portfolio):
        self.pipeline_calls.append(
            ("history", portfolio)
        )

    def _attach_modified_dietz_performance(
        self,
        portfolio,
    ):
        self.pipeline_calls.append(
            ("performance", portfolio)
        )

    def _run_history_maintenance_if_needed(self):
        self.pipeline_calls.append(
            ("maintenance", None)
        )

    def get_portfolio(self):
        return self.portfolio


class WorkerHarness:
    run = PortfolioRefreshWorker.run

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.result_ready = SignalStub()


class WorkerDataManagerStub:
    def __init__(
        self,
        *,
        result=None,
        error=None,
    ):
        self.result = (
            result
            if result is not None
            else (
                True,
                {"total_usdt": 100.0},
            )
        )
        self.error = error
        self.call_count = 0

    def refresh_portfolio(self):
        self.call_count += 1

        if self.error is not None:
            raise self.error

        return self.result


class DashboardDataManagerStub:
    def __init__(self, portfolio):
        self.portfolio = portfolio
        self.get_portfolio_calls = 0

    def get_portfolio(self):
        self.get_portfolio_calls += 1
        return self.portfolio


class DashboardHarness:
    refresh = DashboardPage.refresh

    def __init__(self, data_manager):
        self.data_manager = data_manager
        self.waiting_count = 0
        self.updated_portfolios = []

    def _set_waiting_status(self):
        self.waiting_count += 1

    def on_portfolio_updated(self, portfolio):
        self.updated_portfolios.append(portfolio)


class DataRefreshTestCase(unittest.TestCase):
    def test_second_refresh_is_blocked_while_loading(self):
        okx = OKXStub()
        manager = DataManagerHarness(okx=okx)
        manager.loading = True

        success, result = manager.refresh_portfolio()

        self.assertFalse(success)
        self.assertEqual(result, "Loading")
        self.assertEqual(okx.call_count, 0)
        self.assertTrue(manager.loading)
        self.assertEqual(
            manager.portfolio_updated.calls,
            [],
        )
        self.assertEqual(
            manager.portfolio_error.calls,
            [],
        )

    def test_successful_refresh_runs_pipeline_in_order(self):
        portfolio = {
            "total_usdt": 100.0,
            "funding_usdt": 40.0,
            "trading_usdt": 60.0,
            "assets": [],
        }
        okx = OKXStub(
            success=True,
            result=portfolio,
        )
        manager = DataManagerHarness(okx=okx)

        success, result = manager.refresh_portfolio()

        self.assertTrue(success)
        self.assertIs(result, portfolio)
        self.assertIs(manager.portfolio, portfolio)
        self.assertIsNone(manager.last_error)
        self.assertFalse(manager.loading)

        self.assertEqual(
            [
                call[0]
                for call in manager.pipeline_calls
            ],
            [
                "cost_basis",
                "history",
                "performance",
                "maintenance",
            ],
        )

        for _, received_portfolio in (
            manager.pipeline_calls[:3]
        ):
            self.assertIs(
                received_portfolio,
                portfolio,
            )

        self.assertEqual(
            manager.portfolio_updated.calls,
            [(portfolio,)],
        )
        self.assertEqual(
            manager.portfolio_error.calls,
            [],
        )

    def test_failed_api_refresh_preserves_previous_portfolio(self):
        previous_portfolio = {
            "total_usdt": 75.0,
        }
        api_error = "API unavailable"

        okx = OKXStub(
            success=False,
            result=api_error,
        )
        manager = DataManagerHarness(
            okx=okx,
            portfolio=previous_portfolio,
        )

        success, result = manager.refresh_portfolio()

        self.assertFalse(success)
        self.assertEqual(result, api_error)
        self.assertIs(
            manager.portfolio,
            previous_portfolio,
        )
        self.assertEqual(
            manager.last_error,
            api_error,
        )
        self.assertFalse(manager.loading)
        self.assertEqual(manager.pipeline_calls, [])
        self.assertEqual(
            manager.portfolio_updated.calls,
            [],
        )
        self.assertEqual(
            manager.portfolio_error.calls,
            [(api_error,)],
        )

    def test_exception_preserves_previous_portfolio_and_unlocks(self):
        previous_portfolio = {
            "total_usdt": 50.0,
        }
        okx = OKXStub(
            error=RuntimeError("network failure"),
        )
        manager = DataManagerHarness(
            okx=okx,
            portfolio=previous_portfolio,
        )

        success, result = manager.refresh_portfolio()

        self.assertFalse(success)
        self.assertEqual(result, "network failure")
        self.assertIs(
            manager.portfolio,
            previous_portfolio,
        )
        self.assertEqual(
            manager.last_error,
            "network failure",
        )
        self.assertFalse(manager.loading)
        self.assertEqual(
            manager.portfolio_error.calls,
            [("network failure",)],
        )

    def test_pipeline_exception_does_not_replace_cached_portfolio(self):
        previous_portfolio = {
            "total_usdt": 25.0,
        }
        new_portfolio = {
            "total_usdt": 100.0,
            "assets": [],
        }

        okx = OKXStub(
            success=True,
            result=new_portfolio,
        )
        manager = DataManagerHarness(
            okx=okx,
            portfolio=previous_portfolio,
        )

        def raise_in_history(portfolio):
            raise RuntimeError("history failure")

        manager._attach_history_data = raise_in_history

        success, result = manager.refresh_portfolio()

        self.assertFalse(success)
        self.assertEqual(result, "history failure")
        self.assertIs(
            manager.portfolio,
            previous_portfolio,
        )
        self.assertFalse(manager.loading)
        self.assertEqual(
            manager.portfolio_updated.calls,
            [],
        )
        self.assertEqual(
            manager.portfolio_error.calls,
            [("history failure",)],
        )

    def test_worker_emits_data_manager_result(self):
        portfolio = {
            "total_usdt": 100.0,
        }
        data_manager = WorkerDataManagerStub(
            result=(True, portfolio)
        )
        worker = WorkerHarness(data_manager)

        worker.run()

        self.assertEqual(
            data_manager.call_count,
            1,
        )
        self.assertEqual(
            worker.result_ready.calls,
            [(True, portfolio)],
        )

    def test_worker_converts_exception_to_error_result(self):
        data_manager = WorkerDataManagerStub(
            error=RuntimeError("worker failure")
        )
        worker = WorkerHarness(data_manager)

        worker.run()

        self.assertEqual(
            data_manager.call_count,
            1,
        )
        self.assertEqual(
            worker.result_ready.calls,
            [(False, "worker failure")],
        )

    def test_dashboard_uses_cached_portfolio(self):
        portfolio = {
            "total_usdt": 100.0,
        }
        data_manager = DashboardDataManagerStub(
            portfolio
        )
        dashboard = DashboardHarness(data_manager)

        dashboard.refresh()

        self.assertEqual(
            data_manager.get_portfolio_calls,
            1,
        )
        self.assertEqual(
            dashboard.waiting_count,
            0,
        )
        self.assertEqual(
            dashboard.updated_portfolios,
            [portfolio],
        )
        self.assertIs(
            dashboard.updated_portfolios[0],
            portfolio,
        )

    def test_dashboard_waits_when_cache_is_empty(self):
        data_manager = DashboardDataManagerStub(None)
        dashboard = DashboardHarness(data_manager)

        dashboard.refresh()

        self.assertEqual(
            data_manager.get_portfolio_calls,
            1,
        )
        self.assertEqual(
            dashboard.waiting_count,
            1,
        )
        self.assertEqual(
            dashboard.updated_portfolios,
            [],
        )

    def test_dashboard_reads_same_object_stored_by_refresh(self):
        portfolio = {
            "total_usdt": 125.0,
            "assets": [],
        }
        okx = OKXStub(
            success=True,
            result=portfolio,
        )
        manager = DataManagerHarness(okx=okx)

        success, result = manager.refresh_portfolio()

        self.assertTrue(success)
        self.assertIs(result, portfolio)

        dashboard = DashboardHarness(manager)
        dashboard.refresh()

        self.assertEqual(
            dashboard.updated_portfolios,
            [portfolio],
        )
        self.assertIs(
            dashboard.updated_portfolios[0],
            manager.portfolio,
        )


if __name__ == "__main__":
    unittest.main()
