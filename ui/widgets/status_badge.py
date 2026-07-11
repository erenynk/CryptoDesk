from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
)

from ui.theme import Theme


class StatusBadge(QFrame):
    NEUTRAL = "neutral"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"

    def __init__(
        self,
        text="Bekleniyor",
        status=NEUTRAL,
        object_name="statusBadge",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)
        self.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        self._status = status

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(8)

        self.dot = QLabel()
        self.dot.setObjectName("statusBadgeDot")
        self.dot.setFixedSize(8, 8)
        self.dot.setAlignment(Qt.AlignCenter)

        self.label = QLabel(text)
        self.label.setObjectName("statusBadgeText")

        layout.addWidget(self.dot)
        layout.addWidget(self.label)

        self._apply_style()

    def set_status(self, text, status=NEUTRAL):
        self._status = status
        self.label.setText(text)
        self._apply_style()

    def set_text(self, text):
        self.label.setText(text)

    def text(self):
        return self.label.text()

    def _get_status_color(self):
        if self._status == self.SUCCESS:
            return Theme.ACCENT

        if self._status == self.WARNING:
            return Theme.WARNING

        if self._status == self.ERROR:
            return Theme.ERROR

        return Theme.TEXT_MUTED

    def _apply_style(self):
        status_color = self._get_status_color()

        self.setStyleSheet(
            f"""
            QFrame#{self.objectName()} {{
                background-color: rgba(14, 21, 29, 235);
                border: 1px solid {Theme.BORDER};
                border-radius: 15px;
            }}

            QFrame#{self.objectName()} QLabel#statusBadgeDot {{
                background-color: {status_color};
                border: none;
                border-radius: 4px;
            }}

            QFrame#{self.objectName()} QLabel#statusBadgeText {{
                background: transparent;
                color: {status_color};
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 12px;
                font-weight: 600;
            }}
            """
        )