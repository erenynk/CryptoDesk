import time
import json
import requests
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
        """Baglantiyi test eder."""
        if not self.client:
            return False, "API bilgileri veritabaninda bulunamadi."
        
        try:
            status, data = self.client.test_connection()
            if status == 200 and data.get("code") == "0":
                account_data = data.get("data", [{}])[0]
                uid = account_data.get("uid", "Bilinmiyor")
                perm = account_data.get("perm", "")
                
                permissions = {
                    "read": "read" in perm,
                    "trade": "trade" in perm,
                    "withdraw": "withdraw" in perm
                }
                return True, {"uid": uid, "permissions": permissions}
            else:
                error_msg = data.get("msg", "Bilinmeyen bir hata olustu.")
                return False, f"OKX Hatasi: {error_msg}"
        except Exception as e:
            return False, f"Baglanti Hatasi: {str(e)}"

    def get_spot_balances(self):
        """
        Funding ve Trading bakiyelerini ceker, anlik USDT fiyatlariyla
        carparak toplam portfoy degerini ve varlik detaylarini doner.
        """
        if not self.client:
            return False, "API bilgileri bulunamadi."

        combined_balances = {}

        try:
            start_total = time.perf_counter()
            # 1. FUNDING HESABI
            funding_path = "/api/v5/asset/balances"
            funding_headers = self.client._headers("GET", funding_path)
            f_res = requests.get(self.client.BASE_URL + funding_path, headers=funding_headers, timeout=10)
            
            if f_res.status_code == 200 and f_res.json().get("code") == "0":
                for asset in f_res.json().get("data", []):
                    ccy = asset.get("ccy", "")
                    bal = float(asset.get("bal", 0))
                    avail = float(asset.get("availBal", 0))
                    if bal > 0:
                        combined_balances[ccy] = {"total": bal, "available": avail}

            # 2. TRADING HESABI
            trading_path = "/api/v5/account/balance"
            trading_headers = self.client._headers("GET", trading_path)
            t_res = requests.get(self.client.BASE_URL + trading_path, headers=trading_headers, timeout=10)
            
            if t_res.status_code == 200 and t_res.json().get("code") == "0":
                data_list = t_res.json().get("data", [])
                if data_list and "details" in data_list[0]:
                    details = data_list[0].get("details", [])
                    for asset in details:
                        ccy = asset.get("ccy", "")
                        bal = float(asset.get("eq", 0))
                        avail = float(asset.get("availBal", 0))
                        
                        if bal > 0:
                            if ccy in combined_balances:
                                combined_balances[ccy]["total"] += bal
                                combined_balances[ccy]["available"] += avail
                            else:
                                combined_balances[ccy] = {"total": bal, "available": avail}

            # 3. ANLIK FIYATLARI (TICKERS) CEK VE USDT DEGERLERINI HESAPLA
            # OKX'ten tum spot piyasa fiyatlarini tek seferde cekiyoruz (hizli olsun diye)
            ticker_path = "/api/v5/market/tickers?instType=SPOT"
            ticker_res = requests.get(self.client.BASE_URL + ticker_path, timeout=10)
            prices = {}
            
            if ticker_res.status_code == 200 and ticker_res.json().get("code") == "0":
                for t in ticker_res.json().get("data", []):
                    inst_id = t.get("instId", "") # Orn: "BTC-USDT"
                    if inst_id.endswith("-USDT"):
                        coin_name = inst_id.split("-")[0] # "BTC"
                        prices[coin_name] = float(t.get("last", 0))

            # Hesaplamalari yapalim
            active_balances = []
            total_portfolio_usdt = 0.0

            for coin, qty in combined_balances.items():
                total_qty = qty["total"]
                avail_qty = qty["available"]
                
                # Eger varlik zaten USDT ise fiyati 1'dir
                if coin == "USDT":
                    price = 1.0
                else:
                    price = prices.get(coin, 0.0) # Listede yoksa 0 alir
                
                usdt_value = total_qty * price
                total_portfolio_usdt += usdt_value

                active_balances.append({
                    "coin": coin,
                    "total": total_qty,
                    "available": avail_qty,
                    "price": price,
                    "usdt_value": usdt_value
                })

            # Yuksek degerli coinler en ustte gorunsun diye siraliyoruz
            active_balances.sort(key=lambda x: x["usdt_value"], reverse=True)

            return True, {
                "total_usdt": total_portfolio_usdt,
                "assets": active_balances
            }

        except Exception as e:
            return False, f"Portfoy Hesaplama Hatasi: {str(e)}"