# İşlem Geçmişi UI düzeltmesi

Bu paket iki küçük düzeltme içerir:

- Sol baştaki sıra numarası sütununun başlığı boş bırakıldı.
- Sıralama veya filtreleme sonrası eski PnL widget'larının başka satırlara
  taşınması engellendi.

Sorunun nedeni `QTableWidget` aynı satır sayısıyla yeniden doldurulduğunda
önceki `setCellWidget()` içeriğinin aynı hücre koordinatında kalabilmesiydi.
`_populate_table()` artık satırları önce `0` yapıp yeniden oluşturuyor.
Böylece satış satırındaki PnL widget'ı daha sonra aynı satır konumuna gelen
alış işleminde görünmüyor.

Alış işlemlerinin PnL verisi hesaplanmıyor; hücre boş kalmaya devam eder.
