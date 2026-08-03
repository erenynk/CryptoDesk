import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QWidget,
)

from ui.theme import Theme
from ui.widgets.card import Card


class CardTestCase(unittest.TestCase):
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

    def test_constructor_builds_default_card(
        self,
    ):
        card = self.track(Card())

        self.assertEqual(
            card.objectName(),
            "card",
        )
        self.assertTrue(
            card.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        self.assertTrue(card._hover)
        self.assertEqual(
            card._radius,
            Theme.RADIUS_LARGE,
        )
        self.assertFalse(
            card._shadow_enabled
        )
        self.assertEqual(
            card._palette,
            "default",
        )
        self.assertIsNone(
            card.graphicsEffect()
        )

        normal, hover, border = (
            Card.PALETTES["default"]
        )
        stylesheet = card.styleSheet()

        self.assertIn(normal, stylesheet)
        self.assertIn(hover, stylesheet)
        self.assertIn(border, stylesheet)
        self.assertIn(
            Theme.BORDER_HOVER,
            stylesheet,
        )
        self.assertIn(
            f"border-radius: {Theme.RADIUS_LARGE}px",
            stylesheet,
        )
        self.assertIn(
            "QFrame#card:hover",
            stylesheet,
        )

    def test_constructor_applies_custom_values_and_parent(
        self,
    ):
        parent = self.track(QWidget())
        card = self.track(
            Card(
                object_name="summaryCard",
                hover=False,
                radius=12,
                shadow=False,
                palette="blue",
                parent=parent,
            )
        )

        self.assertIs(card.parent(), parent)
        self.assertEqual(
            card.objectName(),
            "summaryCard",
        )
        self.assertFalse(card._hover)
        self.assertEqual(card._radius, 12)
        self.assertEqual(
            card._palette,
            "blue",
        )

        normal, _, border = (
            Card.PALETTES["blue"]
        )
        stylesheet = card.styleSheet()

        self.assertIn(
            "QFrame#summaryCard",
            stylesheet,
        )
        self.assertIn(normal, stylesheet)
        self.assertIn(border, stylesheet)
        self.assertIn(
            "border-radius: 12px",
            stylesheet,
        )
        self.assertNotIn(
            "QFrame#summaryCard:hover",
            stylesheet,
        )

    def test_constructor_falls_back_for_unknown_palette(
        self,
    ):
        card = self.track(
            Card(
                palette="unknown",
            )
        )

        self.assertEqual(
            card._palette,
            "default",
        )
        self.assertIn(
            Card.PALETTES["default"][0],
            card.styleSheet(),
        )

    def test_all_supported_palettes_apply_their_styles(
        self,
    ):
        card = self.track(Card())

        for palette_name, palette_values in (
            Card.PALETTES.items()
        ):
            with self.subTest(
                palette=palette_name
            ):
                card.set_palette(
                    palette_name
                )

                normal, hover, border = (
                    palette_values
                )
                stylesheet = (
                    card.styleSheet()
                )

                self.assertEqual(
                    card._palette,
                    palette_name,
                )
                self.assertIn(
                    normal,
                    stylesheet,
                )
                self.assertIn(
                    hover,
                    stylesheet,
                )
                self.assertIn(
                    border,
                    stylesheet,
                )

    def test_set_palette_rejects_unknown_value(
        self,
    ):
        card = self.track(
            Card(
                palette="teal",
            )
        )
        original_style = card.styleSheet()

        with self.assertRaisesRegex(
            ValueError,
            "Geçersiz kart paleti: invalid",
        ):
            card.set_palette("invalid")

        self.assertEqual(
            card._palette,
            "teal",
        )
        self.assertEqual(
            card.styleSheet(),
            original_style,
        )

    def test_hover_and_radius_setters_update_style(
        self,
    ):
        card = self.track(
            Card(
                object_name="editableCard",
                hover=True,
                radius=18,
            )
        )

        self.assertIn(
            "QFrame#editableCard:hover",
            card.styleSheet(),
        )

        card.set_hover_enabled(False)

        self.assertFalse(card._hover)
        self.assertNotIn(
            "QFrame#editableCard:hover",
            card.styleSheet(),
        )

        card.set_radius(9)

        self.assertEqual(
            card._radius,
            9,
        )
        self.assertIn(
            "border-radius: 9px",
            card.styleSheet(),
        )

        card.set_hover_enabled(True)

        self.assertTrue(card._hover)
        self.assertIn(
            "QFrame#editableCard:hover",
            card.styleSheet(),
        )

    def test_shadow_constructor_and_setter(
        self,
    ):
        card = self.track(
            Card(
                shadow=True,
            )
        )

        effect = card.graphicsEffect()

        self.assertTrue(
            card._shadow_enabled
        )
        self.assertIsInstance(
            effect,
            QGraphicsDropShadowEffect,
        )
        self.assertEqual(
            effect.blurRadius(),
            44.0,
        )
        self.assertEqual(
            effect.xOffset(),
            0.0,
        )
        self.assertEqual(
            effect.yOffset(),
            1.0,
        )
        self.assertEqual(
            effect.color().getRgb(),
            (0, 0, 0, 88),
        )

        card.set_shadow_enabled(False)

        self.assertFalse(
            card._shadow_enabled
        )
        self.assertIsNone(
            card.graphicsEffect()
        )

        card.set_shadow_enabled(True)

        self.assertTrue(
            card._shadow_enabled
        )
        self.assertIsInstance(
            card.graphicsEffect(),
            QGraphicsDropShadowEffect,
        )


if __name__ == "__main__":
    unittest.main()
