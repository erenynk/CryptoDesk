from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from services.alarm_monitor import AlarmMonitor
from services.data_manager import DataManager
from ui.alarms import AlarmsPage
from ui.dashboard import DashboardPage
from ui.notification_popup import NotificationManager
from ui.portfolio import PortfolioPage
from ui.settings import SettingsPage
from ui.watchlist import WatchlistPage


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self._allow_close = False
        self.notification_manager = NotificationManager()

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
        self.menu.setEditTriggers(
            QListWidget.NoEditTriggers
        )
        self.menu.setSelectionMode(
            QListWidget.SingleSelection
        )

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

        self.dashboard_page = DashboardPage(
            self.data_manager
        )

        self.portfolio_page = PortfolioPage(
            self.data_manager,
            self.dashboard_page,
        )

        self.watchlist_page = WatchlistPage(
            self.data_manager
        )

        self.alarms_page = AlarmsPage(
            self.data_manager
        )

        self.settings_page = SettingsPage()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.portfolio_page)
        self.pages.addWidget(self.watchlist_page)
        self.pages.addWidget(self.alarms_page)
        self.pages.addWidget(self.settings_page)

        layout.addWidget(self.pages)

        self.menu.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )
        self.menu.setCurrentRow(0)

        self.alarm_monitor = AlarmMonitor(
            self.data_manager,
            self,
        )

        self.alarm_monitor.alarm_triggered.connect(
            self.on_alarm_triggered
        )

        self.alarm_monitor.alarms_checked.connect(
            self.alarms_page.load_alarms
        )

        self.alarm_monitor.start()

    def show_from_tray(self):
        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.raise_()
        self.activateWindow()

    def allow_application_close(self):
        self._allow_close = True

    def closeEvent(self, event: QCloseEvent):
        if self._allow_close:
            self.alarm_monitor.stop()
            event.accept()
            return

        if self.system_tray_available():
            event.ignore()
            self.hide()
            return

        event.accept()

    @staticmethod
    def system_tray_available():
        from PySide6.QtWidgets import QSystemTrayIcon

        return QSystemTrayIcon.isSystemTrayAvailable()

    def on_alarm_triggered(self, alarm):
        symbol = alarm["symbol"]
        current_price = alarm["current_price"]
        target_price = alarm["target_price"]
        condition = alarm["condition"]

        if condition == "above":
            message = (
                f"{symbol}, belirlenen hedef fiyatın "
                f"üzerine çıktı."
            )
        else:
            message = (
                f"{symbol}, belirlenen hedef fiyatın "
                f"altına düştü."
            )

        self.notification_manager.show_alarm(
            title=f"{symbol} Fiyat Alarmı",
            message=message,
            current_price=self.format_alarm_price(
                current_price
            ),
            target_price=self.format_alarm_price(
                target_price
            ),
            note=alarm.get("note", ""),
        )

    @staticmethod
    def format_alarm_price(price):
        if price >= 1:
            return f"${price:,.2f}"

        if price >= 0.01:
            return f"${price:,.4f}"

        return f"${price:,.8f}"