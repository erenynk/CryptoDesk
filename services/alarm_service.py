from database.settings_db import (
    add_price_alarm,
    delete_price_alarm,
    get_active_price_alarms,
    get_price_alarms,
    set_price_alarm_active,
)
from services.watchlist_service import normalize_symbol
from database.settings_db import (
    add_price_alarm,
    delete_price_alarm,
    get_active_price_alarms,
    get_price_alarms,
    mark_price_alarm_triggered,
    set_price_alarm_active,
)


CONDITION_ABOVE = "above"
CONDITION_BELOW = "below"

VALID_CONDITIONS = {
    CONDITION_ABOVE,
    CONDITION_BELOW,
}


def create_alarm(
    symbol: str,
    target_price: float,
    condition: str,
) -> tuple[bool, int | str]:
    normalized_symbol = normalize_symbol(symbol)
    normalized_condition = condition.strip().lower()

    if not normalized_symbol:
        return False, "Coin adı boş olamaz."

    if normalized_condition not in VALID_CONDITIONS:
        return False, "Geçersiz alarm koşulu."

    try:
        normalized_price = float(target_price)
    except (TypeError, ValueError):
        return False, "Geçerli bir hedef fiyat girin."

    if normalized_price <= 0:
        return False, "Hedef fiyat sıfırdan büyük olmalıdır."

    alarm_id = add_price_alarm(
        normalized_symbol,
        normalized_price,
        normalized_condition,
    )

    if alarm_id is None:
        return False, "Alarm kaydedilemedi."

    return True, alarm_id


def get_all_alarms() -> list[dict]:
    return get_price_alarms()


def get_enabled_alarms() -> list[dict]:
    return get_active_price_alarms()


def change_alarm_status(
    alarm_id: int,
    is_active: bool,
) -> bool:
    return set_price_alarm_active(alarm_id, is_active)


def remove_alarm(alarm_id: int) -> bool:
    return delete_price_alarm(alarm_id)


def get_condition_text(condition: str) -> str:
    if condition == CONDITION_ABOVE:
        return "Üstüne çıkınca"

    if condition == CONDITION_BELOW:
        return "Altına düşünce"

    return "Bilinmiyor"


def get_status_text(alarm: dict) -> str:
    if alarm.get("is_triggered"):
        return "Tetiklendi"

    if alarm.get("is_active"):
        return "Aktif"

    return "Pasif"
def is_alarm_triggered(
    alarm: dict,
    current_price: float,
) -> bool:
    if current_price <= 0:
        return False

    target_price = float(alarm["target_price"])
    condition = alarm["condition"]

    if condition == CONDITION_ABOVE:
        return current_price >= target_price

    if condition == CONDITION_BELOW:
        return current_price <= target_price

    return False


def complete_alarm(alarm_id: int) -> bool:
    return mark_price_alarm_triggered(alarm_id)