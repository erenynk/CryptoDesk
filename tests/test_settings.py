import os
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, call, patch
from unittest.mock import sentinel

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)

import ui.settings as settings_module


class BareSettingsPage(settings_module.SettingsPage):
    def __init__(self):
        QWidget.__init__(self)
        self.password_fields = []
        self.app_setting_controls = {}


class SettingsPageTestCase(unittest.TestCase):
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
        page = BareSettingsPage()
        self.pages.append(page)
        return page

    def test_constructor_initializes_dependencies_and_ui(
        self,
    ):
        with (
            patch.object(
                settings_module,
                "OKXService",
                return_value=sentinel.okx_service,
            ) as service_class,
            patch.object(
                settings_module.SettingsPage,
                "_build_ui",
            ) as build_ui,
            patch.object(
                settings_module.SettingsPage,
                "_apply_styles",
            ) as apply_styles,
            patch.object(
                settings_module.SettingsPage,
                "_apply_settings_palette",
            ) as apply_palette,
            patch.object(
                settings_module.SettingsPage,
                "_connect_signals",
            ) as connect_signals,
            patch.object(
                settings_module.SettingsPage,
                "_load_saved_settings",
            ) as load_saved,
        ):
            page = settings_module.SettingsPage()
            self.pages.append(page)

        self.assertIs(
            page.okx_service,
            sentinel.okx_service,
        )
        self.assertEqual(page.password_fields, [])
        self.assertEqual(
            page.app_setting_controls,
            {},
        )
        self.assertEqual(
            page.objectName(),
            "settingsPage",
        )
        self.assertTrue(
            page.testAttribute(
                Qt.WA_StyledBackground
            )
        )
        service_class.assert_called_once_with()
        build_ui.assert_called_once_with()
        apply_styles.assert_called_once_with()
        apply_palette.assert_called_once_with()
        connect_signals.assert_called_once_with()
        load_saved.assert_called_once_with()

    def test_create_normal_input_section(
        self,
    ):
        page = self.make_page()

        section = page._create_input_section(
            label="API",
            description="Anahtar",
            password=False,
        )

        line_edit = section["input"]

        self.assertIsInstance(
            section["widget"],
            QWidget,
        )
        self.assertIsInstance(
            line_edit,
            QLineEdit,
        )
        self.assertEqual(
            line_edit.echoMode(),
            QLineEdit.Normal,
        )
        self.assertTrue(
            line_edit.isClearButtonEnabled()
        )
        self.assertEqual(
            page.password_fields,
            [],
        )
        self.assertIsNone(
            section["widget"].findChild(
                QPushButton,
                "visibilityButton",
            )
        )

    def test_create_password_input_section(
        self,
    ):
        page = self.make_page()

        section = page._create_input_section(
            label="Secret",
            description="Gizli anahtar",
            password=True,
        )

        line_edit = section["input"]
        button = section["widget"].findChild(
            QPushButton,
            "visibilityButton",
        )

        self.assertEqual(
            line_edit.echoMode(),
            QLineEdit.Password,
        )
        self.assertFalse(
            line_edit.isClearButtonEnabled()
        )
        self.assertEqual(
            page.password_fields,
            [line_edit],
        )
        self.assertIsNotNone(button)
        self.assertEqual(button.text(), "Göster")

    def test_create_setting_row_registers_checkbox(
        self,
    ):
        page = self.make_page()

        row = page._create_setting_row(
            key="notifications_enabled",
            label="Bildirimler",
            description="Bildirimleri göster.",
        )

        checkbox = page.app_setting_controls[
            "notifications_enabled"
        ]

        self.assertIsInstance(row, QWidget)
        self.assertIsInstance(
            checkbox,
            QCheckBox,
        )
        self.assertEqual(
            checkbox.objectName(),
            "settingToggle",
        )
        self.assertGreaterEqual(
            row.minimumHeight(),
            58,
        )

        texts = [
            label.text()
            for label in row.findChildren(QLabel)
        ]
        self.assertIn("Bildirimler", texts)
        self.assertIn(
            "Bildirimleri göster.",
            texts,
        )

    def test_load_saved_settings_populates_credentials(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit()
        page.secret = QLineEdit()
        page.passphrase = QLineEdit()
        page.connection_result = QLabel(
            "Başlangıç"
        )
        page._load_saved_app_settings = Mock()

        with patch.object(
            settings_module,
            "load_settings",
            return_value=(
                "api-key",
                "secret-key",
                "passphrase",
            ),
        ) as load_settings:
            page._load_saved_settings()

        load_settings.assert_called_once_with()
        self.assertEqual(
            page.api.text(),
            "api-key",
        )
        self.assertEqual(
            page.secret.text(),
            "secret-key",
        )
        self.assertEqual(
            page.passphrase.text(),
            "passphrase",
        )
        self.assertEqual(
            page.connection_result.text(),
            (
                "Kayıtlı API bilgileri bulundu. "
                "Bağlantıyı doğrulamak için "
                "test edebilirsiniz."
            ),
        )
        page._load_saved_app_settings.assert_called_once_with()

    def test_load_saved_settings_handles_empty_values(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit()
        page.secret = QLineEdit()
        page.passphrase = QLineEdit()
        page.connection_result = QLabel(
            "Değişmedi"
        )
        page._load_saved_app_settings = Mock()

        with patch.object(
            settings_module,
            "load_settings",
            return_value=(None, "", None),
        ):
            page._load_saved_settings()

        self.assertEqual(page.api.text(), "")
        self.assertEqual(page.secret.text(), "")
        self.assertEqual(
            page.passphrase.text(),
            "",
        )
        self.assertEqual(
            page.connection_result.text(),
            "Değişmedi",
        )
        page._load_saved_app_settings.assert_called_once_with()

    def test_load_saved_app_settings_updates_all_controls(
        self,
    ):
        page = self.make_page()
        first = Mock()
        second = Mock()
        third = Mock()
        page.app_setting_controls = {
            "enabled": first,
            "disabled": second,
            "missing": third,
        }

        with patch.object(
            settings_module,
            "get_all_app_settings",
            return_value={
                "enabled": 1,
                "disabled": 0,
            },
        ) as get_settings:
            page._load_saved_app_settings()

        get_settings.assert_called_once_with()
        first.setChecked.assert_called_once_with(
            True
        )
        second.setChecked.assert_called_once_with(
            False
        )
        third.setChecked.assert_called_once_with(
            False
        )

    def test_save_app_preferences_success(
        self,
    ):
        page = self.make_page()
        page.save_preferences_button = Mock()
        first = Mock()
        second = Mock()
        first.isChecked.return_value = True
        second.isChecked.return_value = False
        page.app_setting_controls = {
            "notifications_enabled": first,
            "alarm_sound_enabled": second,
        }
        emissions = []
        page.app_settings_changed.connect(
            emissions.append
        )

        with (
            patch.object(
                settings_module,
                "save_app_settings",
                return_value=True,
            ) as save_settings,
            patch.object(
                settings_module.QMessageBox,
                "information",
            ) as information,
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save_app_preferences()

        expected = {
            "notifications_enabled": True,
            "alarm_sound_enabled": False,
        }
        save_settings.assert_called_once_with(
            expected
        )
        self.assertEqual(emissions, [expected])
        information.assert_called_once_with(
            page,
            "Başarılı",
            "Uygulama tercihleri kaydedildi.",
        )
        warning.assert_not_called()
        self.assertEqual(
            page.save_preferences_button
            .setEnabled.call_args_list,
            [
                call(False),
                call(True),
            ],
        )
        self.assertEqual(
            page.save_preferences_button
            .setText.call_args_list,
            [
                call("Kaydediliyor..."),
                call("Tercihleri Kaydet"),
            ],
        )

    def test_save_app_preferences_handles_false_result(
        self,
    ):
        page = self.make_page()
        page.save_preferences_button = Mock()
        checkbox = Mock()
        checkbox.isChecked.return_value = True
        page.app_setting_controls = {
            "balance_widget_enabled": checkbox,
        }
        emissions = []
        page.app_settings_changed.connect(
            emissions.append
        )

        with (
            patch.object(
                settings_module,
                "save_app_settings",
                return_value=False,
            ),
            patch.object(
                settings_module.QMessageBox,
                "information",
            ) as information,
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save_app_preferences()

        self.assertEqual(emissions, [])
        information.assert_not_called()
        warning.assert_called_once()
        self.assertIn(
            "veritabanına yazılamadı",
            warning.call_args.args[2],
        )
        page.save_preferences_button.setEnabled.assert_called_with(
            True
        )
        page.save_preferences_button.setText.assert_called_with(
            "Tercihleri Kaydet"
        )

    def test_save_app_preferences_handles_exception(
        self,
    ):
        page = self.make_page()
        page.save_preferences_button = Mock()
        checkbox = Mock()
        checkbox.isChecked.return_value = False
        page.app_setting_controls = {
            "notifications_enabled": checkbox,
        }

        with (
            patch.object(
                settings_module,
                "save_app_settings",
                side_effect=RuntimeError(
                    "database unavailable"
                ),
            ),
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save_app_preferences()

        warning.assert_called_once_with(
            page,
            "Kayıt Hatası",
            (
                "Tercihler kaydedilemedi:\n"
                "database unavailable"
            ),
        )
        page.save_preferences_button.setEnabled.assert_called_with(
            True
        )

    def test_toggle_password_visibility_both_directions(
        self,
    ):
        field = QLineEdit()
        button = QPushButton()

        field.setEchoMode(QLineEdit.Password)
        settings_module.SettingsPage._toggle_password_visibility(
            field,
            button,
        )

        self.assertEqual(
            field.echoMode(),
            QLineEdit.Normal,
        )
        self.assertEqual(button.text(), "Gizle")

        settings_module.SettingsPage._toggle_password_visibility(
            field,
            button,
        )

        self.assertEqual(
            field.echoMode(),
            QLineEdit.Password,
        )
        self.assertEqual(button.text(), "Göster")

    def test_save_rejects_missing_credentials(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit(" api ")
        page.secret = QLineEdit("")
        page.passphrase = QLineEdit(" pass ")
        page.save_button = Mock()
        page.okx_service = Mock()

        with (
            patch.object(
                settings_module,
                "save_settings",
            ) as save_settings,
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save()

        save_settings.assert_not_called()
        page.okx_service.refresh_client.assert_not_called()
        page.save_button.setEnabled.assert_not_called()
        warning.assert_called_once_with(
            page,
            "Eksik Bilgi",
            (
                "API Key, Secret Key ve Passphrase "
                "alanlarının tamamını doldurun."
            ),
        )

    def test_save_trims_persists_and_refreshes_client(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit("  api-key  ")
        page.secret = QLineEdit(
            "  secret-key  "
        )
        page.passphrase = QLineEdit(
            "  passphrase  "
        )
        page.save_button = Mock()
        page.okx_service = Mock()
        page.connection_result = QLabel()

        with (
            patch.object(
                settings_module,
                "save_settings",
            ) as save_settings,
            patch.object(
                settings_module.QMessageBox,
                "information",
            ) as information,
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save()

        save_settings.assert_called_once_with(
            "api-key",
            "secret-key",
            "passphrase",
        )
        page.okx_service.refresh_client.assert_called_once_with()
        self.assertEqual(
            page.connection_result.text(),
            (
                "API bilgileri güvenli şekilde "
                "kaydedildi."
            ),
        )
        information.assert_called_once_with(
            page,
            "Başarılı",
            "Ayarlar güvenli şekilde kaydedildi.",
        )
        warning.assert_not_called()
        self.assertEqual(
            page.save_button.setEnabled.call_args_list,
            [
                call(False),
                call(True),
            ],
        )
        self.assertEqual(
            page.save_button.setText.call_args_list,
            [
                call("Kaydediliyor..."),
                call("Ayarları Kaydet"),
            ],
        )

    def test_save_handles_storage_error_and_resets_button(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit("api")
        page.secret = QLineEdit("secret")
        page.passphrase = QLineEdit("pass")
        page.save_button = Mock()
        page.okx_service = Mock()
        page.connection_result = QLabel(
            "unchanged"
        )

        with (
            patch.object(
                settings_module,
                "save_settings",
                side_effect=OSError(
                    "disk error"
                ),
            ),
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.save()

        page.okx_service.refresh_client.assert_not_called()
        self.assertEqual(
            page.connection_result.text(),
            "unchanged",
        )
        warning.assert_called_once_with(
            page,
            "Kayıt Hatası",
            "Ayarlar kaydedilemedi:\ndisk error",
        )
        page.save_button.setEnabled.assert_called_with(
            True
        )
        page.save_button.setText.assert_called_with(
            "Ayarları Kaydet"
        )

    def test_connection_rejects_missing_credentials(
        self,
    ):
        page = self.make_page()
        page.api = QLineEdit("api")
        page.secret = QLineEdit("")
        page.passphrase = QLineEdit("pass")
        page.test_button = Mock()
        page.okx_service = Mock()

        with (
            patch.object(
                settings_module,
                "OKXClient",
            ) as client_class,
            patch.object(
                settings_module.QMessageBox,
                "warning",
            ) as warning,
        ):
            page.test_connection()

        client_class.assert_not_called()
        page.okx_service.check_connection.assert_not_called()
        page.test_button.setEnabled.assert_not_called()
        warning.assert_called_once_with(
            page,
            "Eksik Bilgi",
            (
                "Bağlantıyı test etmek için tüm API "
                "alanlarını doldurun."
            ),
        )

    def prepare_connection_page(self):
        page = self.make_page()
        page.api = QLineEdit("  api  ")
        page.secret = QLineEdit(" secret ")
        page.passphrase = QLineEdit(" pass ")
        page.test_button = Mock()
        page.okx_service = SimpleNamespace(
            client=None,
            check_connection=Mock(),
        )
        page.connection_result = QLabel()
        page.permission_summary = Mock()
        page._set_connection_state = Mock()
        page._handle_successful_connection = Mock()
        page._handle_failed_connection = Mock()
        return page

    def test_connection_success_creates_client_and_delegates(
        self,
    ):
        page = self.prepare_connection_page()
        result = {
            "uid": "123",
        }
        page.okx_service.check_connection.return_value = (
            True,
            result,
        )

        with patch.object(
            settings_module,
            "OKXClient",
            return_value=sentinel.client,
        ) as client_class:
            page.test_connection()

        client_class.assert_called_once_with(
            "api",
            "secret",
            "pass",
        )
        self.assertIs(
            page.okx_service.client,
            sentinel.client,
        )
        page._set_connection_state.assert_called_once_with(
            text="Bağlantı kontrol ediliyor",
            color=settings_module.Theme.WARNING,
        )
        self.assertEqual(
            page.connection_result.text(),
            "OKX API bağlantısı kontrol ediliyor...",
        )
        page.permission_summary.hide.assert_called_once_with()
        page._handle_successful_connection.assert_called_once_with(
            result
        )
        page._handle_failed_connection.assert_not_called()
        self.assertEqual(
            page.test_button.setEnabled.call_args_list,
            [
                call(False),
                call(True),
            ],
        )
        self.assertEqual(
            page.test_button.setText.call_args_list,
            [
                call("Test ediliyor..."),
                call("Bağlantıyı Test Et"),
            ],
        )

    def test_connection_failed_result_delegates_message(
        self,
    ):
        page = self.prepare_connection_page()
        page.okx_service.check_connection.return_value = (
            False,
            {
                "error": "invalid key",
            },
        )

        with patch.object(
            settings_module,
            "OKXClient",
            return_value=sentinel.client,
        ):
            page.test_connection()

        page._handle_successful_connection.assert_not_called()
        page._handle_failed_connection.assert_called_once_with(
            "{'error': 'invalid key'}"
        )
        page.test_button.setEnabled.assert_called_with(
            True
        )

    def test_connection_exception_delegates_and_resets(
        self,
    ):
        page = self.prepare_connection_page()

        with patch.object(
            settings_module,
            "OKXClient",
            side_effect=RuntimeError(
                "client failed"
            ),
        ):
            page.test_connection()

        page._handle_failed_connection.assert_called_once_with(
            "client failed"
        )
        page.okx_service.check_connection.assert_not_called()
        page.test_button.setEnabled.assert_called_with(
            True
        )
        page.test_button.setText.assert_called_with(
            "Bağlantıyı Test Et"
        )

    def test_handle_successful_connection_updates_ui(
        self,
    ):
        page = self.make_page()
        page.connection_result = QLabel()
        page.permission_summary = QLabel()
        page._set_connection_state = Mock()

        result = {
            "uid": "user-7",
            "permissions": {
                "read": True,
                "trade": False,
                "withdraw": True,
            },
        }

        with patch.object(
            settings_module.QMessageBox,
            "information",
        ) as information:
            page._handle_successful_connection(
                result
            )

        page._set_connection_state.assert_called_once_with(
            text="API Bağlı",
            color=settings_module.Theme.ACCENT,
        )
        self.assertEqual(
            page.connection_result.text(),
            "OKX bağlantısı başarılı. UID: user-7",
        )
        self.assertEqual(
            page.permission_summary.text(),
            (
                "Read: İzin Var\n"
                "Trade: İzin Yok\n"
                "Withdraw: İzin Var"
            ),
        )
        self.assertFalse(
            page.permission_summary.isHidden()
        )
        information.assert_called_once()
        message = information.call_args.args[2]
        self.assertIn("UID: user-7", message)
        self.assertIn("✓ Read", message)
        self.assertIn("✗ Trade", message)
        self.assertIn("✓ Withdraw", message)

    def test_handle_successful_connection_uses_defaults(
        self,
    ):
        page = self.make_page()
        page.connection_result = QLabel()
        page.permission_summary = QLabel()
        page._set_connection_state = Mock()

        with patch.object(
            settings_module.QMessageBox,
            "information",
        ):
            page._handle_successful_connection(
                {}
            )

        self.assertEqual(
            page.connection_result.text(),
            "OKX bağlantısı başarılı. UID: -",
        )
        self.assertEqual(
            page.permission_summary.text(),
            (
                "Read: İzin Yok\n"
                "Trade: İzin Yok\n"
                "Withdraw: İzin Yok"
            ),
        )

    def test_handle_failed_connection_updates_ui(
        self,
    ):
        page = self.make_page()
        page.connection_result = QLabel()
        page.permission_summary = QLabel(
            "permissions"
        )
        page.permission_summary.show()
        page._set_connection_state = Mock()

        with patch.object(
            settings_module.QMessageBox,
            "warning",
        ) as warning:
            page._handle_failed_connection(
                "invalid credentials"
            )

        page._set_connection_state.assert_called_once_with(
            text="Bağlantı Hatası",
            color=settings_module.Theme.ERROR,
        )
        self.assertEqual(
            page.connection_result.text(),
            (
                "OKX bağlantısı kurulamadı: "
                "invalid credentials"
            ),
        )
        self.assertTrue(
            page.permission_summary.isHidden()
        )
        warning.assert_called_once_with(
            page,
            "Bağlantı Hatası",
            "invalid credentials",
        )

    def test_set_connection_state_maps_colors(
        self,
    ):
        page = self.make_page()
        page.connection_badge = Mock()

        cases = (
            (
                settings_module.Theme.ACCENT,
                settings_module.StatusBadge.SUCCESS,
            ),
            (
                settings_module.Theme.WARNING,
                settings_module.StatusBadge.WARNING,
            ),
            (
                settings_module.Theme.ERROR,
                settings_module.StatusBadge.ERROR,
            ),
            (
                "#123456",
                settings_module.StatusBadge.NEUTRAL,
            ),
        )

        for color, expected_status in cases:
            with self.subTest(color=color):
                page.connection_badge.reset_mock()

                page._set_connection_state(
                    "Durum",
                    color,
                )

                page.connection_badge.set_status.assert_called_once_with(
                    "Durum",
                    expected_status,
                )

    def test_permission_helpers(
        self,
    ):
        self.assertEqual(
            settings_module.SettingsPage
            ._permission_icon(True),
            "✓",
        )
        self.assertEqual(
            settings_module.SettingsPage
            ._permission_icon(False),
            "✗",
        )
        self.assertEqual(
            settings_module.SettingsPage
            ._permission_text(
                "Read",
                True,
            ),
            "Read: İzin Var",
        )
        self.assertEqual(
            settings_module.SettingsPage
            ._permission_text(
                "Trade",
                False,
            ),
            "Trade: İzin Yok",
        )



    def test_full_constructor_builds_complete_page(
        self,
    ):
        saved_app_settings = {
            "windows_startup_enabled": True,
            "balance_widget_enabled": False,
            "minimize_to_tray_enabled": True,
            "notifications_enabled": True,
            "alarm_sound_enabled": False,
            "refresh_on_start_enabled": True,
            "portfolio_history_enabled": False,
        }

        with (
            patch.object(
                settings_module,
                "OKXService",
                return_value=sentinel.okx_service,
            ),
            patch.object(
                settings_module,
                "load_settings",
                return_value=(
                    "api-key",
                    "secret-key",
                    "passphrase",
                ),
            ),
            patch.object(
                settings_module,
                "get_all_app_settings",
                return_value=saved_app_settings,
            ),
        ):
            page = settings_module.SettingsPage()
            self.pages.append(page)

        self.assertIs(
            page.okx_service,
            sentinel.okx_service,
        )
        self.assertEqual(
            page.scroll_area.objectName(),
            "settingsScrollArea",
        )
        self.assertTrue(
            page.scroll_area.widgetResizable()
        )
        self.assertIsNotNone(
            page.scroll_area.widget()
        )
        self.assertEqual(
            page.scroll_area.widget().objectName(),
            "settingsContent",
        )
        self.assertEqual(
            page.layout().count(),
            1,
        )

        self.assertEqual(
            page.connection_badge.objectName(),
            "connectionBadge",
        )
        self.assertEqual(
            page.connection_badge.text(),
            "Kontrol edilmedi",
        )

        self.assertEqual(
            page.api.text(),
            "api-key",
        )
        self.assertEqual(
            page.secret.text(),
            "secret-key",
        )
        self.assertEqual(
            page.passphrase.text(),
            "passphrase",
        )
        self.assertEqual(
            page.api.echoMode(),
            QLineEdit.Normal,
        )
        self.assertEqual(
            page.secret.echoMode(),
            QLineEdit.Password,
        )
        self.assertEqual(
            page.passphrase.echoMode(),
            QLineEdit.Password,
        )
        self.assertEqual(
            page.password_fields,
            [
                page.secret,
                page.passphrase,
            ],
        )

        visibility_buttons = page.findChildren(
            QPushButton,
            "visibilityButton",
        )
        self.assertEqual(
            len(visibility_buttons),
            2,
        )
        self.assertTrue(
            all(
                button.text() == "Göster"
                for button in visibility_buttons
            )
        )

        self.assertEqual(
            page.test_button.objectName(),
            "testButton",
        )
        self.assertEqual(
            page.save_button.objectName(),
            "saveButton",
        )
        self.assertEqual(
            page.save_preferences_button.objectName(),
            "savePreferencesButton",
        )

        self.assertEqual(
            page.connection_result.text(),
            (
                "Kayıtlı API bilgileri bulundu. "
                "Bağlantıyı doğrulamak için test edebilirsiniz."
            ),
        )
        self.assertTrue(
            page.permission_summary.isHidden()
        )

        self.assertEqual(
            len(page.app_setting_controls),
            7,
        )

        for key, expected in saved_app_settings.items():
            with self.subTest(key=key):
                self.assertEqual(
                    page.app_setting_controls[
                        key
                    ].isChecked(),
                    expected,
                )

        dividers = page.findChildren(
            QFrame,
            "settingsRowDivider",
        )
        self.assertEqual(
            len(dividers),
            6,
        )

        for object_name in (
            "credentialsCard",
            "connectionCard",
            "applicationSettingsCard",
        ):
            with self.subTest(
                object_name=object_name
            ):
                card = page.findChild(
                    QFrame,
                    object_name,
                )
                self.assertIsNotNone(card)
                self.assertIn(
                    f"QFrame#{object_name}",
                    card.styleSheet(),
                )
                self.assertIn(
                    "#182B38",
                    card.styleSheet(),
                )
                self.assertIn(
                    "#293B46",
                    card.styleSheet(),
                )

        stylesheet = page.styleSheet()

        self.assertIn(
            "QWidget#settingsPage",
            stylesheet,
        )
        self.assertIn(
            "QScrollArea#settingsScrollArea",
            stylesheet,
        )
        self.assertIn(
            "QPushButton#visibilityButton",
            stylesheet,
        )
        self.assertIn(
            "QCheckBox#settingToggle",
            stylesheet,
        )
        self.assertIn(
            settings_module.Theme.TEXT_PRIMARY,
            stylesheet,
        )
        self.assertIn(
            settings_module.Theme.ACCENT,
            stylesheet,
        )



if __name__ == "__main__":
    unittest.main()
