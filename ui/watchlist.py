from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from database.settings_db import (
    add_watchlist_symbol,
    get_watchlist_symbols,
    remove_watchlist_symbol,
)


class WatchlistPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        self.setFont(QFont("Segoe UI", 10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("Watchlist")
        title.setStyleSheet("""
            font-size: 28px;
            font-weight: bold;
        """)
        layout.addWidget(title)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #848E9C; font-size: 13px;")
        layout.addWidget(self.status_label)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(10)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Örn: BTC-USDT")
        self.symbol_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E222D;
                color: #FFFFFF;
                border: 1px solid #2A2E39;
                border-radius: 6px;
                padding: 8px 12px;
            }
        """)
        self.symbol_input.returnPressed.connect(self.add_symbol)
        input_layout.addWidget(self.symbol_input, 1)

        self.add_button = QPushButton("Ekle")
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #2D3748;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #4A5568;
            }
        """)
        self.add_button.clicked.connect(self.add_symbol)
        input_layout.addWidget(self.add_button)

        layout.addLayout(input_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Sembol", "İşlem"])
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)
        self.table.verticalHeader().setVisible(False)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161A25;
                color: #FFFFFF;
                gridline-color: transparent;
                border: 1px solid #2A2E39;
                border-radius: 8px;
            }

            QTableWidget::item {
                padding: 10px;
                border-bottom: 1px solid #1E222D;
            }

            QHeaderView::section:horizontal {
                background-color: #1E222D;
                color: #848E9C;
                padding: 10px;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid #2A2E39;
            }
        """)

        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )

        layout.addWidget(self.table)

        self.load_symbols()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_symbols()

    def set_status(self, message, error=False):
        color = "#F6465D" if error else "#848E9C"
        self.status_label.setStyleSheet(
            f"color: {color}; font-size: 13px;"
        )
        self.status_label.setText(message)

    def clear_status(self):
        self.status_label.setText("")

    def add_symbol(self):
        raw = self.symbol_input.text()

        if not raw.strip():
            self.set_status("Sembol boş olamaz.", error=True)
            return

        normalized = raw.strip().upper()

        if add_watchlist_symbol(raw):
            self.symbol_input.clear()
            self.clear_status()
            self.load_symbols()
            return

        symbols = get_watchlist_symbols()
        if normalized in symbols:
            self.set_status(f"{normalized} zaten watchlist'te.", error=True)
        else:
            self.set_status("Sembol eklenemedi.", error=True)

    def remove_symbol(self, symbol):
        if remove_watchlist_symbol(symbol):
            self.clear_status()
            self.load_symbols()
        else:
            self.set_status(f"{symbol} silinemedi.", error=True)

    def load_symbols(self):
        symbols = get_watchlist_symbols()

        self.table.setRowCount(len(symbols))

        for row, symbol in enumerate(symbols):
            symbol_item = QTableWidgetItem(symbol)
            symbol_item.setTextAlignment(Qt.AlignCenter)
            symbol_item.setForeground(QColor("#FFFFFF"))

            font = symbol_item.font()
            font.setBold(True)
            symbol_item.setFont(font)

            self.table.setItem(row, 0, symbol_item)

            delete_button = QPushButton("Sil")
            delete_button.setStyleSheet("""
                QPushButton {
                    background-color: #2D3748;
                    color: #FFFFFF;
                    border: none;
                    padding: 6px 14px;
                    border-radius: 6px;
                    font-weight: 600;
                }
                QPushButton:hover {
                    background-color: #4A5568;
                }
            """)
            delete_button.clicked.connect(
                lambda _checked=False, s=symbol: self.remove_symbol(s)
            )

            self.table.setCellWidget(row, 1, delete_button)

        self.table.resizeRowsToContents()
