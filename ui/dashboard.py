from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from ui.theme import Theme, scroll_bar_style
from ui.widgets.card import Card
from ui.widgets.page_header import PageHeader
from ui.widgets.status_badge import StatusBadge
from services import alarm_service, watchlist_service


class PerformanceChart(QWidget):
    PERIODS = (
        ("1G", "1d"),
        ("7G", "7d"),
        ("30G", "30d"),
        ("90G", "90d"),
        ("1Y", "1y"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)

        self._changes = {key: None for _, key in self.PERIODS}
        self.setMinimumHeight(170)
        self.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

    def set_changes(self, changes):
        for _, key in self.PERIODS:
            value = changes.get(key)
            self._changes[key] = (
                float(value)
                if isinstance(value, (int, float))
                else None
            )
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)

        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        outer = self.rect().adjusted(10, 12, -10, -10)
        chart_rect = QRectF(
            outer.left(),
            outer.top() + 24,
            outer.width(),
            max(outer.height() - 52, 60),
        )

        painter.setPen(
            QPen(QColor(255, 255, 255, 16), 1)
        )
        painter.drawLine(
            QPointF(chart_rect.left(), chart_rect.center().y()),
            QPointF(chart_rect.right(), chart_rect.center().y()),
        )

        values = [
            self._changes[key]
            for _, key in self.PERIODS
        ]
        available = [value for value in values if value is not None]

        if not available:
            painter.setPen(QColor(Theme.TEXT_MUTED))
            painter.drawText(
                outer,
                Qt.AlignCenter,
                "Portföy geçmişi oluştuğunda dönemsel değişimler burada görünecek",
            )
            self._draw_period_labels(painter, chart_rect)
            return

        max_abs = max(max(abs(value) for value in available), 1.0)
        points = []

        for index, value in enumerate(values):
            x = (
                chart_rect.left()
                + chart_rect.width()
                * index
                / max(len(values) - 1, 1)
            )

            if value is None:
                y = chart_rect.center().y()
            else:
                normalized = value / max_abs
                y = (
                    chart_rect.center().y()
                    - normalized
                    * chart_rect.height()
                    * 0.42
                )

            points.append(QPointF(x, y))

        path = QPainterPath(points[0])
        for point in points[1:]:
            path.lineTo(point)

        fill_path = QPainterPath(path)
        fill_path.lineTo(
            QPointF(points[-1].x(), chart_rect.bottom())
        )
        fill_path.lineTo(
            QPointF(points[0].x(), chart_rect.bottom())
        )
        fill_path.closeSubpath()

        gradient = QLinearGradient(
            0,
            chart_rect.top(),
            0,
            chart_rect.bottom(),
        )
        gradient.setColorAt(0, QColor(24, 201, 139, 70))
        gradient.setColorAt(1, QColor(24, 201, 139, 4))
        painter.fillPath(fill_path, gradient)

        painter.setPen(QPen(QColor(Theme.ACCENT), 2.1))
        painter.drawPath(path)

        label_font = QFont(Theme.FONT_FAMILY, 9)
        label_font.setBold(True)
        painter.setFont(label_font)

        for index, point in enumerate(points):
            value = values[index]
            color = QColor(Theme.TEXT_MUTED)

            if value is not None:
                color = QColor(
                    Theme.ACCENT
                    if value >= 0
                    else Theme.ERROR
                )

            painter.setBrush(color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(point, 4, 4)

            painter.setPen(color)
            text = "—" if value is None else f"{value:+.2f}%"
            painter.drawText(
                QRectF(
                    point.x() - 38,
                    point.y() - 28,
                    76,
                    20,
                ),
                Qt.AlignCenter,
                text,
            )

        self._draw_period_labels(painter, chart_rect)

    def _draw_period_labels(self, painter, chart_rect):
        painter.setPen(QColor(Theme.TEXT_SECONDARY))
        font = QFont(Theme.FONT_FAMILY, 9)
        font.setBold(True)
        painter.setFont(font)

        for index, (label, _) in enumerate(self.PERIODS):
            x = (
                chart_rect.left()
                + chart_rect.width()
                * index
                / max(len(self.PERIODS) - 1, 1)
            )
            painter.drawText(
                QRectF(
                    x - 30,
                    chart_rect.bottom() + 10,
                    60,
                    20,
                ),
                Qt.AlignCenter,
                label,
            )


class DashboardPage(QWidget):
    RESPONSIVE_BREAKPOINT = 920

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.layout_mode = None
        self.account_cards = []
        self.summary_cards = []

        self.setObjectName("dashboardPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self.refresh()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("dashboardScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.content_widget = QWidget()
        self.content_widget.setObjectName("dashboardContent")
        self.content_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        self.main_layout = QVBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        self.main_layout.setSpacing(Theme.PAGE_SPACING)

        self.status_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="dashboardStatusBadge",
        )

        self.header = PageHeader(
            title="Dashboard",
            subtitle=(
                "Portföy durumunu ve hesap dağılımını "
                "tek ekrandan takip et."
            ),
            right_widget=self.status_badge,
            object_name="dashboardHeader",
        )
        self.main_layout.addWidget(self.header)

        self.hero_card = self._create_hero_card()
        self.main_layout.addWidget(self.hero_card)

        self.summary_container = QWidget()
        self.summary_container.setObjectName("summaryContainer")

        self.summary_grid = QGridLayout(self.summary_container)
        self.summary_grid.setContentsMargins(0, 0, 0, 0)
        self.summary_grid.setHorizontalSpacing(16)
        self.summary_grid.setVerticalSpacing(16)

        self._create_summary_cards()
        self.main_layout.addWidget(self.summary_container)
        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area)

        self._set_layout_mode("wide")

    def _create_hero_card(self):
        card = Card(
            "dashboardHeroCard",
            hover=False,
            radius=20,
            shadow=True,
            palette="blue_dark",
        )
        card.setMinimumHeight(350)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(22)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(6)

        eyebrow = QLabel("TOPLAM PORTFÖY")
        eyebrow.setObjectName("heroEyebrow")

        description = QLabel(
            "Funding ve Trading hesaplarının birleşik güncel değeri"
        )
        description.setObjectName("heroDescription")
        description.setWordWrap(True)

        title_layout.addWidget(eyebrow)
        title_layout.addWidget(description)

        self.hero_body = QWidget()
        self.hero_body.setObjectName("heroBody")
        self.hero_body_grid = QGridLayout(self.hero_body)
        self.hero_body_grid.setContentsMargins(0, 0, 0, 0)
        self.hero_body_grid.setHorizontalSpacing(28)
        self.hero_body_grid.setVerticalSpacing(16)

        self.metric_widget = QWidget()
        self.metric_widget.setObjectName("metricWidget")

        metric_layout = QVBoxLayout(self.metric_widget)
        metric_layout.setContentsMargins(0, 0, 0, 0)
        metric_layout.setSpacing(8)

        self.value = QLabel("$0.00")
        self.value.setObjectName("heroValue")
        self.value.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.hero_caption = QLabel(
            "Dönemsel portföy performansı"
        )
        self.hero_caption.setObjectName("heroCaption")

        metric_layout.addWidget(self.value)
        metric_layout.addWidget(self.hero_caption)
        metric_layout.addStretch()

        self.performance_chart = PerformanceChart()

        divider = QFrame()
        divider.setObjectName("heroDivider")
        divider.setFrameShape(QFrame.HLine)
        divider.setFixedHeight(1)

        self.account_container = QWidget()
        self.account_container.setObjectName("accountContainer")

        self.account_grid = QGridLayout(self.account_container)
        self.account_grid.setContentsMargins(0, 0, 0, 0)
        self.account_grid.setHorizontalSpacing(16)
        self.account_grid.setVerticalSpacing(14)

        funding = self._create_account_card(
            title="Funding",
            description="Fon hesabı",
            accent_text="Cüzdan bakiyesi",
        )
        self.funding_value = funding["value"]
        self.account_cards.append(funding["widget"])

        trading = self._create_account_card(
            title="Trading",
            description="Spot işlem hesabı",
            accent_text="İşlem bakiyesi",
        )
        self.trading_value = trading["value"]
        self.account_cards.append(trading["widget"])

        layout.addLayout(title_layout)
        layout.addWidget(self.hero_body)
        layout.addWidget(divider)
        layout.addWidget(self.account_container)

        return card

    def _create_account_card(self, title, description, accent_text):
        card = Card(
            "dashboardAccountCard",
            hover=True,
            radius=14,
            shadow=False,
            palette="blue_dark",
        )
        card.setMinimumHeight(98)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        accent_bar = QFrame()
        accent_bar.setObjectName("accountAccentBar")
        accent_bar.setFixedWidth(3)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(4)

        top_line = QHBoxLayout()
        top_line.setContentsMargins(0, 0, 0, 0)
        top_line.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("accountTitle")

        accent_label = QLabel(accent_text)
        accent_label.setObjectName("accountMeta")

        top_line.addWidget(title_label)
        top_line.addStretch()
        top_line.addWidget(accent_label)

        value_label = QLabel("$0.00")
        value_label.setObjectName("accountValue")
        value_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        description_label = QLabel(description)
        description_label.setObjectName("accountDescription")

        text_layout.addLayout(top_line)
        text_layout.addWidget(value_label)
        text_layout.addWidget(description_label)

        layout.addWidget(accent_bar)
        layout.addLayout(text_layout, 1)

        return {
            "widget": card,
            "value": value_label,
        }

    def _create_summary_cards(self):
        performance = self._create_summary_card(
            title="Portföy Performansı",
            description="Son kayıtlı dönemsel değişim",
        )
        self.performance_summary_value = performance["value"]
        self.performance_summary_detail = performance["detail"]
        self.summary_cards.append(performance["widget"])

        alarms = self._create_summary_card(
            title="Aktif Alarmlar",
            description="Kurulu fiyat alarmı durumu",
        )
        self.alarms_summary_value = alarms["value"]
        self.alarms_summary_detail = alarms["detail"]
        self.summary_cards.append(alarms["widget"])

        watchlist = self._create_summary_card(
            title="Watchlist Özeti",
            description="Takip edilen varlık görünümü",
        )
        self.watchlist_summary_value = watchlist["value"]
        self.watchlist_summary_detail = watchlist["detail"]
        self.summary_cards.append(watchlist["widget"])

    def _create_summary_card(self, title, description):
        card = Card(
            "dashboardSummaryCard",
            hover=True,
            radius=16,
            shadow=False,
            palette="blue_dark",
        )
        card.setMinimumHeight(158)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(7)

        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(10)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")

        indicator = QLabel("•")
        indicator.setObjectName("summaryIndicator")

        top_row.addWidget(title_label)
        top_row.addStretch()
        top_row.addWidget(indicator)

        description_label = QLabel(description)
        description_label.setObjectName("summaryDescription")
        description_label.setWordWrap(True)

        value_label = QLabel("—")
        value_label.setObjectName("summaryValue")

        detail_label = QLabel("Veri bekleniyor")
        detail_label.setObjectName("summaryDetail")
        detail_label.setWordWrap(True)

        layout.addLayout(top_row)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(value_label)
        layout.addWidget(detail_label)

        return {
            "widget": card,
            "value": value_label,
            "detail": detail_label,
        }

    @staticmethod
    def _clear_grid(grid):
        while grid.count():
            item = grid.takeAt(0)
            widget = item.widget()

            if widget is not None:
                widget.setParent(None)

    def _set_layout_mode(self, mode):
        if mode == self.layout_mode:
            return

        self._clear_grid(self.hero_body_grid)
        self._clear_grid(self.account_grid)
        self._clear_grid(self.summary_grid)

        if mode == "narrow":
            self.main_layout.setContentsMargins(22, 22, 22, 28)
            self.main_layout.setSpacing(20)

            self.hero_body_grid.addWidget(
                self.metric_widget,
                0,
                0,
            )
            self.hero_body_grid.addWidget(
                self.performance_chart,
                1,
                0,
            )

            for row, card in enumerate(self.account_cards):
                self.account_grid.addWidget(card, row, 0)

            for row, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(card, row, 0)

            self.hero_body_grid.setColumnStretch(0, 1)
            self.account_grid.setColumnStretch(0, 1)
            self.summary_grid.setColumnStretch(0, 1)

        else:
            self.main_layout.setContentsMargins(
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
            )
            self.main_layout.setSpacing(Theme.PAGE_SPACING)

            self.hero_body_grid.addWidget(
                self.metric_widget,
                0,
                0,
            )
            self.hero_body_grid.addWidget(
                self.performance_chart,
                0,
                1,
            )
            self.hero_body_grid.setColumnStretch(0, 2)
            self.hero_body_grid.setColumnStretch(1, 3)

            self.account_grid.addWidget(
                self.account_cards[0],
                0,
                0,
            )
            self.account_grid.addWidget(
                self.account_cards[1],
                0,
                1,
            )
            self.account_grid.setColumnStretch(0, 1)
            self.account_grid.setColumnStretch(1, 1)

            for column, card in enumerate(self.summary_cards):
                self.summary_grid.addWidget(card, 0, column)
                self.summary_grid.setColumnStretch(column, 1)

        self.layout_mode = mode

        self.hero_body.adjustSize()
        self.account_container.adjustSize()
        self.summary_container.adjustSize()
        self.hero_card.adjustSize()
        self.content_widget.adjustSize()

    def _connect_signals(self):
        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )
        self.data_manager.portfolio_error.connect(
            self.on_portfolio_error
        )

    def _apply_styles(self):
        self.setStyleSheet(
            scroll_bar_style()
            + f"""
            QWidget#dashboardPage {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0A121A,
                    stop:1 #0D1B25
                );
            }}

            QScrollArea#dashboardScrollArea,
            QScrollArea#dashboardScrollArea > QWidget > QWidget {{
                background: transparent;
                border: none;
            }}

            QWidget#dashboardContent,
            QWidget#summaryContainer,
            QWidget#accountContainer,
            QWidget#heroBody,
            QWidget#metricWidget {{
                background: transparent;
                border: none;
            }}

            QLabel {{
                background: transparent;
                border: none;
                color: {Theme.TEXT_PRIMARY};
                font-family: "{Theme.FONT_FAMILY}";
            }}

            QLabel#heroEyebrow {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#heroDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
            }}

            QLabel#heroValue {{
                color: {Theme.ACCENT};
                font-size: 46px;
                font-weight: 700;
            }}

            QLabel#heroCaption {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 600;
            }}

            QFrame#heroDivider {{
                background-color: rgba(255,255,255,20);
                border: none;
            }}

            QFrame#accountAccentBar {{
                background-color: {Theme.ACCENT};
                border: none;
                border-radius: 1px;
            }}

            QLabel#accountTitle {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#accountMeta {{
                color: {Theme.TEXT_MUTED};
                font-size: 10px;
            }}

            QLabel#accountValue {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 20px;
                font-weight: 700;
            }}

            QLabel#accountDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
            }}

            QLabel#summaryTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#summaryIndicator {{
                color: {Theme.ACCENT};
                font-size: 18px;
            }}

            QLabel#summaryDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
            }}

            QLabel#summaryValue {{
                color: {Theme.ACCENT};
                font-size: 24px;
                font-weight: 700;
            }}

            QLabel#summaryDetail {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
                font-weight: 600;
            }}
            """
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)

        available_width = self.scroll_area.viewport().width()

        if available_width < self.RESPONSIVE_BREAKPOINT:
            self._set_layout_mode("narrow")
        else:
            self._set_layout_mode("wide")

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if not portfolio:
            self._set_waiting_status()
            return

        self.on_portfolio_updated(portfolio)

    def on_portfolio_updated(self, portfolio):
        total = float(portfolio.get("total_usdt", 0.0))
        funding_total = float(
            portfolio.get("funding_usdt", 0.0)
        )
        trading_total = float(
            portfolio.get("trading_usdt", 0.0)
        )

        self.value.setText(f"${total:,.2f}")
        self.funding_value.setText(
            f"${funding_total:,.2f}"
        )
        self.trading_value.setText(
            f"${trading_total:,.2f}"
        )

        performance = portfolio.get("performance", {})
        if not isinstance(performance, dict):
            performance = {}

        self.performance_chart.set_changes(performance)
        self._update_dashboard_summaries(performance)
        self._set_connected_status()

    def _update_dashboard_summaries(self, performance):
        one_day = performance.get("1d")

        if isinstance(one_day, (int, float)):
            self.performance_summary_value.setText(
                f"{float(one_day):+.2f}%"
            )
            self.performance_summary_value.setStyleSheet(
                f"color: {Theme.ACCENT if one_day >= 0 else Theme.ERROR};"
            )
            self.performance_summary_detail.setText(
                "1 günlük portföy değişimi"
            )
        else:
            self.performance_summary_value.setText("—")
            self.performance_summary_value.setStyleSheet("")
            self.performance_summary_detail.setText(
                "Geçmiş kayıt oluşması bekleniyor"
            )

        alarms = alarm_service.get_all_alarms()
        active_alarms = [
            alarm
            for alarm in alarms
            if alarm.get("is_active")
            and not alarm.get("is_triggered")
        ]
        triggered_count = sum(
            1 for alarm in alarms if alarm.get("is_triggered")
        )

        self.alarms_summary_value.setText(
            str(len(active_alarms))
        )
        self.alarms_summary_detail.setText(
            f"{triggered_count} tamamlanan alarm"
        )

        watchlist_items = watchlist_service.get_items()
        changes = []

        for item in watchlist_items:
            symbol = watchlist_service.normalize_symbol(
                item.get("symbol", "")
            )
            current_price = self.data_manager.get_price(symbol)
            added_price = item.get("added_price")

            if (
                current_price
                and added_price
                and added_price > 0
            ):
                changes.append(
                    ((current_price - added_price) / added_price)
                    * 100
                )

        self.watchlist_summary_value.setText(
            str(len(watchlist_items))
        )

        if changes:
            average_change = sum(changes) / len(changes)
            self.watchlist_summary_detail.setText(
                f"Ortalama değişim {average_change:+.2f}%"
            )
        else:
            self.watchlist_summary_detail.setText(
                "Takip edilen toplam varlık"
            )

    def showEvent(self, event):
        super().showEvent(event)
        portfolio = self.data_manager.get_portfolio() or {}
        performance = portfolio.get("performance", {})
        if not isinstance(performance, dict):
            performance = {}
        self._update_dashboard_summaries(performance)

    def on_portfolio_error(self, error):
        self._set_error_status()

    def _set_waiting_status(self):
        self.status_badge.set_status(
            "Bekleniyor",
            StatusBadge.NEUTRAL,
        )

    def _set_connected_status(self):
        self.status_badge.set_status(
            "API Bağlı",
            StatusBadge.SUCCESS,
        )

    def _set_error_status(self):
        self.status_badge.set_status(
            "Bağlantı Hatası",
            StatusBadge.ERROR,
        )
