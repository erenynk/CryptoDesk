import json

# Yeni oluşturduğumuz servis katmanını içeri aktarıyoruz
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

        # Servis katmanını sınıf içinde başlatıyoruz
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

        # Ayarlar değiştiği için servisin içindeki API istemcisini güncelliyoruz
        self.okx_service.refresh_client()

        QMessageBox.information(
            self,
            "Başarılı",
            "Ayarlar güvenli şekilde kaydedildi."
        )

    def test_connection(self):
        # Önce mevcut arayüzdeki güncel verilerle servisi geçici olarak yeniliyoruz
        # (Kullanıcı kaydet butonuna basmadan direkt test etmek isterse diye)
        from api.okx_client import OKXClient
        self.okx_service.client = OKXClient(
            self.api.text(),
            self.secret.text(),
            self.passphrase.text()
        )

        # Yeni servisimiz üzerinden bağlantıyı kontrol ediyoruz
        success, result = self.okx_service.check_connection()

        if success:
            QMessageBox.information(
                self,
                "Başarılı",
                "OKX bağlantısı başarılı."
            )
        else:
            QMessageBox.warning(
                self,
                "Hata",
                result  # Servisten gelen temiz Türkçe hata mesajını gösteriyoruz
            )