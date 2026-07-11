from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QFrame, QGraphicsDropShadowEffect

from ui.theme import Theme


class Card(QFrame):
    PALETTES = {
        "default": (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(18,27,38,248),"
            "stop:0.55 rgba(15,23,33,246),"
            "stop:1 rgba(12,19,28,246))",
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(23,34,47,252),"
            "stop:1 rgba(16,25,36,252))",
            Theme.BORDER,
        ),
        "blue": (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(20,35,63,248),"
            "stop:0.55 rgba(16,29,48,246),"
            "stop:1 rgba(13,23,35,246))",
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(25,44,78,252),"
            "stop:1 rgba(17,31,49,252))",
            "#294B70",
        ),
        "teal": (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(13,45,50,248),"
            "stop:0.55 rgba(13,32,40,246),"
            "stop:1 rgba(12,23,32,246))",
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(16,55,62,252),"
            "stop:1 rgba(15,35,44,252))",
            "#245B61",
        ),
        "violet": (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(37,29,66,248),"
            "stop:0.55 rgba(26,24,49,246),"
            "stop:1 rgba(15,22,34,246))",
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(46,36,81,252),"
            "stop:1 rgba(28,27,52,252))",
            "#4C4275",
        ),
        "indigo": (
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(26,36,64,248),"
            "stop:0.55 rgba(20,28,47,246),"
            "stop:1 rgba(14,21,32,246))",
            "qlineargradient(x1:0,y1:0,x2:1,y2:1,"
            "stop:0 rgba(33,45,79,252),"
            "stop:1 rgba(22,31,51,252))",
            "#394D79",
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
                border-top-color: rgba(255,255,255,32);
                border-bottom-color: rgba(0,0,0,105);
                border-radius: {self._radius}px;
            }}
        """
        if self._hover:
            style += f"""
                QFrame#{name}:hover {{
                    background: {hover};
                    border-color: {Theme.BORDER_HOVER};
                    border-top-color: rgba(255,255,255,42);
                    border-bottom-color: rgba(0,0,0,120);
                }}
            """
        self.setStyleSheet(style)

    def _update_shadow(self):
        if not self._shadow_enabled:
            self.setGraphicsEffect(None)
            return
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(54)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 110))
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
