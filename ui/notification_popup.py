from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QTimer,
    Qt,
)
from PySide6.QtGui import QColor, QCursor
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class NotificationPopup(QWidget):
    WIDTH = 390
    HEIGHT_WITHOUT_NOTE = 190
    HEIGHT_WITH_NOTE = 225

    DISPLAY_TIME_MS = 15000
    ANIMATION_TIME_MS = 250

    def __init__(
        self,
        title: str,
        message: str,
        current_price: str,
        target_price: str,
        note: str = "",
        parent=None,
    ):
        super().__init__(parent)

        self.note = note.strip()
        self.popup_height = (
            self.HEIGHT_WITH_NOTE
            if self.note
            else self.HEIGHT_WITHOUT_NOTE
        )

        self._remaining_ms = self.DISPLAY_TIME_MS
        self._elapsed_step_ms = 100
        self._closing = False
        self._manager = None

        self.setWindowFlags(
            Qt.Tool
            | Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        self.setFixedSize(
            self.WIDTH,
            self.popup_height,
        )

        self._build_ui(
            title=title,
            message=message,
            current_price=current_price,
            target_price=target_price,
            note=self.note,
        )

        self.timer = QTimer(self)
        self.timer.setInterval(self._elapsed_step_ms)
        self.timer.timeout.connect(self._update_timer)

        self.slide_animation = QPropertyAnimation(
            self,
            b"pos",
            self,
        )
        self.slide_animation.setDuration(
            self.ANIMATION_TIME_MS
        )
        self.slide_animation.setEasingCurve(
            QEasingCurve.OutCubic
        )

        self.opacity_animation = QPropertyAnimation(
            self,
            b"windowOpacity",
            self,
        )
        self.opacity_animation.setDuration(
            self.ANIMATION_TIME_MS
        )
        self.opacity_animation.setEasingCurve(
            QEasingCurve.OutCubic
        )

    def _build_ui(
        self,
        title: str,
        message: str,
        current_price: str,
        target_price: str,
        note: str,
    ):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(12, 12, 12, 12)

        self.container = QFrame()
        self.container.setObjectName("notificationContainer")
        self.container.setStyleSheet("""
            QFrame#notificationContainer {
                background-color: rgba(20, 27, 39, 245);
                border: 1px solid rgba(255, 255, 255, 32);
                border-radius: 14px;
            }

            QLabel {
                background: transparent;
                border: none;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.container)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 150))
        self.container.setGraphicsEffect(shadow)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(18, 15, 16, 14)
        container_layout.setSpacing(9)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)

        icon_label = QLabel("🔔")
        icon_label.setFixedWidth(28)
        icon_label.setStyleSheet("""
            QLabel {
                color: #00C087;
                font-size: 20px;
            }
        """)

        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                font-weight: 800;
            }
        """)

        close_button = QPushButton("×")
        close_button.setFixedSize(28, 28)
        close_button.setCursor(Qt.PointingHandCursor)
        close_button.setToolTip("Bildirimi kapat")
        close_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #9AA4B2;
                border: none;
                border-radius: 7px;
                font-size: 20px;
                font-weight: 500;
                padding: 0px;
            }

            QPushButton:hover {
                background-color: rgba(255, 255, 255, 18);
                color: #FFFFFF;
            }

            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 30);
            }
        """)
        close_button.clicked.connect(self.close_animated)

        header_layout.addWidget(icon_label)
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_button)

        message_label = QLabel(message)
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                color: #C7CDD6;
                font-size: 13px;
                font-weight: 600;
            }
        """)

        price_layout = QHBoxLayout()
        price_layout.setContentsMargins(0, 2, 0, 2)
        price_layout.setSpacing(32)

        current_layout = self._create_price_section(
            label_text="ANLIK FİYAT",
            price_text=current_price,
            value_color="#00C087",
        )

        target_layout = self._create_price_section(
            label_text="HEDEF FİYAT",
            price_text=target_price,
            value_color="#FFFFFF",
        )

        price_layout.addLayout(current_layout)
        price_layout.addLayout(target_layout)
        price_layout.addStretch()

        container_layout.addLayout(header_layout)
        container_layout.addWidget(message_label)
        container_layout.addLayout(price_layout)

        if note:
            note_layout = QHBoxLayout()
            note_layout.setContentsMargins(0, 1, 0, 1)
            note_layout.setSpacing(7)

            note_title = QLabel("Not:")
            note_title.setStyleSheet("""
                QLabel {
                    color: #848E9C;
                    font-size: 12px;
                    font-weight: 700;
                }
            """)

            note_label = QLabel(note)
            note_label.setWordWrap(True)
            note_label.setStyleSheet("""
                QLabel {
                    color: #D7DCE3;
                    font-size: 12px;
                    font-weight: 500;
                }
            """)

            note_layout.addWidget(
                note_title,
                0,
                Qt.AlignTop,
            )
            note_layout.addWidget(
                note_label,
                1,
            )

            container_layout.addLayout(note_layout)

        container_layout.addStretch()

        self.progress_bar = QFrame()
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet("""
            QFrame {
                background-color: #00C087;
                border: none;
                border-radius: 1px;
            }
        """)

        container_layout.addWidget(self.progress_bar)
        outer_layout.addWidget(self.container)

    @staticmethod
    def _create_price_section(
        label_text: str,
        price_text: str,
        value_color: str,
    ):
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(label_text)
        label.setStyleSheet("""
            QLabel {
                color: #848E9C;
                font-size: 10px;
                font-weight: 800;
                letter-spacing: 1px;
                background: transparent;
                border: none;
            }
        """)

        value = QLabel(price_text)
        value.setStyleSheet(f"""
            QLabel {{
                color: {value_color};
                font-size: 15px;
                font-weight: 800;
                background: transparent;
                border: none;
            }}
        """)

        layout.addWidget(label)
        layout.addWidget(value)

        return layout

    def show_at(self, final_position: QPoint):
        self._final_position = final_position

        start_position = QPoint(
            final_position.x() + 45,
            final_position.y(),
        )

        self.move(start_position)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()

        self.slide_animation.stop()
        self.slide_animation.setStartValue(start_position)
        self.slide_animation.setEndValue(final_position)

        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(0.0)
        self.opacity_animation.setEndValue(1.0)

        self.slide_animation.start()
        self.opacity_animation.start()
        self.timer.start()

    def move_animated(self, final_position: QPoint):
        self._final_position = final_position

        self.slide_animation.stop()
        self.slide_animation.setStartValue(self.pos())
        self.slide_animation.setEndValue(final_position)
        self.slide_animation.start()

    def close_animated(self):
        if self._closing:
            return

        self._closing = True
        self.timer.stop()

        end_position = QPoint(
            self.x() + 45,
            self.y(),
        )

        self.slide_animation.stop()
        self.slide_animation.setStartValue(self.pos())
        self.slide_animation.setEndValue(end_position)

        self.opacity_animation.stop()
        self.opacity_animation.setStartValue(
            self.windowOpacity()
        )
        self.opacity_animation.setEndValue(0.0)

        self.opacity_animation.finished.connect(
            self._finish_close
        )

        self.slide_animation.start()
        self.opacity_animation.start()

    def _finish_close(self):
        try:
            self.opacity_animation.finished.disconnect(
                self._finish_close
            )
        except RuntimeError:
            pass

        if self._manager is not None:
            self._manager.remove_popup(self)

        self.close()
        self.deleteLater()

    def _update_timer(self):
        if self.underMouse():
            return

        self._remaining_ms -= self._elapsed_step_ms

        progress = max(
            0.0,
            self._remaining_ms / self.DISPLAY_TIME_MS,
        )

        available_width = max(
            1,
            self.container.width() - 36,
        )

        self.progress_bar.setFixedWidth(
            int(available_width * progress)
        )

        if self._remaining_ms <= 0:
            self.close_animated()

    def enterEvent(self, event):
        self.setCursor(QCursor(Qt.ArrowCursor))
        super().enterEvent(event)


