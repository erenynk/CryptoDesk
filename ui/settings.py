import json

from services.okx_service import OKXService
from database.settings_db import save_settings, load_settings

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

        self.okx_service = OKXService()

        layout = QVBoxLayout(self)

        title = QLabel("Settings")
        title.setStyleSheet("""
            font-size:28px;
            font-weight:bold;
        """)

        layout.addWidget(title)

        # API KEY
        layout.addWidget(QLabel("OKX API Key"))

        self.api = QLineEdit()

        layout.addWidget(self.api)

        # SECRET
        layout.addWidget(QLabel("Secret Key"))

        self.secret = QLineEdit()

        self.secret.setEchoMode(QLineEdit.Password)

        layout.addWidget(self.secret)

        # PASSPHRASE
        layout.addWidget(QLabel("Passphrase"))

        self.passphrase = QLineEdit()

        self.passphrase.setEchoMode(QLineEdit.Password)

        layout.addWidget(self.passphrase)

        # BUTTONS
        button = QPushButton("Kaydet")
        button.clicked.connect(self.save)
        layout.addWidget(button)

        # TEST BUTTON
        test_button = QPushButton("Bağlantıyı Test Et")
        test_button.clicked.connect(self.test_connection)
        layout.addWidget(test_button)

        layout.addStretch()

        api, secret, passphrase = load_settings()

        self.api.setText(api)
        self.secret.setText(secret)
        self.passphrase.setText(passphrase)

    def save(self):
        save_settings(
            self.api.text(),
            self.secret.text(),
            self.passphrase.text(),
        )

        self.okx_service.refresh_client()

        QMessageBox.information(
            self,
            "Başarılı",
            "Ayarlar güvenli şekilde kaydedildi."
        )

    def test_connection(self):
        from api.okx_client import OKXClient
        self.okx_service.client = OKXClient(
            self.api.text(),
            self.secret.text(),
            self.passphrase.text()
        )

        success, result = self.okx_service.check_connection()

        if success:
            # İzin durumlarına göre onay veya çarpı işareti belirliyoruz
            p = result["permissions"]
            read_icon = "✓" if p["read"] else "✗"
            trade_icon = "✓" if p["trade"] else "✗"
            withdraw_icon = "✓" if p["withdraw"] else "✗"

            # Şık bir bilgilendirme metni oluşturuyoruz
            message = (
                f"🟢 OKX bağlantısı başarılı\n\n"
                f"UID: {result['uid']}\n\n"
                f"API Key: Geçerli\n\n"
                f"Permissions:\n"
                f"{read_icon} Read\n"
                f"{trade_icon} Trade\n"
                f"{withdraw_icon} Withdraw"
            )

            QMessageBox.information(
                self,
                "Bağlantı Başarılı",
                message
            )
        else:
            QMessageBox.warning(
                self,
                "Hata",
                result
            )