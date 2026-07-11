from PySide6.QtWidgets import QLineEdit

from ui.theme import Theme


class AppLineEdit(QLineEdit):
    def __init__(
        self,
        placeholder="",
        object_name="appInput",
        parent=None,
    ):
        super().__init__(parent)

        self.setObjectName(object_name)
        self.setPlaceholderText(placeholder)
        self.setMinimumHeight(42)

        self.setStyleSheet(
            f"""
            QLineEdit#{object_name} {{
                background-color: rgba(14, 21, 29, 245);
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius: {Theme.RADIUS_SMALL}px;
                padding-left: 14px;
                padding-right: 14px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 13px;
                font-weight: 500;
                selection-background-color: {Theme.ACCENT_SOFT};
            }}

            QLineEdit#{object_name}:hover {{
                border-color: {Theme.BORDER_HOVER};
            }}

            QLineEdit#{object_name}:focus {{
                background-color: rgba(15, 23, 32, 250);
                border-color: {Theme.ACCENT};
            }}

            QLineEdit#{object_name}::placeholder {{
                color: {Theme.TEXT_MUTED};
            }}
            """
        )