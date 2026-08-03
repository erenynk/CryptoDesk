import re
import unittest

from ui.theme import (
    Theme,
    card_style,
    checkbox_style,
    label_style,
    page_style,
    page_title_style,
    primary_button_style,
    scroll_bar_style,
    secondary_button_style,
    table_style,
)


class ThemeTestCase(unittest.TestCase):
    def test_color_constants_are_valid_hex_values(self):
        color_names = (
            "BACKGROUND",
            "CONTENT_BACKGROUND",
            "SIDEBAR_BACKGROUND",
            "CARD_BACKGROUND",
            "CARD_BACKGROUND_HOVER",
            "CARD_BACKGROUND_SECONDARY",
            "BORDER",
            "BORDER_HOVER",
            "BORDER_SOFT",
            "TEXT_PRIMARY",
            "TEXT_SECONDARY",
            "TEXT_MUTED",
            "ACCENT",
            "ACCENT_HOVER",
            "ACCENT_SOFT",
            "ACCENT_BORDER",
            "ERROR",
            "WARNING",
        )

        for name in color_names:
            with self.subTest(name=name):
                value = getattr(Theme, name)
                self.assertRegex(
                    value,
                    r"^#[0-9A-Fa-f]{6}$",
                )

    def test_dimension_constants_are_positive_integers(self):
        dimension_names = (
            "RADIUS_SMALL",
            "RADIUS_MEDIUM",
            "RADIUS_LARGE",
            "RADIUS_XLARGE",
            "PAGE_MARGIN_HORIZONTAL",
            "PAGE_MARGIN_VERTICAL",
            "PAGE_SPACING",
        )

        for name in dimension_names:
            with self.subTest(name=name):
                value = getattr(Theme, name)
                self.assertIsInstance(value, int)
                self.assertGreater(value, 0)

    def test_font_family_is_defined(self):
        self.assertIsInstance(
            Theme.FONT_FAMILY,
            str,
        )
        self.assertTrue(
            Theme.FONT_FAMILY.strip()
        )

    def test_page_style_uses_requested_object_name(self):
        style = page_style("settingsPage")

        self.assertIn(
            "QWidget#settingsPage",
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CONTENT_BACKGROUND};"
            ),
            style,
        )

    def test_label_style_uses_shared_text_theme(self):
        style = label_style()

        self.assertIn("QLabel {", style)
        self.assertIn(
            "background: transparent;",
            style,
        )
        self.assertIn("border: none;", style)
        self.assertIn(
            f"color: {Theme.TEXT_PRIMARY};",
            style,
        )
        self.assertIn(
            (
                "font-family: "
                f'"{Theme.FONT_FAMILY}";'
            ),
            style,
        )

    def test_page_title_style_contains_title_and_subtitle(self):
        style = page_title_style()

        self.assertIn(
            "QLabel#pageTitle",
            style,
        )
        self.assertIn(
            "font-size: 27px;",
            style,
        )
        self.assertIn(
            "font-weight: 700;",
            style,
        )
        self.assertIn(
            "QLabel#pageSubtitle",
            style,
        )
        self.assertIn(
            f"color: {Theme.TEXT_SECONDARY};",
            style,
        )
        self.assertIn(
            "font-size: 13px;",
            style,
        )

    def test_card_style_uses_default_radius_without_hover(self):
        style = card_style("portfolioCard")

        self.assertIn(
            "QFrame#portfolioCard",
            style,
        )
        self.assertIn(
            "QWidget#portfolioCard",
            style,
        )
        self.assertIn(
            f"border-radius: {Theme.RADIUS_LARGE}px;",
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CARD_BACKGROUND};"
            ),
            style,
        )
        self.assertNotIn(":hover", style)

    def test_card_style_supports_custom_radius_and_hover(self):
        style = card_style(
            "summaryCard",
            radius=21,
            hover=True,
        )

        self.assertIn(
            "border-radius: 21px;",
            style,
        )
        self.assertIn(
            "QFrame#summaryCard:hover",
            style,
        )
        self.assertIn(
            "QWidget#summaryCard:hover",
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CARD_BACKGROUND_HOVER};"
            ),
            style,
        )
        self.assertIn(
            (
                "border-color: "
                f"{Theme.BORDER_HOVER};"
            ),
            style,
        )

    def test_primary_button_style_uses_default_selector(self):
        style = primary_button_style()

        self.assertIn(
            "QPushButton {",
            style,
        )
        self.assertIn(
            f"background-color: {Theme.ACCENT};",
            style,
        )
        self.assertIn(
            f"QPushButton:hover",
            style,
        )
        self.assertIn(
            f"QPushButton:pressed",
            style,
        )
        self.assertIn(
            f"QPushButton:disabled",
            style,
        )
        self.assertIn(
            f"color: {Theme.TEXT_MUTED};",
            style,
        )

    def test_primary_button_style_supports_object_name(self):
        style = primary_button_style(
            "saveButton"
        )

        self.assertIn(
            "QPushButton#saveButton {",
            style,
        )
        self.assertIn(
            "QPushButton#saveButton:hover",
            style,
        )
        self.assertIn(
            "QPushButton#saveButton:pressed",
            style,
        )
        self.assertIn(
            "QPushButton#saveButton:disabled",
            style,
        )

    def test_secondary_button_style_has_all_states(self):
        style = secondary_button_style()

        self.assertIn(
            "QPushButton {",
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CARD_BACKGROUND_SECONDARY};"
            ),
            style,
        )
        self.assertIn(
            "QPushButton:hover",
            style,
        )
        self.assertIn(
            "QPushButton:pressed",
            style,
        )
        self.assertIn(
            "QPushButton:disabled",
            style,
        )
        self.assertIn(
            f"border: 1px solid {Theme.BORDER};",
            style,
        )

    def test_secondary_button_style_supports_object_name(self):
        style = secondary_button_style(
            "cancelButton"
        )

        self.assertIn(
            "QPushButton#cancelButton {",
            style,
        )
        self.assertIn(
            "QPushButton#cancelButton:hover",
            style,
        )
        self.assertIn(
            "QPushButton#cancelButton:disabled",
            style,
        )

    def test_checkbox_style_uses_default_selector_and_states(self):
        style = checkbox_style()

        self.assertIn(
            "QCheckBox {",
            style,
        )
        self.assertIn(
            "QCheckBox::indicator",
            style,
        )
        self.assertIn(
            "QCheckBox::indicator:hover",
            style,
        )
        self.assertIn(
            "QCheckBox::indicator:checked",
            style,
        )
        self.assertIn(
            "QCheckBox:disabled",
            style,
        )
        self.assertIn(
            f"background-color: {Theme.ACCENT};",
            style,
        )

    def test_checkbox_style_supports_object_name(self):
        style = checkbox_style(
            "rememberCheckBox"
        )

        self.assertIn(
            "QCheckBox#rememberCheckBox {",
            style,
        )
        self.assertIn(
            (
                "QCheckBox#rememberCheckBox"
                "::indicator:checked"
            ),
            style,
        )
        self.assertIn(
            (
                "QCheckBox#rememberCheckBox"
                ":disabled"
            ),
            style,
        )

    def test_scroll_bar_style_contains_vertical_rules(self):
        style = scroll_bar_style()

        self.assertIn(
            "QScrollBar:vertical",
            style,
        )
        self.assertIn(
            "QScrollBar::handle:vertical",
            style,
        )
        self.assertIn(
            "QScrollBar::handle:vertical:hover",
            style,
        )
        self.assertIn(
            "min-height: 36px;",
            style,
        )
        self.assertIn(
            "height: 0;",
            style,
        )

    def test_scroll_bar_style_contains_horizontal_rules(self):
        style = scroll_bar_style()

        self.assertIn(
            "QScrollBar:horizontal",
            style,
        )
        self.assertIn(
            "QScrollBar::handle:horizontal",
            style,
        )
        self.assertIn(
            "QScrollBar::handle:horizontal:hover",
            style,
        )
        self.assertIn(
            "min-width: 36px;",
            style,
        )
        self.assertIn(
            "width: 0;",
            style,
        )

    def test_table_style_uses_default_table_name(self):
        style = table_style()

        self.assertIn(
            "QTableWidget#portfolioTable",
            style,
        )
        self.assertIn(
            "QTableWidget#portfolioTable::item",
            style,
        )
        self.assertIn(
            (
                "QTableWidget#portfolioTable"
                "::item:hover"
            ),
            style,
        )
        self.assertIn(
            (
                "QTableWidget#portfolioTable"
                "::item:selected"
            ),
            style,
        )
        self.assertIn(
            "QHeaderView::section:horizontal",
            style,
        )
        self.assertIn(
            "QHeaderView::section:vertical",
            style,
        )
        self.assertIn(
            "QTableCornerButton::section",
            style,
        )
        self.assertIn(
            "QScrollBar:vertical",
            style,
        )
        self.assertIn(
            "QScrollBar:horizontal",
            style,
        )

    def test_table_style_supports_custom_table_name(self):
        style = table_style(
            "alarmsTable"
        )

        self.assertIn(
            "QTableWidget#alarmsTable",
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CARD_BACKGROUND};"
            ),
            style,
        )
        self.assertIn(
            (
                "background-color: "
                f"{Theme.CARD_BACKGROUND_SECONDARY};"
            ),
            style,
        )
        self.assertIn(
            f"border: 1px solid {Theme.BORDER};",
            style,
        )

    def test_all_style_helpers_return_balanced_qss(self):
        styles = (
            page_style("page"),
            label_style(),
            page_title_style(),
            card_style("card", hover=True),
            primary_button_style(),
            secondary_button_style(),
            checkbox_style(),
            scroll_bar_style(),
            table_style(),
        )

        for style in styles:
            with self.subTest(
                preview=style.strip()[:30]
            ):
                self.assertIsInstance(style, str)
                self.assertTrue(style.strip())
                self.assertEqual(
                    style.count("{"),
                    style.count("}"),
                )
                self.assertNotIn("None", style)


if __name__ == "__main__":
    unittest.main()
