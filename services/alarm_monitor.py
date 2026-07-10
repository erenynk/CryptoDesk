from PySide6.QtCore import QObject, QTimer, Signal

from services import alarm_service


class AlarmMonitor(QObject):
    alarm_triggered = Signal(dict)
    alarms_checked = Signal()

    CHECK_INTERVAL_MS = 30000

    def __init__(self, data_manager, parent=None):
        super().__init__(parent)

        self.data_manager = data_manager
        self._checking = False

        self.timer = QTimer(self)
        self.timer.setInterval(self.CHECK_INTERVAL_MS)
        self.timer.timeout.connect(self.check_alarms)

        self.data_manager.portfolio_updated.connect(
            self.on_prices_updated
        )

    def start(self):
        if self.timer.isActive():
            return

        self.timer.start()

        QTimer.singleShot(
            1000,
            self.check_alarms,
        )

    def stop(self):
        self.timer.stop()

    def on_prices_updated(self, _portfolio):
        self.check_alarms()

    def check_alarms(self):
        if self._checking:
            return

        self._checking = True

        try:
            alarms = alarm_service.get_enabled_alarms()

            for alarm in alarms:
                self.check_alarm(alarm)

            self.alarms_checked.emit()

        finally:
            self._checking = False

    def check_alarm(self, alarm: dict):
        symbol = alarm["symbol"]
        current_price = self.data_manager.get_price(symbol)

        if current_price is None or current_price <= 0:
            return

        triggered = alarm_service.is_alarm_triggered(
            alarm,
            current_price,
        )

        if not triggered:
            return

        completed = alarm_service.complete_alarm(
            alarm["id"]
        )

        if not completed:
            return

        triggered_alarm = dict(alarm)
        triggered_alarm["current_price"] = current_price
        triggered_alarm["is_active"] = False
        triggered_alarm["is_triggered"] = True

        self.alarm_triggered.emit(triggered_alarm)