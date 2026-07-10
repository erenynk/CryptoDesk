from PySide6.QtCore import Qt

from PySide6.QtGui import QFont

from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from services.data_manager import DataManager

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
            QMainWindow {
                background: #202124;
            }

            QWidget {
                background: #202124;
                color: white;
                font-size: 14px;
            }

            QListWidget {
                background: #2A2B2F;
                border: none;
                outline: none;
                padding: 10px;
            }

            QListWidget::item {
                padding: 14px;
                margin: 4px 0px;
                border-radius: 8px;
                border: none;
                outline: none;
                color: #E5E7EB;
                font-size: 16px;
                font-weight: 700;
            }

            QListWidget::item:hover {
                background: #34363D;
            }

            QListWidget::item:selected {
                background: #3D7EFF;
                color: #FFFFFF;
                border: none;
                outline: none;
            }

            QListWidget::item:selected:active {
                background: #3D7EFF;
                border: none;
                outline: none;
            }

            QListWidget::item:selected:!active {
                background: #3D7EFF;
                border: none;
                outline: none;
            }

            QListWidget::item:focus {
                border: none;
                outline: none;
            }
        """)

        self.data_manager = DataManager()

        central = QWidget()
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        self.menu = QListWidget()
        self.menu.setFixedWidth(220)
        self.menu.setFocusPolicy(Qt.NoFocus)
        self.menu.setEditTriggers(QListWidget.NoEditTriggers)
        self.menu.setSelectionMode(QListWidget.SingleSelection)
        menu_font = QFont("Segoe UI", 11)
        menu_font.setBold(True)
        self.menu.setFont(menu_font)

        for item in (
            "📊 Dashboard",
            "💰 Portfolio",
            "⭐ Watchlist",
            "🔔 Alarms",
            "⚙ Settings",
        ):
            self.menu.addItem(QListWidgetItem(item))

        layout.addWidget(self.menu)

        self.pages = QStackedWidget()

        self.dashboard_page = DashboardPage(self.data_manager)

        self.portfolio_page = PortfolioPage(
            self.data_manager,
            self.dashboard_page,
        )

        self.watchlist_page = WatchlistPage(self.data_manager)

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.portfolio_page)
        self.pages.addWidget(self.watchlist_page)
        self.alarms_page = AlarmsPage(self.data_manager)
        self.pages.addWidget(self.alarms_page)
        self.pages.addWidget(SettingsPage())

        layout.addWidget(self.pages)

        self.menu.currentRowChanged.connect(self.pages.setCurrentIndex)
        self.menu.setCurrentRow(0)