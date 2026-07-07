import json

from api.okx_client import OKXClient

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)

from database.settings_db import save_settings, load_settings


class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()

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

        QMessageBox.information(
            self,
            "Başarılı",
            "Ayarlar güvenli şekilde kaydedildi."
        )

    def test_connection(self):
        client = OKXClient(
            self.api.text(),
            self.secret.text(),
            self.passphrase.text(),
        )

        try:
            status, data = client.test_connection()

            if status == 200 and data.get("code") == "0":
                QMessageBox.information(
                    self,
                    "Başarılı",
                    "OKX bağlantısı başarılı."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Hata",
                    json.dumps(data, indent=2)
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Bağlantı Hatası",
                str(e)
            )