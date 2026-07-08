import sys

from PySide6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PySide6.QtCore import Qt

from services.data_manager import DataManager
from ui.main_window import MainWindow


class BalanceWidget(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(200, 60)

        layout = QVBoxLayout(self)

        self.label = QLabel("💰 Yükleniyor...", self)
        self.label.setStyleSheet("""
            color: #FFFFFF;
            font-weight: bold;
            font-size: 18px;
            background: rgba(20, 20, 20, 200);
            border-radius: 15px;
            padding: 10px;
        """)
        self.label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.label)

        self.dragging = False
        self.offset = None

        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )

    def on_portfolio_updated(self, portfolio):
        total = portfolio["total_usdt"]
        self.update_balance(total)

    def update_balance(self, total):
        self.label.setText(f"💰 ${total:,.2f}")

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self.dragging:
            self.move(
                event.globalPosition().toPoint()
                - self.offset
            )

    def mouseReleaseEvent(self, event):
        self.dragging = False


app = QApplication(sys.argv)

data_manager = DataManager()

window = MainWindow()
window.show()

balance_widget = BalanceWidget(data_manager)
balance_widget.move(100, 100)
balance_widget.show()

sys.exit(app.exec())