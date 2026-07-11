from datetime import datetime
from ui.widgets.card import Card
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDoubleValidator, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import alarm_service
from services.watchlist_service import normalize_symbol
from ui.theme import (
    Theme,
    label_style,
    page_style,
    page_title_style,
    primary_button_style,
    scroll_bar_style,
)


class AlarmsPage(QWidget):
    TOGGLE_COLUMN = 7
    DELETE_COLUMN = 8

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.row_alarms = []
        self.selected_condition = (
            alarm_service.CONDITION_ABOVE
        )

        self.headers = [
            "Varlık",
            "Hedef Fiyat",
            "Koşul",
            "Anlık Fiyat",
            "Alarm Notu",
            "Durum",
            "Oluşturulma",
            "Aktif/Pasif",
            "Sil",
        ]

        self.setObjectName("alarmsPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFont(QFont(Theme.FONT_FAMILY, 10))

        self._build_ui()
        self._apply_styles()
        self._connect_signals()

        self.load_alarms()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        main_layout.setSpacing(20)

        header = self._create_header()
        main_layout.addWidget(header)

        form_card = self._create_form_card()
        main_layout.addWidget(form_card)

        table_card = self._create_table_card()
        main_layout.addWidget(table_card, 1)

    def _create_header(self):
        header = QWidget()
        header.setObjectName("alarmsHeader")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        title = QLabel("Alarmlar")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "OKX Spot varlıkları için hedef fiyat "
            "bildirimlerini yönet."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.alarm_count_badge = QFrame()
        self.alarm_count_badge.setObjectName(
            "alarmCountBadge"
        )
        self.alarm_count_badge.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        badge_layout = QHBoxLayout(
            self.alarm_count_badge
        )
        badge_layout.setContentsMargins(
            12,
            7,
            12,
            7,
        )
        badge_layout.setSpacing(8)

        self.alarm_count_dot = QLabel()
        self.alarm_count_dot.setObjectName(
            "alarmCountDot"
        )
        self.alarm_count_dot.setFixedSize(8, 8)

        self.alarm_count_label = QLabel("0 alarm")
        self.alarm_count_label.setObjectName(
            "alarmCountText"
        )

        badge_layout.addWidget(self.alarm_count_dot)
        badge_layout.addWidget(self.alarm_count_label)

        layout.addLayout(title_layout, 1)
        layout.addWidget(
            self.alarm_count_badge,
            0,
            Qt.AlignTop | Qt.AlignRight,
        )

        return header

    def _create_form_card(self):
        card = Card(
            "alarmFormCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Yeni Alarm")
        title.setObjectName("formTitle")

        description = QLabel(
            "Coin kodu, hedef fiyat ve tetikleme "
            "koşulunu belirle."
        )
        description.setObjectName("formDescription")
        description.setWordWrap(True)

        form_layout = QHBoxLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(10)

        self.symbol_input = QLineEdit()
        self.symbol_input.setObjectName("symbolInput")
        self.symbol_input.setPlaceholderText("Coin: BTC")
        self.symbol_input.setMinimumHeight(42)
        self.symbol_input.setMinimumWidth(120)
        self.symbol_input.setMaximumWidth(180)
        self.symbol_input.setClearButtonEnabled(True)

        self.price_input = QLineEdit()
        self.price_input.setObjectName("priceInput")
        self.price_input.setPlaceholderText(
            "Hedef fiyat"
        )
        self.price_input.setMinimumHeight(42)
        self.price_input.setMinimumWidth(140)
        self.price_input.setMaximumWidth(210)
        self.price_input.setClearButtonEnabled(True)

        price_validator = QDoubleValidator(
            0.00000001,
            999999999999.0,
            8,
            self.price_input,
        )
        price_validator.setNotation(
            QDoubleValidator.StandardNotation
        )
        self.price_input.setValidator(
            price_validator
        )

        self.condition_button = QPushButton(
            "Fiyat Üstüne Çıkınca"
        )
        self.condition_button.setObjectName(
            "conditionButton"
        )
        self.condition_button.setMinimumHeight(42)
        self.condition_button.setMinimumWidth(190)
        self.condition_button.setCursor(
            Qt.PointingHandCursor
        )

        self.note_input = QLineEdit()
        self.note_input.setObjectName("noteInput")
        self.note_input.setPlaceholderText(
            "Alarm notu (isteğe bağlı)"
        )
        self.note_input.setMinimumHeight(42)
        self.note_input.setMinimumWidth(180)
        self.note_input.setMaxLength(
            alarm_service.MAX_NOTE_LENGTH
        )
        self.note_input.setClearButtonEnabled(True)

        self.add_button = QPushButton(
            "Alarm Oluştur"
        )
        self.add_button.setObjectName("addButton")
        self.add_button.setMinimumHeight(42)
        self.add_button.setMinimumWidth(130)
        self.add_button.setCursor(
            Qt.PointingHandCursor
        )

        form_layout.addWidget(self.symbol_input)
        form_layout.addWidget(self.price_input)
        form_layout.addWidget(
            self.condition_button
        )
        form_layout.addWidget(self.note_input, 1)
        form_layout.addWidget(self.add_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.hide()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(form_layout)
        layout.addWidget(self.status_label)

        return card

    def _create_table_card(self):
        card = Card(
            "alarmsTableCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        table_header = QWidget()
        table_header.setObjectName("tableHeader")

        header_layout = QHBoxLayout(table_header)
        header_layout.setContentsMargins(
            20,
            16,
            20,
            16,
        )
        header_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(3)

        title = QLabel("Fiyat Alarmları")
        title.setObjectName("tableTitle")

        description = QLabel(
            "Aktif, pasif ve tamamlanan alarm kayıtları"
        )
        description.setObjectName(
            "tableDescription"
        )

        title_layout.addWidget(title)
        title_layout.addWidget(description)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()

        self.table = QTableWidget()
        self.table.setObjectName("alarmsTable")
        self.table.setColumnCount(
            len(self.headers)
        )
        self.table.setHorizontalHeaderLabels(
            self.headers
        )

        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.table.setSelectionMode(
            QTableWidget.NoSelection
        )
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        horizontal_header = (
            self.table.horizontalHeader()
        )
        horizontal_header.setFocusPolicy(
            Qt.NoFocus
        )
        horizontal_header.setHighlightSections(
            False
        )
        horizontal_header.setStretchLastSection(
            False
        )

        horizontal_header.setSectionResizeMode(
            QHeaderView.Stretch
        )
        horizontal_header.setSectionResizeMode(
            4,
            QHeaderView.Interactive,
        )
        horizontal_header.setSectionResizeMode(
            self.TOGGLE_COLUMN,
            QHeaderView.Fixed,
        )
        horizontal_header.setSectionResizeMode(
            self.DELETE_COLUMN,
            QHeaderView.Fixed,
        )

        self.table.setColumnWidth(4, 240)
        self.table.setColumnWidth(
            self.TOGGLE_COLUMN,
            110,
        )
        self.table.setColumnWidth(
            self.DELETE_COLUMN,
            64,
        )

        vertical_header = self.table.verticalHeader()
        vertical_header.setVisible(False)
        vertical_header.setDefaultSectionSize(52)
        vertical_header.setMinimumSectionSize(52)
        vertical_header.setSectionResizeMode(
            QHeaderView.Fixed
        )

        layout.addWidget(table_header)
        layout.addWidget(self.table, 1)

        return card

    def _connect_signals(self):
        self.symbol_input.returnPressed.connect(
            self.create_alarm
        )
        self.price_input.returnPressed.connect(
            self.create_alarm
        )
        self.note_input.returnPressed.connect(
            self.create_alarm
        )
        self.condition_button.clicked.connect(
            self.toggle_condition
        )
        self.add_button.clicked.connect(
            self.create_alarm
        )
        self.table.cellClicked.connect(
            self.on_table_cell_clicked
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("alarmsPage")
            + label_style()
            + page_title_style()
            + primary_button_style("addButton")
            + scroll_bar_style()
            + f"""
            QWidget#alarmsHeader {{
                background: transparent;
                border: none;
            }}

            QFrame#alarmCountBadge {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 15px;
            }}

            QLabel#alarmCountDot {{
                background-color: {Theme.ACCENT};
                border-radius: 4px;
            }}

            QLabel#alarmCountText {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
            }}

            
            QLabel#formTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#formDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QLineEdit#symbolInput,
            QLineEdit#priceInput,
            QLineEdit#noteInput {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius:
                    {Theme.RADIUS_SMALL}px;
                padding: 0 13px;
                font-family:
                    "{Theme.FONT_FAMILY}";
                font-size: 13px;
                font-weight: 500;
                selection-background-color:
                    {Theme.ACCENT_SOFT};
            }}

            QLineEdit#symbolInput:hover,
            QLineEdit#priceInput:hover,
            QLineEdit#noteInput:hover {{
                border-color: {Theme.BORDER_HOVER};
            }}

            QLineEdit#symbolInput:focus,
            QLineEdit#priceInput:focus,
            QLineEdit#noteInput:focus {{
                border-color: {Theme.ACCENT};
            }}

            QPushButton#conditionButton {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-radius:
                    {Theme.RADIUS_SMALL}px;
                padding: 0 13px;
                text-align: left;
                font-family:
                    "{Theme.FONT_FAMILY}";
                font-size: 12px;
                font-weight: 600;
            }}

            QPushButton#conditionButton:hover {{
                background-color:
                    {Theme.CARD_BACKGROUND_HOVER};
                border-color: {Theme.BORDER_HOVER};
            }}

            QPushButton#conditionButton:pressed {{
                background-color: #1B2530;
                border-color: {Theme.ACCENT};
            }}

            QLabel#statusLabel {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 500;
            }}

            
            QWidget#tableHeader {{
                background-color: transparent;
                border: none;
                border-bottom:
                    1px solid {Theme.BORDER};
            }}

            QLabel#tableTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#tableDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
                font-weight: 400;
            }}

            QTableWidget#alarmsTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#alarmsTable::item {{
                color: {Theme.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                border-bottom:
                    1px solid {Theme.BORDER_SOFT};
                padding: 11px 10px;
            }}

            QTableWidget#alarmsTable::item:hover {{
                background-color:
                    {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView::section:horizontal {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                color: {Theme.TEXT_SECONDARY};
                border: none;
                border-bottom:
                    1px solid {Theme.BORDER};
                padding: 12px 9px;
                font-family:
                    "{Theme.FONT_FAMILY}";
                font-size: 11px;
                font-weight: 700;
            }}

            QHeaderView::section:horizontal:hover {{
                color: {Theme.TEXT_PRIMARY};
                background-color:
                    {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView::section:horizontal:pressed {{
                color: {Theme.TEXT_PRIMARY};
                background-color:
                    {Theme.CARD_BACKGROUND_HOVER};
            }}

            QTableCornerButton::section {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                border: none;
                border-bottom:
                    1px solid {Theme.BORDER};
            }}
            """
        )

    def toggle_condition(self):
        if (
            self.selected_condition
            == alarm_service.CONDITION_ABOVE
        ):
            self.selected_condition = (
                alarm_service.CONDITION_BELOW
            )
            self.condition_button.setText(
                "Fiyat Altına Düşünce"
            )
            return

        self.selected_condition = (
            alarm_service.CONDITION_ABOVE
        )
        self.condition_button.setText(
            "Fiyat Üstüne Çıkınca"
        )

    def reset_condition(self):
        self.selected_condition = (
            alarm_service.CONDITION_ABOVE
        )
        self.condition_button.setText(
            "Fiyat Üstüne Çıkınca"
        )

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
                alarm.get("is_active", False),
            )
            return

        if column == self.DELETE_COLUMN:
            self.delete_alarm(alarm_id)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_alarms()

    def set_status(
        self,
        message: str,
        error: bool = False,
    ):
        color = (
            Theme.ERROR
            if error
            else Theme.ACCENT
        )

        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            f"""
            color: {color};
            font-size: 12px;
            font-weight: 500;
            """
        )
        self.status_label.show()

    def clear_status(self):
        self.status_label.clear()
        self.status_label.hide()

    def create_alarm(self):
        normalized_symbol = normalize_symbol(
            self.symbol_input.text()
        )

        price_text = (
            self.price_input.text()
            .strip()
            .replace(",", ".")
        )

        note = self.note_input.text().strip()

        if not normalized_symbol:
            self.set_status(
                "Coin kodu boş olamaz.",
                error=True,
            )
            return

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

        if target_price <= 0:
            self.set_status(
                "Hedef fiyat sıfırdan büyük olmalıdır.",
                error=True,
            )
            return

        self.add_button.setEnabled(False)
        self.add_button.setText(
            "Kontrol ediliyor..."
        )

        try:
            success, result = (
                self.data_manager.okx
                .is_spot_symbol_available(
                    normalized_symbol
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
                    (
                        f"{normalized_symbol} OKX Spot "
                        "piyasasında bulunamadı."
                    ),
                    error=True,
                )
                return

            success, result = (
                alarm_service.create_alarm(
                    symbol=normalized_symbol,
                    target_price=target_price,
                    condition=self.selected_condition,
                    note=note,
                )
            )

            if not success:
                self.set_status(
                    str(result),
                    error=True,
                )
                return

            self.symbol_input.clear()
            self.price_input.clear()
            self.note_input.clear()
            self.reset_condition()

            self.set_status(
                (
                    f"{normalized_symbol} alarmı "
                    "oluşturuldu."
                )
            )
            self.load_alarms()

        except Exception as error:
            self.set_status(
                f"Alarm oluşturulamadı: {error}",
                error=True,
            )

        finally:
            self.add_button.setEnabled(True)
            self.add_button.setText(
                "Alarm Oluştur"
            )

    def toggle_alarm(
        self,
        alarm_id: int,
        current_status: bool,
    ):
        new_status = not current_status

        changed = alarm_service.change_alarm_status(
            alarm_id,
            new_status,
        )

        if changed:
            self.clear_status()
            self.load_alarms()
            return

        self.set_status(
            "Alarm durumu değiştirilemedi.",
            error=True,
        )

    def delete_alarm(self, alarm_id: int):
        removed = alarm_service.remove_alarm(
            alarm_id
        )

        if removed:
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

        active_count = 0

        try:
            for row, alarm in enumerate(alarms):
                if (
                    alarm.get("is_active")
                    and not alarm.get("is_triggered")
                ):
                    active_count += 1

                self._populate_alarm_row(
                    row,
                    alarm,
                )
        finally:
            self.table.setUpdatesEnabled(True)

        self.alarm_count_label.setText(
            f"{active_count} aktif alarm"
        )

        self.alarm_count_dot.setStyleSheet(
            f"""
            background-color: {
                Theme.ACCENT
                if active_count > 0
                else Theme.TEXT_MUTED
            };
            border-radius: 4px;
            """
        )

    def _populate_alarm_row(self, row, alarm):
        symbol = alarm.get("symbol", "")
        target_price = alarm.get(
            "target_price",
            0.0,
        )
        current_price = (
            self.data_manager.get_price(symbol)
        )

        self.table.setItem(
            row,
            0,
            self.create_item(
                symbol,
                color=Theme.TEXT_PRIMARY,
                bold=True,
            ),
        )

        self.table.setItem(
            row,
            1,
            self.create_item(
                self.format_price(target_price),
                color=Theme.TEXT_PRIMARY,
                bold=True,
            ),
        )

        condition = alarm.get("condition")

        condition_color = (
            Theme.ACCENT
            if condition
            == alarm_service.CONDITION_ABOVE
            else Theme.WARNING
        )

        self.table.setItem(
            row,
            2,
            self.create_item(
                alarm_service.get_condition_text(
                    condition
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
                color=(
                    Theme.ACCENT
                    if current_price
                    else Theme.TEXT_MUTED
                ),
                bold=True,
            ),
        )

        note = str(
            alarm.get("note", "") or ""
        ).strip()

        note_item = self.create_item(
            note if note else "-",
            color=(
                Theme.TEXT_SECONDARY
                if note
                else Theme.TEXT_MUTED
            ),
            bold=False,
            alignment=(
                Qt.AlignLeft | Qt.AlignVCenter
            ),
        )

        if note:
            note_item.setToolTip(note)

        self.table.setItem(
            row,
            4,
            note_item,
        )

        self.table.setItem(
            row,
            5,
            self.create_item(
                alarm_service.get_status_text(alarm),
                color=self.get_status_color(alarm),
                bold=True,
            ),
        )

        self.table.setItem(
            row,
            6,
            self.create_item(
                self.format_date(
                    alarm.get("created_at")
                ),
                color=Theme.TEXT_SECONDARY,
                bold=False,
            ),
        )

        toggle_text, toggle_color = (
            self.get_toggle_display(alarm)
        )

        toggle_item = self.create_item(
            toggle_text,
            color=toggle_color,
            bold=True,
        )

        if not alarm.get("is_triggered"):
            toggle_item.setToolTip(
                "Alarm durumunu değiştirmek için tıklayın."
            )

        self.table.setItem(
            row,
            self.TOGGLE_COLUMN,
            toggle_item,
        )

        delete_item = self.create_item(
            "Sil",
            color=Theme.ERROR,
            bold=True,
        )
        delete_item.setToolTip(
            "Alarmı silmek için tıklayın."
        )

        self.table.setItem(
            row,
            self.DELETE_COLUMN,
            delete_item,
        )

    @staticmethod
    def get_toggle_display(alarm):
        if alarm.get("is_triggered"):
            return "Tamamlandı", Theme.TEXT_MUTED

        if alarm.get("is_active"):
            return "Pasif Et", Theme.WARNING

        return "Aktif Et", Theme.ACCENT

    @staticmethod
    def create_item(
        text,
        color=Theme.TEXT_PRIMARY,
        bold=True,
        alignment=Qt.AlignCenter,
    ):
        item = QTableWidgetItem(str(text))
        item.setForeground(QColor(color))
        item.setTextAlignment(alignment)

        font = QFont(Theme.FONT_FAMILY, 10)
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
            return date_value.strftime(
                "%d.%m.%Y %H:%M"
            )
        except (TypeError, ValueError):
            return "-"

    @staticmethod
    def get_status_color(alarm):
        if alarm.get("is_triggered"):
            return Theme.TEXT_MUTED

        if alarm.get("is_active"):
            return Theme.ACCENT

        return Theme.WARNING