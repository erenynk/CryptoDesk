from PySide6.QtCore import Qt
from ui.widgets.card import Card
from ui.widgets.button import AppButton
from ui.widgets.input import AppLineEdit
from ui.widgets.status_badge import StatusBadge
from ui.widgets.page_header import PageHeader
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from api.okx_client import OKXClient
from database.settings_db import load_settings, save_settings
from services.okx_service import OKXService
from ui.theme import (
    Theme,
    label_style,
    page_style,
    page_title_style,    
    scroll_bar_style,
    
)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.okx_service = OKXService()
        self.password_fields = []

        self.setObjectName("settingsPage")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self._load_saved_settings()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
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

        main_layout.addStretch()

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
            palette="indigo",
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

        input_layout.addWidget(line_edit, 1)

        if password:
            line_edit.setEchoMode(QLineEdit.Password)
            self.password_fields.append(line_edit)

            visibility_button = QPushButton("Göster")
            visibility_button.setObjectName("visibilityButton")
            visibility_button.setCursor(Qt.PointingHandCursor)
            visibility_button.setFocusPolicy(Qt.NoFocus)
            visibility_button.setFixedSize(66, 40)

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
            palette="indigo",
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

    def _connect_signals(self):
        self.save_button.clicked.connect(self.save)
        self.test_button.clicked.connect(
            self.test_connection
        )

    def _apply_styles(self):
        self.setStyleSheet(
            page_style("settingsPage")
            + label_style()
            + page_title_style()            
            + scroll_bar_style()
            + f"""
            
            
            QWidget#settingsPage {{
                background: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #101522,
                    stop:0.52 #171E31,
                    stop:1 #232B49
                );
            }}

            QLabel#cardTitle {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 16px;
                font-weight: 700;
            }}

            QLabel#cardDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 12px;
                font-weight: 400;
            }}

            QLabel#fieldLabel {{
                color: {Theme.TEXT_PRIMARY};
                font-size: 12px;
                font-weight: 650;
            }}

            QLabel#fieldDescription {{
                color: {Theme.TEXT_MUTED};
                font-size: 11px;
                font-weight: 400;
            }}

            QFrame#inputContainer {{
                background-color:
                    {Theme.CARD_BACKGROUND_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius:
                    {Theme.RADIUS_SMALL}px;
            }}

            QFrame#inputContainer:hover {{
                border-color: {Theme.BORDER_HOVER};
            }}

                        
            QPushButton#visibilityButton {{
                background-color: transparent;
                color: {Theme.TEXT_SECONDARY};
                border: none;
                border-left: 1px solid {Theme.BORDER};
                border-radius: 0px;
                padding: 0px;
                font-family: "{Theme.FONT_FAMILY}";
                font-size: 11px;
                font-weight: 600;
            }}

            QPushButton#visibilityButton:pressed {{
                color: {Theme.ACCENT};
                background-color: transparent;
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