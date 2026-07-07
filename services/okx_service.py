import json
from api.okx_client import OKXClient
from database.settings_db import load_settings

class OKXService:
    def __init__(self):
        self.client = None
        self.refresh_client()

    def refresh_client(self):
        """Veritabanindan guncel ayarlari yukler ve OKXClient'i yeniler."""
        api, secret, passphrase = load_settings()
        if api and secret and passphrase:
            self.client = OKXClient(api, secret, passphrase)
        else:
            self.client = None

    def check_connection(self):
        """
        Baglantiyi test eder.
        Basariliysa UID ve Izin bilgilerini duzenleyip doner.
        """
        if not self.client:
            return False, "API bilgileri veritabaninda bulunamadi."
        
        try:
            status, data = self.client.test_connection()
            if status == 200 and data.get("code") == "0":
                # OKX'ten gelen listenin ilk elemanini aliyoruz (Hata duzeltildi)
                account_data = data.get("data", [{}])[0]
                
                uid = account_data.get("uid", "Bilinmiyor")
                perm = account_data.get("perm", "") # Orn: "read" veya "read,trade"
                
                # Izinleri kontrol ediyoruz
                permissions = {
                    "read": "read" in perm,
                    "trade": "trade" in perm,
                    "withdraw": "withdraw" in perm
                }
                
                result_details = {
                    "uid": uid,
                    "permissions": permissions
                }
                return True, result_details
            else:
                error_msg = data.get("msg", "Bilinmeyen bir hata olustu.")
                return False, f"OKX Hatasi: {error_msg}"
        except Exception as e:
            return False, f"Baglanti Hatasi: {str(e)}"