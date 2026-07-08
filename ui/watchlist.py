from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class WatchlistPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        layout = QVBoxLayout(self)

        title = QLabel("Watchlist")
        title.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
        """)

        layout.addWidget(title)
        layout.addStretch()