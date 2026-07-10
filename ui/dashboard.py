from PySide6.QtWidgets import (
    QLabel,
    QFrame,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class DashboardPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        layout.addSpacing(50)

        
        
        card = QFrame()
        card.setFixedHeight(125)
        
        card.setStyleSheet("""
            QFrame {
                background-color: #1E222D;
                border: 1px solid #2A2E39;
                border-radius: 12px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(4)

        label = QLabel("TOPLAM PORTFÖY")
        label.setStyleSheet("""
            color: #FFFFFF;
            font-size: 11px;
            font-weight: 800;
            letter-spacing: 1px;
            border: none;
            background: transparent;
        """)

        balance_row = QHBoxLayout()
        balance_row.setContentsMargins(0, 0, 0, 0)
        balance_row.setSpacing(30)

        self.value = QLabel("$0.00 USDT")
        self.value.setStyleSheet("""
            color: #00C087;
            font-size: 32px;
            font-weight: 800;
            border: none;
            background: transparent;
        """)

        details_layout = QVBoxLayout()
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(4)

        self.funding_value = QLabel("Funding: $0.00")
        self.funding_value.setStyleSheet("""
            color: #C7CDD6;
            font-size: 16px;
            font-weight: 700;
            border: none;
            background: transparent;
        """)

        self.trading_value = QLabel("Trading: $0.00")
        self.trading_value.setStyleSheet("""
            color: #C7CDD6;
            font-size: 16px;
            font-weight: 700;
            border: none;
            background: transparent;
        """)

        details_layout.addWidget(self.funding_value)
        details_layout.addWidget(self.trading_value)

        balance_row.addWidget(self.value)
        balance_row.addStretch()
        balance_row.addLayout(details_layout)

        self.status = QLabel("Bekleniyor...")
        self.status.setStyleSheet("""
            color: #848E9C;
            font-size: 12px;
            border: none;
            background: transparent;
        """)

        card_layout.addWidget(label)
        card_layout.addLayout(balance_row)
        card_layout.addWidget(self.status)

        layout.addWidget(card)
        
        layout.addStretch()

        self.data_manager.portfolio_updated.connect(self.on_portfolio_updated)
        self.data_manager.portfolio_error.connect(self.on_portfolio_error)

        self.refresh()

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if not portfolio:
            self.status.setText("Bekleniyor...")
            return

        self.on_portfolio_updated(portfolio)

    def on_portfolio_updated(self, portfolio):
        total = portfolio["total_usdt"]
        funding_total = portfolio.get("funding_usdt", 0.0)
        trading_total = portfolio.get("trading_usdt", 0.0)

        self.value.setText(f"${total:,.2f} USDT")
        self.funding_value.setText(f"Funding: ${funding_total:,.2f}")
        self.trading_value.setText(f"Trading: ${trading_total:,.2f}")

        self.status.setText("API Bağlı")
        self.status.setStyleSheet("""
            color: #00C087;
            font-size: 12px;
            border: none;
            background: transparent;
        """)

    def on_portfolio_error(self, error):
        self.status.setText("Bağlantı Hatası")
        self.status.setStyleSheet("""
            color: #F6465D;
            font-size: 12px;
            background: transparent;
        """)