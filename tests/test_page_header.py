import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
)

from ui.theme import Theme
from ui.widgets.page_header import PageHeader


class PageHeaderTestCase(unittest.TestCase):
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

    def test_constructor_builds_title_subtitle_and_right_widget(
        self,
    ):
        parent = self.track(QWidget())
        right_widget = QLabel("Durum")
        header = self.track(
            PageHeader(
                title="Portfolio",
                subtitle="Portföy durumunu takip et.",
                right_widget=right_widget,
                object_name="portfolioHeader",
                parent=parent,
            )
        )

        self.assertIs(header.parent(), parent)
        self.assertEqual(
            header.objectName(),
            "portfolioHeader",
        )
        self.assertTrue(
            header.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        self.assertEqual(
            header.title_label.text(),
            "Portfolio",
        )
        self.assertEqual(
            header.title_label.objectName(),
            "pageHeaderTitle",
        )
        self.assertEqual(
            header.subtitle_label.text(),
            "Portföy durumunu takip et.",
        )
        self.assertEqual(
            header.subtitle_label.objectName(),
            "pageHeaderSubtitle",
        )
        self.assertTrue(
            header.subtitle_label.wordWrap()
        )
        self.assertFalse(
            header.subtitle_label.isHidden()
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
            "QWidget#portfolioHeader",
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_PRIMARY,
            stylesheet,
        )
        self.assertIn(
            Theme.TEXT_SECONDARY,
            stylesheet,
        )
        self.assertIn(
            Theme.FONT_FAMILY,
            stylesheet,
        )

    def test_empty_subtitle_is_hidden_without_right_widget(
        self,
    ):
        header = self.track(
            PageHeader(
                title="Analytics",
                subtitle="",
            )
        )

        self.assertEqual(
            header.objectName(),
            "pageHeader",
        )
        self.assertEqual(
            header.title_label.text(),
            "Analytics",
        )
        self.assertEqual(
            header.subtitle_label.text(),
            "",
        )
        self.assertTrue(
            header.subtitle_label.isHidden()
        )
        self.assertEqual(
            header.layout().count(),
            1,
        )

    def test_set_title_updates_title_label(self):
        header = self.track(
            PageHeader(
                title="Eski Başlık",
            )
        )

        header.set_title("Yeni Başlık")

        self.assertEqual(
            header.title_label.text(),
            "Yeni Başlık",
        )

    def test_set_subtitle_updates_text_and_visibility(
        self,
    ):
        header = self.track(
            PageHeader(
                title="Ayarlar",
                subtitle="",
            )
        )

        self.assertTrue(
            header.subtitle_label.isHidden()
        )

        header.set_subtitle(
            "Uygulama tercihlerini yönet."
        )

        self.assertEqual(
            header.subtitle_label.text(),
            "Uygulama tercihlerini yönet.",
        )
        self.assertTrue(
            header.subtitle_label.isVisible()
        )

        header.set_subtitle("")

        self.assertEqual(
            header.subtitle_label.text(),
            "",
        )
        self.assertFalse(
            header.subtitle_label.isVisible()
        )


if __name__ == "__main__":
    unittest.main()
