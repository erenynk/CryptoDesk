import threading
from datetime import datetime
from typing import Any

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.trade_history_service import TradeHistoryService
from ui.dashboard import ElevatedInnerPanel
from ui.theme import Theme, scroll_bar_style
from ui.widgets.button import AppButton
from ui.widgets.input import AppLineEdit
from ui.widgets.page_header import PageHeader
from ui.widgets.section_header import SectionHeader
from ui.widgets.status_badge import StatusBadge


class TradeHistorySyncSignals(QObject):
    result_ready = Signal(bool, object)


class TradeHistoryPage(QWidget):
    HEADERS = [
        "",
        "VARLIK",
        "İŞLEM",
        "MİKTAR",
        "FİYAT",
        "TOPLAM",
        "PNL",
        "TARİH",
    ]

    SORT_KEYS = {
        1: "coin",
        2: "side",
        3: "quantity",
        4: "price",
        5: "total_usdt",
        6: "pnl_usdt",
        7: "executed_at_ms",
    }

    ROW_HEIGHT = 74
    NUMBER_COLUMN = 0
    ASSET_COLUMN = 1
    SIDE_COLUMN = 2
    QUANTITY_COLUMN = 3
    PRICE_COLUMN = 4
    TOTAL_COLUMN = 5
    PNL_COLUMN = 6
    DATE_COLUMN = 7

    def __init__(self, data_manager, trade_service=None):
        super().__init__()

        self.data_manager = data_manager
        self.trade_service = trade_service or TradeHistoryService()
        self._all_transactions = []
        self._sort_column = self.DATE_COLUMN
        self._sort_descending = True
        self._sync_in_progress = False
        self._initial_sync_checked = False
        self._shutting_down = False
        self._sync_thread = None

        self._sync_signals = TradeHistorySyncSignals(self)
        self._sync_signals.result_ready.connect(
            self._on_sync_finished
        )

        self.setObjectName("tradeHistoryPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFont(QFont(Theme.FONT_FAMILY, 10))

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self.load_transactions()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        main_layout.setSpacing(20)

        self.count_badge = StatusBadge(
            text="0 işlem",
            status=StatusBadge.NEUTRAL,
            object_name="tradeHistoryCountBadge",
        )

        header = PageHeader(
            title="İşlem Geçmişi",
            subtitle=(
                "OKX Spot Trading hesabındaki gerçekleşmiş "
                "alım ve satım işlemlerini incele."
            ),
            right_widget=self.count_badge,
            object_name="tradeHistoryHeader",
        )
        main_layout.addWidget(header)

        table_card = self._create_table_card()
        main_layout.addWidget(table_card, 1)

    def _create_table_card(self):
        card = ElevatedInnerPanel(
            "tradeHistoryTableCard",
            radius=18,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 12)
        layout.setSpacing(0)

        controls = QWidget()
        controls.setObjectName("tradeHistoryControls")
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(10)

        self.coin_filter = AppLineEdit(
            placeholder="Coin filtrele: BTC",
            object_name="tradeHistoryCoinFilter",
        )
        self.coin_filter.setClearButtonEnabled(True)
        self.coin_filter.setMinimumWidth(170)
        self.coin_filter.setMaximumWidth(210)

        self.refresh_button = AppButton(
            "Yenile",
            variant=AppButton.SECONDARY,
            object_name="tradeHistoryRefreshButton",
        )
        self.refresh_button.setMinimumWidth(96)

        controls_layout.addWidget(self.coin_filter)
        controls_layout.addWidget(self.refresh_button)

        section_header = SectionHeader(
            title="Gerçekleşen İşlemler",
            description="Trading hesabındaki USDT spot işlemleri",
            right_widget=controls,
            object_name="tradeHistorySectionHeader",
        )
        section_header.title_label.setStyleSheet(
            f"""
            color: {Theme.TEXT_PRIMARY};
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 18px;
            font-weight: 800;
            """
        )

        self.status_label = QLabel("")
        self.status_label.setObjectName("tradeHistoryStatusLabel")
        self.status_label.setWordWrap(True)
        self.status_label.hide()

        self.table = QTableWidget()
        self.table.setObjectName("tradeHistoryTable")
        self.table.setColumnCount(len(self.HEADERS))
        self.table.setHorizontalHeaderLabels(self.HEADERS)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        header = self.table.horizontalHeader()
        header.setObjectName("tradeHistoryTableHeader")
        header.setFocusPolicy(Qt.NoFocus)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setSectionsClickable(True)
        header.setSortIndicatorShown(False)

        header.setSectionResizeMode(
            self.NUMBER_COLUMN,
            QHeaderView.Fixed,
        )
        self.table.setColumnWidth(
            self.NUMBER_COLUMN,
            64,
        )

        for column in range(1, len(self.HEADERS)):
            header.setSectionResizeMode(
                column,
                QHeaderView.Stretch,
            )

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(
            self.ROW_HEIGHT
        )
        self.table.verticalHeader().setMinimumSectionSize(
            self.ROW_HEIGHT
        )

        layout.addWidget(section_header)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, 1)

        self._update_header_labels()
        return card

    def _connect_signals(self):
        self.coin_filter.textChanged.connect(
            self._apply_filter_and_sort
        )
        self.refresh_button.clicked.connect(
            self.refresh_from_okx
        )
        self.table.horizontalHeader().sectionClicked.connect(
            self._on_header_clicked
        )

    def _apply_styles(self):
        self.setStyleSheet(
            f"""
            QWidget#tradeHistoryPage {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #172630,
                    stop: 0.50 #13212B,
                    stop: 1 #101923
                );
            }}

            QWidget#tradeHistoryControls {{
                background: transparent;
                border: none;
            }}

            QLabel#tradeHistoryStatusLabel {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 10px 20px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 12px;
                font-weight: 500;
            }}

            QTableWidget#tradeHistoryTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-bottom-left-radius:
                    {Theme.RADIUS_LARGE}px;
                border-bottom-right-radius:
                    {Theme.RADIUS_LARGE}px;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#tradeHistoryTable::item {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER_SOFT};
                padding: 14px 12px;
            }}

            QWidget#tradeHistoryPnlCell {{
                background: transparent;
                border: none;
            }}

            QHeaderView#tradeHistoryTableHeader {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: none;
                border-bottom: 1px solid #293B46;
            }}

            QHeaderView#tradeHistoryTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 14px 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 1px;
            }}

            QHeaderView#tradeHistoryTableHeader::section:horizontal:hover {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView#tradeHistoryTableHeader::section:horizontal:pressed {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView#tradeHistoryTableHeader::down-arrow,
            QHeaderView#tradeHistoryTableHeader::up-arrow {{
                image: none;
                width: 0;
                height: 0;
            }}

            QTableCornerButton::section {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: none;
                border-bottom: 1px solid #293B46;
            }}

            {scroll_bar_style()}
            """
        )

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            number = float(value)
            if number != number:
                return 0.0
            return number
        except (TypeError, ValueError, OverflowError):
            return 0.0

    @staticmethod
    def _format_quantity(value: Any) -> str:
        number = TradeHistoryPage._safe_float(value)

        if number == 0:
            return "0"

        digits = 4 if abs(number) >= 1 else 8
        return (
            f"{number:,.{digits}f}"
            .rstrip("0")
            .rstrip(".")
        )

    @staticmethod
    def _format_price(value: Any) -> str:
        number = TradeHistoryPage._safe_float(value)

        if number >= 1:
            return f"${number:,.2f}"
        if number > 0:
            return f"${number:,.6f}"
        return "$0.00"

    @staticmethod
    def _format_total(value: Any) -> str:
        number = TradeHistoryPage._safe_float(value)
        return f"${number:,.2f}"

    @staticmethod
    def _format_date(transaction: dict[str, Any]) -> str:
        raw_value = str(
            transaction.get("executed_at", "")
        ).strip()

        if raw_value:
            try:
                parsed = datetime.fromisoformat(raw_value)
                return parsed.strftime("%d.%m.%Y %H:%M:%S")
            except ValueError:
                pass

        return ""

    def load_transactions(self):
        if self._shutting_down:
            return

        try:
            self._all_transactions = list(
                self.trade_service.get_transactions(
                    sort_by="executed_at_ms",
                    descending=True,
                )
            )
            self._clear_status()
        except Exception as error:
            self._all_transactions = []
            self._set_status(
                f"İşlem geçmişi okunamadı: {error}",
                error=True,
            )

        self._apply_filter_and_sort()

    def _filtered_transactions(self):
        query = self.coin_filter.text().strip().upper()

        if not query:
            return list(self._all_transactions)

        return [
            transaction
            for transaction in self._all_transactions
            if query in str(
                transaction.get("coin", "")
            ).upper()
        ]

    def _sort_value(self, transaction: dict[str, Any]):
        key = self.SORT_KEYS[self._sort_column]
        value = transaction.get(key)

        if key in {"coin", "side"}:
            return str(value or "").upper()

        if key == "executed_at_ms":
            return int(self._safe_float(value))

        if value is None:
            return None

        return self._safe_float(value)

    def _sorted_transactions(self, transactions):
        if self._sort_column == self.PNL_COLUMN:
            known = [
                item
                for item in transactions
                if item.get("pnl_usdt") is not None
            ]
            unknown = [
                item
                for item in transactions
                if item.get("pnl_usdt") is None
            ]
            known.sort(
                key=self._sort_value,
                reverse=self._sort_descending,
            )
            return known + unknown

        return sorted(
            transactions,
            key=self._sort_value,
            reverse=self._sort_descending,
        )

    def _apply_filter_and_sort(self, *_args):
        visible = self._sorted_transactions(
            self._filtered_transactions()
        )
        self._populate_table(visible)
        self.count_badge.set_text(
            f"{len(visible)} işlem"
        )

    def _populate_table(self, transactions):
        self.table.setUpdatesEnabled(False)

        # QTableWidget aynı satır sayısıyla yeniden doldurulduğunda
        # önceki setCellWidget() içerikleri hücrelerde kalabilir.
        # Satırları sıfırlamak eski PnL widget'larını tamamen kaldırır
        # ve alış satırlarının PnL hücresinin gerçekten boş kalmasını
        # garanti eder.
        self.table.setRowCount(0)
        self.table.setRowCount(len(transactions))

        for row, transaction in enumerate(transactions):
            number_item = QTableWidgetItem(str(row + 1))
            number_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )

            coin = str(
                transaction.get("coin", "")
            ).strip().upper()
            side = str(
                transaction.get("side", "")
            ).strip().lower()

            coin_item = QTableWidgetItem(coin)
            coin_item.setForeground(QColor(Theme.TEXT_PRIMARY))
            coin_font = coin_item.font()
            coin_font.setBold(True)
            coin_item.setFont(coin_font)

            side_text = (
                "ALIŞ"
                if side == "buy"
                else "SATIŞ"
                if side == "sell"
                else side.upper()
            )
            side_item = QTableWidgetItem(side_text)
            side_item.setForeground(
                QColor(
                    Theme.ACCENT
                    if side == "buy"
                    else (
                        Theme.ERROR
                        if side == "sell"
                        else Theme.TEXT_SECONDARY
                    )
                )
            )

            quantity_item = QTableWidgetItem(
                self._format_quantity(
                    transaction.get("quantity")
                )
            )
            quantity_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )

            price_item = QTableWidgetItem(
                self._format_price(
                    transaction.get("price")
                )
            )
            price_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )

            total_item = QTableWidgetItem(
                self._format_total(
                    transaction.get("total_usdt")
                )
            )
            total_item.setForeground(QColor(Theme.ACCENT))

            pnl_item = QTableWidgetItem("")

            date_item = QTableWidgetItem(
                self._format_date(transaction)
            )
            date_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )

            items = (
                number_item,
                coin_item,
                side_item,
                quantity_item,
                price_item,
                total_item,
                pnl_item,
                date_item,
            )

            for column, item in enumerate(items):
                item.setTextAlignment(Qt.AlignCenter)

                if column in (
                    self.ASSET_COLUMN,
                    self.SIDE_COLUMN,
                    self.QUANTITY_COLUMN,
                    self.PRICE_COLUMN,
                    self.TOTAL_COLUMN,
                    self.DATE_COLUMN,
                ):
                    item_font = item.font()
                    item_font.setBold(True)
                    item.setFont(item_font)

                self.table.setItem(row, column, item)

            pnl_usdt = transaction.get("pnl_usdt")
            pnl_percent = transaction.get("pnl_percent")

            if (
                side == "sell"
                and isinstance(pnl_usdt, (int, float))
                and isinstance(pnl_percent, (int, float))
            ):
                self.table.setCellWidget(
                    row,
                    self.PNL_COLUMN,
                    self._create_pnl_widget(
                        float(pnl_percent),
                        float(pnl_usdt),
                    ),
                )

        self.table.setUpdatesEnabled(True)

    def _create_pnl_widget(
        self,
        pnl_percent: float,
        pnl_usdt: float,
    ):
        widget = QWidget()
        widget.setObjectName("tradeHistoryPnlCell")

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        percent_label = QLabel(f"{pnl_percent:+.2f}%")
        usdt_label = QLabel(f"{pnl_usdt:+,.2f} USDT")

        color = Theme.ACCENT if pnl_usdt >= 0 else Theme.ERROR
        shared_style = f"""
            color: {color};
            font-size: 12px;
            font-weight: 700;
            font-family: "{Theme.FONT_FAMILY}";
        """

        for label in (percent_label, usdt_label):
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet(shared_style)
            layout.addWidget(label)

        return widget

    def _on_header_clicked(self, column):
        if column == self.NUMBER_COLUMN:
            return

        if column not in self.SORT_KEYS:
            return

        if column == self._sort_column:
            self._sort_descending = not self._sort_descending
        else:
            self._sort_column = column
            self._sort_descending = True

        self._update_header_labels()
        self._apply_filter_and_sort()

    def _update_header_labels(self):
        for column, base_text in enumerate(self.HEADERS):
            item = self.table.horizontalHeaderItem(column)

            if item is None:
                continue

            if column == self._sort_column:
                arrow = " ▼" if self._sort_descending else " ▲"
                item.setText(base_text + arrow)
            else:
                item.setText(base_text)

    def refresh_from_okx(self):
        if self._shutting_down or self._sync_in_progress:
            return

        if getattr(self.data_manager, "loading", False):
            self._set_status(
                (
                    "Portföy verileri şu anda yenileniyor. "
                    "İşlem geçmişini biraz sonra tekrar yenile."
                )
            )
            return

        portfolio = self.data_manager.get_portfolio() or {}
        current_assets = list(
            portfolio.get("assets", []) or []
        )

        self._sync_in_progress = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Güncelleniyor...")
        self._set_status(
            "OKX işlem geçmişi güncelleniyor..."
        )

        def run_sync():
            try:
                success, result = self.trade_service.sync_from_okx(
                    self.data_manager.okx,
                    current_assets=current_assets,
                    force_refresh=True,
                )
            except Exception as error:
                success = False
                result = str(error)

            try:
                self._sync_signals.result_ready.emit(
                    bool(success),
                    result,
                )
            except RuntimeError:
                return

        self._sync_thread = threading.Thread(
            target=run_sync,
            name="CaspianTradeHistorySync",
            daemon=True,
        )
        self._sync_thread.start()

    def _on_sync_finished(self, success, result):
        if self._shutting_down:
            return

        self._sync_in_progress = False
        self._sync_thread = None
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Yenile")

        if success:
            self.load_transactions()
            return

        self._set_status(
            f"İşlem geçmişi güncellenemedi: {result}",
            error=True,
        )

    def _set_status(self, message, error=False):
        color = Theme.ERROR if error else Theme.TEXT_SECONDARY
        self.status_label.setText(str(message))
        self.status_label.setStyleSheet(
            f"""
            background: transparent;
            color: {color};
            border: none;
            padding: 10px 20px;
            font-family: "{Theme.FONT_FAMILY}";
            font-size: 12px;
            font-weight: 500;
            """
        )
        self.status_label.show()

    def _clear_status(self):
        self.status_label.clear()
        self.status_label.hide()

    def _initial_sync_if_needed(self):
        if self._shutting_down or self._initial_sync_checked:
            return

        self._initial_sync_checked = True

        if self._all_transactions:
            return

        self.refresh_from_okx()

    def showEvent(self, event):
        super().showEvent(event)
        self.load_transactions()

        if not self._initial_sync_checked:
            QTimer.singleShot(
                250,
                self._initial_sync_if_needed,
            )

    def shutdown(self):
        self._shutting_down = True
