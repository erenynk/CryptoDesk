from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
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
    ERROR_RED = "#F05D6C"

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        self.setObjectName("dashboardPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()
        self._apply_styles()
        self._connect_signals()

        self.refresh()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(32, 28, 32, 32)
        main_layout.setSpacing(24)

        header_layout = self._create_header()
        main_layout.addLayout(header_layout)

        self.portfolio_card = self._create_portfolio_card()
        main_layout.addWidget(self.portfolio_card)

        summary_grid = self._create_summary_grid()
        main_layout.addLayout(summary_grid)

        main_layout.addStretch()

    def _create_header(self):
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(16)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(5)

        title = QLabel("Dashboard")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Portföy durumunu ve hesap dağılımını tek ekrandan takip et."
        )
        subtitle.setObjectName("pageSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)

        self.status_badge = QFrame()
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        status_layout = QHBoxLayout(self.status_badge)
        status_layout.setContentsMargins(12, 7, 12, 7)
        status_layout.setSpacing(8)

        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setFixedSize(8, 8)

        self.status = QLabel("Bekleniyor...")
        self.status.setObjectName("statusText")

        status_layout.addWidget(self.status_dot)
        status_layout.addWidget(self.status)

        header_layout.addLayout(title_layout)
        header_layout.addStretch()
        header_layout.addWidget(
            self.status_badge,
            alignment=Qt.AlignTop,
        )

        return header_layout

    def _create_portfolio_card(self):
        card = QFrame()
        card.setObjectName("portfolioCard")
        card.setMinimumHeight(250)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 26)
        card_layout.setSpacing(18)

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

        label_layout.addWidget(portfolio_label)
        label_layout.addWidget(portfolio_description)

        currency_label = QLabel("USDT")
        currency_label.setObjectName("currencyBadge")
        currency_label.setAlignment(Qt.AlignCenter)
        currency_label.setFixedSize(58, 30)

        top_layout.addLayout(label_layout)
        top_layout.addStretch()
        top_layout.addWidget(
            currency_label,
            alignment=Qt.AlignTop,
        )

        self.value = QLabel("$0.00")
        self.value.setObjectName("portfolioValue")
        self.value.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        divider = QFrame()
        divider.setObjectName("cardDivider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)

        account_layout = QHBoxLayout()
        account_layout.setContentsMargins(0, 0, 0, 0)
        account_layout.setSpacing(20)

        funding_box = self._create_account_box(
            title="Funding",
            description="Fon hesabı",
        )
        self.funding_value = funding_box["value"]

        trading_box = self._create_account_box(
            title="Trading",
            description="Spot işlem hesabı",
        )
        self.trading_value = trading_box["value"]

        account_layout.addWidget(funding_box["widget"])
        account_layout.addWidget(trading_box["widget"])

        card_layout.addLayout(top_layout)
        card_layout.addWidget(self.value)
        card_layout.addStretch()
        card_layout.addWidget(divider)
        card_layout.addLayout(account_layout)

        return card

    def _create_account_box(self, title, description):
        widget = QFrame()
        widget.setObjectName("accountBox")
        widget.setMinimumHeight(82)

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

    def _create_summary_grid(self):
        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        cards = (
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

        for column, (title, description) in enumerate(cards):
            card = self._create_placeholder_card(
                title,
                description,
            )
            grid.addWidget(card, 0, column)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        return grid

    def _create_placeholder_card(self, title, description):
        card = QFrame()
        card.setObjectName("summaryCard")
        card.setMinimumHeight(140)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 19, 20, 19)
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
        coming_soon.setAlignment(Qt.AlignLeft)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(coming_soon)

        return card

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

            QFrame#statusBadge {{
                background-color: #131A20;
                border: 1px solid {self.CARD_BORDER_COLOR};
                border-radius: 15px;
            }}

            QLabel#statusDot {{
                background-color: {self.TEXT_MUTED};
                border-radius: 4px;
            }}

            QLabel#statusText {{
                color: {self.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
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
                font-weight: 750;
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
                font-weight: 650;
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
            """
        )

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if not portfolio:
            self._set_waiting_status()
            return

        self.on_portfolio_updated(portfolio)

    def on_portfolio_updated(self, portfolio):
        total = float(portfolio.get("total_usdt", 0.0))
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
        self.status.setText("Bekleniyor")
        self.status.setStyleSheet(
            f"""
            color: {self.TEXT_SECONDARY};
            font-size: 12px;
            font-weight: 600;
            """
        )
        self.status_dot.setStyleSheet(
            f"""
            background-color: {self.TEXT_MUTED};
            border-radius: 4px;
            """
        )

    def _set_connected_status(self):
        self.status.setText("API Bağlı")
        self.status.setStyleSheet(
            f"""
            color: {self.ACCENT_GREEN};
            font-size: 12px;
            font-weight: 600;
            """
        )
        self.status_dot.setStyleSheet(
            f"""
            background-color: {self.ACCENT_GREEN};
            border-radius: 4px;
            """
        )

    def _set_error_status(self):
        self.status.setText("Bağlantı Hatası")
        self.status.setStyleSheet(
            f"""
            color: {self.ERROR_RED};
            font-size: 12px;
            font-weight: 600;
            """
        )
        self.status_dot.setStyleSheet(
            f"""
            background-color: {self.ERROR_RED};
            border-radius: 4px;
            """
        )