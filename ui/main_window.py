from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from ui.dashboard import DashboardPage
from ui.portfolio import PortfolioPage
from ui.watchlist import WatchlistPage
from ui.alarms import AlarmsPage
from ui.settings import SettingsPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("CryptoDesk")
        self.resize(1300, 800)

        self.setStyleSheet("""
            QMainWindow{
                background:#202124;
            }

            QWidget{
                background:#202124;
                color:white;
                font-size:14px;
            }

            QListWidget{
                background:#2a2b2f;
                border:none;
                padding:10px;
            }

            QListWidget::item{
                padding:12px;
                border-radius:8px;
            }

            QListWidget::item:selected{
                background:#3d7eff;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Sol Menü
        self.menu = QListWidget()
        self.menu.setFixedWidth(220)

        items = [
            "📊 Dashboard",
            "💰 Portfolio",
            "⭐ Watchlist",
            "🔔 Alarms",
            "⚙ Settings",
        ]

        for item in items:
            self.menu.addItem(QListWidgetItem(item))

        layout.addWidget(self.menu)

        # Sayfalar
        self.pages = QStackedWidget()

        self.pages.addWidget(DashboardPage())
        self.pages.addWidget(PortfolioPage())
        self.pages.addWidget(WatchlistPage())
        self.pages.addWidget(AlarmsPage())
        self.pages.addWidget(SettingsPage())

        layout.addWidget(self.pages)

        self.menu.currentRowChanged.connect(self.pages.setCurrentIndex)

        self.menu.setCurrentRow(0)