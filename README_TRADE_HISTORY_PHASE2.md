# İşlem Geçmişi - Aşama 2

Bu paket yeni İşlem Geçmişi menüsünü ekler.

Tablo:
`COIN | İŞLEM | MİKTAR | FİYAT | TOPLAM | PNL | TARİH`

Arayüz Portfolio tablosuyla aynı temel ölçüleri kullanır:

- Satır yüksekliği: 74 px
- Hücre padding: 14 px / 12 px
- Header font: 14 px / 800
- Aynı header gradient ve border renkleri
- `Theme.FONT_FAMILY` / Inter
- PnL yeşil-kırmızı renkleri Theme üzerinden gelir
- Alış PnL hücresi tamamen boştur
- Satış PnL hücresinde yüzde ve USDT iki satırdır
- Tarih son sütundur
- Coin filtresi yazdıkça çalışır
- Başlık tıklaması sıralama yönünü değiştirir
- PnL sütunu USDT kâr/zarar değerine göre sıralanır

`main_window.py` doğrudan değiştirilmiş tam dosya olarak verilmedi; güncel
yerel dosyayı bozmamak için `tools/apply_trade_history_ui.py` yalnızca gerekli
entegrasyon noktalarını kontrol ederek değiştirir ve yedek oluşturur.

Uygulama:

```bash
python tools/apply_trade_history_ui.py
```

Ardından test:

```bash
PYTHONPATH="$PWD" \
QT_QPA_PLATFORM=offscreen \
python -m pytest -q
```
