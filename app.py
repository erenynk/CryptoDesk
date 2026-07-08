import sys

from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt

from services.data_manager import DataManager
from ui.main_window import MainWindow


class BalanceWidget(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.balance_hidden = False
        self.last_total = 0.0

        self.setWindowFlags(
            Qt.WindowStaysOnTopHint |
            Qt.FramelessWindowHint |
            Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setFixedSize(235, 62)

        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background: rgba(18, 18, 18, 95);
                border: 1px solid rgba(255, 255, 255, 40);
                border-radius: 30px;
            }
        """)

        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(12, 6, 8, 6)
        inner_layout.setSpacing(4)

        self.icon_label = QLabel("💰")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(28, 36)
        self.icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: white;
                font-size: 24px;
                border: none;
            }
        """)

        self.balance_label = QLabel("$0.00")
        self.balance_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self.balance_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #FFFFFF;
                font-size: 28px;
                font-weight: 900;
                border: none;
            }
        """)

        self.hide_button = QPushButton("⊙")
        self.hide_button.setFixedSize(38, 38)
        self.hide_button.setCursor(Qt.PointingHandCursor)
        self.hide_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 35);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 19px;
                font-size: 20px;
                font-weight: 800;
                padding-bottom: 2px;
            }

            QPushButton:hover {
                background: rgba(255, 255, 255, 55);
            }

            QPushButton:pressed {
                background: rgba(255, 255, 255, 75);
            }
        """)
        self.hide_button.clicked.connect(self.toggle_balance)

        inner_layout.addWidget(self.icon_label)
        inner_layout.addWidget(self.balance_label, 1)
        inner_layout.addWidget(self.hide_button)

        outer_layout.addWidget(self.container)

        self.dragging = False
        self.offset = None

        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )

    def clamp_to_screen(self, pos):
        screen = QApplication.screenAt(pos)

        if screen is None:
            screen = QApplication.primaryScreen()

        area = screen.availableGeometry()
        margin = 4

        x = max(
            area.left() + margin,
            min(pos.x(), area.right() - self.width() - margin)
        )

        y = max(
            area.top() + margin,
            min(pos.y(), area.bottom() - self.height() - margin)
        )

        return x, y

    def on_portfolio_updated(self, portfolio):
        self.last_total = portfolio["total_usdt"]
        self.update_balance()

    def update_balance(self):
        if self.balance_hidden:
            self.balance_label.setText("••••••")
            self.hide_button.setText("○")
        else:
            self.balance_label.setText(f"${self.last_total:,.2f}")
            self.hide_button.setText("⊙")

    def toggle_balance(self):
        self.balance_hidden = not self.balance_hidden
        self.update_balance()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if self.dragging:
            wanted_pos = event.globalPosition().toPoint() - self.offset
            x, y = self.clamp_to_screen(wanted_pos)
            self.move(x, y)

    def mouseReleaseEvent(self, event):
        self.dragging = False

        x, y = self.clamp_to_screen(self.pos())
        self.move(x, y)


app = QApplication(sys.argv)

data_manager = DataManager()

window = MainWindow()
window.show()

balance_widget = BalanceWidget(data_manager)
balance_widget.move(100, 100)
balance_widget.show()

sys.exit(app.exec())