class NotificationManager:
    SCREEN_MARGIN = 18
    POPUP_SPACING = 8
    MAX_VISIBLE_POPUPS = 4

    def __init__(self):
        self.popups = []

    def show_alarm(
        self,
        title: str,
        message: str,
        current_price: str,
        target_price: str,
        note: str = "",
    ):
        popup = NotificationPopup(
            title=title,
            message=message,
            current_price=current_price,
            target_price=target_price,
            note=note,
        )

        popup._manager = self
        self.popups.append(popup)

        while len(self.popups) > self.MAX_VISIBLE_POPUPS:
            oldest = self.popups[0]
            oldest.close_animated()
            break

        positions = self._calculate_positions()

        for existing_popup, position in zip(
            self.popups,
            positions,
        ):
            if existing_popup is popup:
                existing_popup.show_at(position)
            else:
                existing_popup.move_animated(position)

    def remove_popup(self, popup):
        if popup in self.popups:
            self.popups.remove(popup)

        positions = self._calculate_positions()

        for existing_popup, position in zip(
            self.popups,
            positions,
        ):
            existing_popup.move_animated(position)

    def _calculate_positions(self):
        screen = QApplication.screenAt(
            QCursor.pos()
        )

        if screen is None:
            screen = QApplication.primaryScreen()

        available = screen.availableGeometry()

        x = (
            available.right()
            - NotificationPopup.WIDTH
            - self.SCREEN_MARGIN
            + 1
        )

        positions = []
        bottom_y = available.bottom() - self.SCREEN_MARGIN + 1

        for popup in self.popups:
            y = bottom_y - popup.height()

            positions.append(
                QPoint(x, y)
            )

            bottom_y = (
                y
                - self.POPUP_SPACING
            )

        return positions