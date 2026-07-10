from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDoubleValidator, QFont
from PySide6.QtWidgets import (
    QComboBox,
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

from services import alarm_service


class AlarmsPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        self.headers = [
            "Coin",
            "Hedef Fiyat",
            "Koşul",
            "Anlık Fiyat",
            "Durum",
            "Oluşturulma",
            "Aktif/Pasif",
            "Sil",
        ]

        self.setFont(QFont("Segoe UI", 10))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        title = QLabel("Alarmlar")
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 30px;
                font-weight: 800;
                background: transparent;
            }
        """)
        layout.addWidget(title)

        description = QLabel(
            "Coin fiyatı belirlediğiniz seviyeye ulaştığında "
            "tek seferlik bildirim alın."
        )
        description.setStyleSheet("""
            QLabel {
                color: #848E9C;
                font-size: 13px;
                background: transparent;
            }
        """)
        layout.addWidget(description)

        form_layout = QHBoxLayout()
        form_layout.setSpacing(12)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Coin, örn: BTC")
        self.symbol_input.setMinimumHeight(42)
        self.symbol_input.setMaximumWidth(220)
        self.symbol_input.returnPressed.connect(self.create_alarm)
        self.symbol_input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.symbol_input)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Hedef fiyat")
        self.price_input.setMinimumHeight(42)
        self.price_input.setMaximumWidth(240)

        price_validator = QDoubleValidator(
            0.00000001,
            999999999999.0,
            8,
            self.price_input,
        )
        price_validator.setNotation(QDoubleValidator.StandardNotation)
        self.price_input.setValidator(price_validator)
        self.price_input.returnPressed.connect(self.create_alarm)
        self.price_input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.price_input)

        self.condition_combo = QComboBox()
        self.condition_combo.setMinimumHeight(42)
        self.condition_combo.setMinimumWidth(190)
        self.condition_combo.addItem(
            "Üstüne çıkınca",
            alarm_service.CONDITION_ABOVE,
        )
        self.condition_combo.addItem(
            "Altına düşünce",
            alarm_service.CONDITION_BELOW,
        )
        self.condition_combo.setStyleSheet("""
            QComboBox {
                background-color: #161B26;
                color: #FFFFFF;
                border: 1px solid #2A3342;
                border-radius: 8px;
                padding: 0px 14px;
                font-size: 14px;
            }

            QComboBox:focus {
                border: 1px solid #3B82F6;
            }

            QComboBox::drop-down {
                border: none;
                width: 30px;
            }

            QComboBox QAbstractItemView {
                background-color: #161B26;
                color: #FFFFFF;
                border: 1px solid #2A3342;
                selection-background-color: #263246;
                selection-color: #FFFFFF;
                outline: none;
            }
        """)
        form_layout.addWidget(self.condition_combo)

        self.add_button = QPushButton("Alarm Oluştur")
        self.add_button.setMinimumSize(130, 42)
        self.add_button.setCursor(Qt.PointingHandCursor)
        self.add_button.clicked.connect(self.create_alarm)
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #263246;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                padding: 0px 18px;
                font-size: 14px;
                font-weight: 700;
            }

            QPushButton:hover {
                background-color: #334155;
            }

            QPushButton:pressed {
                background-color: #1E293B;
            }
        """)
        form_layout.addWidget(self.add_button)

        form_layout.addStretch()
        layout.addLayout(form_layout)

        self.status_label = QLabel("")
        self.status_label.setMinimumHeight(20)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #848E9C;
                font-size: 13px;
                background: transparent;
            }
        """)
        layout.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setShowGrid(False)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)
        self.table.verticalHeader().setMinimumSectionSize(52)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.Stretch
        )
        self.table.horizontalHeader().setSectionResizeMode(
            6,
            QHeaderView.ResizeToContents,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            7,
            QHeaderView.ResizeToContents,
        )

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
                padding: 12px;
                border-bottom: 1px solid #263142;
            }

            QHeaderView::section:horizontal {
                background-color: #1E222D;
                color: #848E9C;
                padding: 10px;
                font-size: 12px;
                font-weight: 700;
                border: none;
                border-bottom: 2px solid #2A2E39;
                outline: none;
            }

            QHeaderView::section:horizontal:pressed {
                background-color: #1E222D;
                border: none;
                border-bottom: 2px solid #2A2E39;
            }

            QTableCornerButton::section {
                background-color: #1E222D;
                border: none;
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

        layout.addWidget(self.table)

        self.load_alarms()

    @staticmethod
    def input_style():
        return """
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
        """

    def showEvent(self, event):
        super().showEvent(event)
        self.load_alarms()

    def set_status(self, message: str, error: bool = False):
        color = "#F6465D" if error else "#00C087"

        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 13px;
                background: transparent;
            }}
        """)
        self.status_label.setText(message)

    def clear_status(self):
        self.status_label.setText("")

    def create_alarm(self):
        symbol = self.symbol_input.text()
        price_text = self.price_input.text().strip().replace(",", ".")
        condition = self.condition_combo.currentData()

        if not price_text:
            self.set_status(
                "Hedef fiyat boş olamaz.",
                error=True,
            )
            return

        try:
            target_price = float(price_text)
        except ValueError:
            self.set_status(
                "Geçerli bir hedef fiyat girin.",
                error=True,
            )
            return

        success, result = alarm_service.create_alarm(
            symbol,
            target_price,
            condition,
        )

        if not success:
            self.set_status(str(result), error=True)
            return

        normalized_symbol = symbol.strip().upper()

        self.symbol_input.clear()
        self.price_input.clear()
        self.condition_combo.setCurrentIndex(0)

        self.set_status(
            f"{normalized_symbol} alarmı oluşturuldu."
        )
        self.load_alarms()

    def toggle_alarm(self, alarm_id: int, current_status: bool):
        new_status = not current_status

        if alarm_service.change_alarm_status(
            alarm_id,
            new_status,
        ):
            self.clear_status()
            self.load_alarms()
            return

        self.set_status(
            "Alarm durumu değiştirilemedi.",
            error=True,
        )

    def delete_alarm(self, alarm_id: int):
        if alarm_service.remove_alarm(alarm_id):
            self.clear_status()
            self.load_alarms()
            return

        self.set_status(
            "Alarm silinemedi.",
            error=True,
        )

    def load_alarms(self):
        alarms = alarm_service.get_all_alarms()

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(alarms))

        for row, alarm in enumerate(alarms):
            symbol = alarm["symbol"]
            target_price = alarm["target_price"]
            current_price = self.data_manager.get_price(symbol)

            self.table.setItem(
                row,
                0,
                self.create_item(
                    symbol,
                    color="#FFFFFF",
                    bold=True,
                ),
            )

            self.table.setItem(
                row,
                1,
                self.create_item(
                    self.format_price(target_price),
                    color="#FFFFFF",
                    bold=True,
                ),
            )

            condition_color = (
                "#00C087"
                if alarm["condition"] == alarm_service.CONDITION_ABOVE
                else "#F0B90B"
            )

            self.table.setItem(
                row,
                2,
                self.create_item(
                    alarm_service.get_condition_text(
                        alarm["condition"]
                    ),
                    color=condition_color,
                    bold=True,
                ),
            )

            self.table.setItem(
                row,
                3,
                self.create_item(
                    self.format_price(current_price),
                    color="#00C087" if current_price else "#848E9C",
                    bold=True,
                ),
            )

            status_text = alarm_service.get_status_text(alarm)
            status_color = self.get_status_color(alarm)

            self.table.setItem(
                row,
                4,
                self.create_item(
                    status_text,
                    color=status_color,
                    bold=True,
                ),
            )

            self.table.setItem(
                row,
                5,
                self.create_item(
                    self.format_date(alarm.get("created_at")),
                    color="#C7CDD6",
                    bold=False,
                ),
            )

            if alarm.get("is_triggered"):
                triggered_item = self.create_item(
                    "Tamamlandı",
                    color="#848E9C",
                    bold=True,
                )
                self.table.setItem(row, 6, triggered_item)
            else:
                toggle_widget = self.create_toggle_button(
                    alarm["id"],
                    alarm["is_active"],
                )
                self.table.setCellWidget(row, 6, toggle_widget)

            delete_widget = self.create_delete_button(
                alarm["id"]
            )
            self.table.setCellWidget(row, 7, delete_widget)

        self.table.setUpdatesEnabled(True)

    def create_item(
        self,
        text: str,
        color: str = "#FFFFFF",
        bold: bool = True,
    ):
        item = QTableWidgetItem(text)
        item.setForeground(QColor(color))
        item.setTextAlignment(Qt.AlignCenter)

        font = QFont("Segoe UI", 10)
        font.setBold(bold)
        item.setFont(font)

        return item

    def create_toggle_button(
        self,
        alarm_id: int,
        is_active: bool,
    ):
        container = QWidget()
        container.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setAlignment(Qt.AlignCenter)

        button = QPushButton(
            "Aktif" if is_active else "Pasif"
        )
        button.setCursor(Qt.PointingHandCursor)
        button.setMinimumSize(72, 30)

        if is_active:
            background = "#153B32"
            hover = "#1B4F43"
            color = "#00C087"
            border = "#236B59"
        else:
            background = "#252A35"
            hover = "#303744"
            color = "#848E9C"
            border = "#3A4251"

        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {background};
                color: {color};
                border: 1px solid {border};
                border-radius: 7px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 700;
            }}

            QPushButton:hover {{
                background-color: {hover};
            }}
        """)

        button.clicked.connect(
            lambda _checked=False,
            selected_id=alarm_id,
            current=is_active: self.toggle_alarm(
                selected_id,
                current,
            )
        )

        layout.addWidget(button)
        return container

    def create_delete_button(self, alarm_id: int):
        container = QWidget()
        container.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setAlignment(Qt.AlignCenter)

        button = QToolButton()
        button.setText("×")
        button.setToolTip("Alarmı sil")
        button.setCursor(Qt.PointingHandCursor)
        button.setFixedSize(30, 30)

        button.setStyleSheet("""
            QToolButton {
                background-color: #151D29;
                color: #F6465D;
                border: 1px solid #2A3342;
                border-radius: 7px;
                font-size: 18px;
                font-weight: 400;
                padding: 0px 0px 4px 0px;
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
            lambda _checked=False,
            selected_id=alarm_id: self.delete_alarm(
                selected_id
            )
        )

        layout.addWidget(button)
        return container

    @staticmethod
    def format_price(price):
        if price is None or price <= 0:
            return "-"

        if price >= 1:
            return f"${price:,.2f}"

        if price >= 0.01:
            return f"${price:,.4f}"

        return f"${price:,.8f}"

    @staticmethod
    def format_date(value):
        if not value:
            return "-"

        try:
            date_value = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
            return date_value.strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def get_status_color(alarm):
        if alarm.get("is_triggered"):
            return "#848E9C"

        if alarm.get("is_active"):
            return "#00C087"

        return "#F0B90B"