# CryptoDesk

## Projenin Amacı

CryptoDesk, OKX Spot hesabındaki kripto varlıkları masaüstünden takip etmek için geliştirilen profesyonel bir Windows uygulamasıdır.

Amaç:

- Portföy takibi
- Anlık fiyatlar
- Toplam bakiye
- Watchlist
- Alarm sistemi
- Portföy analizi

---

# Teknolojiler

- Python 3.14
- PySide6
- SQLite
- OKX REST API

---

# Mimari

Merkezi veri yöneticisi:

DataManager

Veri akışı:

UI
↓

DataManager
↓

Services
↓

OKX API

UI hiçbir zaman doğrudan OKX API çağırmaz.

---

# Proje Yapısı

api/
database/
security/
services/
ui/

app.py

---

# Tamamlanan Özellikler

- Dashboard
- Portfolio
- Funding + Trading hesaplarını birleştirme
- Anlık fiyat güncelleme
- Toplam portföy değeri
- Balance Widget
- Küçük bakiye filtreleme
- Thread ile arka planda veri çekme
- 30 saniyede otomatik yenileme

---

# Geliştirilecek Özellikler

- Watchlist
- Alarm Sistemi
- Grafikler
- Portföy geçmişi
- İşlem geçmişi
- WebSocket canlı fiyatlar
- EXE paketleme

---

# Kod Kuralları

- DataManager tek veri kaynağıdır.
- UI doğrudan OKXService kullanamaz.
- Çalışan mimari korunmalıdır.
- Gereksiz refactor yapılmamalıdır.
- Kod modüler olmalıdır.
- Performans ön planda tutulmalıdır.

---

# Kod Yazarken

Her görevde:

1. Plan oluştur.
2. Değişecek dosyaları belirt.
3. Kodu üret.
4. Değişiklikleri özetle.

---

# Yasaklar

- API anahtarlarını koda yazma.
- Tüm projeyi yeniden yazma.
- Çalışan mimariyi bozma.
- Kullanıcı istemedikçe dosya taşıma.
- Kullanıcı istemedikçe gereksiz dosya oluşturma.

---

# Hedef

CryptoDesk;

Profesyonel,

yüksek performanslı,

bakımı kolay,

uzun yıllar geliştirilebilecek

bir Windows masaüstü uygulaması olacaktır.