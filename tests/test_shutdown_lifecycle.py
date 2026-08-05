import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from ui.main_window import MainWindow
from ui.portfolio import PortfolioPage


class ShutdownLifecycleTestCase(unittest.TestCase):
    def test_portfolio_waits_for_running_worker(self):
        worker = Mock()
        worker.isRunning.return_value = True

        page = SimpleNamespace(
            _shutting_down=False,
            refresh_timer=Mock(),
            worker=worker,
        )

        PortfolioPage.shutdown(page)

        page.refresh_timer.stop.assert_called_once_with()
        worker.requestInterruption.assert_called_once_with()
        worker.wait.assert_called_once_with()
        self.assertIsNone(page.worker)

    def test_portfolio_without_worker(self):
        page = SimpleNamespace(
            _shutting_down=False,
            refresh_timer=Mock(),
            worker=None,
        )

        PortfolioPage.shutdown(page)

        page.refresh_timer.stop.assert_called_once_with()

    def test_main_window_shutdown_runs_once(self):
        window = SimpleNamespace(
            _shutdown_complete=False,
            alarm_monitor=Mock(),
            portfolio_page=Mock(),
        )

        MainWindow.shutdown(window)
        MainWindow.shutdown(window)

        window.alarm_monitor.stop.assert_called_once_with()
        window.portfolio_page.shutdown.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
