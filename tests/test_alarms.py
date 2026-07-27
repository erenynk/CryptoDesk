import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QDoubleValidator
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QWidget,
)

import ui.alarms as alarms_module


class SignalStub:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)


class BareAlarmsPage(alarms_module.AlarmsPage):
    def __init__(self):
        QWidget.__init__(self)
        self.data_manager = SimpleNamespace(
            okx=SimpleNamespace(
                is_spot_symbol_available=Mock()
            ),
            get_price=Mock(),
        )
        self.row_alarms = []
        self.selected_condition = (
            alarms_module.alarm_service.CONDITION_ABOVE
        )


class AlarmsPageTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()
        cls.qt_app = (
            instance
            if isinstance(instance, QApplication)
            else QApplication([])
        )

    def setUp(self):
        self.pages = []

    def tearDown(self):
        for page in self.pages:
            page.deleteLater()

    def make_page(self):
        page = BareAlarmsPage()
        self.pages.append(page)
        return page

    def prepare_create_page(self):
        page = self.make_page()
        page.symbol_input = QLineEdit()
        page.price_input = QLineEdit()
        page.note_input = QLineEdit()
        page.condition_button = QPushButton()
        page.add_button = Mock()
        page.set_status = Mock()
        page.reset_condition = Mock()
        page.load_alarms = Mock()
        return page

    def test_constructor_initializes_and_loads(self):
        with (
            patch.object(
                alarms_module.AlarmsPage,
                "_build_ui",
            ) as build_ui,
            patch.object(
                alarms_module.AlarmsPage,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                alarms_module.AlarmsPage,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                alarms_module.AlarmsPage,
                "load_alarms",
            ) as load_alarms,
        ):
            page = alarms_module.AlarmsPage(
                sentinel.data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            sentinel.data_manager,
        )
        self.assertEqual(page.row_alarms, [])
        self.assertEqual(
            page.selected_condition,
            alarms_module.alarm_service.CONDITION_ABOVE,
        )
        self.assertEqual(page.objectName(), "alarmsPage")
        self.assertEqual(len(page.headers), 10)
        self.assertEqual(page.TOGGLE_COLUMN, 8)
        self.assertEqual(page.DELETE_COLUMN, 9)
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        connect_signals.assert_called_once_with()
        load_alarms.assert_called_once_with()

    def test_connect_signals_wires_controls(self):
        page = self.make_page()
        signals = [SignalStub() for _ in range(6)]
        page.symbol_input = SimpleNamespace(
            returnPressed=signals[0]
        )
        page.price_input = SimpleNamespace(
            returnPressed=signals[1]
        )
        page.note_input = SimpleNamespace(
            returnPressed=signals[2]
        )
        page.condition_button = SimpleNamespace(
            clicked=signals[3]
        )
        page.add_button = SimpleNamespace(
            clicked=signals[4]
        )
        page.table = SimpleNamespace(
            cellClicked=signals[5]
        )

        page._connect_signals()

        self.assertEqual(
            signals[0].callbacks,
            [page.create_alarm],
        )
        self.assertEqual(
            signals[1].callbacks,
            [page.create_alarm],
        )
        self.assertEqual(
            signals[2].callbacks,
            [page.create_alarm],
        )
        self.assertEqual(
            signals[3].callbacks,
            [page.toggle_condition],
        )
        self.assertEqual(
            signals[4].callbacks,
            [page.create_alarm],
        )
        self.assertEqual(
            signals[5].callbacks,
            [page.on_table_cell_clicked],
        )

    def test_toggle_reset_and_table_actions(self):
        page = self.make_page()
        page.condition_button = QPushButton()

        page.toggle_condition()
        self.assertEqual(
            page.selected_condition,
            alarms_module.alarm_service.CONDITION_BELOW,
        )
        self.assertEqual(
            page.condition_button.text(),
            "Fiyat Altına Düşünce",
        )

        page.reset_condition()
        self.assertEqual(
            page.selected_condition,
            alarms_module.alarm_service.CONDITION_ABOVE,
        )
        self.assertEqual(
            page.condition_button.text(),
            "Fiyat Üstüne Çıkınca",
        )

        page.row_alarms = [
            {
                "id": 11,
                "is_active": True,
                "is_triggered": False,
            },
            {
                "id": 12,
                "is_active": False,
                "is_triggered": True,
            },
        ]
        page.toggle_alarm = Mock()
        page.delete_alarm = Mock()

        page.on_table_cell_clicked(0, 8)
        page.on_table_cell_clicked(1, 8)
        page.on_table_cell_clicked(0, 9)
        page.on_table_cell_clicked(-1, 9)

        page.toggle_alarm.assert_called_once_with(11, True)
        page.delete_alarm.assert_called_once_with(11)

    def test_status_helpers(self):
        page = self.make_page()
        page.status_label = QLabel()
        page.status_label.hide()

        page.set_status("Başarılı")
        self.assertEqual(page.status_label.text(), "Başarılı")
        self.assertIn(
            alarms_module.Theme.ACCENT,
            page.status_label.styleSheet(),
        )
        self.assertFalse(page.status_label.isHidden())

        page.set_status("Hata", error=True)
        self.assertIn(
            alarms_module.Theme.ERROR,
            page.status_label.styleSheet(),
        )

        page.clear_status()
        self.assertEqual(page.status_label.text(), "")
        self.assertTrue(page.status_label.isHidden())

    def test_create_alarm_validates_symbol_and_price(self):
        cases = (
            ("", "100", "Coin kodu boş olamaz."),
            ("BTC", "", "Hedef fiyat boş olamaz."),
            ("BTC", "abc", "Geçerli bir hedef fiyat girin."),
            (
                "BTC",
                "0",
                "Hedef fiyat sıfırdan büyük olmalıdır.",
            ),
        )

        for symbol, price, expected in cases:
            with self.subTest(symbol=symbol, price=price):
                page = self.prepare_create_page()
                page.symbol_input.setText(symbol)
                page.price_input.setText(price)

                with patch.object(
                    alarms_module,
                    "normalize_symbol",
                    return_value=symbol.strip(),
                ):
                    page.create_alarm()

                page.set_status.assert_called_once_with(
                    expected,
                    error=True,
                )
                page.add_button.setEnabled.assert_not_called()

    def test_create_alarm_handles_market_lookup_results(self):
        page = self.prepare_create_page()
        page.symbol_input.setText("BTC")
        page.price_input.setText("100")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            False,
            "Sembol listesi alınamadı.",
        )

        with patch.object(
            alarms_module,
            "normalize_symbol",
            return_value="BTC",
        ):
            page.create_alarm()

        page.set_status.assert_called_once_with(
            "Sembol listesi alınamadı.",
            error=True,
        )
        self.assertEqual(
            page.add_button.setEnabled.call_args_list,
            [call(False), call(True)],
        )

        page.set_status.reset_mock()
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            False,
        )

        with patch.object(
            alarms_module,
            "normalize_symbol",
            return_value="BTC",
        ):
            page.create_alarm()

        page.set_status.assert_called_once_with(
            "BTC OKX Spot piyasasında bulunamadı.",
            error=True,
        )

    def test_create_alarm_service_failure_and_exception(self):
        page = self.prepare_create_page()
        page.symbol_input.setText("BTC")
        page.price_input.setText("70,5")
        page.note_input.setText("  Kâr al  ")
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            True,
        )

        with (
            patch.object(
                alarms_module,
                "normalize_symbol",
                return_value="BTC",
            ),
            patch.object(
                alarms_module.alarm_service,
                "create_alarm",
                return_value=(False, "Veritabanı hatası"),
            ) as create_alarm,
        ):
            page.create_alarm()

        create_alarm.assert_called_once_with(
            symbol="BTC",
            target_price=70.5,
            condition=(
                alarms_module.alarm_service.CONDITION_ABOVE
            ),
            note="Kâr al",
        )
        page.set_status.assert_called_once_with(
            "Veritabanı hatası",
            error=True,
        )

        page.set_status.reset_mock()
        page.data_manager.okx.is_spot_symbol_available.side_effect = (
            RuntimeError("network error")
        )

        with patch.object(
            alarms_module,
            "normalize_symbol",
            return_value="BTC",
        ):
            page.create_alarm()

        page.set_status.assert_called_once_with(
            "Alarm oluşturulamadı: network error",
            error=True,
        )
        page.add_button.setText.assert_called_with(
            "Alarm Oluştur"
        )

    def test_create_alarm_success_resets_form(self):
        page = self.prepare_create_page()
        page.symbol_input.setText(" btc-usdt ")
        page.price_input.setText(" 70000.25 ")
        page.note_input.setText("  Kâr al  ")
        page.selected_condition = (
            alarms_module.alarm_service.CONDITION_BELOW
        )
        page.data_manager.okx.is_spot_symbol_available.return_value = (
            True,
            True,
        )

        with (
            patch.object(
                alarms_module,
                "normalize_symbol",
                return_value="BTC",
            ),
            patch.object(
                alarms_module.alarm_service,
                "create_alarm",
                return_value=(True, 123),
            ) as create_alarm,
        ):
            page.create_alarm()

        create_alarm.assert_called_once_with(
            symbol="BTC",
            target_price=70000.25,
            condition=(
                alarms_module.alarm_service.CONDITION_BELOW
            ),
            note="Kâr al",
        )
        self.assertEqual(page.symbol_input.text(), "")
        self.assertEqual(page.price_input.text(), "")
        self.assertEqual(page.note_input.text(), "")
        page.reset_condition.assert_called_once_with()
        page.set_status.assert_called_once_with(
            "BTC alarmı oluşturuldu."
        )
        page.load_alarms.assert_called_once_with()
        page.add_button.setEnabled.assert_called_with(True)

    def test_toggle_alarm_success_and_failure(self):
        page = self.make_page()
        page.clear_status = Mock()
        page.load_alarms = Mock()
        page.set_status = Mock()

        with patch.object(
            alarms_module.alarm_service,
            "change_alarm_status",
            return_value=True,
        ) as change_status:
            page.toggle_alarm(10, True)

        change_status.assert_called_once_with(10, False)
        page.clear_status.assert_called_once_with()
        page.load_alarms.assert_called_once_with()

        page.clear_status.reset_mock()
        page.load_alarms.reset_mock()

        with patch.object(
            alarms_module.alarm_service,
            "change_alarm_status",
            return_value=False,
        ):
            page.toggle_alarm(11, False)

        page.set_status.assert_called_once_with(
            "Alarm durumu değiştirilemedi.",
            error=True,
        )

    def test_delete_alarm_success_and_failure(self):
        page = self.make_page()
        page.clear_status = Mock()
        page.load_alarms = Mock()
        page.set_status = Mock()

        with patch.object(
            alarms_module.alarm_service,
            "remove_alarm",
            return_value=True,
        ):
            page.delete_alarm(20)

        page.clear_status.assert_called_once_with()
        page.load_alarms.assert_called_once_with()

        page.clear_status.reset_mock()
        page.load_alarms.reset_mock()

        with patch.object(
            alarms_module.alarm_service,
            "remove_alarm",
            return_value=False,
        ):
            page.delete_alarm(21)

        page.set_status.assert_called_once_with(
            "Alarm silinemedi.",
            error=True,
        )

    def test_load_alarms_counts_active_and_restores_updates(self):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(10)
        page.alarm_count_badge = Mock()
        page._populate_alarm_row = Mock()
        alarms = [
            {
                "id": 1,
                "is_active": True,
                "is_triggered": False,
            },
            {
                "id": 2,
                "is_active": False,
                "is_triggered": False,
            },
            {
                "id": 3,
                "is_active": True,
                "is_triggered": True,
            },
        ]

        with patch.object(
            alarms_module.alarm_service,
            "get_all_alarms",
            return_value=alarms,
        ):
            page.load_alarms()

        self.assertIs(page.row_alarms, alarms)
        self.assertEqual(page.table.rowCount(), 3)
        self.assertEqual(
            page._populate_alarm_row.call_args_list,
            [
                call(0, alarms[0]),
                call(1, alarms[1]),
                call(2, alarms[2]),
            ],
        )
        self.assertTrue(page.table.updatesEnabled())
        page.alarm_count_badge.set_status.assert_called_once_with(
            "1 aktif alarm",
            alarms_module.StatusBadge.SUCCESS,
        )

    def test_load_alarms_restores_updates_after_error(self):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(10)
        page.alarm_count_badge = Mock()
        page._populate_alarm_row = Mock(
            side_effect=RuntimeError("row failed")
        )

        with (
            patch.object(
                alarms_module.alarm_service,
                "get_all_alarms",
                return_value=[{"id": 1}],
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "row failed",
            ),
        ):
            page.load_alarms()

        self.assertTrue(page.table.updatesEnabled())

    def test_populate_alarm_row_sets_cells_and_tooltips(self):
        page = self.make_page()
        page.table = QTableWidget()
        page.table.setColumnCount(10)
        page.table.setRowCount(1)
        page.data_manager.get_price.return_value = 71000.0
        alarm = {
            "id": 1,
            "symbol": "BTC",
            "target_price": 70000.0,
            "condition": (
                alarms_module.alarm_service.CONDITION_ABOVE
            ),
            "note": "Kâr al",
            "is_active": True,
            "is_triggered": False,
            "created_at": "2026-07-22T18:45:00",
        }

        with (
            patch.object(
                alarms_module.alarm_service,
                "get_condition_text",
                return_value="Fiyat Üstüne Çıkınca",
            ),
            patch.object(
                alarms_module.alarm_service,
                "get_status_text",
                return_value="Aktif",
            ),
        ):
            page._populate_alarm_row(0, alarm)

        expected = {
            0: "1",
            1: "BTC",
            2: "$70,000.00",
            3: "Fiyat Üstüne Çıkınca",
            4: "$71,000.00",
            5: "Kâr al",
            6: "Aktif",
            7: "22.07.2026 18:45",
            8: "Pasif Et",
            9: "🗑",
        }

        for column, text in expected.items():
            with self.subTest(column=column):
                self.assertEqual(
                    page.table.item(0, column).text(),
                    text,
                )

        self.assertEqual(
            page.table.item(0, 5).toolTip(),
            "Kâr al",
        )
        self.assertTrue(
            page.table.item(0, 8).toolTip()
        )
        self.assertTrue(
            page.table.item(0, 9).toolTip()
        )

    def test_display_color_and_item_helpers(self):
        self.assertEqual(
            alarms_module.AlarmsPage.get_toggle_display(
                {"is_triggered": True}
            ),
            (
                "Tamamlandı",
                alarms_module.Theme.TEXT_MUTED,
            ),
        )
        self.assertEqual(
            alarms_module.AlarmsPage.get_toggle_display(
                {"is_active": True}
            ),
            (
                "Pasif Et",
                alarms_module.Theme.WARNING,
            ),
        )
        self.assertEqual(
            alarms_module.AlarmsPage.get_toggle_display({}),
            (
                "Aktif Et",
                alarms_module.Theme.ACCENT,
            ),
        )
        self.assertEqual(
            alarms_module.AlarmsPage.get_status_color(
                {"is_triggered": True}
            ),
            alarms_module.Theme.TEXT_MUTED,
        )
        self.assertEqual(
            alarms_module.AlarmsPage.get_status_color(
                {"is_active": True}
            ),
            alarms_module.Theme.ACCENT,
        )
        self.assertEqual(
            alarms_module.AlarmsPage.get_status_color({}),
            alarms_module.Theme.ERROR,
        )

        item = alarms_module.AlarmsPage.create_item(
            "BTC",
            color="#123456",
            bold=False,
            alignment=Qt.AlignLeft | Qt.AlignVCenter,
        )
        self.assertEqual(item.text(), "BTC")
        self.assertEqual(
            item.foreground().color(),
            QColor("#123456"),
        )
        self.assertFalse(item.font().bold())

    def test_format_helpers(self):
        price_cases = (
            (None, "-"),
            (0, "-"),
            (1, "$1.00"),
            (1234.567, "$1,234.57"),
            (0.123456, "$0.1235"),
            (0.00123456789, "$0.00123457"),
        )

        for price, expected in price_cases:
            with self.subTest(price=price):
                self.assertEqual(
                    alarms_module.AlarmsPage.format_price(
                        price
                    ),
                    expected,
                )

        date_cases = (
            (
                "2026-07-22T18:45:00",
                "22.07.2026 18:45",
            ),
            (
                "2026-07-22T15:45:00Z",
                "22.07.2026 15:45",
            ),
            (None, "-"),
            ("invalid", "-"),
        )

        for value, expected in date_cases:
            with self.subTest(value=value):
                self.assertEqual(
                    alarms_module.AlarmsPage.format_date(
                        value
                    ),
                    expected,
                )

    def test_show_event_reloads_alarms(self):
        page = self.make_page()
        page.load_alarms = Mock()
        event = Mock()

        with patch.object(
            QWidget,
            "showEvent",
        ) as super_show:
            page.showEvent(event)

        super_show.assert_called_once_with(event)
        page.load_alarms.assert_called_once_with()



    def test_full_constructor_builds_complete_page(
        self,
    ):
        data_manager = SimpleNamespace(
            okx=SimpleNamespace(
                is_spot_symbol_available=Mock()
            ),
            get_price=Mock(),
        )

        with patch.object(
            alarms_module.alarm_service,
            "get_all_alarms",
            return_value=[],
        ):
            page = alarms_module.AlarmsPage(
                data_manager
            )
            self.pages.append(page)

        self.assertIs(
            page.data_manager,
            data_manager,
        )
        self.assertEqual(
            page.layout().count(),
            3,
        )
        self.assertEqual(
            page.alarm_count_badge.objectName(),
            "alarmCountBadge",
        )
        self.assertEqual(
            page.alarm_count_badge.text(),
            "0 aktif alarm",
        )

        self.assertEqual(
            page.symbol_input.objectName(),
            "symbolInput",
        )
        self.assertEqual(
            page.symbol_input.placeholderText(),
            "Coin: BTC",
        )
        self.assertTrue(
            page.symbol_input.isClearButtonEnabled()
        )
        self.assertEqual(
            page.symbol_input.minimumWidth(),
            120,
        )
        self.assertEqual(
            page.symbol_input.maximumWidth(),
            180,
        )

        self.assertEqual(
            page.price_input.objectName(),
            "priceInput",
        )
        self.assertEqual(
            page.price_input.placeholderText(),
            "Hedef fiyat",
        )
        self.assertTrue(
            page.price_input.isClearButtonEnabled()
        )
        self.assertEqual(
            page.price_input.minimumWidth(),
            140,
        )
        self.assertEqual(
            page.price_input.maximumWidth(),
            210,
        )

        validator = page.price_input.validator()

        self.assertIsInstance(
            validator,
            QDoubleValidator,
        )
        self.assertEqual(
            validator.bottom(),
            0.00000001,
        )
        self.assertEqual(
            validator.top(),
            999999999999.0,
        )
        self.assertEqual(
            validator.decimals(),
            8,
        )
        self.assertEqual(
            validator.notation(),
            QDoubleValidator.StandardNotation,
        )

        self.assertEqual(
            page.condition_button.objectName(),
            "conditionButton",
        )
        self.assertEqual(
            page.condition_button.text(),
            "Fiyat Üstüne Çıkınca",
        )
        self.assertEqual(
            page.condition_button.cursor().shape(),
            Qt.PointingHandCursor,
        )

        self.assertEqual(
            page.note_input.objectName(),
            "noteInput",
        )
        self.assertEqual(
            page.note_input.placeholderText(),
            "Alarm notu (isteğe bağlı)",
        )
        self.assertEqual(
            page.note_input.maxLength(),
            alarms_module.alarm_service.MAX_NOTE_LENGTH,
        )
        self.assertTrue(
            page.note_input.isClearButtonEnabled()
        )

        self.assertEqual(
            page.add_button.objectName(),
            "addButton",
        )
        self.assertEqual(
            page.add_button.text(),
            "Alarm Oluştur",
        )
        self.assertEqual(
            page.status_label.objectName(),
            "statusLabel",
        )
        self.assertTrue(
            page.status_label.isHidden()
        )

        self.assertEqual(
            page.table.objectName(),
            "alarmsTable",
        )
        self.assertEqual(
            page.table.columnCount(),
            10,
        )
        self.assertEqual(
            page.table.horizontalHeader().objectName(),
            "alarmsTableHeader",
        )
        self.assertFalse(
            page.table.showGrid()
        )
        self.assertFalse(
            page.table.wordWrap()
        )
        self.assertFalse(
            page.table.verticalHeader().isVisible()
        )
        self.assertEqual(
            page.table.columnWidth(0),
            54,
        )
        self.assertEqual(
            page.table.columnWidth(5),
            240,
        )
        self.assertEqual(
            page.table.columnWidth(
                page.TOGGLE_COLUMN
            ),
            110,
        )
        self.assertEqual(
            page.table.columnWidth(
                page.DELETE_COLUMN
            ),
            64,
        )

        labels = [
            label.text()
            for label in page.findChildren(QLabel)
        ]

        self.assertIn(
            "Alarmlar",
            labels,
        )
        self.assertIn(
            "Yeni Alarm",
            labels,
        )
        self.assertIn(
            "Fiyat Alarmları",
            labels,
        )

        stylesheet = page.styleSheet()

        self.assertIn(
            "QWidget#alarmsPage",
            stylesheet,
        )
        self.assertIn(
            "QPushButton#conditionButton",
            stylesheet,
        )
        self.assertIn(
            "QTableWidget#alarmsTable",
            stylesheet,
        )
        self.assertIn(
            "QHeaderView#alarmsTableHeader",
            stylesheet,
        )
        self.assertIn(
            alarms_module.Theme.TEXT_PRIMARY,
            stylesheet,
        )
        self.assertIn(
            alarms_module.Theme.BORDER_SOFT,
            stylesheet,
        )

    def test_toggle_condition_switches_both_directions(
        self,
    ):
        page = self.make_page()
        page.condition_button = QPushButton(
            "Fiyat Üstüne Çıkınca"
        )

        page.toggle_condition()

        self.assertEqual(
            page.selected_condition,
            alarms_module.alarm_service.CONDITION_BELOW,
        )
        self.assertEqual(
            page.condition_button.text(),
            "Fiyat Altına Düşünce",
        )

        page.toggle_condition()

        self.assertEqual(
            page.selected_condition,
            alarms_module.alarm_service.CONDITION_ABOVE,
        )
        self.assertEqual(
            page.condition_button.text(),
            "Fiyat Üstüne Çıkınca",
        )



if __name__ == "__main__":
    unittest.main()
