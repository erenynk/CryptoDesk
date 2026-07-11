from PySide6.QtCore import (
    QEasingCurve,
    QPointF,
    QPropertyAnimation,
    QRectF,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QCloseEvent,
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
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
from ui.theme import Theme
from ui.watchlist import WatchlistPage


class MainWindow(QMainWindow):
    WINDOW_BACKGROUND = Theme.BACKGROUND
    SIDEBAR_BACKGROUND = Theme.SIDEBAR_BACKGROUND
    SIDEBAR_BORDER = Theme.BORDER_SOFT
    CONTENT_BACKGROUND = Theme.CONTENT_BACKGROUND

    TEXT_PRIMARY = Theme.TEXT_PRIMARY
    TEXT_SECONDARY = Theme.TEXT_SECONDARY
    TEXT_MUTED = Theme.TEXT_MUTED

    MENU_HOVER = Theme.CARD_BACKGROUND_HOVER
    MENU_SELECTED = Theme.ACCENT_SOFT

    def __init__(self):
        super().__init__()

        self._allow_close = False
        self.notification_manager = NotificationManager()
        self._page_animation = None

        self.setWindowTitle("Caspian")
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
        sidebar.setFixedWidth(252)

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 26, 20, 22)
        sidebar_layout.setSpacing(0)

        brand_widget = self._create_brand()
        sidebar_layout.addWidget(brand_widget)

        sidebar_layout.addSpacing(34)

        navigation_label = QLabel("MENÜ")
        navigation_label.setObjectName("navigationLabel")
        sidebar_layout.addWidget(navigation_label)

        sidebar_layout.addSpacing(10)

        self.menu = QListWidget()
        self.menu.setObjectName("navigationMenu")
        self.menu.setFocusPolicy(Qt.NoFocus)
        self.menu.setEditTriggers(QListWidget.NoEditTriggers)
        self.menu.setSelectionMode(QListWidget.SingleSelection)
        self.menu.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.menu.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.menu.setIconSize(QSize(20, 20))
        self.menu.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        menu_font = QFont(Theme.FONT_FAMILY, 10)
        menu_font.setWeight(QFont.DemiBold)
        self.menu.setFont(menu_font)

        menu_items = (
            ("Dashboard", "dashboard", "#4F9CF9"),
            ("Portfolio", "portfolio", "#18C98B"),
            ("Watchlist", "watchlist", "#F1B84B"),
            ("Alarmlar", "alarms", "#F06475"),
            ("Ayarlar", "settings", "#9B7CF6"),
        )

        for text, icon_name, icon_color in menu_items:
            item = QListWidgetItem(
                self._create_nav_icon(
                    icon_name,
                    QColor(icon_color),
                ),
                text,
            )
            item.setSizeHint(self._menu_item_size())
            self.menu.addItem(item)

        self.menu.setFixedHeight(len(menu_items) * 56)

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
        layout.setSpacing(12)

        logo = QLabel()
        logo.setObjectName("brandLogo")
        logo.setAlignment(Qt.AlignCenter)
        logo.setFixedSize(46, 46)
        logo.setPixmap(self._create_brand_logo())

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(2)

        title = QLabel("Caspian")
        title.setObjectName("brandTitle")

        subtitle = QLabel("Portfolio Terminal")
        subtitle.setObjectName("brandSubtitle")

        text_layout.addWidget(title)
        text_layout.addWidget(subtitle)

        layout.addWidget(logo)
        layout.addLayout(text_layout)
        layout.addStretch()

        return brand

    @staticmethod
    def _create_brand_logo():
        size = 46
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        background = QLinearGradient(0, 0, size, size)
        background.setColorAt(0.0, QColor("#183A55"))
        background.setColorAt(1.0, QColor("#0B1D2B"))

        painter.setPen(QPen(QColor("#2C6074"), 1.2))
        painter.setBrush(background)
        painter.drawRoundedRect(
            1,
            1,
            size - 2,
            size - 2,
            14,
            14,
        )

        wave_gradient = QLinearGradient(8, 10, 38, 36)
        wave_gradient.setColorAt(0.0, QColor("#55D6B2"))
        wave_gradient.setColorAt(1.0, QColor("#1A8FA8"))

        wave_path = QPainterPath()
        wave_path.moveTo(11, 17)
        wave_path.cubicTo(17, 10, 28, 9, 35, 15)
        wave_path.cubicTo(29, 14, 23, 17, 20, 22)
        wave_path.cubicTo(17, 27, 22, 32, 34, 31)
        wave_path.cubicTo(27, 37, 15, 35, 11, 27)
        wave_path.cubicTo(8, 23, 8, 20, 11, 17)
        wave_path.closeSubpath()

        painter.setPen(Qt.NoPen)
        painter.setBrush(wave_gradient)
        painter.drawPath(wave_path)

        highlight = QPainterPath()
        highlight.moveTo(14, 18)
        highlight.cubicTo(19, 14, 27, 13, 32, 16)

        painter.setBrush(Qt.NoBrush)
        painter.setPen(
            QPen(
                QColor(255, 255, 255, 95),
                1.4,
                Qt.SolidLine,
                Qt.RoundCap,
                Qt.RoundJoin,
            )
        )
        painter.drawPath(highlight)

        painter.end()
        return pixmap

    def _create_sidebar_footer(self):
        footer = QFrame()
        footer.setObjectName("sidebarFooter")

        layout = QVBoxLayout(footer)
        layout.setContentsMargins(14, 13, 14, 13)
        layout.setSpacing(5)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        dot = QLabel()
        dot.setObjectName("footerStatusDot")
        dot.setFixedSize(8, 8)

        title = QLabel("OKX Spot")
        title.setObjectName("footerTitle")

        description = QLabel("Güvenli bağlantı")
        description.setObjectName("footerDescription")

        top_row.addWidget(dot)
        top_row.addWidget(title)
        top_row.addStretch()

        layout.addLayout(top_row)
        layout.addWidget(description)

        return footer

    @staticmethod
    def _menu_item_size():
        return QSize(196, 48)

    @staticmethod
    def _create_nav_icon(name, color):
        size = 22
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        pen = QPen(color)
        pen.setWidthF(1.7)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)

        if name == "dashboard":
            painter.drawRoundedRect(QRectF(3, 3, 7, 7), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(12, 3, 7, 7), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(3, 12, 7, 7), 1.5, 1.5)
            painter.drawRoundedRect(QRectF(12, 12, 7, 7), 1.5, 1.5)

        elif name == "portfolio":
            painter.drawRoundedRect(QRectF(3, 6, 16, 12), 2, 2)
            painter.drawLine(QPointF(7, 6), QPointF(7, 4))
            painter.drawLine(QPointF(15, 6), QPointF(15, 4))
            painter.drawLine(QPointF(7, 4), QPointF(15, 4))
            painter.drawLine(QPointF(3, 10), QPointF(19, 10))

        elif name == "watchlist":
            points = (
                QPointF(11, 2.5),
                QPointF(13.7, 8),
                QPointF(19.7, 8.8),
                QPointF(15.3, 13.1),
                QPointF(16.3, 19),
                QPointF(11, 16.2),
                QPointF(5.7, 19),
                QPointF(6.7, 13.1),
                QPointF(2.3, 8.8),
                QPointF(8.3, 8),
            )
            for index in range(len(points)):
                painter.drawLine(
                    points[index],
                    points[(index + 1) % len(points)],
                )

        elif name == "alarms":
            painter.drawArc(QRectF(5, 4, 12, 13), 25 * 16, 130 * 16)
            painter.drawArc(QRectF(5, 4, 12, 13), 205 * 16, 130 * 16)
            painter.drawLine(QPointF(5, 13), QPointF(3.5, 16))
            painter.drawLine(QPointF(3.5, 16), QPointF(18.5, 16))
            painter.drawLine(QPointF(18.5, 16), QPointF(17, 13))
            painter.drawArc(QRectF(8.5, 16, 5, 4), 200 * 16, 140 * 16)

        elif name == "settings":
            painter.drawEllipse(QRectF(8, 8, 6, 6))
            painter.drawEllipse(QRectF(4, 4, 14, 14))
            for angle in range(0, 360, 45):
                import math
                rad = math.radians(angle)
                x1 = 11 + 7 * math.cos(rad)
                y1 = 11 + 7 * math.sin(rad)
                x2 = 11 + 9 * math.cos(rad)
                y2 = 11 + 9 * math.sin(rad)
                painter.drawLine(
                    QPointF(x1, y1),
                    QPointF(x2, y2),
                )

        painter.end()
        return QIcon(pixmap)

    def _create_pages(self):
        self.dashboard_page = DashboardPage(self.data_manager)

        self.portfolio_page = PortfolioPage(
            self.data_manager,
            self.dashboard_page,
        )

        self.watchlist_page = WatchlistPage(self.data_manager)
        self.alarms_page = AlarmsPage(self.data_manager)
        self.settings_page = SettingsPage()

        self.pages.addWidget(self.dashboard_page)
        self.pages.addWidget(self.portfolio_page)
        self.pages.addWidget(self.watchlist_page)
        self.pages.addWidget(self.alarms_page)
        self.pages.addWidget(self.settings_page)

        self.menu.setCurrentRow(0)

    def _connect_signals(self):
        self.menu.currentRowChanged.connect(
            self._change_page
        )

    def _change_page(self, index):
        if index < 0 or index >= self.pages.count():
            return

        if index == self.pages.currentIndex():
            return

        self.pages.setCurrentIndex(index)
        page = self.pages.currentWidget()

        effect = QGraphicsOpacityEffect(page)
        page.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        animation = QPropertyAnimation(
            effect,
            b"opacity",
            self,
        )
        animation.setDuration(180)
        animation.setStartValue(0.0)
        animation.setEndValue(1.0)
        animation.setEasingCurve(
            QEasingCurve.OutCubic
        )
        animation.finished.connect(
            lambda: page.setGraphicsEffect(None)
        )

        self._page_animation = animation
        animation.start()

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
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #101923,
                    stop: 0.55 #14202B,
                    stop: 1 #182631
                );
                border-right: 1px solid {self.SIDEBAR_BORDER};
            }}

            QWidget#brandWidget {{
                background: transparent;
            }}

            QLabel#brandLogo {{
                background: transparent;
                border: none;
            }}

            QLabel#brandTitle {{
                color: {self.TEXT_PRIMARY};
                background: transparent;
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 20px;
                font-weight: 750;
            }}

            QLabel#brandSubtitle {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 10px;
                font-weight: 500;
            }}

            QLabel#navigationLabel {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                padding-left: 10px;
                font-family: "{Theme.FONT_FAMILY}";
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
                border-radius: 12px;
                padding: 0 16px;
                margin: 4px 0;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 600;
            }}

            QListWidget#navigationMenu::item:hover {{
                color: {self.TEXT_PRIMARY};
                background-color: rgba(22, 31, 43, 220);
                border: 1px solid {Theme.BORDER_HOVER};
            }}

            QListWidget#navigationMenu::item:selected,
            QListWidget#navigationMenu::item:selected:active,
            QListWidget#navigationMenu::item:selected:!active {{
                color: {self.TEXT_PRIMARY};
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 0,
                    stop: 0 rgba(21, 54, 47, 230),
                    stop: 1 rgba(20, 32, 42, 220)
                );
                border: 1px solid {Theme.ACCENT_BORDER};
                border-top-color: #326251;
                border-bottom-color: #1C3B32;
                border-radius: 16px;
                padding: 0 16px;
                margin: 4px 0;
                font-weight: 700;
            }}

            QFrame#sidebarFooter {{
                background-color: rgba(13, 21, 29, 235);
                border: 1px solid {self.SIDEBAR_BORDER};
                border-radius: 14px;
            }}

            QLabel#footerStatusDot {{
                background-color: {Theme.ACCENT};
                border: none;
                border-radius: 4px;
            }}

            QLabel#footerTitle {{
                color: {self.TEXT_PRIMARY};
                background: transparent;
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 13px;
                font-weight: 650;
            }}

            QLabel#footerDescription {{
                color: {self.TEXT_MUTED};
                background: transparent;
                border: none;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 10px;
                font-weight: 500;
                padding-left: 16px;
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
            current_price=self.format_alarm_price(current_price),
            target_price=self.format_alarm_price(target_price),
            note=alarm.get("note", ""),
        )

    @staticmethod
    def format_alarm_price(price):
        if price >= 1:
            return f"${price:,.2f}"

        if price >= 0.01:
            return f"${price:,.4f}"

        return f"${price:,.8f}"
