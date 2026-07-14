from PySide6.QtCore import Qt
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

from ui.theme import (
    Theme,
    label_style,
    page_style,
    page_title_style,
    scroll_bar_style,
)
from ui.dashboard import ElevatedInnerPanel
from ui.widgets.page_header import PageHeader
from ui.widgets.status_badge import StatusBadge


class AnalyticsPage(QWidget):
    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.metric_labels = {}

        self.setObjectName("analyticsPage")
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
        self.scroll_area.setObjectName("analyticsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        content = QWidget()
        content.setObjectName("analyticsContent")

        main_layout = QVBoxLayout(content)
        main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        main_layout.setSpacing(20)

        self.status_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="analyticsStatusBadge",
        )

        header = PageHeader(
            title="Analytics",
            subtitle=(
                "Portföy geçmişi ve hesap bazlı temel "
                "istatistikleri takip et."
            ),
            right_widget=self.status_badge,
            object_name="analyticsHeader",
        )
        main_layout.addWidget(header)

        self.summary_grid = QGridLayout()
        self.summary_grid.setContentsMargins(0, 0, 0, 0)
        self.summary_grid.setHorizontalSpacing(16)
        self.summary_grid.setVerticalSpacing(16)

        total_card = self._create_account_card(
            key="total",
            title="Toplam Portföy",
            description="Tüm hesapların birleşik geçmiş özeti",
        )
        funding_card = self._create_account_card(
            key="funding",
            title="Funding",
            description="Uzun vadeli fon hesabı geçmiş özeti",
        )
        trading_card = self._create_account_card(
            key="trading",
            title="Trading",
            description="Spot işlem hesabı geçmiş özeti",
        )

        self.summary_grid.addWidget(total_card, 0, 0)
        self.summary_grid.addWidget(funding_card, 0, 1)
        self.summary_grid.addWidget(trading_card, 0, 2)

        for column in range(3):
            self.summary_grid.setColumnStretch(column, 1)

        main_layout.addLayout(self.summary_grid)

        history_card = self._create_history_card()
        main_layout.addWidget(history_card)

        performance_card = self._create_performance_card()
        main_layout.addWidget(performance_card)

        main_layout.addStretch()

        self.scroll_area.setWidget(content)
        root_layout.addWidget(self.scroll_area)

    def _create_account_card(
        self,
        key,
        title,
        description,
    ):
        card = ElevatedInnerPanel(
            f"{key}AnalyticsCard",
            radius=17,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        card.setMinimumHeight(220)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 32)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("analyticsCardTitle")

        description_label = QLabel(description)
        description_label.setObjectName(
            "analyticsCardDescription"
        )
        description_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addSpacing(10)

        values = (
            ("highest_usdt", "En Yüksek"),
            ("lowest_usdt", "En Düşük"),
            ("average_usdt", "Ortalama"),
        )

        for metric_key, metric_title in values:
            row = self._create_metric_row(
                title=metric_title,
                object_name="analyticsMetricValue",
            )
            layout.addLayout(row["layout"])
            self.metric_labels[
                f"{key}.{metric_key}"
            ] = row["value"]

        layout.addStretch()
        return card

    def _create_history_card(self):
        card = ElevatedInnerPanel(
            "historyOverviewCard",
            radius=17,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 32)
        layout.setSpacing(12)

        title = QLabel("Geçmiş Durumu")
        title.setObjectName("analyticsCardTitle")

        description = QLabel(
            "Kaydedilen snapshot sayısı ve kayıt aralığı"
        )
        description.setObjectName(
            "analyticsCardDescription"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(24)
        grid.setVerticalSpacing(12)

        entries = (
            ("snapshot_count", "Snapshot Sayısı"),
            ("first_timestamp", "İlk Kayıt"),
            ("last_timestamp", "Son Kayıt"),
        )

        for column, (key, label) in enumerate(entries):
            section = QWidget()
            section.setObjectName("analyticsInfoSection")

            section_layout = QVBoxLayout(section)
            section_layout.setContentsMargins(0, 0, 0, 0)
            section_layout.setSpacing(5)

            title_label = QLabel(label)
            title_label.setObjectName("analyticsInfoTitle")

            value_label = QLabel("—")
            value_label.setObjectName("analyticsInfoValue")
            value_label.setTextInteractionFlags(
                Qt.TextSelectableByMouse
            )

            section_layout.addWidget(title_label)
            section_layout.addWidget(value_label)

            grid.addWidget(section, 0, column)
            grid.setColumnStretch(column, 1)
            self.metric_labels[key] = value_label

        layout.addLayout(grid)
        return card

    def _create_performance_card(self):
        card = ElevatedInnerPanel(
            "performanceOverviewCard",
            radius=17,
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(34, 28, 34, 32)
        layout.setSpacing(12)

        title = QLabel("Hesap Performansı")
        title.setObjectName("analyticsCardTitle")

        description = QLabel(
            "Toplam, Funding ve Trading hesaplarının "
            "dönemsel değişimi"
        )
        description.setObjectName(
            "analyticsCardDescription"
        )

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(4)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(10)

        periods = (
            ("1d", "1 Gün"),
            ("7d", "7 Gün"),
            ("30d", "30 Gün"),
            ("90d", "90 Gün"),
            ("1y", "1 Yıl"),
        )
        groups = (
            ("total", "Toplam"),
            ("funding", "Funding"),
            ("trading", "Trading"),
        )

        for row, (group_key, group_title) in enumerate(groups):
            group_label = QLabel(group_title)
            group_label.setObjectName("analyticsPerformanceGroup")
            grid.addWidget(group_label, row + 1, 0)

            for column, (period_key, period_title) in enumerate(
                periods,
                start=1,
            ):
                if row == 0:
                    period_label = QLabel(period_title)
                    period_label.setObjectName(
                        "analyticsPerformancePeriod"
                    )
                    period_label.setAlignment(Qt.AlignCenter)
                    grid.addWidget(period_label, 0, column)

                value_label = QLabel("—")
                value_label.setObjectName(
                    "analyticsPerformanceValue"
                )
                value_label.setAlignment(Qt.AlignCenter)
                grid.addWidget(value_label, row + 1, column)

                self.metric_labels[
                    f"performance.{group_key}.{period_key}"
                ] = value_label

        grid.setColumnStretch(0, 2)

        for column in range(1, 6):
            grid.setColumnStretch(column, 1)

        layout.addLayout(grid)
        return card

    @staticmethod
    def _create_metric_row(title, object_name):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("analyticsMetricTitle")

        value_label = QLabel("—")
        value_label.setObjectName(object_name)
        value_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )
        value_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        layout.addWidget(title_label)
        layout.addStretch()
        layout.addWidget(value_label)

        return {
            "layout": layout,
            "value": value_label,
        }

    def _connect_signals(self):
        self.data_manager.portfolio_updated.connect(
            self.on_portfolio_updated
        )
        self.data_manager.portfolio_error.connect(
            self.on_portfolio_error
        )

    def refresh(self):
        portfolio = self.data_manager.get_portfolio()

        if isinstance(portfolio, dict):
            self.on_portfolio_updated(portfolio)
        else:
            self._set_waiting_state()

    def on_portfolio_updated(self, portfolio):
        analytics = portfolio.get("analytics", {})
        breakdown = portfolio.get(
            "performance_breakdown",
            {},
        )

        if not isinstance(analytics, dict):
            analytics = {}

        if not isinstance(breakdown, dict):
            breakdown = {}

        summary = analytics.get("summary", {})

        if not isinstance(summary, dict):
            summary = {}

        for group_key in ("total", "funding", "trading"):
            group_data = summary.get(group_key, {})

            if not isinstance(group_data, dict):
                group_data = {}

            for metric_key in (
                "highest_usdt",
                "lowest_usdt",
                "average_usdt",
            ):
                label = self.metric_labels[
                    f"{group_key}.{metric_key}"
                ]
                value = group_data.get(metric_key)
                label.setText(self._format_usdt(value))

        snapshot_count = summary.get("snapshot_count")
        self.metric_labels["snapshot_count"].setText(
            str(snapshot_count)
            if isinstance(snapshot_count, int)
            else "—"
        )
        self.metric_labels["first_timestamp"].setText(
            self._format_timestamp(
                summary.get("first_timestamp")
            )
        )
        self.metric_labels["last_timestamp"].setText(
            self._format_timestamp(
                summary.get("last_timestamp")
            )
        )

        for group_key in ("total", "funding", "trading"):
            group_data = breakdown.get(group_key, {})

            if not isinstance(group_data, dict):
                group_data = {}

            for period_key in (
                "1d",
                "7d",
                "30d",
                "90d",
                "1y",
            ):
                label = self.metric_labels[
                    f"performance.{group_key}.{period_key}"
                ]
                value = group_data.get(period_key)

                if isinstance(value, (int, float)):
                    color = (
                        Theme.ACCENT
                        if value >= 0
                        else Theme.ERROR
                    )
                    label.setText(f"{float(value):+.2f}%")
                    label.setStyleSheet(
                        f"color: {color};"
                    )
                else:
                    label.setText("—")
                    label.setStyleSheet(
                        f"color: {Theme.TEXT_MUTED};"
                    )

        self.status_badge.set_status(
            "Veri Hazır",
            StatusBadge.SUCCESS,
        )

    def on_portfolio_error(self, error):
        self.status_badge.set_status(
            "Veri Hatası",
            StatusBadge.ERROR,
        )

    def _set_waiting_state(self):
        self.status_badge.set_status(
            "Bekleniyor",
            StatusBadge.NEUTRAL,
        )

    @staticmethod
    def _format_usdt(value):
        if not isinstance(value, (int, float)):
            return "—"

        return f"${float(value):,.2f}"

    @staticmethod
    def _format_timestamp(value):
        if not value:
            return "—"

        text = str(value)

        try:
            date_part, time_part = text.split("T", 1)
            time_part = time_part.split("+", 1)[0]
            return f"{date_part} {time_part[:8]}"
        except ValueError:
            return text

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("analyticsPage")
            + label_style()
            + page_title_style()
            + scroll_bar_style()
            + f"""
            QWidget#analyticsPage {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #172630,
                    stop: 0.50 #13212B,
                    stop: 1 #101923
                );
            }}

            QScrollArea#analyticsScrollArea,
            QScrollArea#analyticsScrollArea
            > QWidget
            > QWidget,
            QWidget#analyticsContent,
            QWidget#analyticsInfoSection {{
                background: transparent;
                border: none;
            }}

            QFrame#totalAnalyticsCard,
            QFrame#fundingAnalyticsCard,
            QFrame#tradingAnalyticsCard,
            QFrame#historyOverviewCard,
            QFrame#performanceOverviewCard {{
                background: transparent;
                border: none;
            }}

            QLabel#analyticsCardTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#analyticsCardDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#analyticsMetricTitle,
            QLabel#analyticsInfoTitle,
            QLabel#analyticsPerformancePeriod {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#analyticsMetricValue,
            QLabel#analyticsInfoValue {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#analyticsPerformanceGroup {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#analyticsPerformanceValue {{
                color: {Theme.TEXT_MUTED};
                font-size: 13px;
                font-weight: 700;
            }}
            """
        )
