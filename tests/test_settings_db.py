import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from database import settings_db


class SettingsDatabaseTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_directory.name)

        self.db_path_patcher = patch.object(
            settings_db,
            "DB_PATH",
            self.temp_path / "test_cryptodesk.db",
        )
        self.config_path_patcher = patch.object(
            settings_db,
            "CONFIG",
            self.temp_path / "test_config.json",
        )

        self.db_path_patcher.start()
        self.config_path_patcher.start()

        settings_db._init_watchlist_table()
        settings_db._init_price_alarms_table()
        settings_db._init_app_settings_table()

    def tearDown(self):
        self.config_path_patcher.stop()
        self.db_path_patcher.stop()
        self.temp_directory.cleanup()

    def test_load_settings_returns_empty_values_when_missing(self):
        self.assertEqual(
            settings_db.load_settings(),
            ("", "", ""),
        )

    def test_save_and_load_settings_round_trip(self):
        def encrypt_stub(value):
            return f"encrypted:{value}"

        def decrypt_stub(value):
            prefix = "encrypted:"
            self.assertTrue(value.startswith(prefix))
            return value[len(prefix):]

        with (
            patch.object(
                settings_db,
                "encrypt",
                side_effect=encrypt_stub,
            ),
            patch.object(
                settings_db,
                "decrypt",
                side_effect=decrypt_stub,
            ),
        ):
            settings_db.save_settings(
                "api-key",
                "secret-key",
                "passphrase",
            )

            loaded = settings_db.load_settings()

        self.assertEqual(
            loaded,
            (
                "api-key",
                "secret-key",
                "passphrase",
            ),
        )

        stored = json.loads(
            settings_db.CONFIG.read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            stored["api"],
            "encrypted:api-key",
        )
        self.assertEqual(
            stored["secret"],
            "encrypted:secret-key",
        )
        self.assertEqual(
            stored["passphrase"],
            "encrypted:passphrase",
        )

    def test_load_settings_handles_invalid_json(self):
        settings_db.CONFIG.write_text(
            "{invalid-json",
            encoding="utf-8",
        )

        self.assertEqual(
            settings_db.load_settings(),
            ("", "", ""),
        )

    def test_default_app_settings_are_initialized(self):
        result = settings_db.get_all_app_settings()

        for key, expected in (
            settings_db.DEFAULT_APP_SETTINGS.items()
        ):
            with self.subTest(key=key):
                self.assertIn(key, result)
                self.assertEqual(
                    result[key],
                    expected,
                )

    def test_get_unknown_app_setting_returns_default(self):
        self.assertEqual(
            settings_db.get_app_setting(
                "unknown-setting",
                "fallback",
            ),
            "fallback",
        )

    def test_set_and_get_app_setting(self):
        result = settings_db.set_app_setting(
            "notifications_enabled",
            False,
        )

        self.assertTrue(result)
        self.assertFalse(
            settings_db.get_app_setting(
                "notifications_enabled"
            )
        )

    def test_set_app_setting_rejects_invalid_values(self):
        self.assertFalse(
            settings_db.set_app_setting("", True)
        )
        self.assertFalse(
            settings_db.set_app_setting(
                "unserializable",
                object(),
            )
        )

    def test_save_app_settings_updates_multiple_values(self):
        result = settings_db.save_app_settings(
            {
                "notifications_enabled": False,
                "alarm_sound_enabled": True,
                "custom_value": {
                    "enabled": True,
                    "count": 3,
                },
                "   ": "ignored",
            }
        )

        self.assertTrue(result)

        saved = settings_db.get_all_app_settings()

        self.assertFalse(
            saved["notifications_enabled"]
        )
        self.assertTrue(
            saved["alarm_sound_enabled"]
        )
        self.assertEqual(
            saved["custom_value"],
            {
                "enabled": True,
                "count": 3,
            },
        )
        self.assertNotIn("   ", saved)

    def test_save_app_settings_rejects_invalid_payload(self):
        self.assertFalse(
            settings_db.save_app_settings(
                ["not", "a", "dictionary"]
            )
        )
        self.assertFalse(
            settings_db.save_app_settings(
                {
                    "invalid": object(),
                }
            )
        )

    def test_reset_app_settings_restores_defaults(self):
        self.assertTrue(
            settings_db.set_app_setting(
                "notifications_enabled",
                False,
            )
        )
        self.assertTrue(
            settings_db.set_app_setting(
                "alarm_sound_enabled",
                True,
            )
        )

        self.assertTrue(
            settings_db.reset_app_settings()
        )

        result = settings_db.get_all_app_settings()

        self.assertEqual(
            result["notifications_enabled"],
            settings_db.DEFAULT_APP_SETTINGS[
                "notifications_enabled"
            ],
        )
        self.assertEqual(
            result["alarm_sound_enabled"],
            settings_db.DEFAULT_APP_SETTINGS[
                "alarm_sound_enabled"
            ],
        )

    def test_watchlist_adds_normalized_symbol_and_price(self):
        self.assertTrue(
            settings_db.add_watchlist_symbol(
                " btc ",
                65000.50,
            )
        )

        self.assertEqual(
            settings_db.get_watchlist_symbols(),
            ["BTC"],
        )

        items = settings_db.get_watchlist_items()

        self.assertEqual(len(items), 1)
        self.assertEqual(
            items[0]["symbol"],
            "BTC",
        )
        self.assertEqual(
            items[0]["added_price"],
            65000.50,
        )
        self.assertTrue(items[0]["created_at"])

    def test_watchlist_rejects_empty_and_duplicate_symbols(self):
        self.assertFalse(
            settings_db.add_watchlist_symbol("")
        )
        self.assertTrue(
            settings_db.add_watchlist_symbol("BTC")
        )
        self.assertFalse(
            settings_db.add_watchlist_symbol(" btc ")
        )

        self.assertEqual(
            settings_db.get_watchlist_symbols(),
            ["BTC"],
        )

    def test_watchlist_removes_existing_symbol(self):
        self.assertTrue(
            settings_db.add_watchlist_symbol("ETH")
        )
        self.assertTrue(
            settings_db.remove_watchlist_symbol(
                " eth "
            )
        )
        self.assertFalse(
            settings_db.remove_watchlist_symbol(
                "ETH"
            )
        )
        self.assertEqual(
            settings_db.get_watchlist_items(),
            [],
        )

    def test_alarm_adds_normalized_record(self):
        alarm_id = settings_db.add_price_alarm(
            symbol=" btc ",
            target_price=70000,
            condition=" ABOVE ",
            note="  Ana hedef  ",
        )

        self.assertIsInstance(alarm_id, int)

        alarms = settings_db.get_price_alarms()

        self.assertEqual(len(alarms), 1)
        self.assertEqual(
            alarms[0]["symbol"],
            "BTC",
        )
        self.assertEqual(
            alarms[0]["target_price"],
            70000,
        )
        self.assertEqual(
            alarms[0]["condition"],
            "above",
        )
        self.assertEqual(
            alarms[0]["note"],
            "Ana hedef",
        )
        self.assertTrue(
            alarms[0]["is_active"]
        )
        self.assertFalse(
            alarms[0]["is_triggered"]
        )

    def test_alarm_rejects_invalid_values(self):
        self.assertIsNone(
            settings_db.add_price_alarm(
                symbol="",
                target_price=100,
                condition="above",
            )
        )
        self.assertIsNone(
            settings_db.add_price_alarm(
                symbol="BTC",
                target_price=0,
                condition="above",
            )
        )
        self.assertIsNone(
            settings_db.add_price_alarm(
                symbol="BTC",
                target_price=100,
                condition="invalid",
            )
        )

        self.assertEqual(
            settings_db.get_price_alarms(),
            [],
        )

    def test_active_alarm_query_filters_inactive_records(self):
        active_id = settings_db.add_price_alarm(
            "BTC",
            70000,
            "above",
        )
        inactive_id = settings_db.add_price_alarm(
            "ETH",
            2000,
            "below",
        )

        self.assertTrue(
            settings_db.set_price_alarm_active(
                inactive_id,
                False,
            )
        )

        active = (
            settings_db.get_active_price_alarms()
        )

        self.assertEqual(
            [item["id"] for item in active],
            [active_id],
        )

    def test_alarm_status_can_be_changed(self):
        alarm_id = settings_db.add_price_alarm(
            "BTC",
            70000,
            "above",
        )

        self.assertTrue(
            settings_db.set_price_alarm_active(
                alarm_id,
                False,
            )
        )
        self.assertFalse(
            settings_db.get_price_alarms()[0][
                "is_active"
            ]
        )
        self.assertFalse(
            settings_db.set_price_alarm_active(
                999999,
                True,
            )
        )

    def test_alarm_can_only_be_triggered_once(self):
        alarm_id = settings_db.add_price_alarm(
            "BTC",
            70000,
            "above",
            "Tetikleme testi",
        )

        self.assertTrue(
            settings_db.mark_price_alarm_triggered(
                alarm_id
            )
        )
        self.assertFalse(
            settings_db.mark_price_alarm_triggered(
                alarm_id
            )
        )

        alarm = settings_db.get_price_alarms()[0]

        self.assertFalse(alarm["is_active"])
        self.assertTrue(alarm["is_triggered"])
        self.assertTrue(alarm["triggered_at"])
        self.assertEqual(
            settings_db.get_active_price_alarms(),
            [],
        )

    def test_alarm_can_be_deleted(self):
        alarm_id = settings_db.add_price_alarm(
            "ETH",
            2000,
            "below",
        )

        self.assertTrue(
            settings_db.delete_price_alarm(
                alarm_id
            )
        )
        self.assertFalse(
            settings_db.delete_price_alarm(
                alarm_id
            )
        )
        self.assertEqual(
            settings_db.get_price_alarms(),
            [],
        )

    def test_database_schema_contains_required_columns_and_indexes(
        self,
    ):
        with settings_db._get_connection() as conn:
            watchlist_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(watchlist_symbols)"
                ).fetchall()
            }
            alarm_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(price_alarms)"
                ).fetchall()
            }
            app_setting_columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(app_settings)"
                ).fetchall()
            }
            alarm_indexes = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA index_list(price_alarms)"
                ).fetchall()
            }

        self.assertTrue(
            {
                "id",
                "symbol",
                "created_at",
                "added_price",
            }.issubset(watchlist_columns)
        )
        self.assertTrue(
            {
                "id",
                "symbol",
                "target_price",
                "condition",
                "note",
                "is_active",
                "is_triggered",
                "created_at",
                "triggered_at",
            }.issubset(alarm_columns)
        )
        self.assertEqual(
            app_setting_columns,
            {
                "setting_key",
                "setting_value",
                "updated_at",
            },
        )
        self.assertIn(
            "idx_price_alarms_active",
            alarm_indexes,
        )
        self.assertIn(
            "idx_price_alarms_symbol",
            alarm_indexes,
        )

    def test_watchlist_table_migrates_added_price_column(self):
        with settings_db._get_connection() as conn:
            conn.execute("DROP TABLE watchlist_symbols")
            conn.execute(
                """
                CREATE TABLE watchlist_symbols (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT UNIQUE NOT NULL,
                    created_at TEXT
                )
                """
            )

        settings_db._init_watchlist_table()

        with settings_db._get_connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(watchlist_symbols)"
                ).fetchall()
            }

        self.assertIn("added_price", columns)

    def test_alarm_table_migrates_note_column(self):
        with settings_db._get_connection() as conn:
            conn.execute("DROP TABLE price_alarms")
            conn.execute(
                """
                CREATE TABLE price_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    target_price REAL NOT NULL,
                    condition TEXT NOT NULL,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_triggered INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    triggered_at TEXT
                )
                """
            )

        settings_db._init_price_alarms_table()

        with settings_db._get_connection() as conn:
            columns = {
                row["name"]
                for row in conn.execute(
                    "PRAGMA table_info(price_alarms)"
                ).fetchall()
            }

        self.assertIn("note", columns)

    def test_connection_rolls_back_and_closes_on_exception(self):
        connection = Mock()

        with (
            patch.object(
                settings_db.sqlite3,
                "connect",
                return_value=connection,
            ),
            self.assertRaisesRegex(
                RuntimeError,
                "transaction failed",
            ),
        ):
            with settings_db._get_connection():
                raise RuntimeError(
                    "transaction failed"
                )

        connection.rollback.assert_called_once_with()
        connection.commit.assert_not_called()
        connection.close.assert_called_once_with()

    def test_get_app_setting_rejects_blank_key(self):
        self.assertEqual(
            settings_db.get_app_setting(
                "   ",
                "fallback",
            ),
            "fallback",
        )

    def test_get_app_setting_handles_invalid_json(self):
        with settings_db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (
                    setting_key,
                    setting_value,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "broken",
                    "{invalid-json",
                    "2026-07-24T00:00:00+00:00",
                ),
            )

        self.assertEqual(
            settings_db.get_app_setting(
                "broken",
                "fallback",
            ),
            "fallback",
        )

    def test_get_app_setting_handles_database_error(self):
        with patch.object(
            settings_db,
            "_get_connection",
            side_effect=sqlite3.Error(
                "database unavailable"
            ),
        ):
            result = settings_db.get_app_setting(
                "notifications_enabled",
                "fallback",
            )

        self.assertEqual(result, "fallback")

    def test_get_all_app_settings_skips_invalid_json(self):
        with settings_db._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO app_settings (
                    setting_key,
                    setting_value,
                    updated_at
                )
                VALUES (?, ?, ?)
                """,
                (
                    "broken",
                    "{invalid-json",
                    "2026-07-24T00:00:00+00:00",
                ),
            )

        result = settings_db.get_all_app_settings()

        self.assertNotIn("broken", result)

    def test_get_all_app_settings_handles_database_error(self):
        with patch.object(
            settings_db,
            "_get_connection",
            side_effect=sqlite3.Error(
                "database unavailable"
            ),
        ):
            result = (
                settings_db.get_all_app_settings()
            )

        self.assertEqual(
            result,
            settings_db.DEFAULT_APP_SETTINGS,
        )

    def test_reset_app_settings_handles_database_error(self):
        with patch.object(
            settings_db,
            "_get_connection",
            side_effect=sqlite3.Error(
                "database unavailable"
            ),
        ):
            result = (
                settings_db.reset_app_settings()
            )

        self.assertFalse(result)

    def test_remove_watchlist_rejects_blank_symbol(self):
        self.assertFalse(
            settings_db.remove_watchlist_symbol(
                "   "
            )
        )

    def test_watchlist_queries_handle_database_errors(self):
        with patch.object(
            settings_db,
            "_get_connection",
            side_effect=sqlite3.Error(
                "database unavailable"
            ),
        ):
            self.assertFalse(
                settings_db.remove_watchlist_symbol(
                    "BTC"
                )
            )
            self.assertEqual(
                settings_db.get_watchlist_symbols(),
                [],
            )
            self.assertEqual(
                settings_db.get_watchlist_items(),
                [],
            )

    def test_alarm_functions_handle_database_errors(self):
        with patch.object(
            settings_db,
            "_get_connection",
            side_effect=sqlite3.Error(
                "database unavailable"
            ),
        ):
            self.assertIsNone(
                settings_db.add_price_alarm(
                    "BTC",
                    100,
                    "above",
                )
            )
            self.assertEqual(
                settings_db.get_price_alarms(),
                [],
            )
            self.assertEqual(
                settings_db.get_active_price_alarms(),
                [],
            )
            self.assertFalse(
                settings_db.set_price_alarm_active(
                    1,
                    True,
                )
            )
            self.assertFalse(
                settings_db.mark_price_alarm_triggered(
                    1
                )
            )
            self.assertFalse(
                settings_db.delete_price_alarm(1)
            )


if __name__ == "__main__":
    unittest.main()
