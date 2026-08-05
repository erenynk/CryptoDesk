import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent

import app as app_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self):
        for callback in list(self.callbacks):
            callback()


class EventStub:
    def __init__(self):
        self.ignore = Mock()

    @staticmethod
    def type():
        return QEvent.Close


class WindowStub:
    def __init__(
        self,
        *,
        worker=None,
        minimize_to_tray=False,
        tray_available=False,
    ):
        self._allow_close = False
        self._minimize_to_tray_enabled = (
            minimize_to_tray
        )
        self._tray_available = tray_available
        self.installEventFilter = Mock()
        self.allow_application_close = Mock(
            side_effect=self._allow_application_close
        )
        self.hide = Mock()
        self.shutdown = Mock()
        self.alarm_monitor = SimpleNamespace(
            stop=Mock()
        )
        self.portfolio_page = SimpleNamespace(
            worker=worker,
            refresh_timer=SimpleNamespace(
                stop=Mock()
            ),
            _shutting_down=False,
        )

    def _allow_application_close(self):
        self._allow_close = True

    def system_tray_available(self):
        return self._tray_available


class WorkerStub:
    def __init__(self, running=True):
        self.finished = SignalStub()
        self._running = running
        self.requestInterruption = Mock()

    def isRunning(self):
        return self._running


class ApplicationShutdownCoordinatorTestCase(
    unittest.TestCase
):
    def make_coordinator(
        self,
        *,
        worker=None,
        minimize_to_tray=False,
        tray_available=False,
    ):
        app = SimpleNamespace(
            quit=Mock()
        )
        window = WindowStub(
            worker=worker,
            minimize_to_tray=minimize_to_tray,
            tray_available=tray_available,
        )
        balance_widget = SimpleNamespace(
            prepare_for_shutdown=Mock()
        )
        coordinator = (
            app_module.ApplicationShutdownCoordinator(
                app=app,
                window=window,
                balance_widget=balance_widget,
            )
        )
        return (
            coordinator,
            app,
            window,
            balance_widget,
        )

    def test_request_exit_waits_for_running_worker(self):
        worker = WorkerStub(running=True)
        (
            coordinator,
            app,
            window,
            balance_widget,
        ) = self.make_coordinator(worker=worker)

        with patch.object(
            app_module.QTimer,
            "singleShot",
        ) as single_shot:
            coordinator.request_exit()

            worker.requestInterruption.assert_called_once_with()
            single_shot.assert_not_called()
            app.quit.assert_not_called()
            window.shutdown.assert_not_called()

            worker._running = False
            worker.finished.emit()

            window.shutdown.assert_called_once_with()
            single_shot.assert_called_once_with(
                0,
                app.quit,
            )

        balance_widget.prepare_for_shutdown.assert_called_once_with()
        window.hide.assert_called_once_with()
        window.portfolio_page.refresh_timer.stop.assert_called_once_with()
        window.alarm_monitor.stop.assert_called_once_with()
        self.assertIsNone(
            window.portfolio_page.worker
        )

    def test_request_exit_without_worker_quits_asynchronously(self):
        (
            coordinator,
            app,
            window,
            _,
        ) = self.make_coordinator(worker=None)

        with patch.object(
            app_module.QTimer,
            "singleShot",
        ) as single_shot:
            coordinator.request_exit()

        window.shutdown.assert_called_once_with()
        single_shot.assert_called_once_with(
            0,
            app.quit,
        )

    def test_close_event_keeps_minimize_to_tray_behavior(self):
        (
            coordinator,
            _,
            _,
            _,
        ) = self.make_coordinator(
            worker=None,
            minimize_to_tray=True,
            tray_available=True,
        )
        event = EventStub()

        handled = coordinator.eventFilter(
            coordinator.window,
            event,
        )

        self.assertFalse(handled)
        event.ignore.assert_not_called()

    def test_close_event_intercepts_real_application_exit(self):
        (
            coordinator,
            _,
            _,
            _,
        ) = self.make_coordinator(
            worker=None,
            minimize_to_tray=False,
            tray_available=True,
        )
        event = EventStub()

        with patch.object(
            app_module.QTimer,
            "singleShot",
        ):
            handled = coordinator.eventFilter(
                coordinator.window,
                event,
            )

        self.assertTrue(handled)
        event.ignore.assert_called_once_with()

    def test_tray_exit_delegates_to_coordinator(self):
        manager = object.__new__(
            app_module.SystemTrayManager
        )
        manager.window = SimpleNamespace(
            allow_application_close=Mock()
        )
        manager.tray_icon = SimpleNamespace(
            hide=Mock()
        )
        manager.shutdown_coordinator = SimpleNamespace(
            request_exit=Mock()
        )
        manager.app = SimpleNamespace(
            quit=Mock()
        )

        manager.exit_application()

        manager.window.allow_application_close.assert_called_once_with()
        manager.tray_icon.hide.assert_called_once_with()
        manager.shutdown_coordinator.request_exit.assert_called_once_with()
        manager.app.quit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
