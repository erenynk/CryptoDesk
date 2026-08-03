from PySide6.QtCore import Signal, Qt
from ui.widgets.card import Card
from ui.widgets.button import AppButton
from ui.widgets.input import AppLineEdit
from ui.widgets.status_badge import StatusBadge
from ui.widgets.page_header import PageHeader
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from api.okx_client import OKXClient
from database.settings_db import (
    get_all_app_settings,
    load_settings,
    save_app_settings,
    save_settings,
)
from services.okx_service import OKXService
from services.startup_service import (
    is_startup_enabled,
    set_startup_enabled,
)
from ui.theme import (
    Theme,
    label_style,
    page_style,
    page_title_style,    
    scroll_bar_style,
    
)


class SettingsPage(QWidget):
    app_settings_changed = Signal(dict)
    def __init__(self):
        super().__init__()

        self.okx_service = OKXService()
        self.password_fields = []
        self.app_setting_controls = {}

        self.setObjectName("settingsPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()
        self._apply_styles()
        self._apply_settings_palette()
        self._connect_signals()
        self._load_saved_settings()

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("settingsScrollArea")
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.scroll_area.setVerticalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )

        content_widget = QWidget()
        content_widget.setObjectName("settingsContent")

        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
            Theme.PAGE_MARGIN_HORIZONTAL,
            Theme.PAGE_MARGIN_VERTICAL,
        )
        main_layout.setSpacing(20)

        header = self._create_header()
        main_layout.addWidget(header)

        credentials_card = self._create_credentials_card()
        main_layout.addWidget(credentials_card)

        connection_card = self._create_connection_card()
        main_layout.addWidget(connection_card)

        application_card = self._create_application_settings_card()
        main_layout.addWidget(application_card)

        main_layout.addStretch()

        self.scroll_area.setWidget(content_widget)
        root_layout.addWidget(self.scroll_area)

    def _create_header(self):
        self.connection_badge = StatusBadge(
            text="Kontrol edilmedi",
            status=StatusBadge.NEUTRAL,
            object_name="connectionBadge",
        )

        return PageHeader(
            title="Ayarlar",
            subtitle=(
                "OKX API bağlantı bilgilerini güvenli "
                "şekilde yönet."
            ),
            right_widget=self.connection_badge,
            object_name="settingsHeader",
        )

    def _create_credentials_card(self):
        card = Card(
            "credentialsCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(18)

        title = QLabel("API Kimlik Bilgileri")
        title.setObjectName("cardTitle")

        description = QLabel(
            "Bilgiler Windows kullanıcı hesabınıza bağlı olarak "
            "şifreli biçimde saklanır."
        )
        description.setObjectName("cardDescription")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

        api_section = self._create_input_section(
            label="OKX API Key",
            description="OKX tarafından oluşturulan API anahtarı",
            password=False,
        )
        self.api = api_section["input"]
        layout.addWidget(api_section["widget"])

        secret_section = self._create_input_section(
            label="Secret Key",
            description="API anahtarına ait gizli anahtar",
            password=True,
        )
        self.secret = secret_section["input"]
        layout.addWidget(secret_section["widget"])

        passphrase_section = self._create_input_section(
            label="Passphrase",
            description="API oluştururken belirlediğiniz parola",
            password=True,
        )
        self.passphrase = passphrase_section["input"]
        layout.addWidget(passphrase_section["widget"])

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 2, 0, 0)
        button_layout.setSpacing(10)

        self.test_button = AppButton(
            "Bağlantıyı Test Et",
            variant=AppButton.SECONDARY,
            object_name="testButton",
        )

        self.save_button = AppButton(
            "Ayarları Kaydet",
            variant=AppButton.PRIMARY,
            object_name="saveButton",
        )

        button_layout.addStretch()
        button_layout.addWidget(self.test_button)
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        return card

    def _create_input_section(
        self,
        label,
        description,
        password=False,
    ):
        container = QWidget()
        container.setObjectName("inputSection")

        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(7)

        title_label = QLabel(label)
        title_label.setObjectName("fieldLabel")

        description_label = QLabel(description)
        description_label.setObjectName("fieldDescription")

        input_container = QFrame()
        input_container.setObjectName("inputContainer")

        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.setSpacing(0)

        line_edit = AppLineEdit(
            placeholder="",
            object_name="settingsInput",
        )
        line_edit.setClearButtonEnabled(not password)
        line_edit.setMinimumHeight(44)
        line_edit.setStyleSheet(
            f"""
            QLineEdit#settingsInput {{
                background: transparent;
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-radius: 0px;
                padding: 0 14px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 13px;
                font-weight: 500;
                selection-background-color: {Theme.ACCENT_SOFT};
            }}

            QLineEdit#settingsInput:focus {{
                background: transparent;
                border: none;
            }}
            """
        )

        input_layout.addWidget(line_edit, 1)

        if password:
            line_edit.setEchoMode(QLineEdit.Password)
            self.password_fields.append(line_edit)

            visibility_button = QPushButton("Göster")
            visibility_button.setObjectName("visibilityButton")
            visibility_button.setCursor(Qt.PointingHandCursor)
            visibility_button.setFocusPolicy(Qt.NoFocus)
            visibility_button.setFixedSize(72, 42)

            visibility_button.clicked.connect(
                lambda checked=False,
                field=line_edit,
                button=visibility_button:
                self._toggle_password_visibility(
                    field,
                    button,
                )
            )

            input_layout.addWidget(visibility_button)

        layout.addWidget(title_label)
        layout.addWidget(description_label)
        layout.addWidget(input_container)

        return {
            "widget": container,
            "input": line_edit,
        }

    def _create_connection_card(self):
        card = Card(
            "connectionCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QHBoxLayout(card)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(20)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(5)

        title = QLabel("Bağlantı Durumu")
        title.setObjectName("connectionCardTitle")

        self.connection_result = QLabel(
            "API bağlantısı henüz test edilmedi."
        )
        self.connection_result.setObjectName(
            "connectionResult"
        )
        self.connection_result.setWordWrap(True)

        text_layout.addWidget(title)
        text_layout.addWidget(self.connection_result)

        self.permission_summary = QLabel("")
        self.permission_summary.setObjectName(
            "permissionSummary"
        )
        self.permission_summary.setWordWrap(True)
        self.permission_summary.hide()

        layout.addLayout(text_layout, 1)
        layout.addWidget(
            self.permission_summary,
            0,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        return card

    def _create_application_settings_card(self):
        card = Card(
            "applicationSettingsCard",
            hover=False,
            radius=Theme.RADIUS_LARGE,
            shadow=True,
            palette="blue_dark",
        )
        card.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        layout = QVBoxLayout(card)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(0)

        title = QLabel("Uygulama Tercihleri")
        title.setObjectName("cardTitle")

        description = QLabel(
            "Başlangıç, sistem tepsisi, widget ve veri "
            "davranışlarını yönet."
        )
        description.setObjectName("cardDescription")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)
        layout.addSpacing(16)

        settings = (
            (
                "windows_startup_enabled",
                "Sistemle başlat",
                "Bilgisayar açıldığında uygulamayı otomatik başlatır.",
            ),
            (
                "balance_widget_enabled",
                "Balance Widget'ı göster",
                "Masaüstü bakiye widget'ını açar veya kapatır.",
            ),
            (
                "minimize_to_tray_enabled",
                "Kapatınca sistem tepsisine küçült",
                "Pencere kapatıldığında uygulamayı arka planda tutar.",
            ),
            (
                "notifications_enabled",
                "Bildirimleri göster",
                "Alarm tetiklendiğinde masaüstü bildirimi gösterir.",
            ),
            (
                "alarm_sound_enabled",
                "Alarm sesini çal",
                "Bildirimle birlikte alarm sesi oynatır.",
            ),
            (
                "refresh_on_start_enabled",
                "Başlangıçta portföyü yenile",
                "Uygulama açıldığında portföy verisini günceller.",
            ),
            (
                "portfolio_history_enabled",
                "Portföy geçmişini kaydet",
                "Performans hesapları için snapshot kaydı oluşturur.",
            ),
        )

        for index, (key, label, description_text) in enumerate(settings):
            row = self._create_setting_row(
                key=key,
                label=label,
                description=description_text,
            )
            layout.addWidget(row)

            if index < len(settings) - 1:
                divider = QFrame()
                divider.setObjectName("settingsRowDivider")
                divider.setFixedHeight(1)
                layout.addWidget(divider)

        layout.addSpacing(16)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)

        self.save_preferences_button = AppButton(
            "Tercihleri Kaydet",
            variant=AppButton.PRIMARY,
            object_name="savePreferencesButton",
        )

        button_layout.addStretch()
        button_layout.addWidget(self.save_preferences_button)
        layout.addLayout(button_layout)

        return card

    def _create_setting_row(
        self,
        key,
        label,
        description,
    ):
        row = QWidget()
        row.setObjectName("applicationSettingRow")
        row.setMinimumHeight(58)

        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 9, 0, 9)
        layout.setSpacing(18)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(3)

        title_label = QLabel(label)
        title_label.setObjectName("settingTitle")

        description_label = QLabel(description)
        description_label.setObjectName("settingDescription")
        description_label.setWordWrap(True)

        checkbox = QCheckBox()
        checkbox.setObjectName("settingToggle")
        checkbox.setCursor(Qt.PointingHandCursor)
        checkbox.setFocusPolicy(Qt.NoFocus)
        checkbox.setMinimumWidth(46)

        text_layout.addWidget(title_label)
        text_layout.addWidget(description_label)

        layout.addLayout(text_layout, 1)
        layout.addWidget(
            checkbox,
            0,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        self.app_setting_controls[key] = checkbox

        return row

    def _apply_settings_palette(self):
        credentials_card = self.findChild(QFrame, "credentialsCard")
        connection_card = self.findChild(QFrame, "connectionCard")
        application_card = self.findChild(
            QFrame,
            "applicationSettingsCard",
        )

        if credentials_card is not None:
            credentials_card.setStyleSheet(
                f"""
                QFrame#credentialsCard {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: 1px solid #293B46;
                border-radius: {Theme.RADIUS_LARGE}px;
            }}
                """
            )

        if connection_card is not None:
            connection_card.setStyleSheet(
                f"""
                QFrame#connectionCard {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: 1px solid #293B46;
                border-radius: {Theme.RADIUS_LARGE}px;
            }}
                """
            )

        if application_card is not None:
            application_card.setStyleSheet(
                f"""
                QFrame#applicationSettingsCard {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: 1px solid #293B46;
                border-radius: {Theme.RADIUS_LARGE}px;
            }}
                """
            )


    def _connect_signals(self):
        self.save_button.clicked.connect(self.save)
        self.test_button.clicked.connect(
            self.test_connection
        )
        self.save_preferences_button.clicked.connect(
            self.save_app_preferences
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("settingsPage")
            + label_style()
            + page_title_style()            
            + scroll_bar_style()
            + f"""
            
            
            QScrollArea#settingsScrollArea,
            QScrollArea#settingsScrollArea
            > QWidget
            > QWidget,
            QWidget#settingsContent {{
                background: transparent;
                border: none;
            }}

            QWidget#settingsPage {{
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

            QLabel#cardTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#cardDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#fieldLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#fieldDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QFrame#inputContainer {{
                background: qlineargradient(
                    x1: 0,
                    y1: 0,
                    x2: 1,
                    y2: 1,
                    stop: 0 #182B38,
                    stop: 0.50 #121F29,
                    stop: 1 #0D1720
                );
                border: 1px solid #293B46;
                border-radius: {Theme.RADIUS_SMALL}px;
            }}

            QFrame#inputContainer:hover {{
                border-color: {Theme.BORDER_HOVER};
            }}

                        
            QPushButton#visibilityButton {{
                background-color: rgba(255, 255, 255, 5);
                color: {Theme.TEXT_SECONDARY};
                border: none;
                border-left: 1px solid {Theme.BORDER};
                border-top-right-radius: {Theme.RADIUS_SMALL}px;
                border-bottom-right-radius: {Theme.RADIUS_SMALL}px;
                padding: 0px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 11px;
                font-weight: 650;
            }}

            QPushButton#visibilityButton:hover {{
                color: {Theme.TEXT_PRIMARY};
                background-color: rgba(255, 255, 255, 10);
            }}

            QPushButton#visibilityButton:pressed {{
                color: {Theme.ACCENT};
                background-color: rgba(24, 201, 139, 12);
            }}

            QLabel#connectionCardTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#connectionResult {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#permissionSummary {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 11px;
                font-weight: 600;
            }}

            QWidget#applicationSettingRow {{
                background: transparent;
                border: none;
            }}

            QLabel#settingTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 13px;
                font-weight: 700;
            }}

            QLabel#settingDescription {{
                color: {Theme.TEXT_SECONDARY};
                font-size: 12px;
                font-weight: 400;
            }}

            QFrame#settingsRowDivider {{
                background-color: rgba(125, 158, 176, 24);
                border: none;
            }}

            QCheckBox#settingToggle {{
                spacing: 0px;
                padding: 8px;
                background: transparent;
                border: none;
            }}

            QCheckBox#settingToggle:hover {{
                background-color: rgba(255, 255, 255, 6);
                border-radius: 14px;
            }}

            QCheckBox#settingToggle::indicator {{
                width: 16px;
                height: 16px;
                border-radius: 8px;
                background-color: #18242E;
                border: 2px solid #5A6E7B;
            }}

            QCheckBox#settingToggle::indicator:hover {{
                background-color: #1C2B36;
                border-color: #8CA2AF;
            }}

            QCheckBox#settingToggle::indicator:pressed {{
                background-color: #223541;
                border-color: #A7BAC4;
            }}

            QCheckBox#settingToggle::indicator:checked {{
                background-color: {Theme.ACCENT};
                border: 2px solid #9CFFD9;
            }}

            QCheckBox#settingToggle::indicator:checked:hover {{
                background-color: #20D99C;
                border-color: #C8FFEA;
            }}

            QCheckBox#settingToggle::indicator:checked:pressed {{
                background-color: #0FAE79;
                border-color: #E0FFF3;
            }}
            """
        )

    def _load_saved_settings(self):
        api, secret, passphrase = load_settings()

        self.api.setText(api or "")
        self.secret.setText(secret or "")
        self.passphrase.setText(passphrase or "")

        if api and secret and passphrase:
            self.connection_result.setText(
                "Kayıtlı API bilgileri bulundu. "
                "Bağlantıyı doğrulamak için test edebilirsiniz."
            )

        self._load_saved_app_settings()

    def _load_saved_app_settings(self):
        settings = get_all_app_settings()

        startup_key = "windows_startup_enabled"

        if startup_key in self.app_setting_controls:
            settings[startup_key] = (
                is_startup_enabled()
            )

        for key, checkbox in self.app_setting_controls.items():
            checkbox.setChecked(
                bool(settings.get(key, False))
            )

    def save_app_preferences(self):
        settings = {
            key: checkbox.isChecked()
            for key, checkbox in self.app_setting_controls.items()
        }

        self.save_preferences_button.setEnabled(False)
        self.save_preferences_button.setText("Kaydediliyor...")

        startup_key = "windows_startup_enabled"
        startup_changed = False
        previous_startup_enabled = False
        preferences_saved = False

        try:
            if startup_key in settings:
                requested_startup_enabled = bool(
                    settings[startup_key]
                )
                previous_startup_enabled = (
                    is_startup_enabled()
                )

                if (
                    requested_startup_enabled
                    != previous_startup_enabled
                ):
                    if not set_startup_enabled(
                        requested_startup_enabled
                    ):
                        raise RuntimeError(
                            "Otomatik başlatma ayarı "
                            "uygulanamadı."
                        )

                    startup_changed = True

            if not save_app_settings(settings):
                raise RuntimeError(
                    "Uygulama tercihleri veritabanına yazılamadı."
                )

            preferences_saved = True
            self.app_settings_changed.emit(settings)

            QMessageBox.information(
                self,
                "Başarılı",
                "Uygulama tercihleri kaydedildi.",
            )

        except Exception as error:
            if startup_changed and not preferences_saved:
                set_startup_enabled(
                    previous_startup_enabled
                )

            QMessageBox.warning(
                self,
                "Kayıt Hatası",
                f"Tercihler kaydedilemedi:\n{error}",
            )

        finally:
            self.save_preferences_button.setEnabled(True)
            self.save_preferences_button.setText(
                "Tercihleri Kaydet"
            )

    @staticmethod
    def _toggle_password_visibility(field, button):
        if field.echoMode() == QLineEdit.Password:
            field.setEchoMode(QLineEdit.Normal)
            button.setText("Gizle")
            return

        field.setEchoMode(QLineEdit.Password)
        button.setText("Göster")

    def save(self):
        api_key = self.api.text().strip()
        secret_key = self.secret.text().strip()
        passphrase = self.passphrase.text().strip()

        if not api_key or not secret_key or not passphrase:
            QMessageBox.warning(
                self,
                "Eksik Bilgi",
                "API Key, Secret Key ve Passphrase "
                "alanlarının tamamını doldurun.",
            )
            return

        self.save_button.setEnabled(False)
        self.save_button.setText("Kaydediliyor...")

        try:
            save_settings(
                api_key,
                secret_key,
                passphrase,
            )

            self.okx_service.refresh_client()

            self.connection_result.setText(
                "API bilgileri güvenli şekilde kaydedildi."
            )

            QMessageBox.information(
                self,
                "Başarılı",
                "Ayarlar güvenli şekilde kaydedildi.",
            )

        except Exception as error:
            QMessageBox.warning(
                self,
                "Kayıt Hatası",
                f"Ayarlar kaydedilemedi:\n{error}",
            )

        finally:
            self.save_button.setEnabled(True)
            self.save_button.setText("Ayarları Kaydet")

    def test_connection(self):
        api_key = self.api.text().strip()
        secret_key = self.secret.text().strip()
        passphrase = self.passphrase.text().strip()

        if not api_key or not secret_key or not passphrase:
            QMessageBox.warning(
                self,
                "Eksik Bilgi",
                "Bağlantıyı test etmek için tüm API "
                "alanlarını doldurun.",
            )
            return

        self.test_button.setEnabled(False)
        self.test_button.setText("Test ediliyor...")

        self._set_connection_state(
            text="Bağlantı kontrol ediliyor",
            color=Theme.WARNING,
        )

        self.connection_result.setText(
            "OKX API bağlantısı kontrol ediliyor..."
        )
        self.permission_summary.hide()

        try:
            self.okx_service.client = OKXClient(
                api_key,
                secret_key,
                passphrase,
            )

            success, result = (
                self.okx_service.check_connection()
            )

            if success:
                self._handle_successful_connection(result)
                return

            self._handle_failed_connection(str(result))

        except Exception as error:
            self._handle_failed_connection(str(error))

        finally:
            self.test_button.setEnabled(True)
            self.test_button.setText(
                "Bağlantıyı Test Et"
            )

    def _handle_successful_connection(self, result):
        permissions = result.get("permissions", {})

        read_allowed = bool(
            permissions.get("read", False)
        )
        trade_allowed = bool(
            permissions.get("trade", False)
        )
        withdraw_allowed = bool(
            permissions.get("withdraw", False)
        )

        uid = result.get("uid", "-")

        self._set_connection_state(
            text="API Bağlı",
            color=Theme.ACCENT,
        )

        self.connection_result.setText(
            f"OKX bağlantısı başarılı. UID: {uid}"
        )

        self.permission_summary.setText(
            "\n".join(
                (
                    self._permission_text(
                        "Read",
                        read_allowed,
                    ),
                    self._permission_text(
                        "Trade",
                        trade_allowed,
                    ),
                    self._permission_text(
                        "Withdraw",
                        withdraw_allowed,
                    ),
                )
            )
        )
        self.permission_summary.show()

        message = (
            "OKX bağlantısı başarılı\n\n"
            f"UID: {uid}\n\n"
            "Permissions:\n"
            f"{self._permission_icon(read_allowed)} Read\n"
            f"{self._permission_icon(trade_allowed)} Trade\n"
            f"{self._permission_icon(withdraw_allowed)} Withdraw"
        )

        QMessageBox.information(
            self,
            "Bağlantı Başarılı",
            message,
        )

    def _handle_failed_connection(self, message):
        self._set_connection_state(
            text="Bağlantı Hatası",
            color=Theme.ERROR,
        )

        self.connection_result.setText(
            f"OKX bağlantısı kurulamadı: {message}"
        )

        self.permission_summary.hide()

        QMessageBox.warning(
            self,
            "Bağlantı Hatası",
            message,
        )

    def _set_connection_state(self, text, color):
        if color == Theme.ACCENT:
            status = StatusBadge.SUCCESS

        elif color == Theme.WARNING:
            status = StatusBadge.WARNING

        elif color == Theme.ERROR:
            status = StatusBadge.ERROR

        else:
            status = StatusBadge.NEUTRAL

        self.connection_badge.set_status(
            text,
            status,
        )

    @staticmethod
    def _permission_icon(allowed):
        return "✓" if allowed else "✗"

    @staticmethod
    def _permission_text(name, allowed):
        status = "İzin Var" if allowed else "İzin Yok"
        return f"{name}: {status}"