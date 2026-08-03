import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

import services.alarm_monitor as alarm_monitor_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class AlarmMonitorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    @staticmethod
    def make_data_manager():
        return SimpleNamespace(
            portfolio_updated=SignalStub(),
            get_price=Mock(),
        )

    def make_monitor(self):
        data_manager = self.make_data_manager()
        monitor = alarm_monitor_module.AlarmMonitor(
            data_manager
        )
        self.addCleanup(monitor.stop)
        return monitor, data_manager

    def test_constructor_configures_timer_and_signal(
        self,
    ):
        monitor, data_manager = self.make_monitor()

        self.assertIs(
            monitor.data_manager,
            data_manager,
        )
        self.assertFalse(monitor._checking)
        self.assertEqual(
            monitor.timer.interval(),
            monitor.CHECK_INTERVAL_MS,
        )
        self.assertEqual(
            monitor.timer.parent(),
            monitor,
        )
        self.assertEqual(
            len(
                data_manager
                .portfolio_updated
                .callbacks
            ),
            1,
        )

        callback = (
            data_manager
            .portfolio_updated
            .callbacks[0]
        )
        self.assertEqual(
            callback.__self__,
            monitor,
        )
        self.assertEqual(
            callback.__func__,
            alarm_monitor_module.AlarmMonitor.on_prices_updated,
        )

    def test_start_starts_timer_and_schedules_initial_check(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.timer = Mock()
        monitor.timer.isActive.return_value = False

        with patch.object(
            alarm_monitor_module.QTimer,
            "singleShot",
        ) as single_shot:
            monitor.start()

        monitor.timer.start.assert_called_once_with()
        single_shot.assert_called_once_with(
            1000,
            monitor.check_alarms,
        )

    def test_start_does_nothing_when_timer_is_active(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.timer = Mock()
        monitor.timer.isActive.return_value = True

        with patch.object(
            alarm_monitor_module.QTimer,
            "singleShot",
        ) as single_shot:
            monitor.start()

        monitor.timer.start.assert_not_called()
        single_shot.assert_not_called()

    def test_stop_stops_timer(self):
        monitor, _ = self.make_monitor()
        monitor.timer = Mock()

        monitor.stop()

        monitor.timer.stop.assert_called_once_with()

    def test_price_update_triggers_alarm_check(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.check_alarms = Mock()

        monitor.on_prices_updated(
            {
                "total_usdt": 1000.0,
            }
        )

        monitor.check_alarms.assert_called_once_with()

    def test_check_alarms_ignores_reentrant_call(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor._checking = True
        monitor.check_alarm = Mock()
        emissions = []
        monitor.alarms_checked.connect(
            lambda: emissions.append(True)
        )

        with patch.object(
            alarm_monitor_module.alarm_service,
            "get_enabled_alarms",
        ) as get_alarms:
            monitor.check_alarms()

        get_alarms.assert_not_called()
        monitor.check_alarm.assert_not_called()
        self.assertEqual(emissions, [])
        self.assertTrue(monitor._checking)

    def test_check_alarms_processes_all_and_emits_once(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.check_alarm = Mock()
        alarms = [
            {
                "id": 1,
            },
            {
                "id": 2,
            },
            {
                "id": 3,
            },
        ]
        emissions = []
        monitor.alarms_checked.connect(
            lambda: emissions.append(True)
        )

        with patch.object(
            alarm_monitor_module.alarm_service,
            "get_enabled_alarms",
            return_value=alarms,
        ) as get_alarms:
            monitor.check_alarms()

        get_alarms.assert_called_once_with()
        self.assertEqual(
            monitor.check_alarm.call_args_list,
            [
                call(alarms[0]),
                call(alarms[1]),
                call(alarms[2]),
            ],
        )
        self.assertEqual(emissions, [True])
        self.assertFalse(monitor._checking)

    def test_check_alarms_emits_for_empty_list(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.check_alarm = Mock()
        emissions = []
        monitor.alarms_checked.connect(
            lambda: emissions.append(True)
        )

        with patch.object(
            alarm_monitor_module.alarm_service,
            "get_enabled_alarms",
            return_value=[],
        ):
            monitor.check_alarms()

        monitor.check_alarm.assert_not_called()
        self.assertEqual(emissions, [True])
        self.assertFalse(monitor._checking)

    def test_check_alarms_resets_guard_after_service_error(
        self,
    ):
        monitor, _ = self.make_monitor()
        emissions = []
        monitor.alarms_checked.connect(
            lambda: emissions.append(True)
        )

        with (
            patch.object(
                alarm_monitor_module.alarm_service,
                "get_enabled_alarms",
                side_effect=RuntimeError(
                    "database failed"
                ),
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "database failed",
            ),
        ):
            monitor.check_alarms()

        self.assertFalse(monitor._checking)
        self.assertEqual(emissions, [])

    def test_check_alarms_resets_guard_after_alarm_error(
        self,
    ):
        monitor, _ = self.make_monitor()
        monitor.check_alarm = Mock(
            side_effect=ValueError(
                "invalid alarm"
            )
        )
        emissions = []
        monitor.alarms_checked.connect(
            lambda: emissions.append(True)
        )

        with (
            patch.object(
                alarm_monitor_module.alarm_service,
                "get_enabled_alarms",
                return_value=[
                    {
                        "id": 1,
                    }
                ],
            ),
            self.assertRaisesRegex(
                ValueError,
                "invalid alarm",
            ),
        ):
            monitor.check_alarms()

        self.assertFalse(monitor._checking)
        self.assertEqual(emissions, [])

    def test_check_alarm_ignores_missing_or_invalid_price(
        self,
    ):
        monitor, data_manager = self.make_monitor()
        alarm = {
            "id": 10,
            "symbol": "BTC",
        }

        for price in (
            None,
            0,
            -1,
        ):
            with self.subTest(price=price):
                data_manager.get_price.reset_mock()
                data_manager.get_price.return_value = price

                with (
                    patch.object(
                        alarm_monitor_module.alarm_service,
                        "is_alarm_triggered",
                    ) as is_triggered,
                    patch.object(
                        alarm_monitor_module.alarm_service,
                        "complete_alarm",
                    ) as complete_alarm,
                ):
                    monitor.check_alarm(alarm)

                data_manager.get_price.assert_called_once_with(
                    "BTC"
                )
                is_triggered.assert_not_called()
                complete_alarm.assert_not_called()

    def test_check_alarm_stops_when_condition_is_not_met(
        self,
    ):
        monitor, data_manager = self.make_monitor()
        data_manager.get_price.return_value = 65000.0
        alarm = {
            "id": 10,
            "symbol": "BTC",
            "condition": "above",
            "target_price": 70000.0,
        }

        with (
            patch.object(
                alarm_monitor_module.alarm_service,
                "is_alarm_triggered",
                return_value=False,
            ) as is_triggered,
            patch.object(
                alarm_monitor_module.alarm_service,
                "complete_alarm",
            ) as complete_alarm,
        ):
            monitor.check_alarm(alarm)

        is_triggered.assert_called_once_with(
            alarm,
            65000.0,
        )
        complete_alarm.assert_not_called()

    def test_check_alarm_stops_when_completion_fails(
        self,
    ):
        monitor, data_manager = self.make_monitor()
        data_manager.get_price.return_value = 71000.0
        alarm = {
            "id": 10,
            "symbol": "BTC",
            "condition": "above",
            "target_price": 70000.0,
        }
        emissions = []
        monitor.alarm_triggered.connect(
            emissions.append
        )

        with (
            patch.object(
                alarm_monitor_module.alarm_service,
                "is_alarm_triggered",
                return_value=True,
            ),
            patch.object(
                alarm_monitor_module.alarm_service,
                "complete_alarm",
                return_value=False,
            ) as complete_alarm,
        ):
            monitor.check_alarm(alarm)

        complete_alarm.assert_called_once_with(10)
        self.assertEqual(emissions, [])

    def test_check_alarm_completes_and_emits_copy(
        self,
    ):
        monitor, data_manager = self.make_monitor()
        data_manager.get_price.return_value = 71000.0
        alarm = {
            "id": 10,
            "symbol": "BTC",
            "condition": "above",
            "target_price": 70000.0,
            "is_active": True,
            "is_triggered": False,
            "note": "Kâr al",
        }
        original = dict(alarm)
        emissions = []
        monitor.alarm_triggered.connect(
            emissions.append
        )

        with (
            patch.object(
                alarm_monitor_module.alarm_service,
                "is_alarm_triggered",
                return_value=True,
            ) as is_triggered,
            patch.object(
                alarm_monitor_module.alarm_service,
                "complete_alarm",
                return_value=True,
            ) as complete_alarm,
        ):
            monitor.check_alarm(alarm)

        data_manager.get_price.assert_called_once_with(
            "BTC"
        )
        is_triggered.assert_called_once_with(
            alarm,
            71000.0,
        )
        complete_alarm.assert_called_once_with(10)

        self.assertEqual(alarm, original)
        self.assertEqual(len(emissions), 1)
        self.assertIsNot(emissions[0], alarm)
        self.assertEqual(
            emissions[0],
            {
                "id": 10,
                "symbol": "BTC",
                "condition": "above",
                "target_price": 70000.0,
                "is_active": False,
                "is_triggered": True,
                "note": "Kâr al",
                "current_price": 71000.0,
            },
        )


if __name__ == "__main__":
    unittest.main()
