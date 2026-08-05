import os
import sys
import tempfile
from pathlib import Path

if sys.platform.startswith("linux"):
    os.environ.setdefault(
        "QT_QPA_PLATFORM",
        "xcb",
    )

from PySide6.QtCore import (
    QEvent,
    QLockFile,
    QObject,
    QTimer,
    Qt,
)
from PySide6.QtGui import QAction, QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)
from database.settings_db import get_all_app_settings
from services.data_manager import DataManager
from ui.main_window import MainWindow


APP_ID = "io.github.erenynk.CryptoDesk"


def single_instance_lock_path() -> Path:
    runtime_directory = Path(
        os.environ.get("XDG_RUNTIME_DIR")
        or tempfile.gettempdir()
    )

    if hasattr(os, "getuid"):
        user_token = str(os.getuid())
    else:
        user_token = os.environ.get(
            "USERNAME",
            "user",
        )
    test_suffix = ""

    if os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        test_suffix = f"-test-{os.getpid()}"

    return runtime_directory / (
        f"{APP_ID}-{user_token}{test_suffix}.lock"
    )


def acquire_single_instance_lock():
    lock = QLockFile(
        str(single_instance_lock_path())
    )

    if not lock.tryLock(100):
        return None

    return lock


def application_icon_path() -> Path:
    base_path = Path(
        getattr(
            sys,
            "_MEIPASS",
            Path(__file__).resolve().parent,
        )
    )

    return (
        base_path
        / "assets"
        / "icons"
        / "cryptodesk.png"
    )


def load_application_icon() -> QIcon:
    icon_path = application_icon_path()

    if not icon_path.is_file():
        return QIcon()

    return QIcon(str(icon_path))


def balance_widget_window_flags():
    flags = (
        Qt.WindowStaysOnTopHint
        | Qt.FramelessWindowHint
        | Qt.Tool
    )

    platform_name = (
        QApplication.platformName()
        .strip()
        .lower()
    )

    if (
        sys.platform.startswith("linux")
        and platform_name == "xcb"
    ):
        flags |= Qt.X11BypassWindowManagerHint

    return flags


