import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QHideEvent, QWindowStateChangeEvent
from PySide6.QtWidgets import QApplication

import app as app_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class DataManagerStub:
    def __init__(self):
        self.portfolio_updated = SignalStub()


class BalanceWidgetVisibilityTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = (
            QApplication.instance()
            or QApplication([])
        )

    @staticmethod
    def make_widget():
        return app_module.BalanceWidget(
            DataManagerStub()
        )

    def test_visibility_setting_tracks_enabled_state(self):
        widget = self.make_widget()
        widget._visibility_restore_pending = True

        widget.set_visibility_enabled(True)
        self.assertTrue(widget._widget_enabled)
        self.assertTrue(
            widget._visibility_restore_pending
        )

        widget.set_visibility_enabled(False)
        self.assertFalse(widget._widget_enabled)
        self.assertFalse(
            widget._visibility_restore_pending
        )

        widget.close()

    def test_schedule_visibility_restore_is_coalesced(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)

        with (
            patch.object(
                app_module.QApplication,
                "closingDown",
                return_value=False,
            ),
            patch.object(
                app_module.QTimer,
                "singleShot",
            ) as single_shot,
        ):
            widget.schedule_visibility_restore()
            widget.schedule_visibility_restore()

        self.assertTrue(
            widget._visibility_restore_pending
        )
        single_shot.assert_called_once_with(
            0,
            widget.restore_visibility,
        )

        widget.set_visibility_enabled(False)
        widget.close()

    def test_restore_visibility_normalizes_minimized_widget(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)
        widget._visibility_restore_pending = True

        with (
            patch.object(
                app_module.QApplication,
                "closingDown",
                return_value=False,
            ),
            patch.object(
                widget,
                "isMinimized",
                return_value=True,
            ),
            patch.object(widget, "showNormal") as show_normal,
            patch.object(widget, "show") as show,
            patch.object(widget, "raise_") as raise_widget,
        ):
            widget.restore_visibility()

        self.assertFalse(
            widget._visibility_restore_pending
        )
        show_normal.assert_called_once_with()
        show.assert_not_called()
        raise_widget.assert_called_once_with()

        widget.set_visibility_enabled(False)
        widget.close()

    def test_restore_visibility_shows_non_minimized_widget(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)

        with (
            patch.object(
                app_module.QApplication,
                "closingDown",
                return_value=False,
            ),
            patch.object(
                widget,
                "isMinimized",
                return_value=False,
            ),
            patch.object(widget, "showNormal") as show_normal,
            patch.object(widget, "show") as show,
            patch.object(widget, "raise_") as raise_widget,
        ):
            widget.restore_visibility()

        show_normal.assert_not_called()
        show.assert_called_once_with()
        raise_widget.assert_called_once_with()

        widget.set_visibility_enabled(False)
        widget.close()

    def test_hide_event_restores_enabled_widget(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)

        with patch.object(
            widget,
            "schedule_visibility_restore",
        ) as schedule_restore:
            widget.hideEvent(QHideEvent())

        schedule_restore.assert_called_once_with()

        widget.set_visibility_enabled(False)
        widget.close()

    def test_window_state_change_restores_minimized_widget(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)
        event = QWindowStateChangeEvent(
            Qt.WindowNoState
        )

        with (
            patch.object(
                widget,
                "isMinimized",
                return_value=True,
            ),
            patch.object(
                widget,
                "schedule_visibility_restore",
            ) as schedule_restore,
        ):
            widget.changeEvent(event)

        self.assertEqual(
            event.type(),
            QEvent.WindowStateChange,
        )
        schedule_restore.assert_called_once_with()

        widget.set_visibility_enabled(False)
        widget.close()

    def test_prepare_for_shutdown_disables_restore(self):
        widget = self.make_widget()
        widget.set_visibility_enabled(True)
        widget._visibility_restore_pending = True

        with patch.object(widget, "hide") as hide:
            widget.prepare_for_shutdown()

        self.assertFalse(widget._widget_enabled)
        self.assertFalse(
            widget._visibility_restore_pending
        )
        hide.assert_called_once_with()

        widget.close()


if __name__ == "__main__":
    unittest.main()
