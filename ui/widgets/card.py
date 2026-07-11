from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
)

from ui.theme import Theme


class Card(QFrame):
    def __init__(
        self,
        object_name="card",
        hover=True,
        radius=Theme.RADIUS_LARGE,
        shadow=False,
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._hover = hover
        self._radius = radius
        self._shadow_enabled = shadow

        self._update_style()
        self._update_shadow()

    def _update_style(self):
        object_name = self.objectName()

        style = f"""
            QFrame#{object_name} {{
                background-color: rgba(17, 24, 33, 246);
                border: 1px solid {Theme.BORDER};
                border-radius: {self._radius}px;
            }}
        """

        if self._hover:
            style += f"""
                QFrame#{object_name}:hover {{
                    background-color: rgba(21, 30, 41, 252);
                    border-color: {Theme.BORDER_HOVER};
                }}
            """

        self.setStyleSheet(style)

    def _update_shadow(self):
        if not self._shadow_enabled:
            self.setGraphicsEffect(None)
            return

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(34)
        shadow.setOffset(0, 10)
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
