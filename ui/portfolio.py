from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QMessageBox,
    QHeaderView,
    QCheckBox,
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from services.okx_service import OKXService

# Sıralama için özel hücre sınıfı
class NumericTableWidgetItem(QTableWidgetItem):
    def __init__(self, value, display_text):
        super().__init__(display_text)
        self.value = value

    def __lt__(self, other):
        if isinstance(other, NumericTableWidgetItem):
            try:
                return self.value < other.value
            except Exception:
                return super().__lt__(other)
        return super().__lt__(other)


# ARKA PLAN İŞÇİSİ (THREAD)
class BalanceFetchWorker(QThread):
    finished = Signal(bool, object)

    def __init__(self, okx_service):
        super().__init__()
        self.okx_service = okx_service

    def run(self):
        self.okx_service.refresh_client()
        success, result = self.okx_service.get_spot_balances()
        self.finished.emit(success, result)


class PortfolioPage(QWidget):
    def __init__(self):
        super().__init__()

        self.okx_service = OKXService()
        self.raw_assets_data = []  

        # Arka plan işçisi kurulumu
        self.worker = BalanceFetchWorker(self.okx_service)
        self.worker.finished.connect(self.on_balances_loaded)

        # 30 Saniyelik Otomatik Yenileme Zamanlayıcısı
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30000)  # 30.000 milisaniye = 30 saniye
        self.refresh_timer.timeout.connect(self.load_balances)

        layout = QVBoxLayout(self)

        # ÜST PANEL
        top_layout = QHBoxLayout()
        title = QLabel("Portfolio")
        title.setStyleSheet("font-size: 28px; font-weight: bold;")
        top_layout.addWidget(title)
        
        top_layout.addStretch()

        self.hide_dust_checkbox = QCheckBox("Küçük Bakiyeleri Gizle (< $1)")
        self.hide_dust_checkbox.setStyleSheet("font-size: 14px; margin-right: 15px;")
        self.hide_dust_checkbox.stateChanged.connect(self.update_table_view)
        top_layout.addWidget(self.hide_dust_checkbox)
        
        self.refresh_button = QPushButton("Bakiyeleri Yenile")
        self.refresh_button.clicked.connect(self.load_balances)
        top_layout.addWidget(self.refresh_button)
        layout.addLayout(top_layout)

        # TOPLAM BAKİYE KARTI
        self.total_balance_label = QLabel("Toplam Bakiye: Yükleniyor...")
        self.total_balance_label.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: #10B981;
            background-color: #1F2937;
            padding: 15px;
            border-radius: 8px;
            margin-top: 10px;
            margin-bottom: 10px;
        """)
        layout.addWidget(self.total_balance_label)

        # TABLO YAPISI
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Varlık (Coin)", 
            "Toplam Miktar", 
            "Kullanılabilir Miktar", 
            "Anlık Fiyat (USDT)", 
            "Toplam Değer (USDT)"
        ])
        
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(False)
        
        layout.addWidget(self.table)

        # İlk açılışta verileri hemen çek ve zamanlayıcıyı başlat
        QTimer.singleShot(100, self.start_page)

    def start_page(self):
        """Sayfa ilk açıldığında hem veriyi yükler hem de 30 saniyelik döngüyü başlatır."""
        self.load_balances()
        self.refresh_timer.start()

    def load_balances(self):
        """Arka plan işçisini tetikler."""
        if self.worker.isRunning():
            return

        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Güncelleniyor...")
        
        self.worker.start()

    def on_balances_loaded(self, success, result):
        """Veriler arka planda yüklenip bittiğinde tetiklenir."""
        if success:
            total_usdt = result["total_usdt"]
            self.total_balance_label.setText(f"Toplam Bakiye: ${total_usdt:,.2f} USDT")
            self.raw_assets_data = result["assets"]
            self.update_table_view()
        else:
            # Otomatik yenilemede kullanıcıyı her 30 saniyede bir popup hata mesajıyla boğmamak için
            # hatayı sadece durum etiketinde gösteriyoruz.
            self.total_balance_label.setText("Toplam Bakiye: Güncelleme Başarısız (Ağ Hatası)")
            
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Bakiyeleri Yenile")

    def update_table_view(self):
        """Tabloyu günceller."""
        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        
        hide_dust = self.hide_dust_checkbox.isChecked()
        row_idx = 0

        for asset in self.raw_assets_data:
            usdt_value = asset["usdt_value"]
            
            if hide_dust and usdt_value < 1.0:
                continue
                
            self.table.insertRow(row_idx)
            
            coin_item = QTableWidgetItem(asset["coin"])
            coin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row_idx, 0, coin_item)
            
            total_text = f"{asset['total']:.8f}".rstrip('0').rstrip('.')
            avail_text = f"{asset['available']:.8f}".rstrip('0').rstrip('.')
            
            total_item = NumericTableWidgetItem(asset["total"], total_text if total_text else "0")
            avail_item = NumericTableWidgetItem(asset["available"], avail_text if avail_text else "0")
            price_item = NumericTableWidgetItem(asset["price"], f"${asset['price']:,.4f}")
            value_item = NumericTableWidgetItem(usdt_value, f"${usdt_value:,.2f}")
            
            total_item.setTextAlignment(Qt.AlignCenter)
            avail_item.setTextAlignment(Qt.AlignCenter)
            price_item.setTextAlignment(Qt.AlignCenter)
            value_item.setTextAlignment(Qt.AlignCenter)
            
            self.table.setItem(row_idx, 1, total_item)
            self.table.setItem(row_idx, 2, avail_item)
            self.table.setItem(row_idx, 3, price_item)
            self.table.setItem(row_idx, 4, value_item)
            
            row_idx += 1

        self.table.setSortingEnabled(True)

    # AKILLI OTO-YENİLEME YÖNETİMİ
    # Kullanıcı sol menüden başka sayfaya geçerse zamanlayıcı durur, bu sayfaya dönünce tekrar başlar.
    def showEvent(self, event):
        super().showEvent(event)
        if not self.refresh_timer.isActive():
            self.refresh_timer.start()

    def hideEvent(self, event):
        super().hideEvent(event)
        self.refresh_timer.stop()