from datetime import datetime

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
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from services import watchlist_service


COIN_BADGES = {
    "BTC": ("₿", "#F7931A"),
    "ETH": ("◆", "#627EEA"),
    "BNB": ("◆", "#F0B90B"),
    "SOL": ("≋", "#14F195"),
    "LTC": ("Ł", "#BEBEBE"),
    "XRP": ("X", "#C7CDD6"),
    "ADA": ("A", "#3CC8C8"),
    "DOGE": ("Ð", "#C2A633"),
    "DOT": ("●", "#E6007A"),
    "AVAX": ("A", "#E84142"),
    "LINK": ("⬡", "#2A5ADA"),
    "TRX": ("T", "#EF0027"),
}

class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)
        self.setForeground(QColor("#FFFFFF"))

class WatchlistPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.headers = [
            "Varlık",
            "Anlık Fiyat",
            "Eklenme Fiyatı",
            "Değişim",
            "Eklenme Tarihi",
            "İşlem",
        ]

        self.setFont(QFont("Segoe UI", 10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(28)

        title = QLabel("Watchlist")
        title.setStyleSheet("""
            font-size: 30px;
            font-weight: 800;
            color: #FFFFFF;
        """)
        layout.addWidget(title)

        input_layout = QHBoxLayout()
        input_layout.setSpacing(12)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Ticker")
        self.symbol_input.setMinimumHeight(42)
        self.symbol_input.setStyleSheet("""
            QLineEdit {
                background-color: #161B26;
                color: #FFFFFF;
                border: 1px solid #2A3342;
                border-radius: 8px;
                padding: 0px 14px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 1px solid #3B82F6;
            }
        """)
        self.symbol_input.returnPressed.connect(self.add_symbol)
        input_layout.addWidget(self.symbol_input, 1)

        self.add_button = QPushButton("Ekle")
        self.add_button.setMinimumSize(70, 42)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #263246;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 700;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton:pressed {
                background-color: #1E293B;
            }
        """)
        self.add_button.clicked.connect(self.add_symbol)
        input_layout.addWidget(self.add_button)

        layout.addLayout(input_layout)

        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #848E9C; font-size: 13px;")
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)

        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setMinimumSectionSize(46)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161A25;
                color: #FFFFFF;
                gridline-color: transparent;
                border: 1px solid #2A2E39;
                border-radius: 8px;
            }

            QTableWidget QWidget {
                background-color: transparent;
            }

            QTableWidget::item {
                padding: 18px 14px;
                border-bottom: 1px solid #263142;
            }

            QTableWidget::item:hover {
                background-color: #222634;
            }

            QHeaderView::section:horizontal {
                background-color: #1E222D;
                color: #848E9C;
                padding: 10px;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-bottom: 2px solid #2A2E39;
                outline: none;
            }

            QHeaderView::section:horizontal:pressed {
                background-color: #1E222D;
                border: none;
                border-bottom: 2px solid #2A2E39;
            }

            QHeaderView::section:horizontal:focus {
                outline: none;
            }

            QHeaderView::section:vertical {
                background-color: #161A25;
                color: #BFD7FF;
                padding-left: 14px;
                padding-right: 14px;
                font-weight: 800;
                font-size: 14px;
                border: none;
                border-right: 1px solid #2A2E39;
                border-bottom: 1px solid #263142;
            }

            QTableCornerButton::section {
                background-color: #1E222D;
                border: none;
                border-bottom: 1px solid #2A2E39;
            }
        """)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)

        layout.addWidget(self.table)
        self.table.cellClicked.connect(self.on_table_cell_clicked)

        self.load_symbols()

    def on_table_cell_clicked(self, row, column):
        if column != 5:
            return

        item = self.table.item(row, 0)
        if item is None:
            return

        symbol = item.text()
        self.remove_symbol(symbol)    

    def showEvent(self, event):
        super().showEvent(event)
        self.load_symbols()

    def set_status(self, message, error=False):
        color = "#F6465D" if error else "#848E9C"
        self.status_label.setStyleSheet(f"color: {color}; font-size: 13px;")
        self.status_label.setText(message)

    def clear_status(self):
        self.status_label.setText("")

    def add_symbol(self):
        raw_symbol = self.symbol_input.text()
        normalized = watchlist_service.normalize_symbol(raw_symbol)

        if not normalized:
            self.set_status(
                "Coin adı boş olamaz.",
                error=True,
            )
            return

        self.add_button.setEnabled(False)
        self.add_button.setText("Kontrol...")

        try:
            success, result = (
                self.data_manager.okx.is_spot_symbol_available(
                    normalized
                )
            )

            if not success:
                self.set_status(
                    str(result),
                    error=True,
                )
                return

            if not result:
                self.set_status(
                    f"{normalized} OKX Spot piyasasında bulunamadı.",
                    error=True,
                )
                return

            current_price = self.data_manager.get_price(normalized)

            if watchlist_service.add_symbol(
                normalized,
                current_price,
            ):
                self.symbol_input.clear()
                self.clear_status()
                self.load_symbols()
                return

            self.set_status(
                f"{normalized} zaten watchlist'te.",
                error=True,
            )

        finally:
            self.add_button.setEnabled(True)
            self.add_button.setText("Ekle")

    def remove_symbol(self, symbol):
        if watchlist_service.remove_symbol(symbol):
            self.clear_status()
            self.load_symbols()
        else:
            self.set_status(f"{symbol} silinemedi.", error=True)

    def format_price(self, price):
        if price is None or price <= 0:
            return "-"

        if price >= 1:
            return f"${price:,.2f}"

        return f"${price:,.4f}"

    def format_date(self, value):
        if not value:
            return "-"

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.strftime("%d.%m.%Y %H:%M")
        except ValueError:
            return "-"

    def format_change(self, current_price, added_price):
        if not current_price or not added_price or added_price <= 0:
            return "-", "#848E9C"

        change = ((current_price - added_price) / added_price) * 100

        if change >= 0:
            return f"+{change:.2f}%", "#00C087"

        return f"{change:.2f}%", "#F6465D"

    def make_item(self, text, color="#FFFFFF", bold=True, alignment=None):
        item = NumericTableWidgetItem(text)
        item.setForeground(QColor(color))

        if alignment is None:
            alignment = Qt.AlignCenter

        item.setTextAlignment(alignment)

        font = QFont("Segoe UI", 10)
        font.setBold(bold)
        item.setFont(font)

        return item

    def create_coin_cell(self, symbol):
        badge_text, badge_color = COIN_BADGES.get(symbol, ("●", "#64748B"))

        cell = QWidget()
        layout = QHBoxLayout(cell)
        layout.setContentsMargins(10, 0, 0, 0)
        layout.setSpacing(10)
        layout.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        badge = QLabel(badge_text)
        badge.setFixedSize(22, 22)
        badge.setAlignment(Qt.AlignCenter)
        badge.setStyleSheet(f"""
            QLabel {{
                background-color: {badge_color};
                color: #0B1220;
                border-radius: 11px;
                font-size: 12px;
                font-weight: 600;
            }}
        """)

        name = QLabel(symbol)
        name.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }
        """)

        layout.addWidget(badge)
        layout.addWidget(name)
        layout.addStretch()

        return cell

    def create_delete_button(self, symbol):
        button = QToolButton()
        button.setText("×")
        button.setFixedSize(26, 26)
        button.setToolTip("Watchlist'ten kaldır")
        button.setCursor(Qt.PointingHandCursor)
        button.setStyleSheet("""
            QToolButton {
                background-color: #151D29;
                color: #F6465D;
                border: 1px solid #2A3342;
                border-radius: 6px;
                font-size: 18px;
                line-height: 30px;             
                font-weight: 400;
                padding: 0px 0px 4px 0px;
                margin: 0px;
            }

            QToolButton:hover {
                background-color: #2A1F2A;
                color: #FF5C6C;
                border: 1px solid #5A2A35;
            }

            QToolButton:pressed {
                background-color: #F6465D;
                color: #FFFFFF;
                border: 1px solid #F6465D;
            }
        """)
        button.clicked.connect(
            lambda _checked=False, s=symbol: self.remove_symbol(s)
        )
        return button

    def create_action_cell(self, symbol):
        cell = QWidget()
        cell.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(cell)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignCenter)

        button = self.create_delete_button(symbol)
        layout.addWidget(button, 0, Qt.AlignCenter)

        return cell

    def load_symbols(self):
        items = watchlist_service.get_items()

        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            symbol = watchlist_service.normalize_symbol(item["symbol"])
            current_price = self.data_manager.get_price(symbol)
            added_price = item.get("added_price")
            created_at = item.get("created_at")

            change_text, change_color = self.format_change(
                current_price,
                added_price,
            )

            coin_item = self.make_item(
                symbol,
                color="#FFFFFF",
                bold=True,
                alignment=Qt.AlignCenter,
            )

            self.table.setItem(row, 0, coin_item)

            self.table.setItem(
                row,
                1,
                self.make_item(
                    self.format_price(current_price),
                    color="#00C087",
                    bold=True,
                    alignment=Qt.AlignHCenter | Qt.AlignVCenter,
                ),
            )

            self.table.setItem(
                row,
                2,
                self.make_item(
                    self.format_price(added_price),
                    color="#FFFFFF",
                    bold=True,
                    alignment=Qt.AlignCenter,
                ),
            )

            self.table.setItem(
                row,
                3,
                self.make_item(
                    change_text,
                    color=change_color,
                    bold=True,
                    alignment=Qt.AlignCenter,
                ),
            )

            self.table.setItem(
                row,
                4,
                self.make_item(
                    self.format_date(created_at),
                    color="#C7CDD6",
                    bold=True,
                    alignment=Qt.AlignVCenter | Qt.AlignCenter,
                ),
            )

            delete_item = self.make_item(
                "×",
                color="#F6465D",
                bold=True,
                alignment=Qt.AlignCenter,
            )
            self.table.setItem(row, 5, delete_item)