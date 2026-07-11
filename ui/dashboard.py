from PySide6.QtCore import Qt
from ui.widgets.card import Card
from ui.widgets.status_badge import StatusBadge
from ui.widgets.page_header import PageHeader
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):
    BACKGROUND_COLOR = "#0D1117"
    CARD_COLOR = "#151B23"
    CARD_HOVER_COLOR = "#18202A"
    CARD_BORDER_COLOR = "#28313D"

    TEXT_PRIMARY = "#F3F5F7"
    TEXT_SECONDARY = "#9AA4B2"
    TEXT_MUTED = "#667180"

    ACCENT_GREEN = "#16C784"
    

    RESPONSIVE_BREAKPOINT = 900

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.layout_mode = None

        self.summary_cards = []
        self.account_widgets = []

        self.setObjectName("dashboardPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()
        self._apply_styles()
        self._connect_signals()

        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.content_widget = QWidget()
        self.content_widget.setObjectName("dashboardContent")
        self.content_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(32, 28, 32, 32)
        self.main_layout.setSpacing(24)

        self.status_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="dashboardStatusBadge",
        )

        self.header_widget = PageHeader(
            title="Dashboard",
            subtitle=(
                "Portföy durumunu ve hesap dağılımını "
                "tek ekrandan takip et."
            ),
            right_widget=self.status_badge,
            object_name="dashboardHeader",
        )

        self.main_layout.addWidget(self.header_widget)

        self.portfolio_card = self._create_portfolio_card()
        self.main_layout.addWidget(self.portfolio_card)

        self.summary_container = QWidget()
        self.summary_container.setObjectName("summaryContainer")

        self.summary_grid = QGridLayout(self.summary_container)
        self.summary_grid.setContentsMargins(0, 0, 0, 0)
        self.summary_grid.setHorizontalSpacing(16)
        self.summary_grid.setVerticalSpacing(16)

        self._create_summary_cards()

        self.main_layout.addWidget(self.summary_container)
        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area)

        self._set_layout_mode("wide")

    def _create_header(self):
        header = QWidget()
        header.setObjectName("headerWidget")

        layout = QHBoxLayout(header)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Portföy durumunu ve hesap dağılımını "
            "tek ekrandan takip et."
        )
        subtitle.setObjectName("pageSubtitle")
        subtitle.setWordWrap(True)

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.status_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="dashboardStatusBadge",
        )

        layout.addLayout(title_layout, 1)
        layout.addWidget(
            self.status_badge,
            0,
            Qt.AlignTop | Qt.AlignRight,
        )

        return header

    def _create_portfolio_card(self):
        card = Card("portfolioCard")        
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 26)
        card_layout.setSpacing(20)

        top_layout = QHBoxLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(16)

        label_layout = QVBoxLayout()
        label_layout.setContentsMargins(0, 0, 0, 0)
        label_layout.setSpacing(4)

        portfolio_label = QLabel("TOPLAM PORTFÖY")
        portfolio_label.setObjectName("portfolioLabel")

        portfolio_description = QLabel(
            "Funding ve Trading hesaplarının toplam değeri"
        )
        portfolio_description.setObjectName(
            "portfolioDescription"
        )
        portfolio_description.setWordWrap(True)

        label_layout.addWidget(portfolio_label)
        label_layout.addWidget(portfolio_description)

        self.currency_label = QLabel("USDT")
        self.currency_label.setObjectName("currencyBadge")
        self.currency_label.setAlignment(Qt.AlignCenter)
        self.currency_label.setFixedSize(58, 30)

        top_layout.addLayout(label_layout, 1)
        top_layout.addWidget(
            self.currency_label,
            0,
            Qt.AlignTop | Qt.AlignRight,
        )

        self.value = QLabel("$0.00")
        self.value.setObjectName("portfolioValue")
        self.value.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )
        self.value.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        divider = QFrame()
        divider.setObjectName("cardDivider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)

        self.account_container = QWidget()
        self.account_container.setObjectName("accountContainer")

        self.account_grid = QGridLayout(self.account_container)
        self.account_grid.setContentsMargins(0, 0, 0, 0)
        self.account_grid.setHorizontalSpacing(16)
        self.account_grid.setVerticalSpacing(12)

        funding_box = self._create_account_box(
            title="Funding",
            description="Fon hesabı",
        )
        self.funding_value = funding_box["value"]
        self.account_widgets.append(funding_box["widget"])

        trading_box = self._create_account_box(
            title="Trading",
            description="Spot işlem hesabı",
        )
        self.trading_value = trading_box["value"]
        self.account_widgets.append(trading_box["widget"])

        card_layout.addLayout(top_layout)
        card_layout.addWidget(self.value)
        card_layout.addWidget(divider)
        card_layout.addWidget(self.account_container)

        return card

    def _create_account_box(self, title, description):
        widget = Card(
            "accountBox",
            hover=True,
            radius=12,
        )
        widget.setMinimumHeight(80)
        widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setObjectName("accountTitle")

        value_label = QLabel("$0.00")
        value_label.setObjectName("accountValue")
        value_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        description_label = QLabel(description)
        description_label.setObjectName(
            "accountDescription"
        )

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        layout.addWidget(description_label)

        return {
            "widget": widget,
            "value": value_label,
        }

    def _create_summary_cards(self):
        definitions = (
            (
                "Portföy Performansı",
                "Günlük ve dönemsel değişimler",
            ),
            (
                "Aktif Alarmlar",
                "Alarm özeti ve son tetiklemeler",
            ),
            (
                "Watchlist Özeti",
                "Takip edilen varlıkların görünümü",
            ),
        )

        for title, description in definitions:
            card = self._create_summary_card(
                title,
                description,
            )
            self.summary_cards.append(card)

    def _create_summary_card(self, title, description):
        card = Card("summaryCard")
        card.setMinimumHeight(116)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(7)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")

        description_label = QLabel(description)
        description_label.setObjectName(
            "summaryDescription"
        )
        description_label.setWordWrap(True)

        coming_soon = QLabel("Yakında")
        coming_soon.setObjectName("comingSoon")

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(coming_soon)

        return card

    def _clear_grid(self, grid):
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(self.content_widget)

    def _set_layout_mode(self, mode):
        if mode == self.layout_mode:
            return

        self._clear_grid(self.account_grid)
        self._clear_grid(self.summary_grid)

        if mode == "narrow":
            self.main_layout.setContentsMargins(
                24,
                24,
                24,
                28,
            )
            self.main_layout.setSpacing(20)

            self.account_grid.addWidget(
                self.account_widgets[0],
                0,
                0,
            )
            self.account_grid.addWidget(
                self.account_widgets[1],
                1,
                0,
            )
            self.account_grid.setColumnStretch(0, 1)

            for row, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(card, row, 0)

            self.summary_grid.setColumnStretch(0, 1)

        else:
            self.main_layout.setContentsMargins(
                32,
                28,
                32,
                32,
            )
            self.main_layout.setSpacing(24)

            self.account_grid.addWidget(
                self.account_widgets[0],
                0,
                0,
            )
            self.account_grid.addWidget(
                self.account_widgets[1],
                0,
                1,
            )
            self.account_grid.setColumnStretch(0, 1)
            self.account_grid.setColumnStretch(1, 1)

            for column, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(
                    card,
                    0,
                    column,
                )
                self.summary_grid.setColumnStretch(
                    column,
                    1,
                )

        self.layout_mode = mode

        self.account_container.adjustSize()
        self.summary_container.adjustSize()
        self.portfolio_card.adjustSize()
        self.content_widget.adjustSize()

    def _connect_signals(self):
        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )
        self.data_manager.portfolio_error.connect(
            self.on_portfolio_error
        )

    def _apply_styles(self):
        self.setStyleSheet(
            f"""
            QWidget#dashboardPage {{
                background-color: {self.BACKGROUND_COLOR};
            }}

            QScrollArea#dashboardScrollArea {{
                background-color: {self.BACKGROUND_COLOR};
                border: none;
            }}

            QScrollArea#dashboardScrollArea > QWidget > QWidget {{
                background-color: {self.BACKGROUND_COLOR};
            }}

            QWidget#dashboardContent,
            QWidget#headerWidget,
            QWidget#summaryContainer,
            QWidget#accountContainer {{
                background: transparent;
                border: none;
            }}

            QLabel {{
                background: transparent;
                border: none;
                color: {self.TEXT_PRIMARY};
                font-family: "Segoe UI";
            }}

            QLabel#pageTitle {{
                color: {self.TEXT_PRIMARY};
                font-size: 27px;
                font-weight: 700;
            }}

            QLabel#pageSubtitle {{
                color: {self.TEXT_SECONDARY};
                font-size: 13px;
                font-weight: 400;
            }}

            
            QFrame#portfolioCard {{
                background-color: {self.CARD_COLOR};
                border: 1px solid {self.CARD_BORDER_COLOR};
                border-radius: 18px;
            }}

            QLabel#portfolioLabel {{
                color: {self.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#portfolioDescription {{
                color: {self.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#currencyBadge {{
                color: {self.TEXT_SECONDARY};
                background-color: #10161D;
                border: 1px solid {self.CARD_BORDER_COLOR};
                border-radius: 9px;
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#portfolioValue {{
                color: {self.ACCENT_GREEN};
                font-size: 40px;
                font-weight: 700;
            }}

            QFrame#cardDivider {{
                background-color: {self.CARD_BORDER_COLOR};
                border: none;
            }}

            QFrame#accountBox {{
                background-color: #11171E;
                border: 1px solid #222C37;
                border-radius: 12px;
            }}

            QFrame#accountBox:hover {{
                background-color: #141C24;
                border-color: #2D3946;
            }}

            QLabel#accountTitle {{
                color: {self.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
            }}

            QLabel#accountValue {{
                color: {self.TEXT_PRIMARY};
                font-size: 18px;
                font-weight: 700;
            }}

            QLabel#accountDescription {{
                color: {self.TEXT_MUTED};
                font-size: 11px;
                font-weight: 400;
            }}

            QFrame#summaryCard {{
                background-color: {self.CARD_COLOR};
                border: 1px solid {self.CARD_BORDER_COLOR};
                border-radius: 15px;
            }}

            QFrame#summaryCard:hover {{
                background-color: {self.CARD_HOVER_COLOR};
                border-color: #354252;
            }}

            QLabel#summaryTitle {{
                color: {self.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 600;
            }}

            QLabel#summaryDescription {{
                color: {self.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#comingSoon {{
                color: {self.TEXT_MUTED};
                font-size: 11px;
                font-weight: 600;
            }}

            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 6px 2px 6px 2px;
            }}

            QScrollBar::handle:vertical {{
                background-color: #2B3541;
                min-height: 36px;
                border-radius: 4px;
            }}

            QScrollBar::handle:vertical:hover {{
                background-color: #3A4654;
            }}

            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0;
                background: transparent;
                border: none;
            }}

            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)

        available_width = self.scroll_area.viewport().width()

        if available_width < self.RESPONSIVE_BREAKPOINT:
            self._set_layout_mode("narrow")
        else:
            self._set_layout_mode("wide")

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if not portfolio:
            self._set_waiting_status()
            return

        self.on_portfolio_updated(portfolio)

    def on_portfolio_updated(self, portfolio):
        total = float(
            portfolio.get("total_usdt", 0.0)
        )
        funding_total = float(
            portfolio.get("funding_usdt", 0.0)
        )
        trading_total = float(
            portfolio.get("trading_usdt", 0.0)
        )

        self.value.setText(f"${total:,.2f}")
        self.funding_value.setText(
            f"${funding_total:,.2f}"
        )
        self.trading_value.setText(
            f"${trading_total:,.2f}"
        )

        self._set_connected_status()

    def on_portfolio_error(self, error):
        self._set_error_status()

    def _set_waiting_status(self):
        self.status_badge.set_status(
            "Bekleniyor",
            StatusBadge.NEUTRAL,
        )


    def _set_connected_status(self):
        self.status_badge.set_status(
            "API Bağlı",
            StatusBadge.SUCCESS,
        )


    def _set_error_status(self):
        self.status_badge.set_status(
            "Bağlantı Hatası",
            StatusBadge.ERROR,
        )

        