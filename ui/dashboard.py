from PySide6.QtCore import QRectF, QTimer, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QRadialGradient,
)
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from services import alarm_service, watchlist_service
from ui.theme import Theme, scroll_bar_style
from ui.widgets.page_header import PageHeader
from ui.widgets.status_badge import StatusBadge


class SurfaceEngine:
    _noise_tile = None

    @classmethod
    def noise_tile(cls):
        if cls._noise_tile is not None:
            return cls._noise_tile

        size = 96
        tile = QPixmap(size, size)
        tile.fill(Qt.transparent)

        painter = QPainter(tile)
        painter.setPen(Qt.NoPen)

        for y in range(size):
            for x in range(size):
                seed = (
                    x * 37
                    + y * 61
                    + x * y * 3
                ) % 113

                if seed == 0:
                    painter.setBrush(
                        QColor(255, 255, 255, 5)
                    )
                    painter.drawRect(x, y, 1, 1)
                elif seed == 47:
                    painter.setBrush(
                        QColor(0, 0, 0, 5)
                    )
                    painter.drawRect(x, y, 1, 1)
                elif seed == 79:
                    painter.setBrush(
                        QColor(120, 150, 165, 3)
                    )
                    painter.drawRect(x, y, 1, 1)

        painter.end()
        cls._noise_tile = tile
        return cls._noise_tile

    @staticmethod
    def draw_surface(
        painter,
        rect,
        radius,
        base_color,
        start_color,
        end_color,
        glow_color,
        border_color,
        border_top_color,
    ):
        path = QPainterPath()
        path.addRoundedRect(
            rect,
            radius,
            radius,
        )

        painter.save()
        painter.setClipPath(path)

        painter.fillPath(
            path,
            QColor(base_color),
        )

        base_gradient = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.right(),
            rect.bottom(),
        )
        base_gradient.setColorAt(
            0.00,
            QColor(start_color),
        )
        base_gradient.setColorAt(
            1.00,
            QColor(end_color),
        )
        painter.fillPath(
            path,
            base_gradient,
        )

        glow = QRadialGradient(
            rect.left() + rect.width() * 0.14,
            rect.top() + rect.height() * 0.08,
            max(rect.width(), rect.height()) * 1.05,
        )
        glow.setColorAt(
            0.00,
            QColor(glow_color),
        )

        faded_glow = QColor(glow_color)
        faded_glow.setAlpha(
            max(1, faded_glow.alpha() // 3)
        )
        glow.setColorAt(
            0.48,
            faded_glow,
        )
        glow.setColorAt(
            1.00,
            QColor(0, 0, 0, 0),
        )
        painter.fillPath(
            path,
            glow,
        )

        wash = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.left(),
            rect.bottom(),
        )
        wash.setColorAt(
            0.00,
            QColor(255, 255, 255, 5),
        )
        wash.setColorAt(
            0.34,
            QColor(255, 255, 255, 2),
        )
        wash.setColorAt(
            0.70,
            QColor(0, 0, 0, 2),
        )
        wash.setColorAt(
            1.00,
            QColor(0, 0, 0, 7),
        )
        painter.fillPath(
            path,
            wash,
        )

        painter.setOpacity(0.72)
        painter.drawTiledPixmap(
            rect.toRect(),
            SurfaceEngine.noise_tile(),
        )
        painter.setOpacity(1.0)
        painter.restore()

        painter.setPen(
            QPen(
                QColor(border_color),
                1.0,
            )
        )
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)


    @staticmethod
    def draw_page_background(painter, rect):
        painter.fillRect(
            rect,
            QColor("#101923"),
        )

        base = QLinearGradient(
            rect.left(),
            rect.top(),
            rect.right(),
            rect.bottom(),
        )
        base.setColorAt(
            0.00,
            QColor("#172630"),
        )
        base.setColorAt(
            1.00,
            QColor("#101923"),
        )
        painter.fillRect(
            rect,
            base,
        )

        glow = QRadialGradient(
            rect.left() + rect.width() * 0.12,
            rect.top() + rect.height() * 0.06,
            max(rect.width(), rect.height()) * 1.10,
        )
        glow.setColorAt(
            0.00,
            QColor(48, 67, 86, 18),
        )
        glow.setColorAt(
            0.46,
            QColor(35, 49, 66, 6),
        )
        glow.setColorAt(
            1.00,
            QColor(0, 0, 0, 0),
        )
        painter.fillRect(
            rect,
            glow,
        )

        painter.setOpacity(0.80)
        painter.drawTiledPixmap(
            rect.toRect(),
            SurfaceEngine.noise_tile(),
        )
        painter.setOpacity(1.0)


