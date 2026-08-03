from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton

from ui.theme import Theme


class AppButton(QPushButton):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    DANGER = "danger"

    def __init__(
        self,
        text="",
        variant=PRIMARY,
        object_name="appButton",
        parent=None,
    ):
        super().__init__(text, parent)

        self._variant = variant

        self.setObjectName(object_name)
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(42)

        self._apply_style()

    def set_variant(self, variant):
        if variant not in (
            self.PRIMARY,
            self.SECONDARY,
            self.DANGER,
        ):
            raise ValueError(
                f"Geçersiz buton tipi: {variant}"
            )

        self._variant = variant
        self._apply_style()

    def _apply_style(self):
        if self._variant == self.SECONDARY:
            background = Theme.CARD_BACKGROUND_SECONDARY
            hover_background = Theme.CARD_BACKGROUND_HOVER
            pressed_background = "#1B2530"
            text_color = Theme.TEXT_PRIMARY
            border = Theme.BORDER
            hover_border = Theme.BORDER_HOVER

        elif self._variant == self.DANGER:
            background = "#2A1B20"
            hover_background = "#382128"
            pressed_background = Theme.ERROR
            text_color = Theme.ERROR
            border = "#57303A"
            hover_border = Theme.ERROR

        else:
            background = Theme.ACCENT
            hover_background = Theme.ACCENT_HOVER
            pressed_background = "#14B87E"
            text_color = "#06110D"
            border = Theme.ACCENT
            hover_border = Theme.ACCENT_HOVER

        self.setStyleSheet(
            f"""
            QPushButton#{self.objectName()} {{
                background-color: {background};
                color: {text_color};
                border: 1px solid {border};
                border-radius: {Theme.RADIUS_SMALL}px;
                padding: 0 16px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 12px;
                font-weight: 700;
            }}

            QPushButton#{self.objectName()}:hover {{
                background-color: {hover_background};
                border-color: {hover_border};
            }}

            QPushButton#{self.objectName()}:pressed {{
                background-color: {pressed_background};
                border-color: {pressed_background};
            }}

            QPushButton#{self.objectName()}:disabled {{
                background-color: {Theme.CARD_BACKGROUND_SECONDARY};
                color: {Theme.TEXT_MUTED};
                border-color: {Theme.BORDER_SOFT};
            }}
            """
        )