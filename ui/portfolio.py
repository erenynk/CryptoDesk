from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import (
    QColor,
    QFont,
)
from ui.widgets.card import Card
from ui.widgets.page_header import PageHeader
from ui.widgets.button import AppButton
from ui.widgets.section_header import SectionHeader
from ui.widgets.status_badge import StatusBadge
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,    
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from services.data_worker import PortfolioRefreshWorker
from ui.theme import (
    Theme,
    checkbox_style,
    label_style,
    page_style,
    page_title_style,    
    scroll_bar_style,
)


class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value, display_text):
        super().__init__(display_text)

        self.value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            return self.value < other.value

        return super().__lt__(other)


class PortfolioPage(QWidget):
    def __init__(self, data_manager, dashboard_page):
        super().__init__()

        self.data_manager = data_manager
        self.dashboard_page = dashboard_page
        self.worker = None
        self.raw_assets_data = []

        self.headers = [
            "",
            "Varlık",
            "Toplam Değer",
            "Anlık Fiyat",
            "Toplam Miktar",
            "PnL",
        ]

        self.setObjectName("portfolioPage")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setFont(QFont(Theme.FONT_FAMILY, 10))

        self._build_ui()
        self._apply_styles()
        self._apply_portfolio_card_styles()
        self._connect_signals()
        self._configure_refresh_timer()

        QTimer.singleShot(100, self.start_page)

    def _build_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        self.main_layout.setSpacing(20)

        self.header = self._create_header()
        self.main_layout.addWidget(self.header)

        self.summary_card = self._create_summary_card()
        self.main_layout.addWidget(self.summary_card)

        self.table_card = self._create_table_card()
        self.main_layout.addWidget(self.table_card, 1)

    def _create_header(self):
        controls = QWidget()
        controls.setObjectName("portfolioHeaderControls")

        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.setSpacing(14)

        self.hide_dust_checkbox = QCheckBox(
            "Küçük Bakiyeleri Gizle (< $1)"
        )
        self.hide_dust_checkbox.setObjectName(
            "hideDustCheckbox"
        )

        self.refresh_button = AppButton(
            "Bakiyeleri Yenile",
            variant=AppButton.PRIMARY,
            object_name="refreshButton",
        )

        controls_layout.addWidget(self.hide_dust_checkbox)
        controls_layout.addWidget(self.refresh_button)

        return PageHeader(
            title="Portfolio",
            subtitle=(
                "Funding ve Trading hesaplarındaki "
                "varlıklarını yönet."
            ),
            right_widget=controls,
            object_name="portfolioHeader",
        )

    def _create_summary_card(self):
        card = Card(
            "portfolioSummaryCard",
            hover=False,
            radius=Theme.RADIUS_XLARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setMinimumHeight(176)
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(28, 26, 28, 26)
        layout.setSpacing(24)

        balance_layout = QVBoxLayout()
        balance_layout.setContentsMargins(0, 0, 0, 0)
        balance_layout.setSpacing(7)

        title = QLabel("TOPLAM PORTFÖY DEĞERİ")
        title.setObjectName("summaryLabel")

        self.total_balance_label = QLabel("$0.00")
        self.total_balance_label.setObjectName("summaryValue")
        self.total_balance_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        self.asset_count_label = QLabel(
            "0 farklı kripto varlık listeleniyor"
        )
        self.asset_count_label.setObjectName("summaryDescription")

        balance_layout.addWidget(title)
        balance_layout.addWidget(self.total_balance_label)
        balance_layout.addWidget(self.asset_count_label)

        self.connection_badge = StatusBadge(
            text="Bekleniyor",
            status=StatusBadge.NEUTRAL,
            object_name="portfolioConnectionBadge",
        )

        pnl_container = QWidget()
        pnl_container.setObjectName("dailyPnlContainer")

        pnl_layout = QVBoxLayout(pnl_container)
        pnl_layout.setContentsMargins(0, 0, 0, 0)
        pnl_layout.setSpacing(5)

        pnl_title = QLabel("GÜNLÜK PNL")
        pnl_title.setObjectName("dailyPnlTitle")
        pnl_title.setAlignment(Qt.AlignCenter)

        self.daily_pnl_label = QLabel("—")
        self.daily_pnl_label.setObjectName("dailyPnlValue")
        self.daily_pnl_label.setAlignment(Qt.AlignCenter)
        self.daily_pnl_label.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )

        pnl_layout.addWidget(pnl_title)
        pnl_layout.addWidget(self.daily_pnl_label)

        right_container = QWidget()
        right_container.setObjectName("summaryRightContainer")

        right_layout = QHBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(22)

        right_layout.addWidget(
            pnl_container,
            0,
            Qt.AlignVCenter,
        )
        right_layout.addWidget(
            self.connection_badge,
            0,
            Qt.AlignTop,
        )

        layout.addLayout(balance_layout, 1)
        layout.addWidget(
            right_container,
            0,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        return card

    def _create_table_card(self):
        card = Card(
            "portfolioTableCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        table_header = SectionHeader(
            title="Varlık Dağılımı",
            description=(
                "Portföyündeki tüm spot varlıkların "
                "güncel görünümü"
            ),
            object_name="portfolioSectionHeader",
        )

        self.table = QTableWidget()
        self.table.setObjectName("portfolioTable")
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.setColumnCount(len(self.headers))
        self.table.setHorizontalHeaderLabels(self.headers)

        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.NoSelection)
        self.table.setAlternatingRowColors(False)
        self.table.setSortingEnabled(False)
        self.table.setShowGrid(False)
        self.table.setWordWrap(False)

        self.table.horizontalHeader().setObjectName(
            "portfolioTableHeader"
        )
        self.table.horizontalHeader().setFocusPolicy(Qt.NoFocus)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.horizontalHeader().setStretchLastSection(False)

        self.table.horizontalHeader().setSectionResizeMode(
            0,
            QHeaderView.Fixed,
        )
        self.table.setColumnWidth(0, 58)

        for column in range(1, len(self.headers)):
            self.table.horizontalHeader().setSectionResizeMode(
                column,
                QHeaderView.Stretch,
            )

        self.table.verticalHeader().setVisible(False)
        self.table.verticalHeader().setDefaultSectionSize(60)
        self.table.verticalHeader().setMinimumSectionSize(60)

        layout.addWidget(table_header)
        layout.addWidget(self.table, 1)

        return card

    def _apply_portfolio_card_styles(self):
        summary_radius = Theme.RADIUS_XLARGE
        table_radius = Theme.RADIUS_LARGE

        self.summary_card.setStyleSheet(
            f"""
            QFrame#portfolioSummaryCard {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0B141D,
                    stop: 0.55 #0D1822,
                    stop: 1 #101C27
                );
                border: 1px solid #253542;
                border-radius: {summary_radius}px;
            }}
            """
        )

        self.table_card.setStyleSheet(
            f"""
            QFrame#portfolioTableCard {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                border: 1px solid #253542;
                border-radius: {table_radius}px;
            }}
            """
        )

    def _connect_signals(self):
        self.hide_dust_checkbox.stateChanged.connect(
            self.update_table_view
        )

        self.refresh_button.clicked.connect(
            self.load_balances
        )

        self.table.horizontalHeader().sortIndicatorChanged.connect(
            self.on_sort_indicator_changed
        )

    def _configure_refresh_timer(self):
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)
        self.refresh_timer.timeout.connect(
            self.load_balances
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("portfolioPage")
            + label_style()
            + page_title_style()
            + checkbox_style("hideDustCheckbox")            
            + scroll_bar_style()
            + f"""
           

            
            QWidget#portfolioPage {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #101923,
                    stop: 0.55 #14202B,
                    stop: 1 #182631
                );
            }}

            QLabel#summaryLabel {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 800;
                letter-spacing: 1px;
            }}

            QLabel#summaryValue {{
                color: {Theme.ACCENT};
                font-size: 40px;
                font-weight: 700;
            }}

            QLabel#summaryDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QWidget#summaryRightContainer,
            QWidget#dailyPnlContainer {{
                background: transparent;
                border: none;
            }}

            QWidget#dailyPnlContainer {{
                min-width: 190px;
            }}

            QLabel#dailyPnlTitle {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 700;
                letter-spacing: 1px;
            }}

            QLabel#dailyPnlValue {{
                color: {Theme.TEXT_MUTED};
                font-size: 32px;
                font-weight: 750;
            }}

                       
            
            QTableWidget#portfolioTable {{
                background-color: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-bottom-left-radius: {Theme.RADIUS_LARGE}px;
                border-bottom-right-radius: {Theme.RADIUS_LARGE}px;
                gridline-color: transparent;
                outline: none;
            }}

            QTableWidget#portfolioTable::item {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {Theme.BORDER_SOFT};
                padding: 14px 12px;
            }}


            QHeaderView#portfolioTableHeader {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                border: none;
                border-bottom: 1px solid #253542;
            }}

            QHeaderView#portfolioTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 14px 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 800;
            }}

            QHeaderView#portfolioTableHeader::section {{
                background: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                padding: 14px 12px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 14px;
                font-weight: 800;
            }}

            QHeaderView::section:horizontal:hover {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView::section:horizontal:pressed {{
                color: {Theme.TEXT_PRIMARY};
                background-color: {Theme.CARD_BACKGROUND_HOVER};
            }}

            QHeaderView::down-arrow,
            QHeaderView::up-arrow {{
                image: none;
                width: 0;
                height: 0;
            }}

            QTableCornerButton::section {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #0A131C,
                    stop: 0.55 #0C1721,
                    stop: 1 #0F1B26
                );
                border: none;
                border-bottom: 1px solid #253542;
            }}
            """
        )

    def on_sort_indicator_changed(self, logical_index, order):
        if logical_index < 0:
            return

        for index in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(index)

            if header_item is None:
                continue

            if index == logical_index:
                arrow = (
                    " ▲"
                    if order == Qt.AscendingOrder
                    else " ▼"
                )
                header_item.setText(
                    self.headers[index] + arrow
                )
            else:
                header_item.setText(self.headers[index])

    def start_page(self):
        self.load_balances()
        self.refresh_timer.start()

    def load_balances(self):
        if self.data_manager.loading:
            return

        if self.worker is not None and self.worker.isRunning():
            return

        self._set_loading_state()

        self.worker = PortfolioRefreshWorker(
            self.data_manager
        )
        self.worker.result_ready.connect(
            self.on_balances_loaded
        )
        self.worker.result_ready.connect(
            self.worker.deleteLater
        )
        self.worker.start()

    def on_balances_loaded(self, success, result):
        if success:
            portfolio = (
                self.data_manager.get_portfolio()
                or result
            )

            total = float(
                portfolio.get("total_usdt", 0.0)
            )

            self.total_balance_label.setText(
                f"${total:,.2f}"
            )

            self.raw_assets_data = portfolio.get(
                "assets",
                [],
            )

            self._update_daily_pnl(portfolio)
            self.update_table_view()
            self._set_connected_state()

        else:
            self.total_balance_label.setText(
                "Bağlantı Hatası"
            )
            self._set_error_state()

            print(
                "Portfolio refresh error:",
                result,
            )

        self.refresh_button.setEnabled(True)
        self.refresh_button.setText(
            "Bakiyeleri Yenile"
        )

        self.worker = None

    def _set_loading_state(self):
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Güncelleniyor...")

        self.connection_badge.set_status(
            "Güncelleniyor",
            StatusBadge.WARNING,
        )

    def _set_connected_state(self):
        self.connection_badge.set_status(
            "API Bağlı",
            StatusBadge.SUCCESS,
        )

    def _set_error_state(self):
        self.connection_badge.set_status(
            "Bağlantı Hatası",
            StatusBadge.ERROR,
        )

    @staticmethod
    def format_amount(value):
        if value == 0:
            return "0"

        text = f"{value:.4f}".rstrip("0").rstrip(".")

        return text if text else "0"

    @staticmethod
    def format_price(price):
        if price >= 1:
            return f"${price:,.2f}"

        if price > 0:
            return f"${price:,.4f}"

        return "$0.00"

    @staticmethod
    def _extract_percentage(data, keys):
        for key in keys:
            value = data.get(key)

            if isinstance(value, (int, float)):
                return float(value)

            if isinstance(value, str):
                try:
                    return float(value.replace("%", "").strip())
                except ValueError:
                    continue

        return None

    def _get_asset_pnl_percent(self, asset):
        direct = self._extract_percentage(
            asset,
            (
                "pnl_percent",
                "pnl_pct",
                "profit_percent",
                "change_24h",
                "change24h",
                "daily_change_percent",
            ),
        )

        if direct is not None:
            return direct

        current_price = float(asset.get("price", 0.0) or 0.0)

        for key in (
            "average_price",
            "avg_price",
            "cost_price",
            "entry_price",
        ):
            cost_price = asset.get(key)

            if not isinstance(cost_price, (int, float)):
                continue

            cost_price = float(cost_price)

            if current_price > 0 and cost_price > 0:
                return (
                    (current_price - cost_price)
                    / cost_price
                    * 100
                )

        return None

    def _update_daily_pnl(self, portfolio):
        performance = portfolio.get("performance", {})
        daily_pnl = None

        if isinstance(performance, dict):
            daily_pnl = self._extract_percentage(
                performance,
                ("1d", "daily", "day"),
            )

        if daily_pnl is None:
            daily_pnl = self._extract_percentage(
                portfolio,
                (
                    "daily_pnl_percent",
                    "pnl_1d",
                    "change_1d",
                ),
            )

        if daily_pnl is None:
            self.daily_pnl_label.setText("—")
            self.daily_pnl_label.setStyleSheet(
                f"color: {Theme.TEXT_MUTED};"
            )
            return

        color = Theme.ACCENT if daily_pnl >= 0 else Theme.ERROR
        self.daily_pnl_label.setText(f"{daily_pnl:+.2f}%")
        self.daily_pnl_label.setStyleSheet(
            f"color: {color};"
        )

    def update_table_view(self):
        self.table.setSortingEnabled(False)
        self.table.setUpdatesEnabled(False)

        hide_dust = self.hide_dust_checkbox.isChecked()

        visible_assets = [
            asset
            for asset in self.raw_assets_data
            if not (
                hide_dust
                and asset.get("usdt_value", 0.0) < 1
            )
        ]

        self.table.setRowCount(len(visible_assets))

        for row, asset in enumerate(visible_assets):
            index_item = QTableWidgetItem(str(row + 1))
            index_item.setForeground(
                QColor(Theme.TEXT_MUTED)
            )
            index_item.setTextAlignment(Qt.AlignCenter)

            index_font = QFont(Theme.FONT_FAMILY, 10)
            index_font.setBold(True)
            index_item.setFont(index_font)

            coin_item = QTableWidgetItem(
                asset.get("coin", "")
            )
            coin_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            coin_item.setTextAlignment(
                Qt.AlignCenter
            )

            coin_font = coin_item.font()
            coin_font.setBold(True)
            coin_item.setFont(coin_font)

            total_item = NumericTableWidgetItem(
                asset.get("total", 0.0),
                self.format_amount(
                    asset.get("total", 0.0)
                ),
            )

            pnl_percent = self._get_asset_pnl_percent(asset)

            pnl_item = NumericTableWidgetItem(
                (
                    pnl_percent
                    if pnl_percent is not None
                    else 0.0
                ),
                (
                    f"{pnl_percent:+.2f}%"
                    if pnl_percent is not None
                    else "—"
                ),
            )

            price_item = NumericTableWidgetItem(
                asset.get("price", 0.0),
                self.format_price(
                    asset.get("price", 0.0)
                ),
            )

            value_item = NumericTableWidgetItem(
                asset.get("usdt_value", 0.0),
                (
                    f"${asset.get('usdt_value', 0.0):,.2f}"
                ),
            )

            total_item.setForeground(
                QColor(Theme.TEXT_SECONDARY)
            )
            pnl_item.setForeground(
                QColor(
                    Theme.ACCENT
                    if pnl_percent is not None
                    and pnl_percent >= 0
                    else (
                        Theme.ERROR
                        if pnl_percent is not None
                        else Theme.TEXT_MUTED
                    )
                )
            )
            price_item.setForeground(
                QColor(Theme.TEXT_PRIMARY)
            )
            value_item.setForeground(
                QColor(Theme.ACCENT)
            )

            for item in (
                total_item,
                pnl_item,
                price_item,
                value_item,
            ):
                item.setTextAlignment(Qt.AlignCenter)

                item_font = item.font()
                item_font.setBold(True)
                item.setFont(item_font)

            self.table.setItem(row, 0, index_item)
            self.table.setItem(row, 1, coin_item)
            self.table.setItem(row, 2, value_item)
            self.table.setItem(row, 3, price_item)
            self.table.setItem(row, 4, total_item)
            self.table.setItem(row, 5, pnl_item)

        self.asset_count_label.setText(
            f"{len(visible_assets)} farklı kripto varlık listeleniyor"
        )

        sort_column = (
            self.table.horizontalHeader()
            .sortIndicatorSection()
        )

        sort_order = (
            self.table.horizontalHeader()
            .sortIndicatorOrder()
        )

        self.on_sort_indicator_changed(
            sort_column,
            sort_order,
        )

        self.table.setUpdatesEnabled(True)
        self.table.setSortingEnabled(True)

    def showEvent(self, event):
        super().showEvent(event)

        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def closeEvent(self, event):
        self.refresh_timer.stop()

        if (
            self.worker is not None
            and self.worker.isRunning()
        ):
            self.worker.quit()
            self.worker.wait(3000)

        super().closeEvent(event)