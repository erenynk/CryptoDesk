from PySide6.QtCore import Qt
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

from ui.theme import Theme, scroll_bar_style
from ui.widgets.card import Card
from ui.widgets.page_header import PageHeader
from ui.widgets.status_badge import StatusBadge


class DashboardPage(QWidget):
    RESPONSIVE_BREAKPOINT = 920

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.layout_mode = None
        self.account_cards = []
        self.summary_cards = []

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
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("dashboardContent")
        self.content_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        self.main_layout.setSpacing(Theme.PAGE_SPACING)

        self.status_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="dashboardStatusBadge",
        )

        self.header = PageHeader(
            title="Dashboard",
            subtitle="Portföy durumunu ve hesap dağılımını tek ekrandan takip et.",
            right_widget=self.status_badge,
            object_name="dashboardHeader",
        )
        self.main_layout.addWidget(self.header)

        self.hero_card = self._create_hero_card()
        self.main_layout.addWidget(self.hero_card)

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

    def _create_hero_card(self):
        card = Card(
            "dashboardHeroCard",
            hover=False,
            radius=20,
            shadow=True,
        )
        card.setMinimumHeight(300)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(24)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)

        eyebrow = QLabel("TOPLAM PORTFÖY")
        eyebrow.setObjectName("heroEyebrow")

        description = QLabel(
            "Funding ve Trading hesaplarının birleşik güncel değeri"
        )
        description.setObjectName("heroDescription")
        description.setWordWrap(True)

        title_layout.addWidget(eyebrow)
        title_layout.addWidget(description)

        currency_badge = QLabel("USDT")
        currency_badge.setObjectName("currencyBadge")
        currency_badge.setAlignment(Qt.AlignCenter)
        currency_badge.setFixedSize(62, 32)

        top_row.addLayout(title_layout, 1)
        top_row.addWidget(
            currency_badge,
            0,
            Qt.AlignTop | Qt.AlignRight,
        )

        self.value = QLabel("$0.00")
        self.value.setObjectName("heroValue")
        self.value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.value.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        self.hero_caption = QLabel("Toplam kullanılabilir portföy değeri")
        self.hero_caption.setObjectName("heroCaption")

        divider = QFrame()
        divider.setObjectName("heroDivider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)

        self.account_container = QWidget()
        self.account_container.setObjectName("accountContainer")

        self.account_grid = QGridLayout(self.account_container)
        self.account_grid.setContentsMargins(0, 0, 0, 0)
        self.account_grid.setHorizontalSpacing(16)
        self.account_grid.setVerticalSpacing(14)

        funding = self._create_account_card(
            title="Funding",
            description="Fon hesabı",
            accent_text="Cüzdan bakiyesi",
        )
        self.funding_value = funding["value"]
        self.account_cards.append(funding["widget"])

        trading = self._create_account_card(
            title="Trading",
            description="Spot işlem hesabı",
            accent_text="İşlem bakiyesi",
        )
        self.trading_value = trading["value"]
        self.account_cards.append(trading["widget"])

        layout.addLayout(top_row)
        layout.addWidget(self.value)
        layout.addWidget(self.hero_caption)
        layout.addWidget(divider)
        layout.addWidget(self.account_container)

        return card

    def _create_account_card(self, title, description, accent_text):
        card = Card(
            "dashboardAccountCard",
            hover=True,
            radius=14,
            shadow=False,
        )
        card.setMinimumHeight(98)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        accent_bar = QFrame()
        accent_bar.setObjectName("accountAccentBar")
        accent_bar.setFixedWidth(3)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        top_line = QHBoxLayout()
        top_line.setContentsMargins(0, 0, 0, 0)
        top_line.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("accountTitle")

        accent_label = QLabel(accent_text)
        accent_label.setObjectName("accountMeta")

        top_line.addWidget(title_label)
        top_line.addStretch()
        top_line.addWidget(accent_label)

        value_label = QLabel("$0.00")
        value_label.setObjectName("accountValue")
        value_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

        description_label = QLabel(description)
        description_label.setObjectName("accountDescription")

        text_layout.addLayout(top_line)
        text_layout.addWidget(value_label)
        text_layout.addWidget(description_label)

        layout.addWidget(accent_bar)
        layout.addLayout(text_layout, 1)

        return {
            "widget": card,
            "value": value_label,
        }

    def _create_summary_cards(self):
        definitions = (
            (
                "Portföy Performansı",
                "Günlük ve dönemsel portföy değişimleri",
                "Analiz yakında",
            ),
            (
                "Aktif Alarmlar",
                "Fiyat alarmları ve son tetiklenmeler",
                "Alarm özeti yakında",
            ),
            (
                "Watchlist Özeti",
                "Takip edilen varlıkların genel görünümü",
                "Piyasa özeti yakında",
            ),
        )

        for title, description, footer in definitions:
            card = self._create_summary_card(
                title,
                description,
                footer,
            )
            self.summary_cards.append(card)

    def _create_summary_card(self, title, description, footer):
        card = Card(
            "dashboardSummaryCard",
            hover=True,
            radius=16,
            shadow=False,
        )
        card.setMinimumHeight(152)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")

        indicator = QLabel("•")
        indicator.setObjectName("summaryIndicator")

        top_row.addWidget(title_label)
        top_row.addStretch()
        top_row.addWidget(indicator)

        description_label = QLabel(description)
        description_label.setObjectName("summaryDescription")
        description_label.setWordWrap(True)

        footer_label = QLabel(footer)
        footer_label.setObjectName("summaryFooter")

        layout.addLayout(top_row)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(footer_label)

        return card

    @staticmethod
    def _clear_grid(grid):
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _set_layout_mode(self, mode):
        if mode == self.layout_mode:
            return

        self._clear_grid(self.account_grid)
        self._clear_grid(self.summary_grid)

        if mode == "narrow":
            self.main_layout.setContentsMargins(22, 22, 22, 28)
            self.main_layout.setSpacing(20)

            for row, card in enumerate(self.account_cards):
                self.account_grid.addWidget(card, row, 0)

            for row, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(card, row, 0)

            self.account_grid.setColumnStretch(0, 1)
            self.summary_grid.setColumnStretch(0, 1)

        else:
            self.main_layout.setContentsMargins(
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
            )
            self.main_layout.setSpacing(Theme.PAGE_SPACING)

            self.account_grid.addWidget(self.account_cards[0], 0, 0)
            self.account_grid.addWidget(self.account_cards[1], 0, 1)
            self.account_grid.setColumnStretch(0, 1)
            self.account_grid.setColumnStretch(1, 1)

            for column, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(card, 0, column)
                self.summary_grid.setColumnStretch(column, 1)

        self.layout_mode = mode

        self.account_container.adjustSize()
        self.summary_container.adjustSize()
        self.hero_card.adjustSize()
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
            scroll_bar_style()
            + f"""
            QWidget#dashboardPage {{
                background-color: {Theme.CONTENT_BACKGROUND};
            }}

            QScrollArea#dashboardScrollArea {{
                background-color: {Theme.CONTENT_BACKGROUND};
                border: none;
            }}

            QScrollArea#dashboardScrollArea > QWidget > QWidget {{
                background-color: {Theme.CONTENT_BACKGROUND};
            }}

            QWidget#dashboardContent,
            QWidget#summaryContainer,
            QWidget#accountContainer {{
                background: transparent;
                border: none;
            }}

            QLabel {{
                background: transparent;
                border: none;
                color: {Theme.TEXT_PRIMARY};
                font-family: "{Theme.FONT_FAMILY}";
            }}

            QLabel#heroEyebrow {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#heroDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#currencyBadge {{
                color: {Theme.TEXT_SECONDARY};
                background-color: rgba(14, 21, 29, 235);
                border: 1px solid {Theme.BORDER};
                border-radius: 10px;
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#heroValue {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 46px;
                font-weight: 700;
            }}

            QLabel#heroCaption {{
                color: {Theme.ACCENT};
                font-size: 12px;
                font-weight: 600;
            }}

            QFrame#heroDivider {{
                background-color: {Theme.BORDER_SOFT};
                border: none;
            }}

            QFrame#accountAccentBar {{
                background-color: {Theme.ACCENT};
                border: none;
                border-radius: 1px;
            }}

            QLabel#accountTitle {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#accountMeta {{
                color: {Theme.TEXT_MUTED};
                font-size: 10px;
                font-weight: 500;
            }}

            QLabel#accountValue {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 20px;
                font-weight: 700;
            }}

            QLabel#accountDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
                font-weight: 400;
            }}

            QLabel#summaryTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#summaryIndicator {{
                color: {Theme.ACCENT};
                font-size: 18px;
                font-weight: 700;
            }}

            QLabel#summaryDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#summaryFooter {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
                font-weight: 600;
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
        total = float(portfolio.get("total_usdt", 0.0))
        funding_total = float(portfolio.get("funding_usdt", 0.0))
        trading_total = float(portfolio.get("trading_usdt", 0.0))

        self.value.setText(f"${total:,.2f}")
        self.funding_value.setText(f"${funding_total:,.2f}")
        self.trading_value.setText(f"${trading_total:,.2f}")

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