class BalanceWidget(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.balance_hidden = False
        self._shutdown_prepared = False
        self.last_total = 0.0
        self.last_trading = 0.0
        self.setWindowFlags(
            balance_widget_window_flags()
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self.setFixedSize(250, 76)
        outer_layout = QHBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        self.container = QWidget(self)
        self.container.setStyleSheet("""
            QWidget {
                background: rgba(18, 24, 34, 225);
                border: 1px solid rgba(255, 255, 255, 35);
                border-radius: 18px;
            }
        """)

        inner_layout = QHBoxLayout(self.container)
        inner_layout.setContentsMargins(12, 8, 8, 8)
        inner_layout.setSpacing(8)
        self.icon_label = QLabel("💰")
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(30, 42)
        self.icon_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #00C087;
                font-size: 22px;
                border: none;
            }
        """)

        values_layout = QVBoxLayout()
        values_layout.setContentsMargins(0, 0, 0, 0)
        values_layout.setSpacing(1)
        self.balance_label = QLabel("$0.00")
        self.balance_label.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )
        self.balance_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #FFFFFF;
                font-size: 23px;
                font-weight: 800;
                border: none;
            }
        """)
        self.trading_label = QLabel("Trading  $0.00")
        self.trading_label.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )
        self.trading_label.setStyleSheet("""
            QLabel {
                background: transparent;
                color: #9AA4B2;
                font-size: 12px;
                font-weight: 700;
                border: none;
            }
        """)
        values_layout.addWidget(self.balance_label)
        values_layout.addWidget(self.trading_label)
        self.hide_button = QPushButton("⊙")
        self.hide_button.setFixedSize(36, 36)
        self.hide_button.setCursor(Qt.PointingHandCursor)
        self.hide_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 22);
                color: #FFFFFF;
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 18px;
                font-size: 18px;
                font-weight: 800;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 42);
            }

            QPushButton:pressed {
                background: rgba(255, 255, 255, 62);
            }
        """)
        self.hide_button.clicked.connect(self.toggle_balance)

        inner_layout.addWidget(self.icon_label)
        inner_layout.addLayout(values_layout, 1)
        inner_layout.addWidget(self.hide_button)

        outer_layout.addWidget(self.container)
        self.dragging = False
        self.offset = None

        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )

    def prepare_for_shutdown(self):
        if self._shutdown_prepared:
            return

        self._shutdown_prepared = True

        portfolio_signal = getattr(
            self.data_manager,
            "portfolio_updated",
            None,
        )
        disconnect = getattr(
            portfolio_signal,
            "disconnect",
            None,
        )

        if callable(disconnect):
            try:
                disconnect(self.on_portfolio_updated)
            except (RuntimeError, TypeError, ValueError):
                pass

        self.hide()

    def clamp_to_screen(self, pos):
        screen = QApplication.screenAt(pos)

        if screen is None:
            screen = QApplication.primaryScreen()

        area = screen.availableGeometry()
        margin = 4
        x = max(
            area.left() + margin,
            min(
                pos.x(),
                area.right() - self.width() - margin,
            ),
        )

        y = max(
            area.top() + margin,
            min(
                pos.y(),
                area.bottom() - self.height() - margin,
            ),
        )

        return x, y

    def on_portfolio_updated(self, portfolio):
        if self._shutdown_prepared:
            return

        self.last_total = portfolio.get("total_usdt", 0.0)
        self.last_trading = portfolio.get("trading_usdt", 0.0)
        self.update_balance()

    def update_balance(self):
        if self.balance_hidden:
            self.balance_label.setText("••••••")
            self.trading_label.setText("Trading  ••••••")
            self.hide_button.setText("○")
        else:
            self.balance_label.setText(
                f"${self.last_total:,.2f}"
            )
            self.trading_label.setText(
                f"Trading  ${self.last_trading:,.2f}"
            )
            self.hide_button.setText("⊙")

    def toggle_balance(self):
        self.balance_hidden = not self.balance_hidden
        self.update_balance()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            platform = (
                QApplication.platformName()
                .strip()
                .lower()
            )

            if platform.startswith("wayland"):
                window = self.windowHandle()
                if (
                    window is not None
                    and window.startSystemMove()
                ):
                    event.accept()
                    return

            self.dragging = True
            self.offset = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.dragging and self.offset is not None:
            wanted_pos = (
                event.globalPosition().toPoint()
                - self.offset
            )

            x, y = self.clamp_to_screen(wanted_pos)
            self.move(x, y)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        used_manual_drag = self.dragging

        self.dragging = False
        self.offset = None
        if used_manual_drag:
            x, y = self.clamp_to_screen(
                self.pos()
            )
            self.move(x, y)

        super().mouseReleaseEvent(event)


class ApplicationShutdownCoordinator(QObject):
    def __init__(
        self,
        app: QApplication,
        window: MainWindow,
        balance_widget: BalanceWidget,
        instance_lock=None,
    ):
        super().__init__()

        self.app = app
        self.window = window
        self.balance_widget = balance_widget
        self.instance_lock = instance_lock
        self.tray_manager = None
        self._exit_requested = False
        self._quit_scheduled = False
        self._worker = None

        self.window.installEventFilter(self)

    def set_tray_manager(self, tray_manager):
        self.tray_manager = tray_manager

    def _release_instance_lock(self):
        instance_lock = self.instance_lock
        self.instance_lock = None

        if instance_lock is None:
            return

        unlock = getattr(
            instance_lock,
            "unlock",
            None,
        )

        if not callable(unlock):
            return

        try:
            unlock()
        except RuntimeError:
            pass

    def eventFilter(self, watched, event):
        if (
            watched is self.window
            and event.type() == QEvent.Close
            and self._should_intercept_close()
        ):
            event.ignore()
            self.request_exit()
            return True

        return False

    def _should_intercept_close(self):
        if getattr(self.window, "_allow_close", False):
            return True

        minimize_to_tray = bool(
            getattr(
                self.window,
                "_minimize_to_tray_enabled",
                False,
            )
        )
        tray_available = False
        checker = getattr(
            self.window,
            "system_tray_available",
            None,
        )

        if callable(checker):
            try:
                tray_available = bool(checker())
            except RuntimeError:
                tray_available = False

        return not (
            minimize_to_tray
            and tray_available
        )

    def request_exit(self):
        if self._exit_requested:
            return

        self._exit_requested = True
        self._release_instance_lock()
        self.window.allow_application_close()
        self.balance_widget.prepare_for_shutdown()
        self.window.hide()

        if self.tray_manager is not None:
            self.tray_manager.tray_icon.hide()

        alarm_monitor = getattr(
            self.window,
            "alarm_monitor",
            None,
        )
        stop_alarm_monitor = getattr(
            alarm_monitor,
            "stop",
            None,
        )

        if callable(stop_alarm_monitor):
            stop_alarm_monitor()

        portfolio_page = getattr(
            self.window,
            "portfolio_page",
            None,
        )

        if portfolio_page is None:
            self._complete_exit()
            return

        portfolio_page._shutting_down = True
        refresh_timer = getattr(
            portfolio_page,
            "refresh_timer",
            None,
        )
        stop_refresh_timer = getattr(
            refresh_timer,
            "stop",
            None,
        )

        if callable(stop_refresh_timer):
            stop_refresh_timer()

        worker = getattr(
            portfolio_page,
            "worker",
            None,
        )

        if worker is None:
            self._complete_exit()
            return

        self._worker = worker
        finished_signal = getattr(
            worker,
            "finished",
            None,
        )
        connect_finished = getattr(
            finished_signal,
            "connect",
            None,
        )

        if callable(connect_finished):
            connect_finished(
                self._on_worker_finished
            )

        is_running = getattr(
            worker,
            "isRunning",
            None,
        )
        running = bool(
            is_running()
            if callable(is_running)
            else False
        )

        if not running:
            self._on_worker_finished()
            return

        request_interruption = getattr(
            worker,
            "requestInterruption",
            None,
        )

        if callable(request_interruption):
            request_interruption()

        if callable(is_running) and not is_running():
            self._on_worker_finished()

    def _on_worker_finished(self):
        worker = self._worker
        self._worker = None

        portfolio_page = getattr(
            self.window,
            "portfolio_page",
            None,
        )

        if (
            portfolio_page is not None
            and getattr(
                portfolio_page,
                "worker",
                None,
            ) is worker
        ):
            portfolio_page.worker = None

        self._complete_exit()

    def _complete_exit(self):
        if self._quit_scheduled:
            return

        self._quit_scheduled = True
        shutdown = getattr(
            self.window,
            "shutdown",
            None,
        )

        if callable(shutdown):
            shutdown()

        QTimer.singleShot(
            0,
            self.app.quit,
        )


class SystemTrayManager:
    def __init__(
        self,
        app: QApplication,
        window: MainWindow,
    ):
        self.app = app
        self.window = window
        self.shutdown_coordinator = None

        self.tray_icon = QSystemTrayIcon(self.window)
        self.tray_icon.setToolTip("CryptoDesk")

        icon = self.window.windowIcon()
        if icon.isNull():
            icon = self.app.style().standardIcon(
                QStyle.SP_ComputerIcon
            )

        self.tray_icon.setIcon(icon)
        self.window.setWindowIcon(icon)

        self.menu = QMenu()

        self.open_action = QAction(
            "CryptoDesk'i Aç",
            self.menu,
        )
        self.open_action.triggered.connect(
            self.show_main_window
        )
        self.exit_action = QAction(
            "Çıkış",
            self.menu,
        )
        self.exit_action.triggered.connect(
            self.exit_application
        )

        self.menu.addAction(self.open_action)
        self.menu.addSeparator()
        self.menu.addAction(self.exit_action)

        self.tray_icon.setContextMenu(self.menu)
        self.tray_icon.activated.connect(
            self.on_tray_activated
        )

        self.tray_icon.show()

    def set_shutdown_coordinator(
        self,
        shutdown_coordinator,
    ):
        self.shutdown_coordinator = (
            shutdown_coordinator
        )

    def show_main_window(self):
        self.window.show_from_tray()

    def exit_application(self):
        self.window.allow_application_close()
        self.tray_icon.hide()

        shutdown_coordinator = getattr(
            self,
            "shutdown_coordinator",
            None,
        )

        if shutdown_coordinator is not None:
            shutdown_coordinator.request_exit()
            return

        shutdown = getattr(
            self.window,
            "shutdown",
            None,
        )

        if callable(shutdown):
            shutdown()

        self.app.quit()

    def on_tray_activated(self, reason):
        if reason in (
            QSystemTrayIcon.Trigger,
            QSystemTrayIcon.DoubleClick,
        ):
            self.show_main_window()


def main():
    app = QApplication(sys.argv)
    app.setDesktopFileName(APP_ID)
    app.setFont(QFont("Segoe UI", 10))

    instance_lock = acquire_single_instance_lock()

    if instance_lock is None:
        return

    app_icon = load_application_icon()

    if not app_icon.isNull():
        app.setWindowIcon(app_icon)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QApplication.setQuitOnLastWindowClosed(True)
    else:
        QApplication.setQuitOnLastWindowClosed(False)
    data_manager = DataManager()
    app_settings = get_all_app_settings()
    data_manager.apply_app_settings(app_settings)

    window = MainWindow()
    window.setWindowTitle("CryptoDesk")

    if not app_icon.isNull():
        window.setWindowIcon(app_icon)

    screen = app.primaryScreen()
    available = screen.availableGeometry()
    window_width = min(
        int(1320 * 1.10),
        available.width(),
    )
    window_height = min(
        int(780 * 1.10),
        available.height(),
    )

    window.resize(window_width, window_height)

    window.move(
        available.left()
        + (available.width() - window_width) // 2,
        available.top()
        + (available.height() - window_height) // 2,
    )

    window.show()

    balance_widget = BalanceWidget(data_manager)
    shutdown_coordinator = (
        ApplicationShutdownCoordinator(
            app=app,
            window=window,
            balance_widget=balance_widget,
            instance_lock=instance_lock,
        )
    )
    shutdown_started = False

    def shutdown_runtime():
        nonlocal shutdown_started

        if shutdown_started:
            return

        shutdown_started = True
        balance_widget.prepare_for_shutdown()
        window.shutdown()

    app.aboutToQuit.connect(shutdown_runtime)

    margin = 4
    balance_widget.move(
        available.right() - balance_widget.width() - margin,
        available.bottom() - balance_widget.height() - margin,
    )

    balance_widget_enabled = app_settings.get(
        "balance_widget_enabled",
        True,
    )

    if balance_widget_enabled:
        balance_widget.show()
    else:
        balance_widget.hide()

    def apply_runtime_settings(settings):
        data_manager.apply_app_settings(settings)
        balance_widget_enabled = settings.get(
            "balance_widget_enabled",
            True,
        )

        if balance_widget_enabled:
            balance_widget.show()
        else:
            balance_widget.hide()

    window.settings_page.app_settings_changed.connect(
        apply_runtime_settings
    )

    tray_manager = None
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray_manager = SystemTrayManager(
            app=app,
            window=window,
        )
        tray_manager.set_shutdown_coordinator(
            shutdown_coordinator
        )
        shutdown_coordinator.set_tray_manager(
            tray_manager
        )

    try:
        exit_code = app.exec()
    finally:
        shutdown_coordinator._release_instance_lock()

    _ = (
        instance_lock,
        data_manager,
        balance_widget,
        shutdown_coordinator,
        tray_manager,
    )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()  # pragma: no cover - uygulama giriş noktası
