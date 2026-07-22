import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QApplication, QMainWindow

import ui.main_window as main_window_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class EffectStub:
    def __init__(self, page):
        self.page = page
        self.opacity = None

    def setOpacity(self, value):
        self.opacity = value


class AnimationStub:
    instances = []

    def __init__(
        self,
        effect,
        property_name,
        parent,
    ):
        self.effect = effect
        self.property_name = property_name
        self.parent = parent
        self.duration = None
        self.start_value = None
        self.end_value = None
        self.easing_curve = None
        self.finished = SignalStub()
        self.started = False
        self.__class__.instances.append(self)

    def setDuration(self, value):
        self.duration = value

    def setStartValue(self, value):
        self.start_value = value

    def setEndValue(self, value):
        self.end_value = value

    def setEasingCurve(self, value):
        self.easing_curve = value

    def start(self):
        self.started = True


class BareMainWindow(main_window_module.MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)


class MainWindowTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.qt_app = (
            QApplication.instance()
            or QApplication([])
        )

    def setUp(self):
        AnimationStub.instances.clear()
        self.windows = []

    def tearDown(self):
        for window in self.windows:
            window.deleteLater()

    def make_window(self):
        window = BareMainWindow()
        self.windows.append(window)
        return window

    def test_constructor_loads_settings_and_services(
        self,
    ):
        data_manager = sentinel.data_manager
        notification_manager = (
            sentinel.notification_manager
        )

        with (
            patch.object(
                main_window_module,
                "get_app_setting",
                side_effect=[
                    False,
                    True,
                    False,
                ],
            ) as get_setting,
            patch.object(
                main_window_module,
                "DataManager",
                return_value=data_manager,
            ) as data_manager_class,
            patch.object(
                main_window_module,
                "NotificationManager",
                return_value=notification_manager,
            ) as notification_manager_class,
            patch.object(
                main_window_module.MainWindow,
                "_build_ui",
            ) as build_ui,
            patch.object(
                main_window_module.MainWindow,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                main_window_module.MainWindow,
                "_create_pages",
            ) as create_pages,
            patch.object(
                main_window_module.MainWindow,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                main_window_module.MainWindow,
                "_start_alarm_monitor",
            ) as start_monitor,
        ):
            window = main_window_module.MainWindow()
            self.windows.append(window)

        self.assertFalse(window._allow_close)
        self.assertFalse(
            window._minimize_to_tray_enabled
        )
        self.assertTrue(
            window._notifications_enabled
        )
        self.assertFalse(
            window._alarm_sound_enabled
        )
        self.assertIs(
            window.notification_manager,
            notification_manager,
        )
        self.assertIs(
            window.data_manager,
            data_manager,
        )
        self.assertIsNone(window._page_animation)
        self.assertEqual(
            window.windowTitle(),
            "Caspian",
        )
        self.assertEqual(
            window.size().width(),
            1320,
        )
        self.assertEqual(
            window.size().height(),
            780,
        )
        self.assertEqual(
            window.minimumWidth(),
            1100,
        )
        self.assertEqual(
            window.minimumHeight(),
            700,
        )

        self.assertEqual(
            get_setting.call_args_list,
            [
                call(
                    "minimize_to_tray_enabled",
                    True,
                ),
                call(
                    "notifications_enabled",
                    True,
                ),
                call(
                    "alarm_sound_enabled",
                    False,
                ),
            ],
        )
        data_manager_class.assert_called_once_with()
        notification_manager_class.assert_called_once_with()
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        create_pages.assert_called_once_with()
        connect_signals.assert_called_once_with()
        start_monitor.assert_called_once_with()

    def test_create_pages_builds_expected_page_order(
        self,
    ):
        window = self.make_window()
        window.data_manager = sentinel.data_manager
        window.pages = Mock()
        window.menu = Mock()

        page_values = {
            "dashboard": sentinel.dashboard,
            "portfolio": sentinel.portfolio,
            "watchlist": sentinel.watchlist,
            "alarms": sentinel.alarms,
            "analytics": sentinel.analytics,
            "settings": sentinel.settings,
        }

        with (
            patch.object(
                main_window_module,
                "DashboardPage",
                return_value=(
                    page_values["dashboard"]
                ),
            ) as dashboard_class,
            patch.object(
                main_window_module,
                "PortfolioPage",
                return_value=(
                    page_values["portfolio"]
                ),
            ) as portfolio_class,
            patch.object(
                main_window_module,
                "WatchlistPage",
                return_value=(
                    page_values["watchlist"]
                ),
            ) as watchlist_class,
            patch.object(
                main_window_module,
                "AlarmsPage",
                return_value=(
                    page_values["alarms"]
                ),
            ) as alarms_class,
            patch.object(
                main_window_module,
                "AnalyticsPage",
                return_value=(
                    page_values["analytics"]
                ),
            ) as analytics_class,
            patch.object(
                main_window_module,
                "SettingsPage",
                return_value=(
                    page_values["settings"]
                ),
            ) as settings_class,
        ):
            window._create_pages()

        dashboard_class.assert_called_once_with(
            sentinel.data_manager
        )
        portfolio_class.assert_called_once_with(
            sentinel.data_manager,
            sentinel.dashboard,
        )
        watchlist_class.assert_called_once_with(
            sentinel.data_manager
        )
        alarms_class.assert_called_once_with(
            sentinel.data_manager
        )
        analytics_class.assert_called_once_with(
            sentinel.data_manager
        )
        settings_class.assert_called_once_with()

        self.assertEqual(
            window.pages.addWidget.call_args_list,
            [
                call(sentinel.dashboard),
                call(sentinel.portfolio),
                call(sentinel.watchlist),
                call(sentinel.alarms),
                call(sentinel.analytics),
                call(sentinel.settings),
            ],
        )
        window.menu.setCurrentRow.assert_called_once_with(
            0
        )

    def test_connect_signals_wires_navigation_and_settings(
        self,
    ):
        window = self.make_window()
        navigation_signal = SignalStub()
        settings_signal = SignalStub()
        window.menu = SimpleNamespace(
            currentRowChanged=navigation_signal
        )
        window.settings_page = SimpleNamespace(
            app_settings_changed=settings_signal
        )

        window._connect_signals()

        self.assertEqual(
            len(navigation_signal.callbacks),
            1,
        )
        self.assertEqual(
            navigation_signal.callbacks[0].__self__,
            window,
        )
        self.assertEqual(
            navigation_signal.callbacks[0].__func__,
            main_window_module.MainWindow._change_page,
        )
        self.assertEqual(
            len(settings_signal.callbacks),
            1,
        )
        self.assertEqual(
            settings_signal.callbacks[0].__self__,
            window,
        )
        self.assertEqual(
            settings_signal.callbacks[0].__func__,
            (
                main_window_module.MainWindow
                ._apply_runtime_settings
            ),
        )

    def test_runtime_settings_apply_explicit_values(
        self,
    ):
        window = self.make_window()

        window._apply_runtime_settings(
            {
                "minimize_to_tray_enabled": 0,
                "notifications_enabled": 1,
                "alarm_sound_enabled": "enabled",
            }
        )

        self.assertFalse(
            window._minimize_to_tray_enabled
        )
        self.assertTrue(
            window._notifications_enabled
        )
        self.assertTrue(
            window._alarm_sound_enabled
        )

    def test_runtime_settings_use_defaults_for_missing_keys(
        self,
    ):
        window = self.make_window()

        window._apply_runtime_settings({})

        self.assertTrue(
            window._minimize_to_tray_enabled
        )
        self.assertTrue(
            window._notifications_enabled
        )
        self.assertFalse(
            window._alarm_sound_enabled
        )

    def test_change_page_ignores_invalid_indexes(
        self,
    ):
        window = self.make_window()
        window.pages = Mock()
        window.pages.count.return_value = 4

        window._change_page(-1)
        window._change_page(4)

        window.pages.currentIndex.assert_not_called()
        window.pages.setCurrentIndex.assert_not_called()

    def test_change_page_ignores_current_page(
        self,
    ):
        window = self.make_window()
        window.pages = Mock()
        window.pages.count.return_value = 4
        window.pages.currentIndex.return_value = 2

        window._change_page(2)

        window.pages.setCurrentIndex.assert_not_called()
        window.pages.currentWidget.assert_not_called()

    def test_change_page_starts_opacity_animation(
        self,
    ):
        window = self.make_window()
        page = Mock()
        window.pages = Mock()
        window.pages.count.return_value = 5
        window.pages.currentIndex.return_value = 0
        window.pages.currentWidget.return_value = page

        with (
            patch.object(
                main_window_module,
                "QGraphicsOpacityEffect",
                EffectStub,
            ),
            patch.object(
                main_window_module,
                "QPropertyAnimation",
                AnimationStub,
            ),
        ):
            window._change_page(3)

        window.pages.setCurrentIndex.assert_called_once_with(
            3
        )
        self.assertEqual(
            len(AnimationStub.instances),
            1,
        )

        animation = AnimationStub.instances[0]
        effect = animation.effect

        self.assertIs(effect.page, page)
        self.assertEqual(effect.opacity, 0.0)
        page.setGraphicsEffect.assert_called_once_with(
            effect
        )
        self.assertEqual(
            animation.property_name,
            b"opacity",
        )
        self.assertIs(animation.parent, window)
        self.assertEqual(animation.duration, 180)
        self.assertEqual(
            animation.start_value,
            0.0,
        )
        self.assertEqual(
            animation.end_value,
            1.0,
        )
        self.assertEqual(
            animation.easing_curve,
            main_window_module.QEasingCurve.OutCubic,
        )
        self.assertTrue(animation.started)
        self.assertIs(
            window._page_animation,
            animation,
        )

        animation.finished.emit()

        page.setGraphicsEffect.assert_called_with(
            None
        )

    def test_start_alarm_monitor_wires_and_starts(
        self,
    ):
        window = self.make_window()
        window.data_manager = sentinel.data_manager
        window.on_alarm_triggered = Mock()
        window.alarms_page = SimpleNamespace(
            load_alarms=Mock()
        )

        monitor = SimpleNamespace(
            alarm_triggered=SignalStub(),
            alarms_checked=SignalStub(),
            start=Mock(),
        )

        with patch.object(
            main_window_module,
            "AlarmMonitor",
            return_value=monitor,
        ) as monitor_class:
            window._start_alarm_monitor()

        monitor_class.assert_called_once_with(
            sentinel.data_manager,
            window,
        )
        self.assertIs(
            window.alarm_monitor,
            monitor,
        )
        self.assertEqual(
            monitor.alarm_triggered.callbacks,
            [
                window.on_alarm_triggered,
            ],
        )
        self.assertEqual(
            monitor.alarms_checked.callbacks,
            [
                window.alarms_page.load_alarms,
            ],
        )
        monitor.start.assert_called_once_with()

    def test_menu_item_size_is_stable(self):
        self.assertEqual(
            main_window_module.MainWindow._menu_item_size(),
            QSize(196, 48),
        )

    def test_show_from_tray_restores_minimized_window(
        self,
    ):
        window = self.make_window()
        window.isMinimized = Mock(
            return_value=True
        )
        window.showNormal = Mock()
        window.show = Mock()
        window.raise_ = Mock()
        window.activateWindow = Mock()

        window.show_from_tray()

        window.showNormal.assert_called_once_with()
        window.show.assert_not_called()
        window.raise_.assert_called_once_with()
        window.activateWindow.assert_called_once_with()

    def test_show_from_tray_shows_normal_window(
        self,
    ):
        window = self.make_window()
        window.isMinimized = Mock(
            return_value=False
        )
        window.showNormal = Mock()
        window.show = Mock()
        window.raise_ = Mock()
        window.activateWindow = Mock()

        window.show_from_tray()

        window.show.assert_called_once_with()
        window.showNormal.assert_not_called()
        window.raise_.assert_called_once_with()
        window.activateWindow.assert_called_once_with()

    def test_allow_application_close_sets_flag(
        self,
    ):
        window = self.make_window()
        window._allow_close = False

        window.allow_application_close()

        self.assertTrue(window._allow_close)

    def test_close_event_accepts_allowed_close(
        self,
    ):
        window = self.make_window()
        window._allow_close = True
        window._minimize_to_tray_enabled = True
        window.alarm_monitor = SimpleNamespace(
            stop=Mock()
        )
        window.hide = Mock()
        event = Mock()

        window.closeEvent(event)

        window.alarm_monitor.stop.assert_called_once_with()
        event.accept.assert_called_once_with()
        event.ignore.assert_not_called()
        window.hide.assert_not_called()

    def test_close_event_minimizes_to_available_tray(
        self,
    ):
        window = self.make_window()
        window._allow_close = False
        window._minimize_to_tray_enabled = True
        window.alarm_monitor = SimpleNamespace(
            stop=Mock()
        )
        window.system_tray_available = Mock(
            return_value=True
        )
        window.hide = Mock()
        event = Mock()

        window.closeEvent(event)

        event.ignore.assert_called_once_with()
        event.accept.assert_not_called()
        window.hide.assert_called_once_with()
        window.alarm_monitor.stop.assert_not_called()
        self.assertFalse(window._allow_close)

    def test_close_event_quits_without_tray_minimize(
        self,
    ):
        window = self.make_window()
        window._allow_close = False
        window._minimize_to_tray_enabled = False
        window.alarm_monitor = SimpleNamespace(
            stop=Mock()
        )
        window.system_tray_available = Mock(
            return_value=True
        )
        event = Mock()
        fake_app = SimpleNamespace(
            quit=Mock()
        )

        with patch.object(
            main_window_module.QApplication,
            "instance",
            return_value=fake_app,
        ):
            window.closeEvent(event)

        self.assertTrue(window._allow_close)
        window.alarm_monitor.stop.assert_called_once_with()
        event.accept.assert_called_once_with()
        event.ignore.assert_not_called()
        fake_app.quit.assert_called_once_with()

    def test_close_event_handles_missing_application(
        self,
    ):
        window = self.make_window()
        window._allow_close = False
        window._minimize_to_tray_enabled = False
        window.alarm_monitor = SimpleNamespace(
            stop=Mock()
        )
        event = Mock()

        with patch.object(
            main_window_module.QApplication,
            "instance",
            return_value=None,
        ):
            window.closeEvent(event)

        self.assertTrue(window._allow_close)
        window.alarm_monitor.stop.assert_called_once_with()
        event.accept.assert_called_once_with()

    def test_system_tray_available_delegates_to_qt(
        self,
    ):
        with patch(
            (
                "PySide6.QtWidgets."
                "QSystemTrayIcon."
                "isSystemTrayAvailable"
            ),
            return_value=True,
        ) as available:
            result = (
                main_window_module.MainWindow
                .system_tray_available()
            )

        self.assertTrue(result)
        available.assert_called_once_with()

    def test_alarm_trigger_sound_can_run_without_notification(
        self,
    ):
        window = self.make_window()
        window._alarm_sound_enabled = True
        window._notifications_enabled = False
        window.notification_manager = SimpleNamespace(
            show_alarm=Mock()
        )

        with patch.object(
            main_window_module.QApplication,
            "beep",
        ) as beep:
            window.on_alarm_triggered(
                {
                    "symbol": "BTC",
                    "current_price": 70000,
                    "target_price": 69000,
                    "condition": "above",
                }
            )

        beep.assert_called_once_with()
        window.notification_manager.show_alarm.assert_not_called()

    def test_alarm_trigger_shows_above_notification(
        self,
    ):
        window = self.make_window()
        window._alarm_sound_enabled = False
        window._notifications_enabled = True
        window.notification_manager = SimpleNamespace(
            show_alarm=Mock()
        )

        with patch.object(
            main_window_module.QApplication,
            "beep",
        ) as beep:
            window.on_alarm_triggered(
                {
                    "symbol": "BTC",
                    "current_price": 70123.456,
                    "target_price": 70000,
                    "condition": "above",
                    "note": "Kâr al",
                }
            )

        beep.assert_not_called()
        window.notification_manager.show_alarm.assert_called_once_with(
            title="BTC Fiyat Alarmı",
            message=(
                "BTC, belirlenen hedef fiyatın "
                "üzerine çıktı."
            ),
            current_price="$70,123.46",
            target_price="$70,000.00",
            note="Kâr al",
        )

    def test_alarm_trigger_shows_below_notification(
        self,
    ):
        window = self.make_window()
        window._alarm_sound_enabled = False
        window._notifications_enabled = True
        window.notification_manager = SimpleNamespace(
            show_alarm=Mock()
        )

        window.on_alarm_triggered(
            {
                "symbol": "DOGE",
                "current_price": 0.123456,
                "target_price": 0.15,
                "condition": "below",
            }
        )

        window.notification_manager.show_alarm.assert_called_once_with(
            title="DOGE Fiyat Alarmı",
            message=(
                "DOGE, belirlenen hedef fiyatın "
                "altına düştü."
            ),
            current_price="$0.1235",
            target_price="$0.1500",
            note="",
        )

    def test_format_alarm_price_uses_value_ranges(
        self,
    ):
        cases = (
            (
                1234.567,
                "$1,234.57",
            ),
            (
                0.123456,
                "$0.1235",
            ),
            (
                0.00987654321,
                "$0.00987654",
            ),
            (
                0.0,
                "$0.00000000",
            ),
        )

        for price, expected in cases:
            with self.subTest(price=price):
                self.assertEqual(
                    (
                        main_window_module
                        .MainWindow
                        .format_alarm_price(price)
                    ),
                    expected,
                )


if __name__ == "__main__":
    unittest.main()