class CorporateSurface(QFrame):
    PALETTES = {
        "hero": {
            "base": "#101B24",
            "start": "#182B38",
            "end": "#0D1720",
            "glow": (58, 78, 103, 18),
            "border": "#293B46",
            "border_top": "#304550",
            "radius": 24,
            "shadow_blur": 48,
            "shadow_alpha": 72,
            "shadow_offset": 6,
        },
        "account": {
            "base": "#101B24",
            "start": "#182B38",
            "end": "#0D1720",
            "glow": (58, 78, 103, 18),
            "border": "#293B46",
            "border_top": "#304550",
            "radius": 17,
            "shadow_blur": 34,
            "shadow_alpha": 62,
            "shadow_offset": 5,
        },
        "total": {
            "base": "#101B24",
            "start": "#182B38",
            "end": "#0D1720",
            "glow": (58, 78, 103, 18),
            "border": "#293B46",
            "border_top": "#304550",
            "radius": 17,
            "shadow_blur": 34,
            "shadow_alpha": 62,
            "shadow_offset": 5,
        },
        "strip": {
            "base": "#0F1922",
            "start": "#162733",
            "end": "#0D1720",
            "glow": (49, 68, 90, 14),
            "border": "#24353F",
            "border_top": "#2B3E49",
            "radius": 19,
            "shadow_blur": 42,
            "shadow_alpha": 66,
            "shadow_offset": 6,
        },
        "overview": {
            "base": "#101B24",
            "start": "#182B38",
            "end": "#0D1720",
            "glow": (58, 78, 103, 18),
            "border": "#293B46",
            "border_top": "#304550",
            "radius": 17,
            "shadow_blur": 34,
            "shadow_alpha": 62,
            "shadow_offset": 5,
        },
    }

    def __init__(
        self,
        role: str,
        object_name: str,
        hover_enabled: bool = False,
        parent=None,
    ):
        super().__init__(parent)

        if role not in self.PALETTES:
            raise ValueError(
                f"Geçersiz yüzey rolü: {role}"
            )

        self._role = role
        self._hover_enabled = hover_enabled
        self._hovered = False

        self.setObjectName(object_name)
        self.setAttribute(
            Qt.WA_StyledBackground,
            False,
        )
        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True,
        )

        palette = self.PALETTES[self._role]

        self._shadow = QGraphicsDropShadowEffect(self)
        self._shadow.setBlurRadius(
            palette["shadow_blur"]
        )
        self._shadow.setOffset(
            0,
            palette["shadow_offset"],
        )
        self._shadow.setColor(
            QColor(
                0,
                0,
                0,
                palette["shadow_alpha"],
            )
        )
        self.setGraphicsEffect(self._shadow)

    def enterEvent(self, event):
        if self._hover_enabled:
            self._hovered = True
            self._shadow.setBlurRadius(
                self.PALETTES[self._role][
                    "shadow_blur"
                ]
                + 4
            )
            self.update()

        super().enterEvent(event)

    def leaveEvent(self, event):
        if self._hover_enabled:
            self._hovered = False
            self._shadow.setBlurRadius(
                self.PALETTES[self._role][
                    "shadow_blur"
                ]
            )
            self.update()

        super().leaveEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing,
        )
        painter.setRenderHint(
            QPainter.SmoothPixmapTransform,
        )

        palette = self.PALETTES[self._role]
        surface_rect = QRectF(self.rect()).adjusted(
            1,
            1,
            -1,
            -1,
        )

        border_color = (
            "#3A5664"
            if self._hovered
            and self._hover_enabled
            else palette["border"]
        )

        glow = QColor(*palette["glow"])

        SurfaceEngine.draw_surface(
            painter=painter,
            rect=surface_rect,
            radius=palette["radius"],
            base_color=palette["base"],
            start_color=palette["start"],
            end_color=palette["end"],
            glow_color=glow,
            border_color=border_color,
            border_top_color=palette["border_top"],
        )

        painter.end()
        super().paintEvent(event)


