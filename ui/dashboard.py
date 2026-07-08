from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QWidget


class DashboardPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        layout = QVBoxLayout(self)

        
        card = QFrame()
        card.setStyleSheet("""
            QFrame{
                background:#26282d;
                border-radius:12px;
            }
        """)

        card_layout = QVBoxLayout(card)

        label = QLabel("Toplam Portföy")
        label.setStyleSheet("font-size:18px;")

        self.value = QLabel("$0.00")
        self.value.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
        """)

        self.status = QLabel("Bekleniyor...")
        self.status.setStyleSheet("color:orange;")

        card_layout.addWidget(label)
        card_layout.addWidget(self.value)
        card_layout.addWidget(self.status)

        layout.addWidget(card)
        layout.addStretch()

        self.data_manager.portfolio_updated.connect(self.on_portfolio_updated)
        self.data_manager.portfolio_error.connect(self.on_portfolio_error)

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if not portfolio:
            self.status.setText("Bekleniyor...")
            return

        self.on_portfolio_updated(portfolio)

    def on_portfolio_updated(self, portfolio):
        total = portfolio["total_usdt"]

        self.value.setText(f"${total:,.2f}")
        self.status.setText("API Bağlı")
        self.status.setStyleSheet("color:#00C087;")

    def on_portfolio_error(self, error):
        self.status.setText("Bağlantı Hatası")
        self.status.setStyleSheet("color:#F6465D;")