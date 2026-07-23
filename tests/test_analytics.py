import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QLabel, QWidget

import ui.analytics as analytics_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in list(self.callbacks):
            callback(*args)


class BareAnalyticsPage(analytics_module.AnalyticsPage):
    def __init__(self):
        QWidget.__init__(self)
        self.metric_labels = {}


class AnalyticsPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    def setUp(self):
        self.pages = []

    def tearDown(self):
        for page in self.pages:
            page.deleteLater()

    def make_page(self):
        page = BareAnalyticsPage()
        self.pages.append(page)
        return page

    def build_metric_labels(self, page):
        keys = []

        for group in ("total", "funding", "trading"):
            for metric in (
                "highest_usdt",
                "lowest_usdt",
                "average_usdt",
            ):
                keys.append(f"{group}.{metric}")

        keys.extend(
            (
                "snapshot_count",
                "first_timestamp",
                "last_timestamp",
            )
        )

        for group in ("total", "funding", "trading"):
            for period in ("1d", "7d", "30d", "90d", "1y"):
                keys.append(
                    f"performance.{group}.{period}"
                )

        page.metric_labels = {
            key: QLabel("initial")
            for key in keys
        }

    def test_constructor_initializes_and_refreshes(self):
        with (
            patch.object(
                analytics_module.AnalyticsPage,
                "_build_ui",
            ) as build_ui,
            patch.object(
                analytics_module.AnalyticsPage,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                analytics_module.AnalyticsPage,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                analytics_module.AnalyticsPage,
                "refresh",
            ) as refresh,
        ):
            page = analytics_module.AnalyticsPage(
                sentinel.data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            sentinel.data_manager,
        )
        self.assertEqual(page.metric_labels, {})
        self.assertEqual(
            page.objectName(),
            "analyticsPage",
        )
        self.assertTrue(
            page.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        connect_signals.assert_called_once_with()
        refresh.assert_called_once_with()

    def test_create_metric_row_builds_value_label(self):
        row = (
            analytics_module.AnalyticsPage
            ._create_metric_row(
                title="En Yüksek",
                object_name="metricValue",
            )
        )

        self.assertIn("layout", row)
        self.assertIn("value", row)
        self.assertIsInstance(row["value"], QLabel)
        self.assertEqual(row["value"].text(), "—")
        self.assertEqual(
            row["value"].objectName(),
            "metricValue",
        )
        self.assertEqual(
            row["value"].alignment(),
            Qt.AlignRight | Qt.AlignVCenter,
        )

        row["value"].deleteLater()

    def test_connect_signals_wires_manager_events(self):
        page = self.make_page()
        updated = SignalStub()
        error = SignalStub()
        page.data_manager = SimpleNamespace(
            portfolio_updated=updated,
            portfolio_error=error,
        )

        page._connect_signals()

        self.assertEqual(
            updated.callbacks,
            [page.on_portfolio_updated],
        )
        self.assertEqual(
            error.callbacks,
            [page.on_portfolio_error],
        )

    def test_refresh_uses_cached_portfolio(self):
        page = self.make_page()
        portfolio = {"analytics": {}}
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(return_value=portfolio)
        )
        page.on_portfolio_updated = Mock()
        page._set_waiting_state = Mock()

        page.refresh()

        page.data_manager.get_portfolio.assert_called_once_with()
        page.on_portfolio_updated.assert_called_once_with(
            portfolio
        )
        page._set_waiting_state.assert_not_called()

    def test_refresh_sets_waiting_for_non_dictionary(self):
        page = self.make_page()
        page.data_manager = SimpleNamespace(
            get_portfolio=Mock(return_value=None)
        )
        page.on_portfolio_updated = Mock()
        page._set_waiting_state = Mock()

        page.refresh()

        page.on_portfolio_updated.assert_not_called()
        page._set_waiting_state.assert_called_once_with()

    def test_portfolio_update_populates_summary_and_history(self):
        page = self.make_page()
        self.build_metric_labels(page)
        page.status_badge = Mock()

        portfolio = {
            "analytics": {
                "summary": {
                    "total": {
                        "highest_usdt": 1500.5,
                        "lowest_usdt": 900,
                        "average_usdt": 1200.125,
                    },
                    "funding": {
                        "highest_usdt": 500,
                        "lowest_usdt": 300,
                        "average_usdt": 400,
                    },
                    "trading": {
                        "highest_usdt": 1000,
                        "lowest_usdt": 600,
                        "average_usdt": 800,
                    },
                    "snapshot_count": 42,
                    "first_timestamp": (
                        "2026-07-01T10:20:30+03:00"
                    ),
                    "last_timestamp": (
                        "2026-07-22T18:45:59+03:00"
                    ),
                }
            },
            "performance_breakdown": {},
        }

        page.on_portfolio_updated(portfolio)

        self.assertEqual(
            page.metric_labels[
                "total.highest_usdt"
            ].text(),
            "$1,500.50",
        )
        self.assertEqual(
            page.metric_labels[
                "total.lowest_usdt"
            ].text(),
            "$900.00",
        )
        self.assertEqual(
            page.metric_labels[
                "total.average_usdt"
            ].text(),
            "$1,200.12",
        )
        self.assertEqual(
            page.metric_labels[
                "funding.average_usdt"
            ].text(),
            "$400.00",
        )
        self.assertEqual(
            page.metric_labels[
                "trading.highest_usdt"
            ].text(),
            "$1,000.00",
        )
        self.assertEqual(
            page.metric_labels[
                "snapshot_count"
            ].text(),
            "42",
        )
        self.assertEqual(
            page.metric_labels[
                "first_timestamp"
            ].text(),
            "2026-07-01 10:20:30",
        )
        self.assertEqual(
            page.metric_labels[
                "last_timestamp"
            ].text(),
            "2026-07-22 18:45:59",
        )
        page.status_badge.set_status.assert_called_once_with(
            "Veri Hazır",
            analytics_module.StatusBadge.SUCCESS,
        )

    def test_portfolio_update_populates_performance_colors(self):
        page = self.make_page()
        self.build_metric_labels(page)
        page.status_badge = Mock()

        page.on_portfolio_updated(
            {
                "analytics": {"summary": {}},
                "performance_breakdown": {
                    "total": {
                        "1d": 1.234,
                        "7d": -2.345,
                        "30d": 0,
                        "90d": None,
                    },
                    "funding": {"1y": 12.5},
                    "trading": {"1d": -0.5},
                },
            }
        )

        self.assertEqual(
            page.metric_labels[
                "performance.total.1d"
            ].text(),
            "+1.23%",
        )
        self.assertIn(
            analytics_module.Theme.ACCENT,
            page.metric_labels[
                "performance.total.1d"
            ].styleSheet(),
        )
        self.assertEqual(
            page.metric_labels[
                "performance.total.7d"
            ].text(),
            "-2.35%",
        )
        self.assertIn(
            analytics_module.Theme.ERROR,
            page.metric_labels[
                "performance.total.7d"
            ].styleSheet(),
        )
        self.assertEqual(
            page.metric_labels[
                "performance.total.30d"
            ].text(),
            "+0.00%",
        )
        self.assertEqual(
            page.metric_labels[
                "performance.total.90d"
            ].text(),
            "—",
        )
        self.assertIn(
            analytics_module.Theme.TEXT_MUTED,
            page.metric_labels[
                "performance.total.90d"
            ].styleSheet(),
        )
        self.assertEqual(
            page.metric_labels[
                "performance.funding.1y"
            ].text(),
            "+12.50%",
        )
        self.assertEqual(
            page.metric_labels[
                "performance.trading.1d"
            ].text(),
            "-0.50%",
        )

    def test_portfolio_update_handles_invalid_nested_data(self):
        page = self.make_page()
        self.build_metric_labels(page)
        page.status_badge = Mock()

        page.on_portfolio_updated(
            {
                "analytics": "invalid",
                "performance_breakdown": ["invalid"],
            }
        )

        for label in page.metric_labels.values():
            self.assertEqual(label.text(), "—")

        page.status_badge.set_status.assert_called_once_with(
            "Veri Hazır",
            analytics_module.StatusBadge.SUCCESS,
        )

    def test_snapshot_count_requires_integer(self):
        page = self.make_page()
        self.build_metric_labels(page)
        page.status_badge = Mock()

        page.on_portfolio_updated(
            {
                "analytics": {
                    "summary": {
                        "snapshot_count": 12.5,
                    }
                },
                "performance_breakdown": {},
            }
        )

        self.assertEqual(
            page.metric_labels[
                "snapshot_count"
            ].text(),
            "—",
        )

    def test_portfolio_error_sets_error_status(self):
        page = self.make_page()
        page.status_badge = Mock()

        page.on_portfolio_error("network failed")

        page.status_badge.set_status.assert_called_once_with(
            "Veri Hatası",
            analytics_module.StatusBadge.ERROR,
        )

    def test_waiting_state_sets_neutral_status(self):
        page = self.make_page()
        page.status_badge = Mock()

        page._set_waiting_state()

        page.status_badge.set_status.assert_called_once_with(
            "Bekleniyor",
            analytics_module.StatusBadge.NEUTRAL,
        )

    def test_format_usdt(self):
        cases = (
            (None, "—"),
            ("100", "—"),
            (0, "$0.00"),
            (1234.567, "$1,234.57"),
            (-10.2, "$-10.20"),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    (
                        analytics_module
                        .AnalyticsPage
                        ._format_usdt(value)
                    ),
                    expected,
                )

    def test_format_timestamp(self):
        cases = (
            (None, "—"),
            ("", "—"),
            (
                "2026-07-22T18:45:59+03:00",
                "2026-07-22 18:45:59",
            ),
            (
                "2026-07-22T18:45:59",
                "2026-07-22 18:45:59",
            ),
            ("plain-text", "plain-text"),
        )

        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(
                    (
                        analytics_module
                        .AnalyticsPage
                        ._format_timestamp(value)
                    ),
                    expected,
                )

    def test_account_card_registers_metric_labels(self):
        page = self.make_page()

        card = page._create_account_card(
            key="total",
            title="Toplam Portföy",
            description="Açıklama",
        )

        self.assertIn(
            "total.highest_usdt",
            page.metric_labels,
        )
        self.assertIn(
            "total.lowest_usdt",
            page.metric_labels,
        )
        self.assertIn(
            "total.average_usdt",
            page.metric_labels,
        )
        self.assertGreaterEqual(
            card.minimumHeight(),
            220,
        )

        card.deleteLater()

    def test_performance_card_registers_all_period_labels(self):
        page = self.make_page()

        card = page._create_performance_card()

        performance_keys = [
            key
            for key in page.metric_labels
            if key.startswith("performance.")
        ]

        self.assertEqual(len(performance_keys), 15)
        self.assertIn(
            "performance.total.1d",
            performance_keys,
        )
        self.assertIn(
            "performance.funding.30d",
            performance_keys,
        )
        self.assertIn(
            "performance.trading.1y",
            performance_keys,
        )

        card.deleteLater()

    def test_history_card_registers_history_labels(self):
        page = self.make_page()

        card = page._create_history_card()

        self.assertIn(
            "snapshot_count",
            page.metric_labels,
        )
        self.assertIn(
            "first_timestamp",
            page.metric_labels,
        )
        self.assertIn(
            "last_timestamp",
            page.metric_labels,
        )

        card.deleteLater()


if __name__ == "__main__":
    unittest.main()
