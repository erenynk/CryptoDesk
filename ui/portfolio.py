from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
)
from ui.dashboard import ElevatedInnerPanel
from ui.widgets.page_header import PageHeader
from ui.widgets.button import AppButton
from ui.widgets.section_header import SectionHeader
from ui.widgets.status_badge import StatusBadge
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
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
        self._shutting_down = False
        self.raw_assets_data = []

        self.headers = [
            "",
            "VARLIK",
            "TOPLAM DEĞER",
            "ANLIK FİYAT",
            "TOPLAM MİKTAR",
            "PNL",
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
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("portfolioScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.content_widget = QWidget()
        self.content_widget.setObjectName("portfolioContent")

        self.main_layout = QVBoxLayout(self.content_widget)
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
        self.main_layout.addWidget(self.table_card)

        self.trading_table_card = self._create_trading_table_card()
        self.main_layout.addWidget(self.trading_table_card)

        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area)

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
        card = ElevatedInnerPanel(
            "portfolioSummaryCard",
            radius=18,
        )
        card.setMinimumHeight(176)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(24)

        balance_layout = QVBoxLayout()
        balance_layout.setContentsMargins(0, 0, 0, 0)
        balance_layout.setSpacing(7)

        title = QLabel("TOPLAM PORTFÖY DEĞERİ")
        title.setObjectName("summaryLabel")

        self.total_balance_label = QLabel("$0.00")
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

        pnl_container = QWidget()
        pnl_container.setObjectName("dailyPnlContainer")

        pnl_layout = QVBoxLayout(pnl_container)
        pnl_layout.setContentsMargins(0, 0, 0, 0)
        pnl_layout.setSpacing(5)

        pnl_title = QLabel("GÜNLÜK PNL")
        pnl_title.setObjectName("dailyPnlTitle")
        pnl_title.setAlignment(Qt.AlignCenter)

        self.daily_pnl_label = QLabel("—")
        self.daily_pnl_label.setObjectName("dailyPnlValue")
        self.daily_pnl_label.setAlignment(Qt.AlignCenter)
        self.daily_pnl_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.daily_pnl_usdt_label = QLabel("—")
        self.daily_pnl_usdt_label.setObjectName(
            "dailyPnlUsdtValue"
        )
        self.daily_pnl_usdt_label.setAlignment(Qt.AlignCenter)
        self.daily_pnl_usdt_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        pnl_layout.addWidget(pnl_title)
        pnl_layout.addWidget(self.daily_pnl_label)
        pnl_layout.addWidget(self.daily_pnl_usdt_label)

        right_container = QWidget()
        right_container.setObjectName("summaryRightContainer")

        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(22)

        right_layout.addWidget(
            pnl_container,
            0,
            Qt.AlignVCenter,
        )
        right_layout.addWidget(
            self.connection_badge,
            0,
            Qt.AlignTop,
        )

        layout.addLayout(balance_layout, 1)
        layout.addWidget(
            right_container,
            0,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        return card

    def _create_trading_table_card(self):
        card = ElevatedInnerPanel(
            "portfolioTradingTableCard",
            radius=18,
        )
        card.setMinimumHeight(900)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 12)
        layout.setSpacing(0)

        table_header = SectionHeader(
            title="Trading Hesabı",
            description=(
                "Trading hesabındaki spot varlıkların "
                "güncel görünümü"
            ),
            object_name="portfolioTradingSectionHeader",
        )

        for label in table_header.findChildren(QLabel):
            if label.text() == "Trading Hesabı":
                label.setStyleSheet(
                    f"""
                    color: {Theme.TEXT_PRIMARY};
                    font-size: 18px;
                    font-weight: 800;
                    """
                )
                break

        self.trading_header_row = QWidget()
        self.trading_header_row.setObjectName(
            "portfolioTradingHeaderRow"
        )

        trading_header_layout = QHBoxLayout(
            self.trading_header_row
        )
        trading_header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        trading_header_layout.setSpacing(0)

        self.trading_total_pnl_widget = QWidget(
            self.trading_header_row
        )
        self.trading_total_pnl_widget.setObjectName(
            "tradingTotalPnlContainer"
        )
        self.trading_total_pnl_widget.setFixedWidth(150)

        trading_total_pnl_layout = QGridLayout(
            self.trading_total_pnl_widget
        )
        trading_total_pnl_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        trading_total_pnl_layout.setHorizontalSpacing(0)
        trading_total_pnl_layout.setVerticalSpacing(1)
        trading_total_pnl_layout.setColumnStretch(0, 1)

        self.trading_total_pnl_percent_value = QLabel("—")
        self.trading_total_pnl_usdt_value = QLabel("—")

        trading_pnl_labels = (
            self.trading_total_pnl_percent_value,
            self.trading_total_pnl_usdt_value,
        )

        for label in trading_pnl_labels:
            label.setObjectName("tradingTotalPnlValue")
            label.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )
            label.setAlignment(
                Qt.AlignLeft | Qt.AlignVCenter
            )
            label.setFixedWidth(112)

        trading_total_pnl_layout.addWidget(
            self.trading_total_pnl_percent_value,
            0,
            1,
        )
        trading_total_pnl_layout.addWidget(
            self.trading_total_pnl_usdt_value,
            1,
            1,
        )

        trading_header_layout.addWidget(table_header, 1)

        self.trading_table = QTableWidget()
        self.trading_table.setObjectName("portfolioTradingTable")
        self.trading_table.setFocusPolicy(Qt.NoFocus)
        self.trading_table.setColumnCount(len(self.headers))
        self.trading_table.setHorizontalHeaderLabels(self.headers)

        self.trading_table.setEditTriggers(
            QTableWidget.NoEditTriggers
        )
        self.trading_table.setSelectionBehavior(
            QTableWidget.SelectRows
        )
        self.trading_table.setSelectionMode(
            QTableWidget.NoSelection
        )
        self.trading_table.setAlternatingRowColors(False)
        self.trading_table.setSortingEnabled(False)
        self.trading_table.setShowGrid(False)
        self.trading_table.setWordWrap(False)

        header = self.trading_table.horizontalHeader()
        header.setObjectName("portfolioTradingTableHeader")
        header.setFocusPolicy(Qt.NoFocus)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.trading_table.setColumnWidth(0, 58)

        for column in range(1, len(self.headers)):
            header.setSectionResizeMode(
                column,
                QHeaderView.Stretch,
            )

        self.trading_table.verticalHeader().setVisible(False)
        self.trading_table.verticalHeader().setDefaultSectionSize(74)
        self.trading_table.verticalHeader().setMinimumSectionSize(74)

        layout.addWidget(self.trading_header_row)
        layout.addWidget(self.trading_table, 1)

        return card

    def _create_table_card(self):
        card = ElevatedInnerPanel(
            "portfolioTableCard",
            radius=18,
        )
        card.setMinimumHeight(900)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(10, 8, 10, 12)
        layout.setSpacing(0)

        table_header = SectionHeader(
            title="Varlık Dağılımı",
            description=(
                "Portföyündeki tüm spot varlıkların "
                "güncel görünümü"
            ),
            object_name="portfolioSectionHeader",
        )

        header_labels = table_header.findChildren(QLabel)

        for label in header_labels:
            if label.text() == "Varlık Dağılımı":
                label.setStyleSheet(
                    f"""
                    color: {Theme.TEXT_PRIMARY};
                    font-size: 18px;
                    font-weight: 800;
                    """
                )
                break

        self.portfolio_header_row = QWidget()
        self.portfolio_header_row.setObjectName(
            "portfolioAssetHeaderRow"
        )

        portfolio_header_layout = QHBoxLayout(
            self.portfolio_header_row
        )
        portfolio_header_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        portfolio_header_layout.setSpacing(0)

        self.portfolio_total_pnl_widget = QWidget(
            self.portfolio_header_row
        )
        self.portfolio_total_pnl_widget.setObjectName(
            "portfolioTotalPnlContainer"
        )
        self.portfolio_total_pnl_widget.setFixedWidth(150)

        portfolio_total_pnl_layout = QGridLayout(
            self.portfolio_total_pnl_widget
        )
        portfolio_total_pnl_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        portfolio_total_pnl_layout.setHorizontalSpacing(0)
        portfolio_total_pnl_layout.setVerticalSpacing(1)
        portfolio_total_pnl_layout.setColumnStretch(0, 1)

        self.portfolio_total_pnl_percent_value = QLabel("—")
        self.portfolio_total_pnl_usdt_value = QLabel("—")

        portfolio_pnl_labels = (
            self.portfolio_total_pnl_percent_value,
            self.portfolio_total_pnl_usdt_value,
        )

        for label in portfolio_pnl_labels:
            label.setObjectName("portfolioTotalPnlValue")
            label.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )
            label.setAlignment(
                Qt.AlignLeft | Qt.AlignVCenter
            )
            label.setFixedWidth(112)

        portfolio_total_pnl_layout.addWidget(
            self.portfolio_total_pnl_percent_value,
            0,
            1,
        )
        portfolio_total_pnl_layout.addWidget(
            self.portfolio_total_pnl_usdt_value,
            1,
            1,
        )

        portfolio_header_layout.addWidget(table_header, 1)

        self.table = QTableWidget()
        self.table.setObjectName("portfolioTable")
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        self.table.horizontalHeader().setObjectName(
            "portfolioTableHeader"
        )
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Fixed,
        )
        self.table.setColumnWidth(0, 58)

        for column in range(1, len(self.headers)):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.Stretch,
            )

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(74)
        self.table.verticalHeader().setMinimumSectionSize(74)

        layout.addWidget(self.portfolio_header_row)
        layout.addWidget(self.table, 1)

        return card

    def _connect_signals(self):
        self.hide_dust_checkbox.stateChanged.connect(
            self.update_table_view
        )
        self.hide_dust_checkbox.stateChanged.connect(
            self.update_trading_table_view
        )

        self.refresh_button.clicked.connect(
            self.load_balances
        )

        self.table.horizontalHeader().sortIndicatorChanged.connect(
            self.on_sort_indicator_changed
        )
        self.trading_table.horizontalHeader().sortIndicatorChanged.connect(
            self.on_trading_sort_indicator_changed
        )

        self.table.horizontalHeader().sectionResized.connect(
            self._schedule_total_pnl_header_sync
        )
        self.table.horizontalHeader().geometriesChanged.connect(
            self._schedule_total_pnl_header_sync
        )
        self.trading_table.horizontalHeader().sectionResized.connect(
            self._schedule_total_pnl_header_sync
        )
        self.trading_table.horizontalHeader().geometriesChanged.connect(
            self._schedule_total_pnl_header_sync
        )

        self._schedule_total_pnl_header_sync()

    def _schedule_total_pnl_header_sync(self, *args):
        QTimer.singleShot(
            0,
            self._sync_total_pnl_headers,
        )

    def _sync_total_pnl_headers(self):
        self._position_total_pnl_widget(
            self.trading_header_row,
            self.trading_table,
            self.trading_total_pnl_widget,
        )
        self._position_total_pnl_widget(
            self.portfolio_header_row,
            self.table,
            self.portfolio_total_pnl_widget,
        )

    def _position_total_pnl_widget(
        self,
        header_row,
        table,
        pnl_widget,
    ):
        header = table.horizontalHeader()
        pnl_column = len(self.headers) - 1

        column_x = (
            header.x()
            + header.sectionViewportPosition(
                pnl_column
            )
        )
        column_width = header.sectionSize(pnl_column)

        widget_width = pnl_widget.width()
        widget_height = pnl_widget.sizeHint().height()

        pnl_widget.resize(
            widget_width,
            widget_height,
        )

        widget_x = (
            column_x
            + max(
                0,
                (column_width - widget_width) // 2,
            )
        )
        widget_y = max(
            0,
            (header_row.height() - widget_height) // 2,
        )

        pnl_widget.move(
            widget_x,
            widget_y,
        )
        pnl_widget.raise_()

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
           

            
            QFrame#portfolioSummaryCard,
            QFrame#portfolioTradingTableCard,
            QFrame#portfolioTableCard {{
                background: transparent;
                border: none;
            }}

            QWidget#portfolioSectionHeader,
            QFrame#portfolioSectionHeader {{
                border-bottom: none;
            }}

            QHeaderView#portfolioTableHeader,
            QHeaderView#portfolioTradingTableHeader {{
                border-top: none;
            }}

            QScrollArea#portfolioScrollArea,
            QScrollArea#portfolioScrollArea
            > QWidget
            > QWidget,
            QWidget#portfolioContent {{
                background: transparent;
                border: none;
            }}

            QWidget#portfolioPage {{
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

            QLabel#summaryLabel {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 1px;
            }}

            QLabel#portfolioSectionHeaderTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#summaryValue {{
                color: {Theme.ACCENT};
                font-size: 40px;
                font-weight: 700;
            }}

            QLabel#summaryDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QWidget#summaryRightContainer,
            QWidget#dailyPnlContainer,
            QWidget#portfolioTradingHeaderRow,
            QWidget#tradingTotalPnlContainer,
            QWidget#portfolioAssetHeaderRow,
            QWidget#portfolioTotalPnlContainer {{
                background: transparent;
                border: none;
            }}

            QLabel#tradingTotalPnlValue,
            QLabel#portfolioTotalPnlValue {{
                color: {Theme.TEXT_MUTED};
                font-size: 15px;
                font-weight: 800;
            }}

            QWidget#dailyPnlContainer {{
                min-width: 190px;
            }}

            QLabel#dailyPnlTitle {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#dailyPnlValue {{
                color: {Theme.TEXT_MUTED};
                font-size: 32px;
                font-weight: 750;
            }}

            QLabel#dailyPnlUsdtValue {{
                color: {Theme.TEXT_MUTED};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#sectionTitle,
            QLabel#portfolioSectionHeaderTitle,
            QLabel#portfolioSectionHeader QLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: 800;
            }}

                       
            
            QTableWidget#portfolioTable,
            QTableWidget#portfolioTradingTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-bottom-left-radius: {Theme.RADIUS_LARGE}px;
                border-bottom-right-radius: {Theme.RADIUS_LARGE}px;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#portfolioTable::item,
            QTableWidget#portfolioTradingTable::item {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER_SOFT};
                padding: 14px 12px;
            }}

            QWidget#portfolioPnlCell {{
                background: transparent;
                border: none;
            }}


            QHeaderView#portfolioTableHeader,
            QHeaderView#portfolioTradingTableHeader {{
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

            QHeaderView#portfolioTableHeader::section,
            QHeaderView#portfolioTradingTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 14px 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 1px;
            }}

            QHeaderView#portfolioTableHeader::section,
            QHeaderView#portfolioTradingTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 14px 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 800;
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

    def on_trading_sort_indicator_changed(
        self,
        logical_index,
        order,
    ):
        if logical_index < 0:
            return

        for index in range(
            self.trading_table.columnCount()
        ):
            header_item = (
                self.trading_table
                .horizontalHeaderItem(index)
            )

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
                header_item.setText(
                    self.headers[index]
                )

    def start_page(self):
        if getattr(self, "_shutting_down", False):
            return

        self.load_balances()
        self.refresh_timer.start()

    def load_balances(self):
        if getattr(self, "_shutting_down", False):
            return

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
        if getattr(self, "_shutting_down", False):
            return

        if success:
            portfolio = (
                self.data_manager.get_portfolio()
                or result
            )

            total = float(
                portfolio.get("total_usdt", 0.0)
            )

            self.total_balance_label.setText(
                f"${total:,.2f}"
            )

            self.raw_assets_data = portfolio.get(
                "assets",
                [],
            )

            self._update_daily_pnl(portfolio)
            self._update_portfolio_total_pnl()
            self._update_trading_total_pnl()
            self.update_table_view()
            self.update_trading_table_view()
            self._set_connected_state()

        else:
            data_manager = getattr(
                self,
                "data_manager",
                None,
            )
            get_portfolio = getattr(
                data_manager,
                "get_portfolio",
                None,
            )
            cached_portfolio = (
                get_portfolio()
                if callable(get_portfolio)
                else None
            )

            if (
                isinstance(cached_portfolio, dict)
                and "total_usdt" in cached_portfolio
            ):
                total = float(
                    cached_portfolio.get(
                        "total_usdt",
                        0.0,
                    )
                )
                self.total_balance_label.setText(
                    f"${total:,.2f}"
                )
                self.raw_assets_data = (
                    cached_portfolio.get(
                        "assets",
                        [],
                    )
                )
                self._update_daily_pnl(
                    cached_portfolio
                )
                self._update_portfolio_total_pnl()
                self._update_trading_total_pnl()
                self.update_table_view()
                self.update_trading_table_view()
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

    @staticmethod
    def _extract_percentage(data, keys):
        for key in keys:
            value = data.get(key)

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                try:
                    return float(value.replace("%", "").strip())
                except ValueError:
                    continue

        return None

    def _get_asset_pnl_percent(
        self,
        asset,
        account_prefix="",
    ):
        if account_prefix:
            direct_keys = (
                f"{account_prefix}pnl_percent",
            )
            average_price_keys = (
                f"{account_prefix}average_price",
            )
        else:
            direct_keys = (
                "pnl_percent",
                "pnl_pct",
                "profit_percent",
                "change_24h",
                "change24h",
                "daily_change_percent",
            )
            average_price_keys = (
                "average_price",
                "avg_price",
                "cost_price",
                "entry_price",
            )

        direct = self._extract_percentage(
            asset,
            direct_keys,
        )

        if direct is not None:
            return direct

        current_price = float(
            asset.get("price", 0.0) or 0.0
        )

        for key in average_price_keys:
            cost_price = asset.get(key)

            if not isinstance(cost_price, (int, float)):
                continue

            cost_price = float(cost_price)

            if current_price > 0 and cost_price > 0:
                return (
                    (current_price - cost_price)
                    / cost_price
                    * 100
                )

        return None

    @staticmethod
    def _get_daily_pnl_usdt(portfolio):
        analytics = portfolio.get("analytics", {})

        if isinstance(analytics, dict):
            period_changes = analytics.get(
                "period_changes",
                {},
            )

            if isinstance(period_changes, dict):
                one_day = period_changes.get("1d", {})

                if isinstance(one_day, dict):
                    total_data = one_day.get("total", {})

                    if isinstance(total_data, dict):
                        amount_usdt = total_data.get(
                            "amount_usdt"
                        )

                        if isinstance(
                            amount_usdt,
                            (int, float),
                        ):
                            return float(amount_usdt)

        for key in (
            "daily_pnl_usdt",
            "pnl_1d_usdt",
            "daily_profit_usdt",
        ):
            value = portfolio.get(key)

            if isinstance(value, (int, float)):
                return float(value)

        return None

    def _update_daily_pnl(self, portfolio):
        performance = portfolio.get("performance", {})
        daily_pnl = None

        if isinstance(performance, dict):
            daily_pnl = self._extract_percentage(
                performance,
                ("1d", "daily", "day"),
            )

        if daily_pnl is None:
            daily_pnl = self._extract_percentage(
                portfolio,
                (
                    "daily_pnl_percent",
                    "pnl_1d",
                    "change_1d",
                ),
            )

        daily_pnl_usdt = self._get_daily_pnl_usdt(
            portfolio
        )

        color_source = (
            daily_pnl
            if isinstance(daily_pnl, (int, float))
            else daily_pnl_usdt
        )

        color = (
            Theme.ACCENT
            if isinstance(color_source, (int, float))
            and color_source >= 0
            else (
                Theme.ERROR
                if isinstance(color_source, (int, float))
                else Theme.TEXT_MUTED
            )
        )

        if isinstance(daily_pnl, (int, float)):
            self.daily_pnl_label.setText(
                f"{daily_pnl:+.2f}%"
            )
            self.daily_pnl_label.setStyleSheet(
                f"color: {color};"
            )
        else:
            self.daily_pnl_label.setText("—")
            self.daily_pnl_label.setStyleSheet(
                f"color: {Theme.TEXT_MUTED};"
            )

        if isinstance(daily_pnl_usdt, (int, float)):
            self.daily_pnl_usdt_label.setText(
                f"{daily_pnl_usdt:+,.2f} USDT"
            )
            self.daily_pnl_usdt_label.setStyleSheet(
                f"color: {color};"
            )
        else:
            self.daily_pnl_usdt_label.setText("—")
            self.daily_pnl_usdt_label.setStyleSheet(
                f"color: {Theme.TEXT_MUTED};"
            )

    def _set_portfolio_total_pnl_placeholder(self):
        labels = (
            self.portfolio_total_pnl_percent_value,
            self.portfolio_total_pnl_usdt_value,
        )

        self.portfolio_total_pnl_percent_value.setText("—")
        self.portfolio_total_pnl_usdt_value.setText("—")

        for label in labels:
            label.setStyleSheet(
                f"""
                color: {Theme.TEXT_MUTED};
                font-size: 15px;
                font-weight: 800;
                """
            )

    def _update_portfolio_total_pnl(self):
        portfolio_assets = [
            asset
            for asset in self.raw_assets_data
            if (
                str(
                    asset.get("coin", "")
                ).strip().upper() != "USDT"
                and float(
                    asset.get("total", 0.0)
                    or 0.0
                ) > 0
            )
        ]

        if not portfolio_assets:
            self._set_portfolio_total_pnl_placeholder()
            return

        total_cost_basis = 0.0
        total_pnl_usdt = 0.0
        valid_position_count = 0

        for asset in portfolio_assets:
            cost_basis_available = asset.get(
                "cost_basis_available",
                False,
            )
            cost_basis_usdt = asset.get(
                "cost_basis_usdt"
            )
            pnl_usdt = asset.get("pnl_usdt")

            if (
                not cost_basis_available
                or not isinstance(
                    cost_basis_usdt,
                    (int, float),
                )
                or not isinstance(
                    pnl_usdt,
                    (int, float),
                )
                or float(cost_basis_usdt) <= 0
            ):
                continue

            total_cost_basis += float(cost_basis_usdt)
            total_pnl_usdt += float(pnl_usdt)
            valid_position_count += 1

        if (
            valid_position_count == 0
            or total_cost_basis <= 0
        ):
            self._set_portfolio_total_pnl_placeholder()
            return

        total_pnl_percent = (
            total_pnl_usdt
            / total_cost_basis
            * 100
        )

        color = (
            Theme.ACCENT
            if total_pnl_usdt >= 0
            else Theme.ERROR
        )

        self.portfolio_total_pnl_percent_value.setText(
            f"{total_pnl_percent:+.2f}%"
        )
        self.portfolio_total_pnl_usdt_value.setText(
            f"{total_pnl_usdt:+,.2f} USDT"
        )

        for label in (
            self.portfolio_total_pnl_percent_value,
            self.portfolio_total_pnl_usdt_value,
        ):
            label.setStyleSheet(
                f"""
                color: {color};
                font-size: 15px;
                font-weight: 800;
                """
            )

    def _set_trading_total_pnl_placeholder(self):
        labels = (
            self.trading_total_pnl_percent_value,
            self.trading_total_pnl_usdt_value,
        )

        self.trading_total_pnl_percent_value.setText("—")
        self.trading_total_pnl_usdt_value.setText("—")

        for label in labels:
            label.setStyleSheet(
                f"""
                color: {Theme.TEXT_MUTED};
                font-size: 15px;
                font-weight: 800;
                """
            )

    def _update_trading_total_pnl(self):
        trading_assets = [
            asset
            for asset in self.raw_assets_data
            if (
                str(
                    asset.get("coin", "")
                ).strip().upper() != "USDT"
                and float(
                    asset.get("trading_total", 0.0)
                    or 0.0
                ) > 0
            )
        ]

        if not trading_assets:
            self._set_trading_total_pnl_placeholder()
            return

        total_cost_basis = 0.0
        total_pnl_usdt = 0.0
        valid_position_count = 0

        for asset in trading_assets:
            cost_basis_available = asset.get(
                "trading_cost_basis_available",
                False,
            )
            cost_basis_usdt = asset.get(
                "trading_cost_basis_usdt"
            )
            pnl_usdt = asset.get("trading_pnl_usdt")

            if (
                not cost_basis_available
                or not isinstance(
                    cost_basis_usdt,
                    (int, float),
                )
                or not isinstance(
                    pnl_usdt,
                    (int, float),
                )
                or float(cost_basis_usdt) <= 0
            ):
                continue

            total_cost_basis += float(cost_basis_usdt)
            total_pnl_usdt += float(pnl_usdt)
            valid_position_count += 1

        if (
            valid_position_count == 0
            or total_cost_basis <= 0
        ):
            self._set_trading_total_pnl_placeholder()
            return

        total_pnl_percent = (
            total_pnl_usdt
            / total_cost_basis
            * 100
        )

        color = (
            Theme.ACCENT
            if total_pnl_usdt >= 0
            else Theme.ERROR
        )

        self.trading_total_pnl_percent_value.setText(
            f"{total_pnl_percent:+.2f}%"
        )
        self.trading_total_pnl_usdt_value.setText(
            f"{total_pnl_usdt:+,.2f} USDT"
        )

        for label in (
            self.trading_total_pnl_percent_value,
            self.trading_total_pnl_usdt_value,
        ):
            label.setStyleSheet(
                f"""
                color: {color};
                font-size: 15px;
                font-weight: 800;
                """
            )

    def _populate_asset_table(
        self,
        table,
        assets,
        amount_key="total",
        value_key="usdt_value",
        pnl_prefix="",
    ):
        table.setSortingEnabled(False)
        table.setUpdatesEnabled(False)
        table.setRowCount(len(assets))

        for row, asset in enumerate(assets):
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setForeground(
                QColor(Theme.TEXT_MUTED)
            )
            index_item.setTextAlignment(Qt.AlignCenter)

            index_font = QFont(Theme.FONT_FAMILY, 10)
            index_font.setBold(True)
            index_item.setFont(index_font)

            coin_item = QTableWidgetItem(
                asset.get("coin", "")
            )
            coin_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            coin_item.setTextAlignment(Qt.AlignCenter)

            coin_font = coin_item.font()
            coin_font.setBold(True)
            coin_item.setFont(coin_font)

            total_amount = asset.get(amount_key, 0.0)
            usdt_value = asset.get(value_key, 0.0)

            total_item = NumericTableWidgetItem(
                total_amount,
                self.format_amount(total_amount),
            )

            pnl_percent = self._get_asset_pnl_percent(
                asset,
                account_prefix=pnl_prefix,
            )
            pnl_usdt = asset.get(
                f"{pnl_prefix}pnl_usdt"
            )

            pnl_item = NumericTableWidgetItem(
                (
                    pnl_percent
                    if pnl_percent is not None
                    else 0.0
                ),
                "",
            )

            pnl_widget = QWidget()
            pnl_widget.setObjectName("portfolioPnlCell")

            pnl_layout = QVBoxLayout(pnl_widget)
            pnl_layout.setContentsMargins(4, 4, 4, 4)
            pnl_layout.setSpacing(8)

            coin_symbol = str(
                asset.get("coin", "")
            ).strip().upper()

            if coin_symbol == "USDT":
                pnl_percent_text = ""
                pnl_usdt_text = ""
            else:
                pnl_percent_text = (
                    f"{pnl_percent:+.2f}%"
                    if isinstance(pnl_percent, (int, float))
                    else "—"
                )
                pnl_usdt_text = (
                    f"{float(pnl_usdt):+,.2f} USDT"
                    if isinstance(pnl_usdt, (int, float))
                    else "—"
                )

            pnl_percent_label = QLabel(pnl_percent_text)
            pnl_percent_label.setAlignment(Qt.AlignCenter)

            pnl_usdt_label = QLabel(pnl_usdt_text)
            pnl_usdt_label.setAlignment(Qt.AlignCenter)

            pnl_color = (
                Theme.ACCENT
                if isinstance(pnl_percent, (int, float))
                and pnl_percent >= 0
                else (
                    Theme.ERROR
                    if isinstance(pnl_percent, (int, float))
                    else Theme.TEXT_MUTED
                )
            )

            shared_style = f"""
                color: {pnl_color};
                font-size: 12px;
                font-weight: 700;
                font-family: "{Theme.FONT_FAMILY}";
            """
            pnl_percent_label.setStyleSheet(shared_style)
            pnl_usdt_label.setStyleSheet(shared_style)

            pnl_layout.addWidget(pnl_percent_label)
            pnl_layout.addWidget(pnl_usdt_label)

            price_item = NumericTableWidgetItem(
                asset.get("price", 0.0),
                self.format_price(
                    asset.get("price", 0.0)
                ),
            )

            value_item = NumericTableWidgetItem(
                usdt_value,
                f"${float(usdt_value):,.2f}",
            )

            total_item.setForeground(
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
                price_item,
                value_item,
            ):
                item.setTextAlignment(Qt.AlignCenter)
                item_font = item.font()
                item_font.setBold(True)
                item.setFont(item_font)

            table.setItem(row, 0, index_item)
            table.setItem(row, 1, coin_item)
            table.setItem(row, 2, value_item)
            table.setItem(row, 3, price_item)
            table.setItem(row, 4, total_item)
            table.setItem(row, 5, pnl_item)
            table.setCellWidget(row, 5, pnl_widget)

        table.setUpdatesEnabled(True)
        table.setSortingEnabled(True)

    def update_trading_table_view(self):
        hide_dust = self.hide_dust_checkbox.isChecked()

        trading_assets = [
            asset
            for asset in self.raw_assets_data
            if float(asset.get("trading_total", 0.0) or 0.0) > 0
            and not (
                hide_dust
                and float(
                    asset.get("trading_usdt_value", 0.0)
                    or 0.0
                ) < 1
            )
        ]

        self._populate_asset_table(
            self.trading_table,
            trading_assets,
            amount_key="trading_total",
            value_key="trading_usdt_value",
            pnl_prefix="trading_",
        )

        sort_column = (
            self.trading_table.horizontalHeader()
            .sortIndicatorSection()
        )
        sort_order = (
            self.trading_table.horizontalHeader()
            .sortIndicatorOrder()
        )
        self.on_trading_sort_indicator_changed(
            sort_column,
            sort_order,
        )

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
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setForeground(
                QColor(Theme.TEXT_MUTED)
            )
            index_item.setTextAlignment(Qt.AlignCenter)

            index_font = QFont(Theme.FONT_FAMILY, 10)
            index_font.setBold(True)
            index_item.setFont(index_font)

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

            pnl_percent = self._get_asset_pnl_percent(asset)
            pnl_usdt = asset.get("pnl_usdt")

            pnl_item = NumericTableWidgetItem(
                (
                    pnl_percent
                    if pnl_percent is not None
                    else 0.0
                ),
                "",
            )

            pnl_widget = QWidget()
            pnl_widget.setObjectName("portfolioPnlCell")

            pnl_layout = QVBoxLayout(pnl_widget)
            pnl_layout.setContentsMargins(4, 4, 4, 4)
            pnl_layout.setSpacing(8)

            coin_symbol = str(
                asset.get("coin", "")
            ).strip().upper()

            if coin_symbol == "USDT":
                pnl_percent_text = ""
                pnl_usdt_text = ""
            else:
                pnl_percent_text = (
                    f"{pnl_percent:+.2f}%"
                    if isinstance(pnl_percent, (int, float))
                    else "—"
                )
                pnl_usdt_text = (
                    f"{float(pnl_usdt):+,.2f} USDT"
                    if isinstance(pnl_usdt, (int, float))
                    else "—"
                )

            pnl_percent_label = QLabel(
                pnl_percent_text
            )
            pnl_percent_label.setObjectName(
                "portfolioPnlPercent"
            )
            pnl_percent_label.setAlignment(Qt.AlignCenter)

            pnl_usdt_label = QLabel(
                pnl_usdt_text
            )
            pnl_usdt_label.setObjectName(
                "portfolioPnlUsdt"
            )
            pnl_usdt_label.setAlignment(Qt.AlignCenter)

            pnl_color = (
                Theme.ACCENT
                if isinstance(pnl_percent, (int, float))
                and pnl_percent >= 0
                else (
                    Theme.ERROR
                    if isinstance(pnl_percent, (int, float))
                    else Theme.TEXT_MUTED
                )
            )

            pnl_percent_label.setStyleSheet(
                f"""
                color: {pnl_color};
                font-size: 12px;
                font-weight: 700;
                font-family: "{Theme.FONT_FAMILY}";
                """
            )
            pnl_usdt_label.setStyleSheet(
                f"""
                color: {pnl_color};
                font-size: 12px;
                font-weight: 700;
                font-family: "{Theme.FONT_FAMILY}";
                """
            )

            pnl_layout.addWidget(pnl_percent_label)
            pnl_layout.addWidget(pnl_usdt_label)

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
            pnl_item.setForeground(
                QColor(
                    Theme.ACCENT
                    if pnl_percent is not None
                    and pnl_percent >= 0
                    else (
                        Theme.ERROR
                        if pnl_percent is not None
                        else Theme.TEXT_MUTED
                    )
                )
            )
            price_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            value_item.setForeground(
                QColor(Theme.ACCENT)
            )

            for item in (
                total_item,
                pnl_item,
                price_item,
                value_item,
            ):
                item.setTextAlignment(Qt.AlignCenter)

                item_font = item.font()
                item_font.setBold(True)
                item.setFont(item_font)

            self.table.setItem(row, 0, index_item)
            self.table.setItem(row, 1, coin_item)
            self.table.setItem(row, 2, value_item)
            self.table.setItem(row, 3, price_item)
            self.table.setItem(row, 4, total_item)
            self.table.setItem(row, 5, pnl_item)
            self.table.setCellWidget(row, 5, pnl_widget)

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

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._schedule_total_pnl_header_sync()

    def showEvent(self, event):
        super().showEvent(event)
        self._schedule_total_pnl_header_sync()

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def shutdown(self):
        if getattr(self, "_shutting_down", False):
            return

        self._shutting_down = True
        self.refresh_timer.stop()

        worker = self.worker

        if worker is not None and worker.isRunning():
            worker.requestInterruption()
            worker.wait()

        self.worker = None

    def closeEvent(self, event):
        self.refresh_timer.stop()

        if (
            self.worker is not None
            and self.worker.isRunning()
        ):
            self.worker.quit()
            self.worker.wait(3000)

        super().closeEvent(event)