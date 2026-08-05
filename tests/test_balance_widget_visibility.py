import os
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
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

    def test_widget_shows_without_activation_or_keyboard_focus(self):
        widget = self.make_widget()

        self.assertTrue(
            widget.testAttribute(
                Qt.WA_ShowWithoutActivating
            )
        )
        self.assertEqual(
            widget.focusPolicy(),
            Qt.NoFocus,
        )
        self.assertFalse(
            bool(
                widget.windowFlags()
                & Qt.WindowDoesNotAcceptFocus
            )
        )

        widget.close()

    def test_linux_xcb_bypasses_window_manager(self):
        with (
            patch.object(
                app_module.sys,
                "platform",
                "linux",
            ),
            patch.object(
                app_module.QApplication,
                "platformName",
                return_value="xcb",
            ),
        ):
            flags = (
                app_module.balance_widget_window_flags()
            )

        self.assertTrue(
            bool(
                flags
                & Qt.X11BypassWindowManagerHint
            )
        )

    def test_linux_non_xcb_remains_window_manager_managed(self):
        with (
            patch.object(
                app_module.sys,
                "platform",
                "linux",
            ),
            patch.object(
                app_module.QApplication,
                "platformName",
                return_value="offscreen",
            ),
        ):
            flags = (
                app_module.balance_widget_window_flags()
            )

        self.assertFalse(
            bool(
                flags
                & Qt.X11BypassWindowManagerHint
            )
        )

    def test_windows_does_not_use_x11_bypass_hint(self):
        with (
            patch.object(
                app_module.sys,
                "platform",
                "win32",
            ),
            patch.object(
                app_module.QApplication,
                "platformName",
                return_value="windows",
            ),
        ):
            flags = (
                app_module.balance_widget_window_flags()
            )

        self.assertFalse(
            bool(
                flags
                & Qt.X11BypassWindowManagerHint
            )
        )

    def test_prepare_for_shutdown_hides_widget(self):
        widget = self.make_widget()

        with patch.object(widget, "hide") as hide:
            widget.prepare_for_shutdown()

        hide.assert_called_once_with()
        widget.close()


if __name__ == "__main__":
    unittest.main()
