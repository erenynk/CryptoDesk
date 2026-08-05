import unittest
from unittest.mock import Mock, patch

from PySide6.QtCore import QTimer
from PySide6.QtGui import QShowEvent
from PySide6.QtWidgets import QApplication, QHeaderView

from ui.alarms import AlarmsPage


class AlarmInitialColumnLayoutTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def make_page(self):
        data_manager = Mock()
        data_manager.get_price.return_value = None

        with patch(
            "ui.alarms.alarm_service.get_all_alarms",
            return_value=[],
        ):
            return AlarmsPage(data_manager)

    def test_column_modes_are_not_user_resizable(self):
        page = self.make_page()
        page._refresh_table_column_layout()
        header = page.table.horizontalHeader()

        self.assertEqual(
            header.sectionResizeMode(0),
            QHeaderView.Fixed,
        )
        self.assertEqual(
            header.sectionResizeMode(1),
            QHeaderView.Stretch,
        )
        self.assertEqual(
            header.sectionResizeMode(5),
            QHeaderView.Fixed,
        )
        self.assertEqual(
            header.sectionResizeMode(page.TOGGLE_COLUMN),
            QHeaderView.Fixed,
        )
        self.assertEqual(
            header.sectionResizeMode(page.DELETE_COLUMN),
            QHeaderView.Fixed,
        )

    def test_note_column_uses_compact_fixed_width(self):
        page = self.make_page()
        page._refresh_table_column_layout()

        self.assertEqual(page.table.columnWidth(5), 160)
        self.assertEqual(page.table.columnWidth(0), 54)
        self.assertEqual(
            page.table.columnWidth(page.TOGGLE_COLUMN),
            110,
        )
        self.assertEqual(
            page.table.columnWidth(page.DELETE_COLUMN),
            64,
        )

    def test_show_event_defers_column_refresh(self):
        page = self.make_page()

        with (
            patch.object(page, "load_alarms"),
            patch.object(QTimer, "singleShot") as single_shot,
        ):
            page.showEvent(QShowEvent())

        single_shot.assert_called_once_with(
            0,
            page._refresh_table_column_layout,
        )

    def test_refresh_without_table_is_safe(self):
        page = AlarmsPage.__new__(AlarmsPage)
        page._refresh_table_column_layout()


if __name__ == "__main__":
    unittest.main()
