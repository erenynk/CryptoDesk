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
    QVBoxLayout,
    QWidget,
)

from services import alarm_service


class AlarmsPage(QWidget):
    TOGGLE_COLUMN = 7
    DELETE_COLUMN = 8

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.row_alarms = []

        self.headers = [
            "Coin",
            "Hedef Fiyat",
            "Koşul",
            "Anlık Fiyat",
            "Not",
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
        self.symbol_input.setMaximumWidth(190)
        self.symbol_input.returnPressed.connect(self.create_alarm)
        self.symbol_input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.symbol_input)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Hedef fiyat")
        self.price_input.setMinimumHeight(42)
        self.price_input.setMaximumWidth(210)

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
        self.condition_combo.setMinimumWidth(180)
        self.condition_combo.addItem(
            "Üstüne çıkınca",
            alarm_service.CONDITION_ABOVE,
        )
        self.condition_combo.addItem(
            "Altına düşünce",
            alarm_service.CONDITION_BELOW,
        )
        self.condition_combo.setStyleSheet(self.combo_style())
        form_layout.addWidget(self.condition_combo)

        self.note_input = QLineEdit()
        self.note_input.setPlaceholderText("İsteğe bağlı not")
        self.note_input.setMinimumHeight(42)
        self.note_input.setMinimumWidth(220)
        self.note_input.setMaxLength(alarm_service.MAX_NOTE_LENGTH)
        self.note_input.returnPressed.connect(self.create_alarm)
        self.note_input.setStyleSheet(self.input_style())
        form_layout.addWidget(self.note_input, 1)

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

        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setStyleSheet("""
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
        """)
        self.table.verticalHeader().setDefaultSectionSize(46)
        self.table.verticalHeader().setMinimumSectionSize(46)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        header.setSectionResizeMode(
            self.TOGGLE_COLUMN,
            QHeaderView.Fixed,
        )
        header.setSectionResizeMode(
            self.DELETE_COLUMN,
            QHeaderView.Fixed,
        )

        self.table.setColumnWidth(4, 230)
        self.table.setColumnWidth(self.TOGGLE_COLUMN, 120)
        self.table.setColumnWidth(self.DELETE_COLUMN, 75)

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

            QTableWidget::item:hover {
                background-color: #222634;
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

        self.table.cellClicked.connect(self.on_table_cell_clicked)

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

    @staticmethod
    def combo_style():
        return """
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
        """

    def on_table_cell_clicked(self, row, column):
        if row < 0 or row >= len(self.row_alarms):
            return

        alarm = self.row_alarms[row]
        alarm_id = alarm["id"]

        if column == self.TOGGLE_COLUMN:
            if alarm.get("is_triggered"):
                return

            self.toggle_alarm(
                alarm_id,
                alarm["is_active"],
            )

        elif column == self.DELETE_COLUMN:
            self.delete_alarm(alarm_id)

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
        note = self.note_input.text().strip()

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
            symbol=symbol,
            target_price=target_price,
            condition=condition,
            note=note,
        )

        if not success:
            self.set_status(str(result), error=True)
            return

        normalized_symbol = symbol.strip().upper()

        self.symbol_input.clear()
        self.price_input.clear()
        self.note_input.clear()
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
        self.row_alarms = alarms

        self.table.setUpdatesEnabled(False)
        self.table.clearContents()
        self.table.setRowCount(len(alarms))

        try:
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

                note = alarm.get("note", "").strip()
                note_item = self.create_item(
                    note if note else "-",
                    color="#C7CDD6" if note else "#848E9C",
                    bold=False,
                    alignment=Qt.AlignLeft | Qt.AlignVCenter,
                )

                if note:
                    note_item.setToolTip(note)

                self.table.setItem(row, 4, note_item)

                status_text = alarm_service.get_status_text(alarm)
                status_color = self.get_status_color(alarm)

                self.table.setItem(
                    row,
                    5,
                    self.create_item(
                        status_text,
                        color=status_color,
                        bold=True,
                    ),
                )

                self.table.setItem(
                    row,
                    6,
                    self.create_item(
                        self.format_date(alarm.get("created_at")),
                        color="#C7CDD6",
                        bold=False,
                    ),
                )

                if alarm.get("is_triggered"):
                    toggle_text = "Tamamlandı"
                    toggle_color = "#848E9C"

                elif alarm.get("is_active"):
                    toggle_text = "Pasif Et"
                    toggle_color = "#F0B90B"

                else:
                    toggle_text = "Aktif Et"
                    toggle_color = "#00C087"

                toggle_item = self.create_item(
                    toggle_text,
                    color=toggle_color,
                    bold=True,
                )
                toggle_item.setToolTip(
                    "Alarm durumunu değiştirmek için tıklayın."
                )

                self.table.setItem(
                    row,
                    self.TOGGLE_COLUMN,
                    toggle_item,
                )

                delete_item = self.create_item(
                    "×",
                    color="#F6465D",
                    bold=True,
                )

                delete_font = delete_item.font()
                delete_font.setPointSize(16)
                delete_font.setBold(False)
                delete_item.setFont(delete_font)
                delete_item.setToolTip(
                    "Alarmı silmek için tıklayın."
                )

                self.table.setItem(
                    row,
                    self.DELETE_COLUMN,
                    delete_item,
                )

        finally:
            self.table.setUpdatesEnabled(True)

    @staticmethod
    def create_item(
        text: str,
        color: str = "#FFFFFF",
        bold: bool = True,
        alignment=Qt.AlignCenter,
    ):
        item = QTableWidgetItem(str(text))
        item.setForeground(QColor(color))
        item.setTextAlignment(alignment)

        font = QFont("Segoe UI", 10)
        font.setBold(bold)
        item.setFont(font)

        return item

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