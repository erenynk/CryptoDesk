# CryptoDesk Geliştirme Rehberi

Bu belge CryptoDesk projesinin geliştirme standartlarını tanımlar.

---

# Amaç

CryptoDesk;

- Python

- PySide6

- SQLite

- OKX API

kullanılarak geliştirilen profesyonel bir masaüstü kripto portföy uygulamasıdır.

Temel hedefler:

- Hızlı

- Kararlı

- Okunabilir

- Modüler

- Performanslı

- Bakımı kolay

bir yapı oluşturmaktır.

---

# Genel Kurallar

- Tüm açıklamalar Türkçe yazılır.

- Kod yorumları Türkçe yazılır.

- Gereksiz açıklama yapılmaz.

- Kod mümkün olduğunca sade tutulur.

- Çalışan kod gereksiz yere değiştirilmez.

---

# Mimari

Merkezi veri yönetimi:

DataManager

Tek veri kaynağıdır.

UI hiçbir zaman doğrudan:

- OKXService

- Database

- PriceCache

ile haberleşmez.

Her veri DataManager üzerinden gelir.

---

# Katmanlar

[app.py](http://app.py)

↓

MainWindow

↓

Pages

↓

DataManager

↓

Services

↓

Database / API

---

# Dosya Yapısı

api/

database/

security/

services/

ui/

[app.py](http://app.py)

---

# Performans Kuralları

- UI thread'i bloklanmaz.

- Ağ işlemleri Thread içinde yapılır.

- Gereksiz API isteği yapılmaz.

- Cache kullanılır.

- Gereksiz repaint yapılmaz.

- Gereksiz widget oluşturulmaz.

---

# Kod Yazım Kuralları

Fonksiyonlar mümkün olduğunca kısa tutulur.

Bir fonksiyon yalnızca tek iş yapmalıdır.

Kod tekrarından kaçınılır.

Magic number kullanılmaz.

Anlamlı değişken isimleri kullanılır.

---

# UI Kuralları

Tema:

Koyu tema

Renkler:

- Beyaz

- Gri

- Yeşil

- Mavi

Mevcut tasarım dili korunur.

Kullanıcı istemedikçe:

- Font değiştirilmez.

- Boyut değiştirilmez.

- Stil değiştirilmez.

---

# Widget Kuralları

Balance Widget

- Her zaman üstte kalır.

- Şeffaf görünüm korunur.

- Kenarlara taşmaz.

- Bakiye gizlenebilir.

- DataManager'dan beslenir.

---

# API Kuralları

API anahtarları

hiçbir zaman

koda yazılmaz.

Şifreler loglanmaz.

Gizli bilgiler gösterilmez.

---

# Git Kuralları

Her çalışan aşamada:

git add .

git commit

git push

yapılır.

Commit mesajları açıklayıcı olmalıdır.

Örnek:

v0.2.3 - Improve floating balance widget

---

# Yeni Özellik Geliştirme

Her yeni özellik şu sırayla geliştirilir.

1.

Plan

↓

2.

Mimari kontrolü

↓

3.

Kod

↓

4.

Test

↓

5.

Git Commit

↓

6.

GitHub

---

# Cursor Kuralları

Cursor hiçbir zaman:

- Tüm projeyi yeniden yazmaz.

- Çalışan mimariyi bozmaz.

- Gereksiz refactor yapmaz.

Cursor yalnızca gerekli dosyaları değiştirir.

Her değişiklikten önce:

Hangi dosyaları değiştireceğini söyler.

Her değişiklikten sonra:

Değiştirilen dosyaları listeler.

---

# ChatGPT Kullanım Kuralları

ChatGPT;

- Mimari kararlarını verir.

- Kodu denetler.

- Performans analizi yapar.

- Güvenlik kontrolü yapar.

- Cursor'un ürettiği kodu inceler.

Cursor ise

yalnızca kod üretiminde yardımcıdır.

---

# Hedef

CryptoDesk;

Kurumsal seviyede,

bakımı kolay,

yüksek performanslı,

uzun yıllar geliştirilebilecek

bir masaüstü uygulaması olacaktır.

# Görev Yönetimi

Her görev yalnızca tek bir özelliği kapsamalıdır.

Bir görev içerisinde birden fazla bağımsız özellik geliştirilmez.

Her görev şu sırayla ilerler:

1. Analiz
2. Plan
3. Kod
4. Test
5. Git Commit
6. GitHub Push