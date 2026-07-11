from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
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
    WINDOW_BACKGROUND = "#0A0E14"
    SIDEBAR_BACKGROUND = "#10161D"
    SIDEBAR_BORDER = "#222C37"
    CONTENT_BACKGROUND = "#0D1117"

    TEXT_PRIMARY = "#F3F5F7"
    TEXT_SECONDARY = "#9AA4B2"
    TEXT_MUTED = "#667180"

    MENU_HOVER = "#17202A"
    MENU_SELECTED = "#192B27"
    MENU_SELECTED_BORDER = "#16C784"

    def __init__(self):
        super().__init__()

        self._allow_close = False
        self.notification_manager = NotificationManager()

        self.setWindowTitle("CryptoDesk")
        self.resize(1360, 840)
        self.setMinimumSize(1100, 700)

        self.data_manager = DataManager()

        self._build_ui()
        self._apply_styles()
        self._create_pages()
        self._connect_signals()
        self._start_alarm_monitor()

    def _build_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("centralWidget")
        self.setCentralWidget(central_widget)

        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.sidebar = self._create_sidebar()
        root_layout.addWidget(self.sidebar)

        self.pages = QStackedWidget()
        self.pages.setObjectName("pageStack")
        root_layout.addWidget(self.pages, 1)

    def _create_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(238)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 24, 18, 20)
        sidebar_layout.setSpacing(0)

        brand_widget = self._create_brand()
        sidebar_layout.addWidget(brand_widget)

        sidebar_layout.addSpacing(30)

        navigation_label = QLabel("MENÜ")
        navigation_label.setObjectName("navigationLabel")
        sidebar_layout.addWidget(navigation_label)

        sidebar_layout.addSpacing(10)

        self.menu = QListWidget()
        self.menu.setObjectName("navigationMenu")
        self.menu.setFocusPolicy(Qt.NoFocus)
        self.menu.setEditTriggers(QListWidget.NoEditTriggers)
        self.menu.setSelectionMode(QListWidget.SingleSelection)
        self.menu.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.menu.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.menu.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        menu_font = QFont("Segoe UI", 10)
        menu_font.setWeight(QFont.DemiBold)
        self.menu.setFont(menu_font)

        menu_items = (
            "Dashboard",
            "Portfolio",
            "Watchlist",
            "Alarmlar",
            "Ayarlar",
        )

        for text in menu_items:
            item = QListWidgetItem(text)
            item.setSizeHint(item.sizeHint().expandedTo(
                self._menu_item_size()
            ))
            self.menu.addItem(item)

        self.menu.setFixedHeight(
            len(menu_items) * 52
        )

        sidebar_layout.addWidget(self.menu)
        sidebar_layout.addStretch()

        footer = self._create_sidebar_footer()
        sidebar_layout.addWidget(footer)

        return sidebar

    def _create_brand(self):
        brand = QWidget()
        brand.setObjectName("brandWidget")

        layout = QHBoxLayout(brand)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(11)

        logo = QLabel("C")
        logo.setObjectName("brandLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(38, 38)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)

        title = QLabel("CryptoDesk")
        title.setObjectName("brandTitle")

        subtitle = QLabel("Portfolio Terminal")
        subtitle.setObjectName("brandSubtitle")

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        layout.addWidget(logo)
        layout.addLayout(text_layout)
        layout.addStretch()

        return brand

    def _create_sidebar_footer(self):
        footer = QFrame()
        footer.setObjectName("sidebarFooter")

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        title = QLabel("OKX Spot")
        title.setObjectName("footerTitle")

        description = QLabel("Güvenli bağlantı")
        description.setObjectName("footerDescription")

        layout.addWidget(title)
        layout.addWidget(description)

        return footer

    @staticmethod
    def _menu_item_size():
        from PySide6.QtCore import QSize

        return QSize(180, 44)

    def _create_pages(self):
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

        self.menu.setCurrentRow(0)

    def _connect_signals(self):
        self.menu.currentRowChanged.connect(
            self.pages.setCurrentIndex
        )

    def _start_alarm_monitor(self):
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

    def _apply_styles(self):
        self.setStyleSheet(
            f"""
            QMainWindow {{
                background-color: {self.WINDOW_BACKGROUND};
            }}

            QWidget#centralWidget {{
                background-color: {self.WINDOW_BACKGROUND};
            }}

            QFrame#sidebar {{
                background-color: {self.SIDEBAR_BACKGROUND};
                border-right: 1px solid {self.SIDEBAR_BORDER};
            }}

            QWidget#brandWidget {{
                background: transparent;
            }}

            QLabel#brandLogo {{
                color: #07100D;
                background-color: {self.MENU_SELECTED_BORDER};
                border: none;
                border-radius: 11px;
                font-family: "Segoe UI";
                font-size: 18px;
                font-weight: 800;
            }}

            QLabel#brandTitle {{
                color: {self.TEXT_PRIMARY};
                background: transparent;
                border: none;
                font-family: "Segoe UI";
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#brandSubtitle {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: 500;
            }}

            QLabel#navigationLabel {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                padding-left: 10px;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QListWidget#navigationMenu {{
                background: transparent;
                border: none;
                outline: none;
                padding: 0;
            }}

            QListWidget#navigationMenu::item {{
                color: {self.TEXT_SECONDARY};
                background: transparent;
                border: 1px solid transparent;
                border-radius: 10px;
                padding: 0 14px;
                margin: 3px 0;
                font-family: "Segoe UI";
                font-size: 13px;
                font-weight: 600;
            }}

            QListWidget#navigationMenu::item:hover {{
                color: {self.TEXT_PRIMARY};
                background-color: {self.MENU_HOVER};
                border-color: #202A35;
            }}

            QListWidget#navigationMenu::item:selected {{
                color: {self.TEXT_PRIMARY};
                background-color: {self.MENU_SELECTED};
                border: 1px solid #24473D;
                border-left: 3px solid {self.MENU_SELECTED_BORDER};
                padding-left: 12px;
            }}

            QListWidget#navigationMenu::item:selected:active {{
                color: {self.TEXT_PRIMARY};
                background-color: {self.MENU_SELECTED};
                border: 1px solid #24473D;
                border-left: 3px solid {self.MENU_SELECTED_BORDER};
            }}

            QListWidget#navigationMenu::item:selected:!active {{
                color: {self.TEXT_PRIMARY};
                background-color: {self.MENU_SELECTED};
                border: 1px solid #24473D;
                border-left: 3px solid {self.MENU_SELECTED_BORDER};
            }}

            QFrame#sidebarFooter {{
                background-color: #111A21;
                border: 1px solid {self.SIDEBAR_BORDER};
                border-radius: 11px;
            }}

            QLabel#footerTitle {{
                color: {self.TEXT_PRIMARY};
                background: transparent;
                border: none;
                font-family: "Segoe UI";
                font-size: 12px;
                font-weight: 650;
            }}

            QLabel#footerDescription {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                font-family: "Segoe UI";
                font-size: 10px;
                font-weight: 500;
            }}

            QStackedWidget#pageStack {{
                background-color: {self.CONTENT_BACKGROUND};
                border: none;
            }}
            """
        )

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