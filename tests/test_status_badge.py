import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QSizePolicy,
    QWidget,
)

from ui.theme import Theme
from ui.widgets.status_badge import StatusBadge


class StatusBadgeTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    def setUp(self):
        self.widgets = []

    def tearDown(self):
        for widget in reversed(self.widgets):
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass

    def track(self, widget):
        self.widgets.append(widget)
        return widget

    def test_constructor_builds_default_neutral_badge(
        self,
    ):
        badge = self.track(StatusBadge())

        self.assertEqual(
            badge.objectName(),
            "statusBadge",
        )
        self.assertEqual(
            badge._status,
            StatusBadge.NEUTRAL,
        )
        self.assertEqual(
            badge.text(),
            "Bekleniyor",
        )
        self.assertEqual(
            badge.dot.objectName(),
            "statusBadgeDot",
        )
        self.assertEqual(
            badge.label.objectName(),
            "statusBadgeText",
        )
        self.assertEqual(
            badge.dot.width(),
            8,
        )
        self.assertEqual(
            badge.dot.height(),
            8,
        )
        self.assertEqual(
            badge.dot.alignment(),
            Qt.AlignCenter,
        )
        self.assertEqual(
            badge.sizePolicy().horizontalPolicy(),
            QSizePolicy.Fixed,
        )
        self.assertEqual(
            badge.sizePolicy().verticalPolicy(),
            QSizePolicy.Fixed,
        )
        self.assertEqual(
            badge._get_status_color(),
            Theme.TEXT_MUTED,
        )
        self.assertIn(
            Theme.TEXT_MUTED,
            badge.styleSheet(),
        )

    def test_custom_parent_name_text_and_status_are_applied(
        self,
    ):
        parent = self.track(QWidget())
        badge = self.track(
            StatusBadge(
                text="Hazır",
                status=StatusBadge.SUCCESS,
                object_name="portfolioStatusBadge",
                parent=parent,
            )
        )

        self.assertIs(badge.parent(), parent)
        self.assertEqual(
            badge.objectName(),
            "portfolioStatusBadge",
        )
        self.assertEqual(
            badge.text(),
            "Hazır",
        )
        self.assertEqual(
            badge._status,
            StatusBadge.SUCCESS,
        )
        self.assertIn(
            "QFrame#portfolioStatusBadge",
            badge.styleSheet(),
        )
        self.assertIn(
            Theme.ACCENT,
            badge.styleSheet(),
        )

    def test_status_colors_cover_all_supported_states(
        self,
    ):
        badge = self.track(StatusBadge())

        cases = (
            (
                "Başarılı",
                StatusBadge.SUCCESS,
                Theme.ACCENT,
            ),
            (
                "Uyarı",
                StatusBadge.WARNING,
                Theme.WARNING,
            ),
            (
                "Hata",
                StatusBadge.ERROR,
                Theme.ERROR,
            ),
            (
                "Bekleniyor",
                StatusBadge.NEUTRAL,
                Theme.TEXT_MUTED,
            ),
            (
                "Bilinmeyen",
                "unsupported",
                Theme.TEXT_MUTED,
            ),
        )

        for text, status, expected_color in cases:
            with self.subTest(status=status):
                badge.set_status(
                    text,
                    status,
                )

                self.assertEqual(
                    badge._status,
                    status,
                )
                self.assertEqual(
                    badge.text(),
                    text,
                )
                self.assertEqual(
                    badge._get_status_color(),
                    expected_color,
                )
                self.assertIn(
                    expected_color,
                    badge.styleSheet(),
                )

    def test_set_text_and_text_accessor(self):
        badge = self.track(
            StatusBadge(
                text="İlk Metin",
            )
        )

        badge.set_text("Yeni Metin")

        self.assertEqual(
            badge.text(),
            "Yeni Metin",
        )
        self.assertEqual(
            badge.label.text(),
            "Yeni Metin",
        )


if __name__ == "__main__":
    unittest.main()
