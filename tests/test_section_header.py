import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
)

from ui.theme import Theme
from ui.widgets.section_header import SectionHeader


class SectionHeaderTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        instance = QApplication.instance()

        if isinstance(instance, QApplication):
            cls.qt_app = instance
        else:
            cls.qt_app = QApplication([])

    def setUp(self):
        self.widgets = []

    def tearDown(self):
        for widget in reversed(self.widgets):
            try:
                widget.close()
                widget.deleteLater()
            except RuntimeError:
                pass

    def track(self, widget):
        self.widgets.append(widget)
        return widget

    def test_constructor_builds_description_and_right_widget(
        self,
    ):
        parent = self.track(QWidget())
        right_widget = QLabel("Durum")

        header = self.track(
            SectionHeader(
                title="Portföy Özeti",
                description="Hesapların birleşik özeti",
                right_widget=right_widget,
                object_name="portfolioSectionHeader",
                parent=parent,
            )
        )

        self.assertIs(header.parent(), parent)
        self.assertEqual(
            header.objectName(),
            "portfolioSectionHeader",
        )
        self.assertEqual(
            header.title_label.text(),
            "Portföy Özeti",
        )
        self.assertEqual(
            header.title_label.objectName(),
            "sectionHeaderTitle",
        )
        self.assertEqual(
            header.description_label.text(),
            "Hesapların birleşik özeti",
        )
        self.assertEqual(
            header.description_label.objectName(),
            "sectionHeaderDescription",
        )
        self.assertTrue(
            header.description_label.wordWrap()
        )
        self.assertFalse(
            header.description_label.isHidden()
        )

        layout = header.layout()

        self.assertEqual(layout.count(), 2)
        self.assertIs(
            layout.itemAt(1).widget(),
            right_widget,
        )
        self.assertIs(
            right_widget.parentWidget(),
            header,
        )

        stylesheet = header.styleSheet()

        self.assertIn(
            "QWidget#portfolioSectionHeader",
            stylesheet,
        )
        self.assertIn(
            Theme.BORDER,
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_PRIMARY,
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_MUTED,
            stylesheet,
        )
        self.assertIn(
            Theme.FONT_FAMILY,
            stylesheet,
        )

    def test_constructor_hides_empty_description(
        self,
    ):
        header = self.track(
            SectionHeader(
                title="Geçmiş",
                description="",
            )
        )

        self.assertEqual(
            header.objectName(),
            "sectionHeader",
        )
        self.assertEqual(
            header.title_label.text(),
            "Geçmiş",
        )
        self.assertEqual(
            header.description_label.text(),
            "",
        )
        self.assertTrue(
            header.description_label.isHidden()
        )
        self.assertEqual(
            header.layout().count(),
            1,
        )

    def test_set_title_updates_title_label(self):
        header = self.track(
            SectionHeader(
                title="Eski Başlık",
            )
        )

        header.set_title("Yeni Başlık")

        self.assertEqual(
            header.title_label.text(),
            "Yeni Başlık",
        )

    def test_set_description_updates_text_and_visibility(
        self,
    ):
        header = self.track(
            SectionHeader(
                title="Performans",
                description="",
            )
        )

        self.assertTrue(
            header.description_label.isHidden()
        )

        header.set_description(
            "Dönemsel portföy değişimi"
        )

        self.assertEqual(
            header.description_label.text(),
            "Dönemsel portföy değişimi",
        )
        self.assertFalse(
            header.description_label.isHidden()
        )

        header.set_description("")

        self.assertEqual(
            header.description_label.text(),
            "",
        )
        self.assertTrue(
            header.description_label.isHidden()
        )


if __name__ == "__main__":
    unittest.main()
