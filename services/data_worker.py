from PySide6.QtCore import QThread, Signal


class PortfolioRefreshWorker(QThread):
    result_ready = Signal(bool, object)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager

    def run(self):
        try:
            success, result = self.data_manager.refresh_portfolio()
        except Exception as e:
            success = False
            result = str(e)

        self.result_ready.emit(success, result)