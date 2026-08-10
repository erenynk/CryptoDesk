# İşlem Geçmişi - Aşama 1

Bu paket yalnızca veri katmanını ekler. Mevcut Caspian arayüzüne dokunmaz.

Eklenen dosyalar:

- `database/trade_history_db.py`
- `services/trade_history_service.py`
- `tests/test_trade_history_db.py`
- `tests/test_trade_history_service.py`

## Kurallar

- Yalnızca `*-USDT` SPOT işlemleri işlenir.
- Aynı OKX emrine ait parçalı fill kayıtları tek işlem satırında birleştirilir.
- Alış işleminde `pnl_usdt` ve `pnl_percent` `None` kalır. UI aşamasında hücre boş gösterilecektir.
- Satış PnL'i Trading hesabının ağırlıklı ortalama maliyetinden hesaplanır.
- Trading -> Funding transferi satış sayılmaz.
- Funding -> Trading transferinde maliyet geçmişi bilinmiyorsa sonraki satış PnL'i tahmin edilmez ve boş bırakılır.
- OKX geçmişinin başlangıcından önce mevcut olan Trading maliyeti bilinmiyorsa PnL tahmin edilmez.
- Tarihler UTC+3 olarak saklanır.
- Veri mevcut `cryptodesk.db` dosyasındaki `trade_history` tablosuna yazılır.

## Sonraki aşama

UI aşamasında tablo:

`COIN | İŞLEM | MİKTAR | FİYAT | TOPLAM | PNL | TARİH`

şeklinde bağlanacaktır. Coin filtresi ve başlığa tıklayarak artan/azalan sıralama repository tarafından desteklenmektedir.
