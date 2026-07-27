import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QEnterEvent
from PySide6.QtWidgets import QApplication, QLabel

import ui.notification_popup as notification_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def disconnect(self, callback):
        if callback not in self.callbacks:
            raise RuntimeError("not connected")

        self.callbacks.remove(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class AnimationStub:
    def __init__(self):
        self.finished = SignalStub()
        self.stop_count = 0
        self.start_count = 0
        self.start_value = None
        self.end_value = None

    def stop(self):
        self.stop_count += 1

    def start(self):
        self.start_count += 1

    def setStartValue(self, value):
        self.start_value = value

    def setEndValue(self, value):
        self.end_value = value


class TimerStub:
    def __init__(self):
        self.start_count = 0
        self.stop_count = 0

    def start(self):
        self.start_count += 1

    def stop(self):
        self.stop_count += 1


class ScreenStub:
    def __init__(self, geometry):
        self.geometry = geometry

    def availableGeometry(self):
        return self.geometry


class PopupStub:
    WIDTH = 390
    HEIGHT_WITHOUT_NOTE = 190
    HEIGHT_WITH_NOTE = 225

    instances = []

    def __init__(
        self,
        title,
        message,
        current_price,
        target_price,
        note="",
    ):
        self.title = title
        self.message = message
        self.current_price = current_price
        self.target_price = target_price
        self.note = note
        self._manager = None
        self.show_positions = []
        self.move_positions = []
        self.close_count = 0
        self._height = (
            self.HEIGHT_WITH_NOTE
            if note.strip()
            else self.HEIGHT_WITHOUT_NOTE
        )
        self.__class__.instances.append(self)

    def height(self):
        return self._height

    def show_at(self, position):
        self.show_positions.append(position)

    def move_animated(self, position):
        self.move_positions.append(position)

    def close_animated(self):
        self.close_count += 1


class NotificationPopupTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    def setUp(self):
        self.popups = []
        PopupStub.instances.clear()

    def tearDown(self):
        for popup in self.popups:
            try:
                popup.timer.stop()
                popup.slide_animation.stop()
                popup.opacity_animation.stop()
                popup.close()
                popup.deleteLater()
            except RuntimeError:
                pass

    def make_popup(self, note=""):
        popup = notification_module.NotificationPopup(
            title="BTC Fiyat Alarmı",
            message="BTC hedef fiyatı geçti.",
            current_price="$70,000.00",
            target_price="$69,000.00",
            note=note,
        )
        self.popups.append(popup)
        return popup

    def test_popup_without_note_uses_compact_height(
        self,
    ):
        popup = self.make_popup("   ")

        self.assertEqual(popup.note, "")
        self.assertEqual(
            popup.popup_height,
            popup.HEIGHT_WITHOUT_NOTE,
        )
        self.assertEqual(
            popup.size().width(),
            popup.WIDTH,
        )
        self.assertEqual(
            popup.size().height(),
            popup.HEIGHT_WITHOUT_NOTE,
        )
        self.assertEqual(
            popup._remaining_ms,
            popup.DISPLAY_TIME_MS,
        )
        self.assertFalse(popup._closing)
        self.assertIsNone(popup._manager)

    def test_popup_with_note_trims_text_and_uses_tall_height(
        self,
    ):
        popup = self.make_popup("  Kâr al  ")

        self.assertEqual(popup.note, "Kâr al")
        self.assertEqual(
            popup.popup_height,
            popup.HEIGHT_WITH_NOTE,
        )
        self.assertEqual(
            popup.height(),
            popup.HEIGHT_WITH_NOTE,
        )

    def test_popup_builds_expected_visible_texts(
        self,
    ):
        popup = self.make_popup("Kâr al")

        texts = [
            label.text()
            for label in popup.findChildren(QLabel)
        ]

        for expected in (
            "🔔",
            "BTC Fiyat Alarmı",
            "BTC hedef fiyatı geçti.",
            "ANLIK FİYAT",
            "$70,000.00",
            "HEDEF FİYAT",
            "$69,000.00",
            "Not:",
            "Kâr al",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, texts)

    def test_price_section_contains_label_and_value(
        self,
    ):
        layout = (
            notification_module.NotificationPopup
            ._create_price_section(
                label_text="ANLIK FİYAT",
                price_text="$1.2345",
                value_color="#00C087",
            )
        )

        label = layout.itemAt(0).widget()
        value = layout.itemAt(1).widget()

        self.assertEqual(
            label.text(),
            "ANLIK FİYAT",
        )
        self.assertEqual(
            value.text(),
            "$1.2345",
        )
        self.assertIn(
            "#00C087",
            value.styleSheet(),
        )

        label.deleteLater()
        value.deleteLater()

    def test_show_at_configures_and_starts_animations(
        self,
    ):
        popup = self.make_popup()
        popup.slide_animation = AnimationStub()
        popup.opacity_animation = AnimationStub()
        popup.timer = TimerStub()
        popup.move = Mock()
        popup.setWindowOpacity = Mock()
        popup.show = Mock()
        popup.raise_ = Mock()
        final_position = QPoint(100, 200)

        popup.show_at(final_position)

        start_position = QPoint(145, 200)

        self.assertEqual(
            popup._final_position,
            final_position,
        )
        popup.move.assert_called_once_with(
            start_position
        )
        popup.setWindowOpacity.assert_called_once_with(
            0.0
        )
        popup.show.assert_called_once_with()
        popup.raise_.assert_called_once_with()
        self.assertEqual(
            popup.slide_animation.start_value,
            start_position,
        )
        self.assertEqual(
            popup.slide_animation.end_value,
            final_position,
        )
        self.assertEqual(
            popup.opacity_animation.start_value,
            0.0,
        )
        self.assertEqual(
            popup.opacity_animation.end_value,
            1.0,
        )
        self.assertEqual(
            popup.slide_animation.start_count,
            1,
        )
        self.assertEqual(
            popup.opacity_animation.start_count,
            1,
        )
        self.assertEqual(popup.timer.start_count, 1)

    def test_move_animated_uses_current_position(
        self,
    ):
        popup = self.make_popup()
        popup.slide_animation = AnimationStub()
        popup.pos = Mock(
            return_value=QPoint(10, 20)
        )
        final_position = QPoint(30, 40)

        popup.move_animated(final_position)

        self.assertEqual(
            popup._final_position,
            final_position,
        )
        self.assertEqual(
            popup.slide_animation.start_value,
            QPoint(10, 20),
        )
        self.assertEqual(
            popup.slide_animation.end_value,
            final_position,
        )
        self.assertEqual(
            popup.slide_animation.stop_count,
            1,
        )
        self.assertEqual(
            popup.slide_animation.start_count,
            1,
        )

    def test_close_animated_stops_timer_and_starts_exit(
        self,
    ):
        popup = self.make_popup()
        popup.slide_animation = AnimationStub()
        popup.opacity_animation = AnimationStub()
        popup.timer = TimerStub()
        popup.x = Mock(return_value=100)
        popup.y = Mock(return_value=200)
        popup.pos = Mock(
            return_value=QPoint(100, 200)
        )
        popup.windowOpacity = Mock(
            return_value=0.75
        )

        popup.close_animated()

        self.assertTrue(popup._closing)
        self.assertEqual(popup.timer.stop_count, 1)
        self.assertEqual(
            popup.slide_animation.start_value,
            QPoint(100, 200),
        )
        self.assertEqual(
            popup.slide_animation.end_value,
            QPoint(145, 200),
        )
        self.assertEqual(
            popup.opacity_animation.start_value,
            0.75,
        )
        self.assertEqual(
            popup.opacity_animation.end_value,
            0.0,
        )
        self.assertEqual(
            popup.opacity_animation.finished.callbacks,
            [popup._finish_close],
        )
        self.assertEqual(
            popup.slide_animation.start_count,
            1,
        )
        self.assertEqual(
            popup.opacity_animation.start_count,
            1,
        )

    def test_close_animated_is_idempotent(self):
        popup = self.make_popup()
        popup._closing = True
        popup.slide_animation = AnimationStub()
        popup.opacity_animation = AnimationStub()
        popup.timer = TimerStub()

        popup.close_animated()

        self.assertEqual(popup.timer.stop_count, 0)
        self.assertEqual(
            popup.slide_animation.start_count,
            0,
        )
        self.assertEqual(
            popup.opacity_animation.start_count,
            0,
        )

    def test_finish_close_notifies_manager_and_deletes(
        self,
    ):
        popup = self.make_popup()
        popup.opacity_animation = AnimationStub()
        popup.opacity_animation.finished.connect(
            popup._finish_close
        )
        popup._manager = SimpleNamespace(
            remove_popup=Mock()
        )
        popup.close = Mock()
        popup.deleteLater = Mock()

        popup._finish_close()

        self.assertEqual(
            popup.opacity_animation.finished.callbacks,
            [],
        )
        popup._manager.remove_popup.assert_called_once_with(
            popup
        )
        popup.close.assert_called_once_with()
        popup.deleteLater.assert_called_once_with()

    def test_finish_close_tolerates_missing_signal_connection(
        self,
    ):
        popup = self.make_popup()
        popup.opacity_animation = AnimationStub()
        popup._manager = None
        popup.close = Mock()
        popup.deleteLater = Mock()

        popup._finish_close()

        popup.close.assert_called_once_with()
        popup.deleteLater.assert_called_once_with()

    def test_update_timer_pauses_while_mouse_is_over_popup(
        self,
    ):
        popup = self.make_popup()
        popup.underMouse = Mock(return_value=True)
        popup.progress_bar = Mock()
        initial_remaining = popup._remaining_ms

        popup._update_timer()

        self.assertEqual(
            popup._remaining_ms,
            initial_remaining,
        )
        popup.progress_bar.setFixedWidth.assert_not_called()

    def test_update_timer_decrements_and_resizes_progress(
        self,
    ):
        popup = self.make_popup()
        popup.underMouse = Mock(return_value=False)
        popup.container = SimpleNamespace(
            width=Mock(return_value=200)
        )
        popup.progress_bar = Mock()
        popup.close_animated = Mock()

        popup._update_timer()

        self.assertEqual(
            popup._remaining_ms,
            popup.DISPLAY_TIME_MS
            - popup._elapsed_step_ms,
        )
        popup.progress_bar.setFixedWidth.assert_called_once_with(
            162
        )
        popup.close_animated.assert_not_called()

    def test_update_timer_closes_when_time_expires(
        self,
    ):
        popup = self.make_popup()
        popup._remaining_ms = 50
        popup.underMouse = Mock(return_value=False)
        popup.container = SimpleNamespace(
            width=Mock(return_value=10)
        )
        popup.progress_bar = Mock()
        popup.close_animated = Mock()

        popup._update_timer()

        self.assertEqual(popup._remaining_ms, -50)
        popup.progress_bar.setFixedWidth.assert_called_once_with(
            0
        )
        popup.close_animated.assert_called_once_with()

    def test_manager_starts_empty(self):
        manager = (
            notification_module.NotificationManager()
        )

        self.assertEqual(manager.popups, [])

    def test_manager_show_alarm_adds_and_shows_popup(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )

        with (
            patch.object(
                notification_module,
                "NotificationPopup",
                PopupStub,
            ),
            patch.object(
                manager,
                "_calculate_positions",
                return_value=[
                    QPoint(500, 600),
                ],
            ),
        ):
            manager.show_alarm(
                title="BTC",
                message="Mesaj",
                current_price="$2",
                target_price="$1",
                note="Not",
            )

        self.assertEqual(len(manager.popups), 1)
        popup = manager.popups[0]
        self.assertIs(popup._manager, manager)
        self.assertEqual(
            popup.show_positions,
            [
                QPoint(500, 600),
            ],
        )
        self.assertEqual(popup.move_positions, [])

    def test_manager_repositions_existing_popups(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )
        existing = PopupStub(
            "OLD",
            "old",
            "$1",
            "$1",
        )
        existing._manager = manager
        manager.popups.append(existing)

        with (
            patch.object(
                notification_module,
                "NotificationPopup",
                PopupStub,
            ),
            patch.object(
                manager,
                "_calculate_positions",
                return_value=[
                    QPoint(10, 20),
                    QPoint(30, 40),
                ],
            ),
        ):
            manager.show_alarm(
                title="NEW",
                message="new",
                current_price="$2",
                target_price="$2",
            )

        new_popup = manager.popups[1]
        self.assertEqual(
            existing.move_positions,
            [
                QPoint(10, 20),
            ],
        )
        self.assertEqual(
            new_popup.show_positions,
            [
                QPoint(30, 40),
            ],
        )

    def test_manager_closes_oldest_over_visible_limit(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )

        for index in range(
            manager.MAX_VISIBLE_POPUPS
        ):
            manager.popups.append(
                PopupStub(
                    str(index),
                    "message",
                    "$1",
                    "$1",
                )
            )

        oldest = manager.popups[0]

        with (
            patch.object(
                notification_module,
                "NotificationPopup",
                PopupStub,
            ),
            patch.object(
                manager,
                "_calculate_positions",
                return_value=[
                    QPoint(index, index)
                    for index in range(5)
                ],
            ),
        ):
            manager.show_alarm(
                title="NEW",
                message="new",
                current_price="$2",
                target_price="$2",
            )

        self.assertEqual(len(manager.popups), 5)
        self.assertEqual(oldest.close_count, 1)

    def test_manager_remove_popup_reflows_remaining(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )
        first = PopupStub(
            "1",
            "m",
            "$1",
            "$1",
        )
        second = PopupStub(
            "2",
            "m",
            "$1",
            "$1",
        )
        manager.popups = [
            first,
            second,
        ]

        with patch.object(
            manager,
            "_calculate_positions",
            return_value=[
                QPoint(100, 200),
            ],
        ):
            manager.remove_popup(first)

        self.assertEqual(
            manager.popups,
            [second],
        )
        self.assertEqual(
            second.move_positions,
            [
                QPoint(100, 200),
            ],
        )

    def test_calculate_positions_uses_cursor_screen(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )
        manager.popups = [
            PopupStub(
                "1",
                "m",
                "$1",
                "$1",
            ),
            PopupStub(
                "2",
                "m",
                "$1",
                "$1",
                note="note",
            ),
        ]
        screen = ScreenStub(
            QRect(100, 50, 1000, 800)
        )

        with (
            patch.object(
                notification_module.QApplication,
                "screenAt",
                return_value=screen,
            ) as screen_at,
            patch.object(
                notification_module.QApplication,
                "primaryScreen",
            ) as primary_screen,
        ):
            positions = (
                manager._calculate_positions()
            )

        self.assertEqual(
            positions,
            [
                QPoint(692, 642),
                QPoint(692, 409),
            ],
        )
        screen_at.assert_called_once()
        primary_screen.assert_not_called()

    def test_calculate_positions_falls_back_to_primary_screen(
        self,
    ):
        manager = (
            notification_module.NotificationManager()
        )
        manager.popups = [
            PopupStub(
                "1",
                "m",
                "$1",
                "$1",
            )
        ]
        screen = ScreenStub(
            QRect(0, 0, 800, 600)
        )

        with (
            patch.object(
                notification_module.QApplication,
                "screenAt",
                return_value=None,
            ),
            patch.object(
                notification_module.QApplication,
                "primaryScreen",
                return_value=screen,
            ) as primary_screen,
        ):
            positions = (
                manager._calculate_positions()
            )

        self.assertEqual(
            positions,
            [
                QPoint(392, 392),
            ],
        )
        primary_screen.assert_called_once_with()



    def test_enter_event_sets_arrow_cursor(self):
        popup = self.make_popup()
        event = QEnterEvent(
            QPointF(1.0, 1.0),
            QPointF(1.0, 1.0),
            QPointF(1.0, 1.0),
        )

        popup.enterEvent(event)

        self.assertEqual(
            popup.cursor().shape(),
            Qt.ArrowCursor,
        )



if __name__ == "__main__":
    unittest.main()