class ElevatedInnerPanel(QFrame):
    def __init__(
        self,
        object_name,
        radius=17,
        parent=None,
    ):
        super().__init__(parent)

        self._radius = radius

        self.setObjectName(object_name)
        self.setAttribute(
            Qt.WA_StyledBackground,
            False,
        )
        self.setAttribute(
            Qt.WA_TranslucentBackground,
            True,
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        full_rect = QRectF(self.rect())

        # Surface is pulled in so the shadow has room to breathe.
        surface_rect = full_rect.adjusted(
            10,
            8,
            -10,
            -12,
        )

        # Stronger depth, but every layer is rounded.
        shadow_layers = (
            (8, 18, 5),
            (5, 26, 4),
            (2, 34, 3),
        )

        for spread, alpha, y_offset in shadow_layers:
            shadow_rect = surface_rect.adjusted(
                -spread,
                -spread + y_offset,
                spread,
                spread + y_offset,
            )

            shadow_path = QPainterPath()
            shadow_path.addRoundedRect(
                shadow_rect,
                self._radius + spread,
                self._radius + spread,
            )

            painter.fillPath(
                shadow_path,
                QColor(0, 0, 0, alpha),
            )

        surface_path = QPainterPath()
        surface_path.addRoundedRect(
            surface_rect,
            self._radius,
            self._radius,
        )

        is_hero_surface = (
            self.objectName() == "dashboardHeroSurface"
        )

        base_color = (
            QColor("#111C25")
            if is_hero_surface
            else QColor("#101B24")
        )
        start_color = (
            QColor("#15232D")
            if is_hero_surface
            else QColor("#182B38")
        )
        middle_color = (
            QColor("#121E27")
            if is_hero_surface
            else QColor("#121F29")
        )
        end_color = (
            QColor("#0F1921")
            if is_hero_surface
            else QColor("#0D1720")
        )

        painter.fillPath(
            surface_path,
            base_color,
        )

        gradient = QLinearGradient(
            surface_rect.topLeft(),
            surface_rect.bottomRight(),
        )
        gradient.setColorAt(
            0.00,
            start_color,
        )
        gradient.setColorAt(
            0.50,
            middle_color,
        )
        gradient.setColorAt(
            1.00,
            end_color,
        )
        painter.fillPath(
            surface_path,
            gradient,
        )

        glow = QRadialGradient(
            surface_rect.left()
            + surface_rect.width() * 0.14,
            surface_rect.top()
            + surface_rect.height() * 0.08,
            max(
                surface_rect.width(),
                surface_rect.height(),
            )
            * 0.95,
        )
        glow.setColorAt(
            0.00,
            QColor(
                45,
                62,
                81,
                10 if is_hero_surface else 14,
            ),
        )
        glow.setColorAt(
            1.00,
            QColor(0, 0, 0, 0),
        )
        painter.fillPath(
            surface_path,
            glow,
        )

        painter.setPen(
            QPen(
                QColor("#293B46"),
                1.0,
            )
        )
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(surface_path)

        painter.end()
        super().paintEvent(event)


class DashboardPage(QWidget):
    RESPONSIVE_BREAKPOINT = 760

    def __init__(self, data_manager):
        super().__init__()

        self.data_manager = data_manager
        self.layout_mode = None
        self.account_cards = []
        self.summary_sections = []
        self.period_cells = []

        self.setObjectName("dashboardPage")
        self.setAttribute(Qt.WA_StyledBackground, False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

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
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        self.content_widget = QWidget()
        self.content_widget.setObjectName("dashboardContent")
        self.content_widget.setAttribute(
            Qt.WA_TranslucentBackground,
            True,
        )
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
        self.main_layout.setSpacing(16)

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

        self.hero_surface = self._create_hero_surface()
        self.main_layout.addWidget(self.hero_surface)

        self.period_surface = self._create_period_surface()
        self.main_layout.addWidget(self.period_surface)

        self.overview_surface = self._create_overview_surface()
        self.main_layout.addWidget(self.overview_surface)

        self.main_layout.addStretch()

        self.scroll_area.setWidget(self.content_widget)
        root_layout.addWidget(self.scroll_area)

        self._set_layout_mode("wide")

    def _create_hero_surface(self):
        surface = ElevatedInnerPanel(
            "dashboardHeroSurface",
            radius=24,
        )
        surface.setMinimumHeight(342)
        surface.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(surface)
        layout.setContentsMargins(26, 20, 26, 18)
        layout.setSpacing(10)

        self.hero_body = QWidget()
        self.hero_body.setObjectName("heroBody")

        self.hero_grid = QGridLayout(self.hero_body)
        self.hero_grid.setContentsMargins(0, 0, 0, 0)
        self.hero_grid.setHorizontalSpacing(16)
        self.hero_grid.setVerticalSpacing(16)

        self.metric_widget = QWidget()
        self.metric_widget.setObjectName("metricWidget")
        self.metric_widget.setMinimumHeight(226)
        self.metric_widget.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        metric_layout = QVBoxLayout(self.metric_widget)
        metric_layout.setContentsMargins(
            34,
            22,
            34,
            24,
        )
        metric_layout.setSpacing(8)

        eyebrow = QLabel("TOPLAM PORTFÖY")
        eyebrow.setObjectName("heroEyebrow")

        self.value = QLabel("$0.00")
        self.value.setObjectName("heroValue")
        self.value.setMinimumWidth(340)
        self.value.setAlignment(
            Qt.AlignLeft | Qt.AlignVCenter
        )
        self.value.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.value.setGraphicsEffect(None)

        self.hero_caption = QLabel(
            "Funding ve Trading Toplamı"
        )
        self.hero_caption.setObjectName("heroCaption")

        self.hero_status = QLabel(
            "Portföy verileri bekleniyor"
        )
        self.hero_status.setObjectName("heroStatus")

        metric_layout.addWidget(eyebrow)
        metric_layout.addSpacing(4)
        metric_layout.addWidget(self.value)
        metric_layout.addWidget(self.hero_caption)
        metric_layout.addWidget(self.hero_status)
        metric_layout.addStretch()

        self.account_container = QWidget()
        self.account_container.setObjectName(
            "accountContainer"
        )

        self.account_grid = QGridLayout(
            self.account_container
        )
        self.account_grid.setContentsMargins(0, 0, 0, 0)
        self.account_grid.setHorizontalSpacing(16)
        self.account_grid.setVerticalSpacing(16)

        funding = self._create_account_surface(
            title="Funding",
            description="Fon hesabı",
            accent_text="Cüzdan bakiyesi",
        )
        self.funding_value = funding["value"]
        self.funding_change = funding["change"]
        self.funding_change_amount = funding["change_amount"]
        self.account_cards.append(funding["widget"])

        trading = self._create_account_surface(
            title="Trading",
            description="Spot işlem hesabı",
            accent_text="İşlem bakiyesi",
        )
        self.trading_value = trading["value"]
        self.trading_change = trading["change"]
        self.trading_change_amount = trading["change_amount"]
        self.account_cards.append(trading["widget"])

        self.hero_grid.addWidget(
            self.metric_widget,
            0,
            0,
            2,
            1,
        )
        self.hero_grid.addWidget(
            self.account_cards[0],
            0,
            1,
        )
        self.hero_grid.addWidget(
            self.account_cards[1],
            1,
            1,
        )
        self.hero_grid.setColumnStretch(0, 3)
        self.hero_grid.setColumnStretch(1, 2)

        divider = QFrame()
        divider.setObjectName("heroDivider")
        divider.setFixedHeight(1)

        footer = QLabel(
            "    Portföy dağılımı ve dönemsel performans özeti"
        )
        footer.setObjectName("heroFooter")

        layout.addWidget(self.hero_body)
        layout.addWidget(divider)
        layout.addWidget(footer)

        return surface

    def _create_account_surface(
        self,
        title,
        description,
        accent_text,
    ):
        panel = ElevatedInnerPanel(
            "dashboardAccountPanel",
            radius=17,
        )
        panel.setMinimumHeight(124)
        panel.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(panel)
        layout.setContentsMargins(30, 18, 30, 18)
        layout.setSpacing(16)

        accent_bar = QFrame()
        accent_bar.setObjectName("accountAccentBar")
        accent_bar.setFixedWidth(3)
        accent_bar.setFixedHeight(76)
        accent_bar.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )

        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(3)

        title_label = QLabel(title)
        title_label.setObjectName("accountTitle")

        value_label = QLabel("$0.00")
        value_label.setObjectName("accountValue")
        value_label.setMinimumWidth(180)

        description_label = QLabel(description)
        description_label.setObjectName(
            "accountDescription"
        )

        left_layout.addWidget(title_label)
        left_layout.addSpacing(8)
        left_layout.addWidget(value_label)
        left_layout.addWidget(description_label)
        left_layout.addStretch()

        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(3)

        change_label = QLabel("—")
        change_label.setObjectName(
            "accountDailyChange"
        )
        change_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        change_amount_label = QLabel("—")
        change_amount_label.setObjectName(
            "accountDailyChangeAmount"
        )
        change_amount_label.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        change_caption = QLabel("1 Günlük Değişim")
        change_caption.setObjectName(
            "accountDailyCaption"
        )
        change_caption.setAlignment(
            Qt.AlignRight | Qt.AlignVCenter
        )

        right_layout.addStretch()
        right_layout.addWidget(change_label)
        right_layout.addWidget(change_amount_label)
        right_layout.addWidget(change_caption)
        right_layout.addStretch()

        layout.addWidget(
            accent_bar,
            alignment=Qt.AlignVCenter,
        )
        layout.addLayout(left_layout, 1)
        layout.addStretch(1)
        layout.addLayout(right_layout)

        return {
            "widget": panel,
            "value": value_label,
            "change": change_label,
            "change_amount": change_amount_label,
        }

    def _create_period_surface(self):
        surface = ElevatedInnerPanel(
            "dashboardPeriodSurface",
            radius=18,
        )
        surface.setMinimumHeight(124)
        surface.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.period_layout = QGridLayout(surface)
        self.period_layout.setContentsMargins(
            24,
            16,
            24,
            16,
        )
        self.period_layout.setHorizontalSpacing(0)
        self.period_layout.setVerticalSpacing(12)

        self.period_value_labels = {}

        periods = (
            ("1 Gün", "1d"),
            ("7 Gün", "7d"),
            ("30 Gün", "30d"),
            ("90 Gün", "90d"),
            ("1 Yıl", "1y"),
        )

        for title, key in periods:
            cell = QWidget()
            cell.setObjectName("periodCell")
            cell.setMinimumHeight(82)

            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(
                16,
                4,
                16,
                4,
            )
            cell_layout.setSpacing(6)

            title_label = QLabel(title)
            title_label.setObjectName("periodTitle")

            value_label = QLabel("—")
            value_label.setObjectName("periodValue")

            detail_label = QLabel("Değişim")
            detail_label.setObjectName("periodDetail")

            cell_layout.addWidget(title_label)
            cell_layout.addStretch()
            cell_layout.addWidget(value_label)
            cell_layout.addWidget(detail_label)

            self.period_cells.append(cell)
            self.period_value_labels[key] = value_label

        self._rebuild_period_layout("wide")
        return surface

    def _create_overview_surface(self):
        container = QWidget()
        container.setObjectName("overviewContainer")
        container.setAttribute(
            Qt.WA_TranslucentBackground,
            True,
        )
        container.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        self.overview_layout = QGridLayout(container)
        self.overview_layout.setContentsMargins(
            0,
            0,
            0,
            0,
        )
        self.overview_layout.setHorizontalSpacing(16)
        self.overview_layout.setVerticalSpacing(16)

        portfolio = self._create_summary_card(
            "Portfolio",
            "Toplam varlık görünümü",
        )
        self.performance_summary_value = portfolio["value"]
        self.performance_summary_detail = portfolio["detail"]
        self.summary_sections.append(
            portfolio["widget"]
        )

        alarms = self._create_summary_card(
            "Alarmlar",
            "Aktif alarm durumu",
        )
        self.alarms_summary_value = alarms["value"]
        self.alarms_summary_detail = alarms["detail"]
        self.summary_sections.append(
            alarms["widget"]
        )

        watchlist = self._create_summary_card(
            "Watchlist",
            "Takip edilen varlıklar",
        )
        self.watchlist_summary_value = watchlist["value"]
        self.watchlist_summary_detail = watchlist["detail"]
        self.summary_sections.append(
            watchlist["widget"]
        )

        self._rebuild_overview_layout("wide")
        return container

    def _create_summary_card(self, title, description):
        surface = ElevatedInnerPanel(
            "dashboardSummarySurface",
            radius=18,
        )
        surface.setMinimumHeight(176)
        surface.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(surface)
        layout.setContentsMargins(
            34,
            28,
            34,
            32,
        )
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("summaryTitle")

        description_label = QLabel(description)
        description_label.setObjectName(
            "summaryDescription"
        )

        value_label = QLabel("—")
        value_label.setObjectName("summaryValue")

        detail_label = QLabel("Veri bekleniyor")
        detail_label.setObjectName("summaryDetail")
        detail_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addStretch()
        layout.addWidget(value_label)
        layout.addWidget(detail_label)

        return {
            "widget": surface,
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

    def _rebuild_period_layout(self, mode):
        self._clear_grid(self.period_layout)

        if mode == "narrow":
            for row, cell in enumerate(self.period_cells):
                self.period_layout.addWidget(
                    cell,
                    row,
                    0,
                )
        else:
            for column, cell in enumerate(self.period_cells):
                self.period_layout.addWidget(
                    cell,
                    0,
                    column * 2,
                )
                self.period_layout.setColumnStretch(
                    column * 2,
                    1,
                )

                if column < len(self.period_cells) - 1:
                    divider = QFrame()
                    divider.setObjectName("verticalDivider")
                    divider.setFixedWidth(1)
                    self.period_layout.addWidget(
                        divider,
                        0,
                        column * 2 + 1,
                    )

    def _rebuild_overview_layout(self, mode):
        self._clear_grid(self.overview_layout)

        if mode == "narrow":
            for row, card in enumerate(
                self.summary_sections
            ):
                self.overview_layout.addWidget(
                    card,
                    row,
                    0,
                )
        else:
            for column, card in enumerate(
                self.summary_sections
            ):
                self.overview_layout.addWidget(
                    card,
                    0,
                    column,
                )
                self.overview_layout.setColumnStretch(
                    column,
                    1,
                )

    def _set_layout_mode(self, mode):
        if mode == self.layout_mode:
            return

        if mode == "narrow":
            self.main_layout.setContentsMargins(
                22,
                22,
                22,
                28,
            )
            self.main_layout.setSpacing(16)

            self._clear_grid(self.hero_grid)
            self.hero_grid.addWidget(
                self.metric_widget,
                0,
                0,
            )
            self.hero_grid.addWidget(
                self.account_cards[0],
                1,
                0,
            )
            self.hero_grid.addWidget(
                self.account_cards[1],
                2,
                0,
            )

            self._rebuild_period_layout("narrow")
            self._rebuild_overview_layout("narrow")
        else:
            self.main_layout.setContentsMargins(
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
                Theme.PAGE_MARGIN_HORIZONTAL,
                Theme.PAGE_MARGIN_VERTICAL,
            )
            self.main_layout.setSpacing(16)

            self._clear_grid(self.hero_grid)
            self.hero_grid.addWidget(
                self.metric_widget,
                0,
                0,
                2,
                1,
            )
            self.hero_grid.addWidget(
                self.account_cards[0],
                0,
                1,
            )
            self.hero_grid.addWidget(
                self.account_cards[1],
                1,
                1,
            )
            self.hero_grid.setColumnStretch(0, 3)
            self.hero_grid.setColumnStretch(1, 2)

            self._rebuild_period_layout("wide")
            self._rebuild_overview_layout("wide")

        self.layout_mode = mode
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
                background: transparent;
            }}

            QScrollArea#dashboardScrollArea,
            QScrollArea#dashboardScrollArea
            > QWidget
            > QWidget {{
                background: transparent;
                border: none;
            }}

            QWidget#dashboardContent,
            QWidget#heroBody,
            QWidget#metricWidget,
            QWidget#accountContainer,
            QWidget#overviewContainer,
            QWidget#periodCell,
            QWidget#overviewSection {{
                background: transparent;
                border: none;
            }}

            QFrame#dashboardHeroSurface,
            QFrame#dashboardInnerPanel,
            QFrame#dashboardAccountPanel,
            QFrame#dashboardPeriodSurface,
            QFrame#dashboardSummarySurface {{
                background: transparent;
                border: none;
            }}

            QLabel {{
                background: transparent;
                border: none;
                color: {Theme.TEXT_PRIMARY};
                font-family: "Inter", "{Theme.FONT_FAMILY}";
            }}

            QLabel#heroEyebrow {{
                color: #94A3B8;
                font-size: 14px;
                font-weight: 800;
                letter-spacing: 0.5px;
            }}

            QLabel#heroValue {{
                color: {Theme.ACCENT};
                font-size: 50px;
                font-weight: 700;
            }}

            QLabel#heroCaption {{
                color: #94A3B8;
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel#heroStatus {{
                color: #6F8093;
                font-size: 10px;
                font-weight: 600;
            }}

            QLabel#heroFooter {{
                color: #94A3B8;
                font-size: 12px;
                font-weight: 650;
            }}

            QFrame#heroDivider,
            QFrame#horizontalDivider,
            QFrame#verticalDivider {{
                background-color: rgba(125, 158, 176, 24);
                border: none;
            }}

            QFrame#accountAccentBar {{
                background-color: {Theme.ACCENT};
                border: none;
                border-radius: 1px;
            }}

            QLabel#accountTitle {{
                color: #94A3B8;
                font-size: 14px;
                font-weight: 700;
            }}

            QLabel#accountMeta {{
                color: #6F8093;
                font-size: 10px;
            }}

            QLabel#accountValue {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 24px;
                font-weight: 700;
            }}

            QLabel#accountDescription {{
                color: #6F8093;
                font-size: 11px;
            }}

            QLabel#accountDailyChange {{
                font-size: 19px;
                font-weight: 800;
                color: #6F8093;
            }}

            QLabel#accountDailyChangeAmount {{
                font-size: 17px;
                font-weight: 800;
                color: #6F8093;
            }}

            QLabel#accountDailyCaption {{
                font-size:10px;
                font-weight:600;
                color:#6F8093;
            }}

            QLabel#periodTitle {{
                color: #94A3B8;
                font-size: 11px;
                font-weight: 700;
            }}

            QLabel#periodValue {{
                color: #6F8093;
                font-size: 28px;
                font-weight: 700;
            }}

            QLabel#periodDetail {{
                color: #6F8093;
                font-size: 10px;
                font-weight: 600;
            }}

            QLabel#summaryTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#summaryDescription {{
                color: #94A3B8;
                font-size: 12px;
            }}

            QLabel#summaryValue {{
                color: #10B981;
                font-size: 32px;
                font-weight: 700;
            }}

            QLabel#summaryDetail {{
                color: #6F8093;
                font-size: 11px;
                font-weight: 600;
            }}
            """
        )

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(
            QPainter.Antialiasing,
        )
        painter.setRenderHint(
            QPainter.SmoothPixmapTransform,
        )

        SurfaceEngine.draw_page_background(
            painter,
            QRectF(self.rect()),
        )

        painter.end()
        super().paintEvent(event)

    def _sync_layout_mode(self):
        available_width = self.scroll_area.viewport().width()

        if available_width <= 0:
            available_width = self.width()

        if available_width < self.RESPONSIVE_BREAKPOINT:
            self._set_layout_mode("narrow")
        else:
            self._set_layout_mode("wide")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_layout_mode()

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
        breakdown=portfolio.get("performance_breakdown",{})
        analytics=portfolio.get("analytics",{})

        if not isinstance(performance, dict):
            performance = {}

        self._update_account_daily_changes(
            breakdown,
            analytics,
        )
        self._update_period_cards(performance)
        self._update_dashboard_summaries(performance)
        self._set_connected_status()


    def _update_account_daily_changes(
        self,
        breakdown,
        analytics,
    ):
        period_changes = (
            analytics.get("period_changes", {})
            if isinstance(analytics, dict)
            else {}
        )
        one_day = (
            period_changes.get("1d", {})
            if isinstance(period_changes, dict)
            else {}
        )

        account_rows = (
            (
                "funding",
                self.funding_change,
                self.funding_change_amount,
            ),
            (
                "trading",
                self.trading_change,
                self.trading_change_amount,
            ),
        )

        for key, percent_label, amount_label in account_rows:
            value = (
                (breakdown.get(key, {}) or {}).get("1d")
                if isinstance(breakdown, dict)
                else None
            )
            account_analytics = (
                one_day.get(key, {})
                if isinstance(one_day, dict)
                else {}
            )
            amount = (
                account_analytics.get("amount_usdt")
                if isinstance(account_analytics, dict)
                else None
            )

            if isinstance(value, (int, float)):
                color = (
                    Theme.ACCENT
                    if value >= 0
                    else Theme.ERROR
                )
                percent_label.setText(f"{value:+.2f}%")
                percent_label.setStyleSheet(
                    f"color:{color};"
                )
            else:
                color = "#6F8093"
                percent_label.setText("—")
                percent_label.setStyleSheet(
                    f"color:{color};"
                )

            if isinstance(amount, (int, float)):
                amount_color = (
                    Theme.ACCENT
                    if amount >= 0
                    else Theme.ERROR
                )
                amount_label.setText(
                    f"{amount:+,.2f} USDT"
                )
                amount_label.setStyleSheet(
                    f"color:{amount_color};"
                )
            else:
                amount_label.setText("—")
                amount_label.setStyleSheet(
                    "color:#6F8093;"
                )

    def _update_period_cards(self, performance):
        for key, label in self.period_value_labels.items():
            value = performance.get(key)

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
                    f"color: #6F8093;"
                )

    def _update_dashboard_summaries(self, performance):
        one_day = performance.get("1d")

        if isinstance(one_day, (int, float)):
            self.performance_summary_value.setText(
                f"{float(one_day):+.2f}%"
            )
            self.performance_summary_value.setStyleSheet(
                f"color: "
                f"{Theme.ACCENT if one_day >= 0 else Theme.ERROR};"
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
            1
            for alarm in alarms
            if alarm.get("is_triggered")
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
                    (
                        (current_price - added_price)
                        / added_price
                    )
                    * 100
                )

        self.watchlist_summary_value.setText(
            str(len(watchlist_items))
        )

        if changes:
            average_change = sum(changes) / len(changes)
            self.watchlist_summary_detail.setText(
                f"Ortalama değişim "
                f"{average_change:+.2f}%"
            )
        else:
            self.watchlist_summary_detail.setText(
                "Takip edilen toplam varlık"
            )

    def showEvent(self, event):
        super().showEvent(event)

        self._set_layout_mode("wide")
        QTimer.singleShot(0, self._sync_layout_mode)
        QTimer.singleShot(120, self._sync_layout_mode)

        portfolio = self.data_manager.get_portfolio() or {}
        performance = portfolio.get("performance", {})
        breakdown=portfolio.get("performance_breakdown",{})

        if not isinstance(performance, dict):
            performance = {}

        self._update_period_cards(performance)
        self._update_dashboard_summaries(performance)

    def on_portfolio_error(self, error):
        self._set_error_status()

    def _set_waiting_status(self):
        self.status_badge.set_status(
            "Bekleniyor",
            StatusBadge.NEUTRAL,
        )
        self.hero_status.setText(
            "Portföy verileri bekleniyor"
        )

    def _set_connected_status(self):
        self.status_badge.set_status(
            "API Bağlı",
            StatusBadge.SUCCESS,
        )
        self.hero_status.setText(
            "Portföy verileri güncel"
        )

    def _set_error_status(self):
        self.status_badge.set_status(
            "Bağlantı Hatası",
            StatusBadge.ERROR,
        )
        self.hero_status.setText(
            "Portföy verileri alınamadı"
        )
