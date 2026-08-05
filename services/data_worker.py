from PySide6.QtCore import QThread, Signal


class PortfolioRefreshWorker(QThread):
    result_ready = Signal(bool, object)

    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self._stop_requested = False

    def requestInterruption(self):
        self._stop_requested = True
        super().requestInterruption()

    @staticmethod
    def _should_stop(worker):
        if getattr(worker, "_stop_requested", False):
            return True

        interruption_check = getattr(
            worker,
            "isInterruptionRequested",
            None,
        )
        if not callable(interruption_check):
            return False

        try:
            return bool(interruption_check())
        except RuntimeError:
            return True

    def run(self):
        if PortfolioRefreshWorker._should_stop(self):
            return

        try:
            success, result = (
                self.data_manager.refresh_portfolio()
            )
        except Exception as error:
            success = False
            result = str(error)

        if PortfolioRefreshWorker._should_stop(self):
            return

        self.result_ready.emit(success, result)
