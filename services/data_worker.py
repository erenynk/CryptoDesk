from PySide6.QtCore import QThread, Signal


class PortfolioRefreshWorker(QThread):
    finished = Signal(bool, object)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager

    def run(self):        
        success, result = self.data_manager.refresh_portfolio()
        self.finished.emit(success, result)