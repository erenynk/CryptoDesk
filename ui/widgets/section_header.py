from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from ui.theme import Theme


class SectionHeader(QWidget):
    def __init__(
        self,
        title,
        description="",
        right_widget=None,
        object_name="sectionHeader",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        self.title_label = QLabel(title)
        self.title_label.setObjectName("sectionHeaderTitle")

        self.description_label = QLabel(description)
        self.description_label.setObjectName(
            "sectionHeaderDescription"
        )
        self.description_label.setWordWrap(True)

        text_layout.addWidget(self.title_label)

        if description:
            text_layout.addWidget(
                self.description_label
            )
        else:
            self.description_label.hide()

        layout.addLayout(text_layout, 1)

        if right_widget is not None:
            layout.addWidget(right_widget)

        self.setStyleSheet(
            f"""
            QWidget#{object_name} {{
                background: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER};
            }}

            QWidget#{object_name}
            QLabel#sectionHeaderTitle {{
                background: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 700;
            }}

            QWidget#{object_name}
            QLabel#sectionHeaderDescription {{
                background: transparent;
                color: {Theme.TEXT_MUTED};
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 11px;
                font-weight: 400;
            }}
            """
        )

    def set_title(self, title):
        self.title_label.setText(title)

    def set_description(self, description):
        self.description_label.setText(description)
        self.description_label.setVisible(
            bool(description)
        )