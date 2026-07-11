from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

from ui.theme import Theme


class Card(QFrame):
    PALETTES = {
        "default": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(25, 38, 52, 250),"
            "stop:1 rgba(11, 18, 27, 250)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(24, 35, 48, 252),"
            "stop:1 rgba(16, 25, 36, 252)"
            ")",
            Theme.BORDER,
        ),
        "blue": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(31, 55, 91, 250),"
            "stop:1 rgba(12, 23, 37, 250)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(29, 49, 81, 252),"
            "stop:1 rgba(17, 31, 49, 252)"
            ")",
            "#2D4E70",
        ),
        "blue_dark": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(24, 44, 73, 252),"
            "stop:1 rgba(8, 17, 28, 252)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(23, 41, 68, 252),"
            "stop:1 rgba(13, 26, 41, 252)"
            ")",
            "#263F5D",
        ),
        "teal": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(19, 63, 68, 250),"
            "stop:1 rgba(10, 23, 32, 250)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(18, 57, 63, 252),"
            "stop:1 rgba(14, 34, 43, 252)"
            ")",
            "#285B61",
        ),
        "violet": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(57, 43, 94, 250),"
            "stop:1 rgba(15, 21, 34, 250)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(50, 38, 85, 252),"
            "stop:1 rgba(29, 28, 54, 252)"
            ")",
            "#504575",
        ),
        "indigo": (
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(42, 58, 96, 250),"
            "stop:1 rgba(13, 20, 32, 250)"
            ")",
            "qlineargradient("
            "x1:0, y1:0, x2:1, y2:1,"
            "stop:0 rgba(36, 49, 82, 252),"
            "stop:1 rgba(23, 32, 52, 252)"
            ")",
            "#3C507B",
        ),
    }

    def __init__(
        self,
        object_name="card",
        hover=True,
        radius=Theme.RADIUS_LARGE,
        shadow=False,
        palette="default",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._hover = hover
        self._radius = radius
        self._shadow_enabled = shadow
        self._palette = palette if palette in self.PALETTES else "default"

        self._update_style()
        self._update_shadow()

    def _update_style(self):
        normal, hover, border = self.PALETTES[self._palette]
        name = self.objectName()

        style = f"""
            QFrame#{name} {{
                background: {normal};
                border: 1px solid {border};
                border-radius: {self._radius}px;
            }}
        """

        if self._hover:
            style += f"""
                QFrame#{name}:hover {{
                    background: {hover};
                    border-color: {Theme.BORDER_HOVER};
                }}
            """

        self.setStyleSheet(style)

    def _update_shadow(self):
        if not self._shadow_enabled:
            self.setGraphicsEffect(None)
            return

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(44)
        shadow.setOffset(0, 1)
        shadow.setColor(QColor(0, 0, 0, 88))
        self.setGraphicsEffect(shadow)

    def set_hover_enabled(self, enabled: bool):
        self._hover = enabled
        self._update_style()

    def set_radius(self, radius: int):
        self._radius = radius
        self._update_style()

    def set_shadow_enabled(self, enabled: bool):
        self._shadow_enabled = enabled
        self._update_shadow()

    def set_palette(self, palette: str):
        if palette not in self.PALETTES:
            raise ValueError(f"Geçersiz kart paleti: {palette}")

        self._palette = palette
        self._update_style()
