import json
from api.okx_client import OKXClient
from database.settings_db import load_settings

class OKXService:
    def __init__(self):
        self.client = None
        self.refresh_client()

    def refresh_client(self):
        """Veritabanından güncel ayarları yükler ve OKXClient'ı yeniler."""
        api, secret, passphrase = load_settings()
        if api and secret and passphrase:
            self.client = OKXClient(api, secret, passphrase)
        else:
            self.client = None

    def check_connection(self):
        """Bağlantıyı test eder ve sonucu temiz bir formatta döner."""
        if not self.client:
            return False, "API bilgileri veritabanında bulunamadı."
        
        try:
            status, data = self.client.test_connection()
            if status == 200 and data.get("code") == "0":
                return True, data
            else:
                error_msg = data.get("msg", "Bilinmeyen bir hata oluştu.")
                return False, f"OKX Hatası: {error_msg}"
        except Exception as e:
            return False, f"Bağlantı Hatası: {str(e)}"