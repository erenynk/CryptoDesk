import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget

from ui.theme import Theme
from ui.widgets.button import AppButton


class AppButtonTestCase(unittest.TestCase):
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

    def test_constructor_builds_default_primary_button(
        self,
    ):
        button = self.track(AppButton())

        self.assertEqual(button.text(), "")
        self.assertEqual(
            button._variant,
            AppButton.PRIMARY,
        )
        self.assertEqual(
            button.objectName(),
            "appButton",
        )
        self.assertEqual(
            button.cursor().shape(),
            Qt.PointingHandCursor,
        )
        self.assertEqual(
            button.minimumHeight(),
            42,
        )

        stylesheet = button.styleSheet()

        self.assertIn(
            Theme.ACCENT,
            stylesheet,
        )
        self.assertIn(
            Theme.ACCENT_HOVER,
            stylesheet,
        )
        self.assertIn(
            "#14B87E",
            stylesheet,
        )
        self.assertIn(
            "#06110D",
            stylesheet,
        )
        self.assertIn(
            f"border-radius: {Theme.RADIUS_SMALL}px",
            stylesheet,
        )
        self.assertIn(
            Theme.FONT_FAMILY,
            stylesheet,
        )

    def test_constructor_applies_custom_values_and_parent(
        self,
    ):
        parent = self.track(QWidget())
        button = self.track(
            AppButton(
                text="Kaydet",
                variant=AppButton.SECONDARY,
                object_name="saveButton",
                parent=parent,
            )
        )

        self.assertIs(button.parent(), parent)
        self.assertEqual(
            button.text(),
            "Kaydet",
        )
        self.assertEqual(
            button._variant,
            AppButton.SECONDARY,
        )
        self.assertEqual(
            button.objectName(),
            "saveButton",
        )
        self.assertIn(
            "QPushButton#saveButton",
            button.styleSheet(),
        )

    def test_secondary_variant_uses_secondary_palette(
        self,
    ):
        button = self.track(
            AppButton(
                text="İptal",
                variant=AppButton.SECONDARY,
            )
        )

        stylesheet = button.styleSheet()

        self.assertIn(
            Theme.CARD_BACKGROUND_SECONDARY,
            stylesheet,
        )
        self.assertIn(
            Theme.CARD_BACKGROUND_HOVER,
            stylesheet,
        )
        self.assertIn(
            "#1B2530",
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_PRIMARY,
            stylesheet,
        )
        self.assertIn(
            Theme.BORDER,
            stylesheet,
        )
        self.assertIn(
            Theme.BORDER_HOVER,
            stylesheet,
        )

    def test_danger_variant_uses_danger_palette(
        self,
    ):
        button = self.track(
            AppButton(
                text="Sil",
                variant=AppButton.DANGER,
            )
        )

        stylesheet = button.styleSheet()

        self.assertIn("#2A1B20", stylesheet)
        self.assertIn("#382128", stylesheet)
        self.assertIn("#57303A", stylesheet)
        self.assertIn(
            Theme.ERROR,
            stylesheet,
        )

    def test_set_variant_updates_variant_and_style(
        self,
    ):
        button = self.track(
            AppButton(
                text="İşlem",
                variant=AppButton.PRIMARY,
            )
        )
        primary_stylesheet = button.styleSheet()

        button.set_variant(
            AppButton.SECONDARY
        )

        self.assertEqual(
            button._variant,
            AppButton.SECONDARY,
        )
        self.assertNotEqual(
            button.styleSheet(),
            primary_stylesheet,
        )
        self.assertIn(
            Theme.CARD_BACKGROUND_SECONDARY,
            button.styleSheet(),
        )

        button.set_variant(
            AppButton.DANGER
        )

        self.assertEqual(
            button._variant,
            AppButton.DANGER,
        )
        self.assertIn(
            Theme.ERROR,
            button.styleSheet(),
        )

        button.set_variant(
            AppButton.PRIMARY
        )

        self.assertEqual(
            button._variant,
            AppButton.PRIMARY,
        )
        self.assertIn(
            Theme.ACCENT,
            button.styleSheet(),
        )

    def test_set_variant_rejects_invalid_value(
        self,
    ):
        button = self.track(
            AppButton(
                text="Test",
                variant=AppButton.PRIMARY,
            )
        )
        original_stylesheet = button.styleSheet()

        with self.assertRaisesRegex(
            ValueError,
            "Geçersiz buton tipi: invalid",
        ):
            button.set_variant("invalid")

        self.assertEqual(
            button._variant,
            AppButton.PRIMARY,
        )
        self.assertEqual(
            button.styleSheet(),
            original_stylesheet,
        )

    def test_disabled_style_is_always_present(
        self,
    ):
        button = self.track(
            AppButton(
                text="Devre Dışı",
                variant=AppButton.PRIMARY,
            )
        )

        stylesheet = button.styleSheet()

        self.assertIn(
            ":disabled",
            stylesheet,
        )
        self.assertIn(
            Theme.CARD_BACKGROUND_SECONDARY,
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_MUTED,
            stylesheet,
        )
        self.assertIn(
            Theme.BORDER_SOFT,
            stylesheet,
        )


if __name__ == "__main__":
    unittest.main()
