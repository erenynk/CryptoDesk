from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from ui.widgets.card import Card
from ui.widgets.page_header import PageHeader
from ui.widgets.button import AppButton
from ui.widgets.section_header import SectionHeader
from ui.widgets.status_badge import StatusBadge
from PySide6.QtWidgets import (
    QCheckBox,
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

from services.data_worker import PortfolioRefreshWorker
from ui.theme import (
    Theme,
    checkbox_style,
    label_style,
    page_style,
    page_title_style,    
    scroll_bar_style,
)


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value, display_text):
        super().__init__(display_text)

        self.value = value

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
            "Varlık",
            "Toplam Değer",
            "Anlık Fiyat",
            "Toplam Miktar",
            "Kullanılabilir Miktar",
        ]

        self.setObjectName("portfolioPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFont(QFont(Theme.FONT_FAMILY, 10))

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self._configure_refresh_timer()

        QTimer.singleShot(100, self.start_page)

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        self.main_layout.setSpacing(20)

        self.header = self._create_header()
        self.main_layout.addWidget(self.header)

        self.summary_card = self._create_summary_card()
        self.main_layout.addWidget(self.summary_card)

        self.table_card = self._create_table_card()
        self.main_layout.addWidget(self.table_card, 1)

    def _create_header(self):
        controls = QWidget()
        controls.setObjectName("portfolioHeaderControls")

        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        self.hide_dust_checkbox = QCheckBox(
            "Küçük Bakiyeleri Gizle (< $1)"
        )
        self.hide_dust_checkbox.setObjectName(
            "hideDustCheckbox"
        )

        self.refresh_button = AppButton(
            "Bakiyeleri Yenile",
            variant=AppButton.PRIMARY,
            object_name="refreshButton",
        )

        controls_layout.addWidget(self.hide_dust_checkbox)
        controls_layout.addWidget(self.refresh_button)

        return PageHeader(
            title="Portfolio",
            subtitle=(
                "Funding ve Trading hesaplarındaki "
                "varlıklarını yönet."
            ),
            right_widget=controls,
            object_name="portfolioHeader",
        )

    def _create_summary_card(self):
        card = Card(
            "portfolioSummaryCard",
            hover=False,
            radius=Theme.RADIUS_XLARGE,
        )
        card.setMinimumHeight(150)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(24)

        balance_layout = QVBoxLayout()
        balance_layout.setContentsMargins(0, 0, 0, 0)
        balance_layout.setSpacing(7)

        title = QLabel("TOPLAM PORTFÖY DEĞERİ")
        title.setObjectName("summaryLabel")

        self.total_balance_label = QLabel("$0.00 USDT")
        self.total_balance_label.setObjectName("summaryValue")
        self.total_balance_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.asset_count_label = QLabel(
            "0 farklı kripto varlık listeleniyor"
        )
        self.asset_count_label.setObjectName("summaryDescription")

        balance_layout.addWidget(title)
        balance_layout.addWidget(self.total_balance_label)
        balance_layout.addWidget(self.asset_count_label)

        self.connection_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="portfolioConnectionBadge",
        )

        
        

        layout.addLayout(balance_layout, 1)
        layout.addWidget(
            self.connection_badge,
            0,
            Qt.AlignTop | Qt.AlignRight,
        )

        return card

    def _create_table_card(self):
        card = Card(
            "portfolioTableCard",
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

        table_header = SectionHeader(
            title="Varlık Dağılımı",
            description=(
                "Portföyündeki tüm spot varlıkların "
                "güncel görünümü"
            ),
            object_name="portfolioSectionHeader",
        )

        self.table = QTableWidget()
        self.table.setObjectName("portfolioTable")
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1,
            QHeaderView.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            2,
            QHeaderView.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            3,
            QHeaderView.Stretch,
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4,
            QHeaderView.Stretch,
        )

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(52)

        layout.addWidget(table_header)
        layout.addWidget(self.table, 1)

        return card

    def _connect_signals(self):
        self.hide_dust_checkbox.stateChanged.connect(
            self.update_table_view
        )

        self.refresh_button.clicked.connect(
            self.load_balances
        )

        self.table.horizontalHeader().sortIndicatorChanged.connect(
            self.on_sort_indicator_changed
        )

    def _configure_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        self.refresh_timer.timeout.connect(
            self.load_balances
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("portfolioPage")
            + label_style()
            + page_title_style()
            + checkbox_style("hideDustCheckbox")            
            + scroll_bar_style()
            + f"""
           

            
            QLabel#summaryLabel {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#summaryValue {{
                color: {Theme.ACCENT};
                font-size: 34px;
                font-weight: 700;
            }}

            QLabel#summaryDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

                       
            
            QTableWidget#portfolioTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-bottom-left-radius: {Theme.RADIUS_LARGE}px;
                border-bottom-right-radius: {Theme.RADIUS_LARGE}px;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#portfolioTable::item {{
                color: {Theme.TEXT_PRIMARY};
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER_SOFT};
                padding: 11px 12px;
            }}

            QTableWidget#portfolioTable::item:hover {{
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QTableWidget#portfolioTable::item:selected {{
                color: {Theme.TEXT_PRIMARY};
                background-color: #1B2530;
                border: none;
            }}

            QHeaderView::section:horizontal {{
                background-color: {Theme.CARD_BACKGROUND_SECONDARY};
                color: {Theme.TEXT_SECONDARY};
                border: none;
                border-bottom: 1px solid {Theme.BORDER};
                padding: 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 11px;
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

            QHeaderView::down-arrow,
            QHeaderView::up-arrow {{
                image: none;
                width: 0;
                height: 0;
            }}

            QTableCornerButton::section {{
                background-color: {Theme.CARD_BACKGROUND_SECONDARY};
                border: none;
                border-bottom: 1px solid {Theme.BORDER};
            }}
            """
        )

    def on_sort_indicator_changed(self, logical_index, order):
        if logical_index < 0:
            return

        for index in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(index)

            if header_item is None:
                continue

            if index == logical_index:
                arrow = (
                    " ▲"
                    if order == Qt.AscendingOrder
                    else " ▼"
                )
                header_item.setText(
                    self.headers[index] + arrow
                )
            else:
                header_item.setText(self.headers[index])

    def start_page(self):
        self.load_balances()
        self.refresh_timer.start()

    def load_balances(self):
        if self.data_manager.loading:
            return

        if self.worker is not None and self.worker.isRunning():
            return

        self._set_loading_state()

        self.worker = PortfolioRefreshWorker(
            self.data_manager
        )
        self.worker.result_ready.connect(
            self.on_balances_loaded
        )
        self.worker.result_ready.connect(
            self.worker.deleteLater
        )
        self.worker.start()

    def on_balances_loaded(self, success, result):
        if success:
            portfolio = (
                self.data_manager.get_portfolio()
                or result
            )

            total = float(
                portfolio.get("total_usdt", 0.0)
            )

            self.total_balance_label.setText(
                f"${total:,.2f} USDT"
            )

            self.raw_assets_data = portfolio.get(
                "assets",
                [],
            )

            self.update_table_view()
            self._set_connected_state()

        else:
            self.total_balance_label.setText(
                "Bağlantı Hatası"
            )
            self._set_error_state()

            print(
                "Portfolio refresh error:",
                result,
            )

        self.refresh_button.setEnabled(True)
        self.refresh_button.setText(
            "Bakiyeleri Yenile"
        )

        self.worker = None

    def _set_loading_state(self):
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Güncelleniyor...")

        self.connection_badge.set_status(
            "Güncelleniyor",
            StatusBadge.WARNING,
        )

    def _set_connected_state(self):
        self.connection_badge.set_status(
            "API Bağlı",
            StatusBadge.SUCCESS,
        )

    def _set_error_state(self):
        self.connection_badge.set_status(
            "Bağlantı Hatası",
            StatusBadge.ERROR,
        )

    @staticmethod
    def format_amount(value):
        if value == 0:
            return "0"

        text = f"{value:.4f}".rstrip("0").rstrip(".")

        return text if text else "0"

    @staticmethod
    def format_price(price):
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
            if not (
                hide_dust
                and asset.get("usdt_value", 0.0) < 1
            )
        ]

        self.table.setRowCount(len(visible_assets))

        for row, asset in enumerate(visible_assets):
            coin_item = QTableWidgetItem(
                asset.get("coin", "")
            )
            coin_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            coin_item.setTextAlignment(
                Qt.AlignCenter
            )

            coin_font = coin_item.font()
            coin_font.setBold(True)
            coin_item.setFont(coin_font)

            total_item = NumericTableWidgetItem(
                asset.get("total", 0.0),
                self.format_amount(
                    asset.get("total", 0.0)
                ),
            )

            available_item = NumericTableWidgetItem(
                asset.get("available", 0.0),
                self.format_amount(
                    asset.get("available", 0.0)
                ),
            )

            price_item = NumericTableWidgetItem(
                asset.get("price", 0.0),
                self.format_price(
                    asset.get("price", 0.0)
                ),
            )

            value_item = NumericTableWidgetItem(
                asset.get("usdt_value", 0.0),
                (
                    f"${asset.get('usdt_value', 0.0):,.2f}"
                ),
            )

            total_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )
            available_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )
            price_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            value_item.setForeground(
                QColor(Theme.ACCENT)
            )

            for item in (
                total_item,
                available_item,
                price_item,
                value_item,
            ):
                item.setTextAlignment(Qt.AlignCenter)

                item_font = item.font()
                item_font.setBold(True)
                item.setFont(item_font)

            self.table.setItem(row, 0, coin_item)
            self.table.setItem(row, 1, value_item)
            self.table.setItem(row, 2, price_item)
            self.table.setItem(row, 3, total_item)
            self.table.setItem(row, 4, available_item)

        self.asset_count_label.setText(
            f"{len(visible_assets)} farklı kripto varlık listeleniyor"
        )

        sort_column = (
            self.table.horizontalHeader()
            .sortIndicatorSection()
        )

        sort_order = (
            self.table.horizontalHeader()
            .sortIndicatorOrder()
        )

        self.on_sort_indicator_changed(
            sort_column,
            sort_order,
        )

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def closeEvent(self, event):
        self.refresh_timer.stop()

        if (
            self.worker is not None
            and self.worker.isRunning()
        ):
            self.worker.quit()
            self.worker.wait(3000)

        super().closeEvent(event)