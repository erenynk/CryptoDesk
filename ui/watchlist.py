from datetime import datetime
from ui.widgets.card import Card
from ui.widgets.button import AppButton
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from ui.widgets.input import AppLineEdit
from ui.widgets.status_badge import StatusBadge
from ui.widgets.page_header import PageHeader
from ui.widgets.section_header import SectionHeader
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,    
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services import watchlist_service
from ui.theme import (
    Theme,
    label_style,
    page_style,
    page_title_style,
    scroll_bar_style,
)


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, text):
        super().__init__(text)


class WatchlistPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        self.headers = [
            "",
            "Varlık",
            "Anlık Fiyat",
            "Eklenme Fiyatı",
            "Değişim",
            "Eklenme Tarihi",
            "İşlem",
        ]

        self.setObjectName("watchlistPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFont(QFont(Theme.FONT_FAMILY, 10))

        self._build_ui()
        self._apply_styles()
        self._apply_watchlist_palette()
        self._connect_signals()

        self.load_symbols()

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

        add_card = self._create_add_card()
        main_layout.addWidget(add_card)

        table_card = self._create_table_card()
        main_layout.addWidget(table_card, 1)

    def _create_header(self):
        self.asset_count_badge = StatusBadge(
            text="0 varlık",
            status=StatusBadge.NEUTRAL,
            object_name="assetCountBadge",
        )

        return PageHeader(
            title="Watchlist",
            subtitle=(
                "Takip etmek istediğin OKX Spot "
                "varlıklarını yönet."
            ),
            right_widget=self.asset_count_badge,
            object_name="watchlistHeader",
        )

    def _create_add_card(self):
        card = Card(
            "addSymbolCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        title = QLabel("Varlık Ekle")
        title.setObjectName("addCardTitle")

        description = QLabel(
            "Coin kodunu gir. Yalnızca OKX Spot piyasasında "
            "bulunan varlıklar eklenebilir."
        )
        description.setObjectName("addCardDescription")
        description.setWordWrap(True)

        input_layout = QHBoxLayout()
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(10)

        self.symbol_input = AppLineEdit(
            placeholder="Örnek: BTC",
            object_name="symbolInput",
        )
        self.symbol_input.setClearButtonEnabled(True)

        self.add_button = AppButton(
            "Watchlist'e Ekle",
            variant=AppButton.PRIMARY,
            object_name="addButton",
        )

        input_layout.addWidget(self.symbol_input, 1)
        input_layout.addWidget(self.add_button)

        self.status_label = QLabel("")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.hide()

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addLayout(input_layout)
        layout.addWidget(self.status_label)

        return card

    def _create_table_card(self):
        card = Card(
            "watchlistTableCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        table_header = SectionHeader(
            title="Takip Edilen Varlıklar",
            description=(
                "Eklenme fiyatı ve güncel değişim bilgileri"
            ),
            object_name="watchlistSectionHeader",
        )

        self.table = QTableWidget()
        self.table.setObjectName("watchlistTable")
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.table.setSelectionMode(
            QTableWidget.NoSelection
        )
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        self.table.horizontalHeader().setObjectName(
            "watchlistTableHeader"
        )
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setHighlightSections(False)

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(56)
        self.table.verticalHeader().setMinimumSectionSize(52)
        self.table.verticalHeader().setSectionResizeMode(
            QHeaderView.Fixed
        )

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Fixed,
        )
        self.table.setColumnWidth(0, 54)

        for column in range(1, 6):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.Stretch,
            )

        self.table.horizontalHeader().setSectionResizeMode(
            6,
            QHeaderView.ResizeToContents,
        )

        layout.addWidget(table_header)
        layout.addWidget(self.table, 1)

        return card

    def _apply_watchlist_palette(self):
        add_card = self.findChild(QFrame, "addSymbolCard")
        table_card = self.findChild(QFrame, "watchlistTableCard")

        if add_card is not None:
            add_card.setStyleSheet(
                f"""
                QFrame#addSymbolCard {{
                    background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0B141D,
                    stop: 0.55 #0D1822,
                    stop: 1 #101C27
                );
                    border: 1px solid #253542;
                    border-radius: {Theme.RADIUS_LARGE}px;
                }}
                """
            )

        if table_card is not None:
            table_card.setStyleSheet(
                f"""
                QFrame#watchlistTableCard {{
                    background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                    border: 1px solid #253542;
                    border-radius: {Theme.RADIUS_LARGE}px;
                }}
                """
            )

    def _connect_signals(self):
        self.symbol_input.returnPressed.connect(
            self.add_symbol
        )
        self.add_button.clicked.connect(
            self.add_symbol
        )
        self.table.cellClicked.connect(
            self.on_table_cell_clicked
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("watchlistPage")
            + label_style()
            + page_title_style()
                    + scroll_bar_style()
            + f"""
            

                        
            QWidget#watchlistPage {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #101923,
                    stop: 0.55 #14202B,
                    stop: 1 #182631
                );
            }}

            QLabel#addCardTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 800;
            }}

            QLabel#addCardDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}
                   
                       
            QLabel#statusLabel {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 500;
            }}

            
            
            QTableWidget#watchlistTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#watchlistTable::item {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER_SOFT};
                padding: 11px 12px;
            }}

            

            QHeaderView#watchlistTableHeader {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                border: none;
                border-bottom: 1px solid #253542;
            }}

            QHeaderView#watchlistTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 15px 14px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 700;
            }}

            QHeaderView::section:horizontal:hover {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView::section:horizontal:pressed {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QTableCornerButton::section {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                border: none;
                border-bottom: 1px solid #253542;
            }}
            """
        )

    def on_table_cell_clicked(self, row, column):
        if column != 6:
            return

        item = self.table.item(row, 1)

        if item is None:
            return

        symbol = item.text().strip()

        if symbol:
            self.remove_symbol(symbol)

    def showEvent(self, event):
        super().showEvent(event)
        self.load_symbols()

    def set_status(self, message, error=False):
        self.status_label.setText(message)
        self.status_label.setStyleSheet(
            f"""
            color: {
                Theme.ERROR
                if error
                else Theme.TEXT_SECONDARY
            };
            font-size: 12px;
            font-weight: 500;
            """
        )
        self.status_label.show()

    def clear_status(self):
        self.status_label.clear()
        self.status_label.hide()

    def add_symbol(self):
        raw_symbol = self.symbol_input.text()
        normalized = watchlist_service.normalize_symbol(
            raw_symbol
        )

        if not normalized:
            self.set_status(
                "Coin adı boş olamaz.",
                error=True,
            )
            return

        self.add_button.setEnabled(False)
        self.add_button.setText("Kontrol ediliyor...")

        try:
            success, result = (
                self.data_manager.okx
                .is_spot_symbol_available(normalized)
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
                        f"{normalized} OKX Spot piyasasında "
                        "bulunamadı."
                    ),
                    error=True,
                )
                return

            current_price = self.data_manager.get_price(
                normalized
            )

            added = watchlist_service.add_symbol(
                normalized,
                current_price,
            )

            if added:
                self.symbol_input.clear()
                self.clear_status()
                self.load_symbols()
                return

            self.set_status(
                f"{normalized} zaten watchlist'te.",
                error=True,
            )

        except Exception as error:
            self.set_status(
                f"Coin kontrol edilemedi: {error}",
                error=True,
            )

        finally:
            self.add_button.setEnabled(True)
            self.add_button.setText("Watchlist'e Ekle")

    def remove_symbol(self, symbol):
        removed = watchlist_service.remove_symbol(symbol)

        if removed:
            self.clear_status()
            self.load_symbols()
            return

        self.set_status(
            f"{symbol} silinemedi.",
            error=True,
        )

    @staticmethod
    def format_price(price):
        if price is None or price <= 0:
            return "-"

        if price >= 1:
            return f"${price:,.2f}"

        return f"${price:,.4f}"

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
    def format_change(current_price, added_price):
        if (
            not current_price
            or not added_price
            or added_price <= 0
        ):
            return "-", Theme.TEXT_MUTED

        change = (
            (current_price - added_price)
            / added_price
        ) * 100

        if change >= 0:
            return (
                f"+{change:.2f}%",
                Theme.ACCENT,
            )

        return (
            f"{change:.2f}%",
            Theme.ERROR,
        )

    @staticmethod
    def make_item(
        text,
        color=Theme.TEXT_PRIMARY,
        bold=True,
        alignment=Qt.AlignCenter,
    ):
        item = NumericTableWidgetItem(str(text))
        item.setForeground(QColor(color))
        item.setTextAlignment(alignment)

        font = QFont(Theme.FONT_FAMILY, 10)
        font.setBold(bold)
        item.setFont(font)

        return item

    def load_symbols(self):
        items = watchlist_service.get_items()

        self.table.setUpdatesEnabled(False)
        self.table.setRowCount(len(items))

        for row, item in enumerate(items):
            index_item = self.make_item(
                str(row + 1),
                color=Theme.TEXT_MUTED,
            )

            symbol = watchlist_service.normalize_symbol(
                item.get("symbol", "")
            )

            current_price = self.data_manager.get_price(
                symbol
            )
            added_price = item.get("added_price")
            created_at = item.get("created_at")

            change_text, change_color = (
                self.format_change(
                    current_price,
                    added_price,
                )
            )

            self.table.setItem(
                row,
                0,
                index_item,
            )

            self.table.setItem(
                row,
                1,
                self.make_item(
                    symbol,
                    color=Theme.TEXT_PRIMARY,
                ),
            )

            self.table.setItem(
                row,
                2,
                self.make_item(
                    self.format_price(current_price),
                    color=Theme.ACCENT,
                ),
            )

            self.table.setItem(
                row,
                3,
                self.make_item(
                    self.format_price(added_price),
                    color=Theme.TEXT_PRIMARY,
                ),
            )

            self.table.setItem(
                row,
                4,
                self.make_item(
                    change_text,
                    color=change_color,
                ),
            )

            self.table.setItem(
                row,
                5,
                self.make_item(
                    self.format_date(created_at),
                    color=Theme.TEXT_SECONDARY,
                ),
            )

            self.table.setItem(
                row,
                6,
                self.make_item(
                    "Kaldır",
                    color=Theme.ERROR,
                ),
            )

        self.table.setUpdatesEnabled(True)

        count = len(items)

        self.asset_count_badge.set_status(
            f"{count} varlık",
            (
                StatusBadge.SUCCESS
                if count > 0
                else StatusBadge.NEUTRAL
            ),
        )