import unittest
from unittest.mock import patch

from services import alarm_service


class AlarmServiceTestCase(unittest.TestCase):
    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_normalizes_and_saves_values(
        self,
        add_price_alarm,
    ):
        add_price_alarm.return_value = 42

        success, result = alarm_service.create_alarm(
            symbol=" ethereum/usdt ",
            target_price="2500.50",
            condition=" ABOVE ",
            note="  Ana hedef  ",
        )

        self.assertTrue(success)
        self.assertEqual(result, 42)
        add_price_alarm.assert_called_once_with(
            symbol="ETH",
            target_price=2500.50,
            condition=alarm_service.CONDITION_ABOVE,
            note="Ana hedef",
        )

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_rejects_empty_symbol(
        self,
        add_price_alarm,
    ):
        success, result = alarm_service.create_alarm(
            symbol="   ",
            target_price=100,
            condition=alarm_service.CONDITION_ABOVE,
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Coin adı boş olamaz.",
        )
        add_price_alarm.assert_not_called()

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_rejects_invalid_condition(
        self,
        add_price_alarm,
    ):
        success, result = alarm_service.create_alarm(
            symbol="BTC",
            target_price=100,
            condition="invalid",
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Geçersiz alarm koşulu.",
        )
        add_price_alarm.assert_not_called()

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_rejects_non_numeric_price(
        self,
        add_price_alarm,
    ):
        success, result = alarm_service.create_alarm(
            symbol="BTC",
            target_price="not-a-number",
            condition=alarm_service.CONDITION_ABOVE,
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Geçerli bir hedef fiyat girin.",
        )
        add_price_alarm.assert_not_called()

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_rejects_zero_or_negative_price(
        self,
        add_price_alarm,
    ):
        for price in (0, -1, -100.5):
            with self.subTest(price=price):
                success, result = alarm_service.create_alarm(
                    symbol="BTC",
                    target_price=price,
                    condition=alarm_service.CONDITION_BELOW,
                )

                self.assertFalse(success)
                self.assertEqual(
                    result,
                    "Hedef fiyat sıfırdan büyük olmalıdır.",
                )

        add_price_alarm.assert_not_called()

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_rejects_note_over_limit(
        self,
        add_price_alarm,
    ):
        success, result = alarm_service.create_alarm(
            symbol="BTC",
            target_price=100,
            condition=alarm_service.CONDITION_ABOVE,
            note="x" * (
                alarm_service.MAX_NOTE_LENGTH + 1
            ),
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            (
                "Alarm notu en fazla "
                f"{alarm_service.MAX_NOTE_LENGTH} "
                "karakter olabilir."
            ),
        )
        add_price_alarm.assert_not_called()

    @patch("services.alarm_service.add_price_alarm")
    def test_create_alarm_returns_error_when_database_fails(
        self,
        add_price_alarm,
    ):
        add_price_alarm.return_value = None

        success, result = alarm_service.create_alarm(
            symbol="BTC",
            target_price=100,
            condition=alarm_service.CONDITION_ABOVE,
        )

        self.assertFalse(success)
        self.assertEqual(
            result,
            "Alarm kaydedilemedi.",
        )

    def test_above_alarm_triggers_at_or_above_target(self):
        alarm = {
            "target_price": 100,
            "condition": alarm_service.CONDITION_ABOVE,
        }

        self.assertFalse(
            alarm_service.is_alarm_triggered(
                alarm,
                99.99,
            )
        )
        self.assertTrue(
            alarm_service.is_alarm_triggered(
                alarm,
                100,
            )
        )
        self.assertTrue(
            alarm_service.is_alarm_triggered(
                alarm,
                101,
            )
        )

    def test_below_alarm_triggers_at_or_below_target(self):
        alarm = {
            "target_price": 100,
            "condition": alarm_service.CONDITION_BELOW,
        }

        self.assertTrue(
            alarm_service.is_alarm_triggered(
                alarm,
                99,
            )
        )
        self.assertTrue(
            alarm_service.is_alarm_triggered(
                alarm,
                100,
            )
        )
        self.assertFalse(
            alarm_service.is_alarm_triggered(
                alarm,
                100.01,
            )
        )

    def test_alarm_does_not_trigger_for_invalid_current_price(
        self,
    ):
        alarm = {
            "target_price": 100,
            "condition": alarm_service.CONDITION_ABOVE,
        }

        self.assertFalse(
            alarm_service.is_alarm_triggered(
                alarm,
                0,
            )
        )
        self.assertFalse(
            alarm_service.is_alarm_triggered(
                alarm,
                -1,
            )
        )

    def test_alarm_does_not_trigger_for_unknown_condition(
        self,
    ):
        alarm = {
            "target_price": 100,
            "condition": "unknown",
        }

        self.assertFalse(
            alarm_service.is_alarm_triggered(
                alarm,
                100,
            )
        )

    def test_condition_texts(self):
        self.assertEqual(
            alarm_service.get_condition_text(
                alarm_service.CONDITION_ABOVE
            ),
            "Üstüne çıkınca",
        )
        self.assertEqual(
            alarm_service.get_condition_text(
                alarm_service.CONDITION_BELOW
            ),
            "Altına düşünce",
        )
        self.assertEqual(
            alarm_service.get_condition_text("unknown"),
            "Bilinmiyor",
        )

    def test_status_texts(self):
        self.assertEqual(
            alarm_service.get_status_text(
                {
                    "is_triggered": True,
                    "is_active": True,
                }
            ),
            "Tetiklendi",
        )
        self.assertEqual(
            alarm_service.get_status_text(
                {
                    "is_triggered": False,
                    "is_active": True,
                }
            ),
            "Aktif",
        )
        self.assertEqual(
            alarm_service.get_status_text(
                {
                    "is_triggered": False,
                    "is_active": False,
                }
            ),
            "Pasif",
        )

    @patch("services.alarm_service.get_price_alarms")
    def test_get_all_alarms_delegates_to_database(
        self,
        get_price_alarms,
    ):
        expected = [{"id": 1}]
        get_price_alarms.return_value = expected

        self.assertIs(
            alarm_service.get_all_alarms(),
            expected,
        )

    @patch(
        "services.alarm_service.get_active_price_alarms"
    )
    def test_get_enabled_alarms_delegates_to_database(
        self,
        get_active_price_alarms,
    ):
        expected = [{"id": 2}]
        get_active_price_alarms.return_value = expected

        self.assertIs(
            alarm_service.get_enabled_alarms(),
            expected,
        )

    @patch("services.alarm_service.set_price_alarm_active")
    def test_change_alarm_status_delegates_to_database(
        self,
        set_price_alarm_active,
    ):
        set_price_alarm_active.return_value = True

        result = alarm_service.change_alarm_status(
            10,
            False,
        )

        self.assertTrue(result)
        set_price_alarm_active.assert_called_once_with(
            10,
            False,
        )

    @patch("services.alarm_service.delete_price_alarm")
    def test_remove_alarm_delegates_to_database(
        self,
        delete_price_alarm,
    ):
        delete_price_alarm.return_value = True

        result = alarm_service.remove_alarm(10)

        self.assertTrue(result)
        delete_price_alarm.assert_called_once_with(10)

    @patch(
        "services.alarm_service.mark_price_alarm_triggered"
    )
    def test_complete_alarm_delegates_to_database(
        self,
        mark_price_alarm_triggered,
    ):
        mark_price_alarm_triggered.return_value = True

        result = alarm_service.complete_alarm(10)

        self.assertTrue(result)
        mark_price_alarm_triggered.assert_called_once_with(
            10
        )


if __name__ == "__main__":
    unittest.main()
