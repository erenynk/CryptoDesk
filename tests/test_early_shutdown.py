import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from services.data_worker import PortfolioRefreshWorker
import app as app_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def disconnect(self, callback):
        self.callbacks.remove(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class EarlyShutdownTestCase(unittest.TestCase):
    def test_worker_does_not_refresh_when_already_interrupted(self):
        manager = Mock()
        worker = PortfolioRefreshWorker(manager)
        worker.requestInterruption()
        emissions = []
        worker.result_ready.connect(
            lambda success, result: emissions.append(
                (success, result)
            )
        )

        worker.run()

        manager.refresh_portfolio.assert_not_called()
        self.assertEqual(emissions, [])

    def test_worker_does_not_emit_after_shutdown_request(self):
        manager = Mock()
        worker = PortfolioRefreshWorker(manager)
        manager.refresh_portfolio.side_effect = lambda: (
            worker.requestInterruption(),
            (True, {"total_usdt": 100.0}),
        )[1]
        emissions = []
        worker.result_ready.connect(
            lambda success, result: emissions.append(
                (success, result)
            )
        )

        worker.run()

        manager.refresh_portfolio.assert_called_once_with()
        self.assertEqual(emissions, [])

    def test_balance_widget_ignores_late_portfolio_signal(self):
        signal = SignalStub()
        manager = SimpleNamespace(
            portfolio_updated=signal,
        )
        widget = app_module.BalanceWidget(manager)
        original_total = widget.last_total

        widget.prepare_for_shutdown()
        signal.emit(
            {
                "total_usdt": 500.0,
                "trading_usdt": 250.0,
            }
        )

        self.assertTrue(widget._shutdown_prepared)
        self.assertEqual(widget.last_total, original_total)
        self.assertNotIn(
            widget.on_portfolio_updated,
            signal.callbacks,
        )
        widget.close()

    def test_tray_exit_stops_window_before_app_quit(self):
        events = []
        manager = object.__new__(
            app_module.SystemTrayManager
        )
        manager.window = SimpleNamespace(
            allow_application_close=lambda: events.append(
                "allow"
            ),
            shutdown=lambda: events.append("shutdown"),
        )
        manager.tray_icon = SimpleNamespace(
            hide=lambda: events.append("tray_hide")
        )
        manager.app = SimpleNamespace(
            quit=lambda: events.append("quit")
        )

        manager.exit_application()

        self.assertEqual(
            events,
            [
                "allow",
                "tray_hide",
                "shutdown",
                "quit",
            ],
        )


if __name__ == "__main__":
    unittest.main()
