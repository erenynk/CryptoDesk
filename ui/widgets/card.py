from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame

from ui.theme import Theme


class Card(QFrame):
    def __init__(
        self,
        object_name="card",
        hover=True,
        radius=Theme.RADIUS_LARGE,
    ):
        super().__init__()

        self.setObjectName(object_name)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._hover = hover
        self._radius = radius

        self._update_style()

    def _update_style(self):
        style = f"""
        QFrame#{self.objectName()} {{
            background-color: {Theme.CARD_BACKGROUND};
            border: 1px solid {Theme.BORDER};
            border-radius: {self._radius}px;
        }}
        """

        if self._hover:
            style += f"""
            QFrame#{self.objectName()}:hover {{
                background-color: {Theme.CARD_BACKGROUND_HOVER};
                border-color: {Theme.BORDER_HOVER};
            }}
            """

        self.setStyleSheet(style)

    def set_hover_enabled(self, enabled: bool):
        self._hover = enabled
        self._update_style()

    def set_radius(self, radius: int):
        self._radius = radius
        self._update_style()