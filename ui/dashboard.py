from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QWidget


class DashboardPage(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        title = QLabel("Dashboard")
        title.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
        """)

        layout.addWidget(title)

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

        value = QLabel("$0.00")
        value.setStyleSheet("""
            font-size:40px;
            font-weight:bold;
        """)

        status = QLabel("API Bağlı Değil")
        status.setStyleSheet("color:orange;")

        card_layout.addWidget(label)
        card_layout.addWidget(value)
        card_layout.addWidget(status)

        layout.addWidget(card)
        layout.addStretch()