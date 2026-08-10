# Caspian Fedora KDE kurulumu

Bu dosyalar Caspian'ı kullanıcı hesabına kurar. `sudo` kullanmaz.

## Kurulum

Proje kökünde:

```bash
bash packaging/fedora/install.sh
```

Kurulum konumları:

- Uygulama: `~/.local/opt/caspian/app`
- Python ortamı: `~/.local/opt/caspian/venv`
- Başlatıcı: `~/.local/bin/caspian`
- Menü kaydı: `~/.local/share/applications/io.github.erenynk.CryptoDesk.desktop`
- Simgeler: `~/.local/share/icons/hicolor`

Kurulumdan sonra uygulama KDE menüsünde **Caspian** adıyla görünür.
Terminalden `caspian` komutuyla da açılabilir.

## Güncelleme

Güncel proje branch'i üzerinde kurulum komutunu yeniden çalıştır:

```bash
bash packaging/fedora/install.sh
```

Mevcut kullanıcı verileri etkilenmez.

## Kaldırma

Kullanıcı verilerini koruyarak:

```bash
bash packaging/fedora/uninstall.sh
```

Ayarlar ve veritabanı dahil tüm kullanıcı verilerini de silerek:

```bash
bash packaging/fedora/uninstall.sh --purge-data
```
