from pathlib import Path
import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication

import app as app_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class ScreenStub:
    def __init__(self, geometry):
        self.geometry = geometry

    def availableGeometry(self):
        return self.geometry


class IconStub:
    def __init__(self, is_null=False):
        self._is_null = is_null

    def isNull(self):
        return self._is_null


class TrayIconStub:
    Trigger = 1
    DoubleClick = 2

    def __init__(self, parent):
        self.parent = parent
        self.activated = SignalStub()
        self.tooltip = None
        self.icon = None
        self.menu = None
        self.show_count = 0
        self.hide_count = 0

    def setToolTip(self, value):
        self.tooltip = value

    def setIcon(self, value):
        self.icon = value

    def setContextMenu(self, value):
        self.menu = value

    def show(self):
        self.show_count += 1

    def hide(self):
        self.hide_count += 1


class ActionStub:
    def __init__(self, text, parent):
        self.text = text
        self.parent = parent
        self.triggered = SignalStub()


class MenuStub:
    def __init__(self):
        self.actions = []
        self.separator_count = 0

    def addAction(self, action):
        self.actions.append(action)

    def addSeparator(self):
        self.separator_count += 1


class AppTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = (
            QApplication.instance()
            or QApplication([])
        )

    @staticmethod
    def make_widget_manager():
        return SimpleNamespace(
            portfolio_updated=SignalStub()
        )

    def test_balance_widget_initial_state_and_signal(self):
        manager = self.make_widget_manager()

        widget = app_module.BalanceWidget(manager)

        self.assertEqual(widget.width(), 250)
        self.assertEqual(widget.height(), 76)
        self.assertFalse(widget.balance_hidden)
        self.assertEqual(widget.last_total, 0.0)
        self.assertEqual(widget.last_trading, 0.0)
        self.assertEqual(
            widget.balance_label.text(),
            "$0.00",
        )
        self.assertEqual(
            widget.trading_label.text(),
            "Trading  $0.00",
        )
        self.assertEqual(
            len(
                manager.portfolio_updated.callbacks
            ),
            1,
        )

        widget.close()

    def test_balance_widget_updates_formatted_values(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )

        widget.on_portfolio_updated(
            {
                "total_usdt": 1234567.891,
                "trading_usdt": 4321.5,
            }
        )

        self.assertEqual(
            widget.last_total,
            1234567.891,
        )
        self.assertEqual(
            widget.last_trading,
            4321.5,
        )
        self.assertEqual(
            widget.balance_label.text(),
            "$1,234,567.89",
        )
        self.assertEqual(
            widget.trading_label.text(),
            "Trading  $4,321.50",
        )

        widget.close()

    def test_balance_widget_defaults_missing_values(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )

        widget.on_portfolio_updated({})

        self.assertEqual(widget.last_total, 0.0)
        self.assertEqual(widget.last_trading, 0.0)
        self.assertEqual(
            widget.balance_label.text(),
            "$0.00",
        )
        self.assertEqual(
            widget.trading_label.text(),
            "Trading  $0.00",
        )

        widget.close()

    def test_balance_widget_toggle_hides_and_restores(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )
        widget.on_portfolio_updated(
            {
                "total_usdt": 100.0,
                "trading_usdt": 40.0,
            }
        )

        widget.toggle_balance()

        self.assertTrue(widget.balance_hidden)
        self.assertEqual(
            widget.balance_label.text(),
            "••••••",
        )
        self.assertEqual(
            widget.trading_label.text(),
            "Trading  ••••••",
        )
        self.assertEqual(
            widget.hide_button.text(),
            "○",
        )

        widget.toggle_balance()

        self.assertFalse(widget.balance_hidden)
        self.assertEqual(
            widget.balance_label.text(),
            "$100.00",
        )
        self.assertEqual(
            widget.trading_label.text(),
            "Trading  $40.00",
        )
        self.assertEqual(
            widget.hide_button.text(),
            "⊙",
        )

        widget.close()

    def test_balance_widget_clamps_to_primary_screen(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )
        screen = ScreenStub(
            QRect(100, 100, 800, 600)
        )

        with (
            patch.object(
                app_module.QApplication,
                "screenAt",
                return_value=None,
            ) as screen_at,
            patch.object(
                app_module.QApplication,
                "primaryScreen",
                return_value=screen,
            ) as primary_screen,
        ):
            upper = widget.clamp_to_screen(
                QPoint(2000, 2000)
            )
            lower = widget.clamp_to_screen(
                QPoint(-100, -100)
            )

        self.assertEqual(upper, (645, 619))
        self.assertEqual(lower, (104, 104))
        screen_at.assert_called()
        primary_screen.assert_called()

        widget.close()

    def test_acquire_single_instance_lock_succeeds(
        self,
    ):
        lock = Mock()
        lock.tryLock.return_value = True
        lock_path = Path("/tmp/cryptodesk-test.lock")

        with (
            patch.object(
                app_module,
                "single_instance_lock_path",
                return_value=lock_path,
            ),
            patch.object(
                app_module,
                "QLockFile",
                return_value=lock,
            ) as lock_class,
        ):
            result = (
                app_module.acquire_single_instance_lock()
            )

        self.assertIs(result, lock)
        lock_class.assert_called_once_with(
            str(lock_path)
        )
        lock.tryLock.assert_called_once_with(100)

    def test_acquire_single_instance_lock_rejects_second_instance(
        self,
    ):
        lock = Mock()
        lock.tryLock.return_value = False

        with (
            patch.object(
                app_module,
                "single_instance_lock_path",
                return_value=Path(
                    "/tmp/cryptodesk-test.lock"
                ),
            ),
            patch.object(
                app_module,
                "QLockFile",
                return_value=lock,
            ),
        ):
            result = (
                app_module.acquire_single_instance_lock()
            )

        self.assertIsNone(result)
        lock.tryLock.assert_called_once_with(100)

    def test_load_application_icon_uses_asset(
        self,
    ):
        icon_path = Mock()
        icon_path.is_file.return_value = True
        icon = Mock()

        with (
            patch.object(
                app_module,
                "application_icon_path",
                return_value=icon_path,
            ),
            patch.object(
                app_module,
                "QIcon",
                return_value=icon,
            ) as qicon,
        ):
            result = app_module.load_application_icon()

        self.assertIs(result, icon)
        qicon.assert_called_once_with(
            str(icon_path)
        )

    def test_load_application_icon_returns_empty_icon_when_missing(
        self,
    ):
        icon_path = Mock()
        icon_path.is_file.return_value = False
        icon = Mock()

        with (
            patch.object(
                app_module,
                "application_icon_path",
                return_value=icon_path,
            ),
            patch.object(
                app_module,
                "QIcon",
                return_value=icon,
            ) as qicon,
        ):
            result = app_module.load_application_icon()

        self.assertIs(result, icon)
        qicon.assert_called_once_with()

    def test_system_tray_initializes_menu_and_fallback_icon(
        self,
    ):
        window_icon = IconStub(is_null=True)
        fallback_icon = IconStub(is_null=False)

        window = SimpleNamespace(
            windowIcon=Mock(
                return_value=window_icon
            ),
            setWindowIcon=Mock(),
            show_from_tray=Mock(),
            allow_application_close=Mock(),
        )
        style = SimpleNamespace(
            standardIcon=Mock(
                return_value=fallback_icon
            )
        )
        qt_app = SimpleNamespace(
            style=Mock(return_value=style),
            quit=Mock(),
        )

        with (
            patch.object(
                app_module,
                "QSystemTrayIcon",
                TrayIconStub,
            ),
            patch.object(
                app_module,
                "QMenu",
                MenuStub,
            ),
            patch.object(
                app_module,
                "QAction",
                ActionStub,
            ),
        ):
            manager = app_module.SystemTrayManager(
                app=qt_app,
                window=window,
            )

        self.assertEqual(
            manager.tray_icon.tooltip,
            "CryptoDesk",
        )
        self.assertIs(
            manager.tray_icon.icon,
            fallback_icon,
        )
        self.assertIs(
            manager.tray_icon.menu,
            manager.menu,
        )
        self.assertEqual(
            manager.tray_icon.show_count,
            1,
        )
        self.assertEqual(
            [
                action.text
                for action in manager.menu.actions
            ],
            [
                "CryptoDesk'i Aç",
                "Çıkış",
            ],
        )
        self.assertEqual(
            manager.menu.separator_count,
            1,
        )
        self.assertEqual(
            len(manager.tray_icon.activated.callbacks),
            1,
        )
        window.setWindowIcon.assert_called_once_with(
            fallback_icon
        )
        style.standardIcon.assert_called_once()

    def test_system_tray_actions_delegate(self):
        manager = object.__new__(
            app_module.SystemTrayManager
        )
        manager.window = SimpleNamespace(
            show_from_tray=Mock(),
            allow_application_close=Mock(),
        )
        manager.tray_icon = SimpleNamespace(
            hide=Mock()
        )
        manager.app = SimpleNamespace(
            quit=Mock()
        )

        manager.show_main_window()
        manager.exit_application()

        manager.window.show_from_tray.assert_called_once_with()
        manager.window.allow_application_close.assert_called_once_with()
        manager.tray_icon.hide.assert_called_once_with()
        manager.app.quit.assert_called_once_with()

    def test_system_tray_activation_filters_reasons(
        self,
    ):
        manager = object.__new__(
            app_module.SystemTrayManager
        )
        manager.show_main_window = Mock()

        manager.on_tray_activated(
            app_module.QSystemTrayIcon.Trigger
        )
        manager.on_tray_activated(
            app_module.QSystemTrayIcon.DoubleClick
        )
        manager.on_tray_activated(
            app_module.QSystemTrayIcon.Context
        )

        self.assertEqual(
            manager.show_main_window.call_count,
            2,
        )

    @staticmethod
    def build_main_dependencies(
        *,
        geometry,
        app_settings,
        exit_code=0,
    ):
        fake_app = Mock()
        fake_app.primaryScreen.return_value = (
            ScreenStub(geometry)
        )
        fake_app.exec.return_value = exit_code

        data_manager = Mock()
        window = Mock()
        window.settings_page = SimpleNamespace(
            app_settings_changed=SignalStub()
        )

        balance_widget = Mock()
        balance_widget.width.return_value = 250
        balance_widget.height.return_value = 76

        return {
            "fake_app": fake_app,
            "data_manager": data_manager,
            "window": window,
            "balance_widget": balance_widget,
            "settings": app_settings,
        }

    def test_main_without_tray_configures_and_starts(
        self,
    ):
        dependencies = self.build_main_dependencies(
            geometry=QRect(0, 0, 1600, 900),
            app_settings={
                "balance_widget_enabled": True,
                "refresh_on_start_enabled": True,
                "portfolio_history_enabled": True,
            },
            exit_code=7,
        )

        with (
            patch.object(
                app_module,
                "QApplication",
            ) as application_class,
            patch.object(
                app_module,
                "QSystemTrayIcon",
            ) as tray_class,
            patch.object(
                app_module,
                "DataManager",
                return_value=(
                    dependencies["data_manager"]
                ),
            ),
            patch.object(
                app_module,
                "get_all_app_settings",
                return_value=(
                    dependencies["settings"]
                ),
            ),
            patch.object(
                app_module,
                "MainWindow",
                return_value=(
                    dependencies["window"]
                ),
            ),
            patch.object(
                app_module,
                "BalanceWidget",
                return_value=(
                    dependencies["balance_widget"]
                ),
            ),
            patch.object(
                app_module,
                "SystemTrayManager",
            ) as tray_manager_class,
            patch.object(
                app_module.QTimer,
                "singleShot",
            ) as single_shot,
            patch.object(
                app_module.sys,
                "exit",
            ) as sys_exit,
        ):
            application_class.return_value = (
                dependencies["fake_app"]
            )
            tray_class.isSystemTrayAvailable.return_value = (
                False
            )

            app_module.main()

        application_class.assert_called_once_with(
            sys.argv
        )
        dependencies[
            "fake_app"
        ].setDesktopFileName.assert_called_once_with(
            app_module.APP_ID
        )
        dependencies["fake_app"].setFont.assert_called_once()
        application_class.setQuitOnLastWindowClosed.assert_called_once_with(
            True
        )
        dependencies[
            "data_manager"
        ].apply_app_settings.assert_called_once_with(
            dependencies["settings"]
        )
        dependencies["window"].resize.assert_called_once_with(
            1452,
            858,
        )
        dependencies["window"].move.assert_called_once_with(
            74,
            21,
        )
        dependencies["window"].show.assert_called_once_with()
        dependencies[
            "balance_widget"
        ].move.assert_called_once_with(
            1345,
            819,
        )
        dependencies[
            "balance_widget"
        ].show.assert_called_once_with()
        single_shot.assert_not_called()
        tray_manager_class.assert_not_called()
        sys_exit.assert_called_once_with(7)

    def test_main_with_tray_respects_disabled_settings(
        self,
    ):
        dependencies = self.build_main_dependencies(
            geometry=QRect(0, 0, 1000, 700),
            app_settings={
                "balance_widget_enabled": False,
                "refresh_on_start_enabled": False,
            },
        )

        with (
            patch.object(
                app_module,
                "QApplication",
            ) as application_class,
            patch.object(
                app_module,
                "QSystemTrayIcon",
            ) as tray_class,
            patch.object(
                app_module,
                "DataManager",
                return_value=(
                    dependencies["data_manager"]
                ),
            ),
            patch.object(
                app_module,
                "get_all_app_settings",
                return_value=(
                    dependencies["settings"]
                ),
            ),
            patch.object(
                app_module,
                "MainWindow",
                return_value=(
                    dependencies["window"]
                ),
            ),
            patch.object(
                app_module,
                "BalanceWidget",
                return_value=(
                    dependencies["balance_widget"]
                ),
            ),
            patch.object(
                app_module,
                "SystemTrayManager",
            ) as tray_manager_class,
            patch.object(
                app_module.QTimer,
                "singleShot",
            ) as single_shot,
            patch.object(
                app_module.sys,
                "exit",
            ),
        ):
            application_class.return_value = (
                dependencies["fake_app"]
            )
            tray_class.isSystemTrayAvailable.return_value = (
                True
            )

            app_module.main()

        application_class.setQuitOnLastWindowClosed.assert_called_once_with(
            False
        )
        dependencies["window"].resize.assert_called_once_with(
            1000,
            700,
        )
        dependencies["window"].move.assert_called_once_with(
            0,
            0,
        )
        dependencies[
            "balance_widget"
        ].hide.assert_called_once_with()
        single_shot.assert_not_called()
        tray_manager_class.assert_called_once_with(
            app=dependencies["fake_app"],
            window=dependencies["window"],
        )

    def test_runtime_settings_toggle_balance_widget(
        self,
    ):
        dependencies = self.build_main_dependencies(
            geometry=QRect(0, 0, 1200, 800),
            app_settings={
                "balance_widget_enabled": False,
                "refresh_on_start_enabled": False,
            },
        )

        with (
            patch.object(
                app_module,
                "QApplication",
            ) as application_class,
            patch.object(
                app_module,
                "QSystemTrayIcon",
            ) as tray_class,
            patch.object(
                app_module,
                "DataManager",
                return_value=(
                    dependencies["data_manager"]
                ),
            ),
            patch.object(
                app_module,
                "get_all_app_settings",
                return_value=(
                    dependencies["settings"]
                ),
            ),
            patch.object(
                app_module,
                "MainWindow",
                return_value=(
                    dependencies["window"]
                ),
            ),
            patch.object(
                app_module,
                "BalanceWidget",
                return_value=(
                    dependencies["balance_widget"]
                ),
            ),
            patch.object(
                app_module,
                "SystemTrayManager",
            ),
            patch.object(
                app_module.QTimer,
                "singleShot",
            ),
            patch.object(
                app_module.sys,
                "exit",
            ),
        ):
            application_class.return_value = (
                dependencies["fake_app"]
            )
            tray_class.isSystemTrayAvailable.return_value = (
                False
            )

            app_module.main()

        signal = (
            dependencies["window"]
            .settings_page
            .app_settings_changed
        )

        self.assertEqual(
            len(signal.callbacks),
            1,
        )

        signal.emit(
            {
                "balance_widget_enabled": True,
                "portfolio_history_enabled": False,
            }
        )
        signal.emit(
            {
                "balance_widget_enabled": False,
                "portfolio_history_enabled": True,
            }
        )

        self.assertEqual(
            dependencies[
                "data_manager"
            ].apply_app_settings.call_count,
            3,
        )
        dependencies[
            "balance_widget"
        ].raise_.assert_not_called()
        self.assertEqual(
            dependencies[
                "balance_widget"
            ].show.call_count,
            1,
        )
        self.assertEqual(
            dependencies[
                "balance_widget"
            ].hide.call_count,
            2,
        )



    def test_balance_widget_left_press_starts_dragging(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )
        widget.move(50, 60)

        event = QMouseEvent(
            QEvent.MouseButtonPress,
            QPointF(10.0, 15.0),
            QPointF(150.0, 175.0),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )

        widget.mousePressEvent(event)

        self.assertTrue(widget.dragging)
        self.assertEqual(
            widget.offset,
            QPoint(100, 115),
        )

        widget.close()

    def test_balance_widget_mouse_move_clamps_and_moves(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )
        widget.dragging = True
        widget.offset = QPoint(20, 30)
        widget.clamp_to_screen = Mock(
            return_value=(300, 400)
        )
        widget.move = Mock()

        event = QMouseEvent(
            QEvent.MouseMove,
            QPointF(5.0, 5.0),
            QPointF(500.0, 600.0),
            Qt.NoButton,
            Qt.LeftButton,
            Qt.NoModifier,
        )

        widget.mouseMoveEvent(event)

        widget.clamp_to_screen.assert_called_once_with(
            QPoint(480, 570)
        )
        widget.move.assert_called_once_with(
            300,
            400,
        )

        widget.close()

    def test_balance_widget_mouse_release_resets_and_clamps(
        self,
    ):
        widget = app_module.BalanceWidget(
            self.make_widget_manager()
        )
        widget.dragging = True
        widget.offset = QPoint(20, 30)
        widget.pos = Mock(
            return_value=QPoint(700, 800)
        )
        widget.clamp_to_screen = Mock(
            return_value=(600, 650)
        )
        widget.move = Mock()

        event = QMouseEvent(
            QEvent.MouseButtonRelease,
            QPointF(5.0, 5.0),
            QPointF(705.0, 805.0),
            Qt.LeftButton,
            Qt.NoButton,
            Qt.NoModifier,
        )

        widget.mouseReleaseEvent(event)

        self.assertFalse(widget.dragging)
        self.assertIsNone(widget.offset)
        widget.clamp_to_screen.assert_called_once_with(
            QPoint(700, 800)
        )
        widget.move.assert_called_once_with(
            600,
            650,
        )

        widget.close()



if __name__ == "__main__":
    unittest.main()
