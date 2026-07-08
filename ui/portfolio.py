from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHeaderView,
    QCheckBox,
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFont, QColor

from services.data_worker import PortfolioRefreshWorker


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value, display_text):
        super().__init__(display_text)
        self.value = value
        self.setForeground(QColor("#FFFFFF"))

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value
        return super().__lt__(other)


class PortfolioPage(QWidget):
    def __init__(self, data_manager, dashboard_page):
        super().__init__()

        self.data_manager = data_manager
        self.dashboard_page = dashboard_page
        self.worker = None
        self.raw_assets_data = []

        self.headers = [
            "Varlık (Coin)",
            "Toplam Değer",
            "Anlık Fiyat",
            "Toplam Miktar",
            "Kullanılabilir Miktar",
        ]

        self.setFont(QFont("Segoe UI", 10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        top_layout = QHBoxLayout()

        top_layout.addStretch()

        self.hide_dust_checkbox = QCheckBox("Küçük Bakiyeleri Gizle (< $1)")
        self.hide_dust_checkbox.setStyleSheet("""
            QCheckBox {
                color: #A0AEC0;
                font-size: 13px;
                font-weight: 500;
                margin-right: 15px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 2px solid #4A5568;
                background-color: #1A202C;
            }
            QCheckBox::indicator:checked {
                background-color: #00C087;
                border-color: #00C087;
            }
        """)
        self.hide_dust_checkbox.stateChanged.connect(self.update_table_view)
        top_layout.addWidget(self.hide_dust_checkbox)

        self.refresh_button = QPushButton("Bakiyeleri Yenile")
        self.refresh_button.setStyleSheet("""
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
            QPushButton:disabled {
                background-color: #1A202C;
                color: #718096;
            }
        """)
        self.refresh_button.clicked.connect(self.load_balances)
        top_layout.addWidget(self.refresh_button)

        layout.addLayout(top_layout)

        self.card_widget = QWidget()
        self.card_widget.setStyleSheet("""
            QWidget {
                background-color: #1E222D;
                border: 1px solid #2A2E39;
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(self.card_widget)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(4)

        card_title = QLabel("TOPLAM VARLIK")
        card_title.setStyleSheet("""
            color: #848E9C;
            font-size: 11px;
            font-weight: 700;
            letter-spacing: 1px;
            border: none;
            background: transparent;
        """)

        self.total_balance_label = QLabel("$0.00 USDT")
        self.total_balance_label.setStyleSheet("""
            color: #00C087;
            font-size: 32px;
            font-weight: 800;
            border: none;
            background: transparent;
        """)

        self.asset_count_label = QLabel("0 farklı kripto varlık listeleniyor")
        self.asset_count_label.setStyleSheet("""
            color: #848E9C;
            font-size: 12px;
            border: none;
            background: transparent;
        """)

        card_layout.addWidget(card_title)
        card_layout.addWidget(self.total_balance_label)
        card_layout.addWidget(self.asset_count_label)

        layout.addWidget(self.card_widget)

        self.table = QTableWidget()
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #161A25;
                color: #FFFFFF;
                gridline-color: transparent;
                border: 1px solid #2A2E39;
                border-radius: 8px;
            }

            QTableWidget QWidget {
                background-color: #161A25;
            }

            QTableWidget::item {
                padding: 12px;
                border-bottom: 1px solid #1E222D;
            }

            QTableWidget::item:hover {
                background-color: #222634;
            }
             
            QTableWidget::item:selected {
            background-color: #222634;
            color: #FFFFFF;
            border: none;
            outline: none;
                                 
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
                color: #A0AEC0;
                padding-left: 14px;
                padding-right: 14px;
                font-weight: 700;
                font-size: 13px;
                border: none;
                border-right: 1px solid #2A2E39;
                border-bottom: 1px solid #1E222D;
            }

            QTableCornerButton::section {
                background-color: #1E222D;
                border: none;
                border-bottom: 2px solid #2A2E39;
            }

            QHeaderView::down-arrow,
            QHeaderView::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }

            QScrollBar:vertical {
                background-color: #161A25;
                width: 12px;
                margin: 0px;
            }

            QScrollBar::handle:vertical {
                background-color: #2D3748;
                min-height: 20px;
                border-radius: 6px;
                margin: 2px;
            }

            QScrollBar::handle:vertical:hover {
                background-color: #4A5568;
            }

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.setShowGrid(False)

        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        self.table.horizontalHeader().sortIndicatorChanged.connect(
            self.on_sort_indicator_changed
        )

        layout.addWidget(self.table)

        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        self.refresh_timer.timeout.connect(self.load_balances)

        QTimer.singleShot(100, self.start_page)

    def on_sort_indicator_changed(self, logical_index, order):
        for i in range(self.table.columnCount()):
            if i == logical_index:
                arrow = " ▲" if order == Qt.AscendingOrder else " ▼"
                self.table.horizontalHeaderItem(i).setText(
                    self.headers[i] + arrow
                )
            else:
                self.table.horizontalHeaderItem(i).setText(self.headers[i])

    def start_page(self):
        self.load_balances()
        self.refresh_timer.start()

    def load_balances(self):
        if self.worker is not None and self.worker.isRunning():
            return

        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Güncelleniyor...")

        self.worker = PortfolioRefreshWorker(self.data_manager)
        self.worker.finished.connect(self.on_balances_loaded)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def on_balances_loaded(self, success, result):
        if success:
            portfolio = self.data_manager.get_portfolio() or result
            total = portfolio["total_usdt"]

            self.total_balance_label.setText(f"${total:,.2f} USDT")
            self.raw_assets_data = portfolio["assets"]
            self.update_table_view()

        else:
            self.total_balance_label.setText("Bağlantı Hatası")
            print("Portfolio refresh error:", result)

        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Bakiyeleri Yenile")
        self.worker = None

    def format_amount(self, value):
        if value == 0:
            return "0"

        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text else "0"

    def format_price(self, price):
        if price >= 1:
            return f"${price:,.2f}"

        if price > 0:
            return f"${price:,.4f}"

        return "$0.00"

    def update_table_view(self):
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)

        hide_dust = self.hide_dust_checkbox.isChecked()

        visible_assets = [
            asset
            for asset in self.raw_assets_data
            if not (hide_dust and asset["usdt_value"] < 1)
        ]

        self.table.setRowCount(len(visible_assets))

        for row, asset in enumerate(visible_assets):
            coin_item = QTableWidgetItem(asset["coin"])
            coin_item.setForeground(QColor("#FFFFFF"))
            coin_item.setTextAlignment(Qt.AlignCenter)

            font = coin_item.font()
            font.setBold(True)
            coin_item.setFont(font)

            total_item = NumericTableWidgetItem(
                asset["total"],
                self.format_amount(asset["total"]),
            )
            total_item.setForeground(QColor("#C7CDD6"))

            available_item = NumericTableWidgetItem(
                asset["available"],
                self.format_amount(asset["available"]),
            )
            available_item.setForeground(QColor("#C7CDD6"))

            price_item = NumericTableWidgetItem(
                asset["price"],
                self.format_price(asset["price"]),
            )

            value_item = NumericTableWidgetItem(
                asset["usdt_value"],
                f"${asset['usdt_value']:,.2f}",
            
            )
            value_item.setForeground(QColor("#00C087"))
            
            font = value_item.font()
            font.setBold(True)
            value_item.setFont(font)

            for item in (
                total_item,
                available_item,
                price_item,
                value_item,
            ):
                item.setTextAlignment(Qt.AlignCenter)
                font = item.font()
                font.setBold(True)
                item.setFont(font)

            self.table.setItem(row, 0, coin_item)
            self.table.setItem(row, 1, value_item)
            self.table.setItem(row, 2, price_item)
            self.table.setItem(row, 3, total_item)
            self.table.setItem(row, 4, available_item)

        self.asset_count_label.setText(
            f"{len(visible_assets)} farklı kripto varlık listeleniyor"
        )

        idx = self.table.horizontalHeader().sortIndicatorSection()
        order = self.table.horizontalHeader().sortIndicatorOrder()

        self.on_sort_indicator_changed(idx, order)

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.refresh_timer.stop()