from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.theme import Theme


class PageHeader(QWidget):
    def __init__(
        self,
        title,
        subtitle="",
        right_widget=None,
        object_name="pageHeader",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui(
            title=title,
            subtitle=subtitle,
            right_widget=right_widget,
        )
        self._apply_style()

    def _build_ui(
        self,
        title,
        subtitle,
        right_widget,
    ):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("pageHeaderTitle")

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName(
            "pageHeaderSubtitle"
        )
        self.subtitle_label.setWordWrap(True)

        text_layout.addWidget(self.title_label)

        if subtitle:
            text_layout.addWidget(self.subtitle_label)
        else:
            self.subtitle_label.hide()

        layout.addLayout(text_layout, 1)

        if right_widget is not None:
            layout.addWidget(
                right_widget,
                0,
                Qt.AlignTop | Qt.AlignRight,
            )

    def set_title(self, title):
        self.title_label.setText(title)

    def set_subtitle(self, subtitle):
        self.subtitle_label.setText(subtitle)
        self.subtitle_label.setVisible(bool(subtitle))

    def _apply_style(self):
        self.setStyleSheet(
            f"""
            QWidget#{self.objectName()} {{
                background: transparent;
                border: none;
            }}

            QWidget#{self.objectName()}
            QLabel#pageHeaderTitle {{
                background: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 27px;
                font-weight: 700;
            }}

            QWidget#{self.objectName()}
            QLabel#pageHeaderSubtitle {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 13px;
                font-weight: 400;
            }}
            """
        )