import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app_paths


class AppPathsTestCase(unittest.TestCase):
    def test_windows_uses_local_app_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(
                    app_paths,
                    "IS_WINDOWS",
                    True,
                ),
                patch.dict(
                    os.environ,
                    {"LOCALAPPDATA": temp_dir},
                    clear=True,
                ),
            ):
                result = app_paths.get_app_data_dir()

        self.assertEqual(
            result,
            Path(temp_dir) / "CryptoDesk",
        )

    def test_windows_falls_back_to_home(self):
        home = Path("/home/TestUser")

        with (
            patch.object(
                app_paths,
                "IS_WINDOWS",
                True,
            ),
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
            patch.object(
                Path,
                "home",
                return_value=home,
            ),
        ):
            result = app_paths.get_app_data_dir()

        self.assertEqual(
            result,
            home / "AppData" / "Local" / "CryptoDesk",
        )

    def test_linux_uses_xdg_data_home(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with (
                patch.object(
                    app_paths,
                    "IS_WINDOWS",
                    False,
                ),
                patch.dict(
                    os.environ,
                    {"XDG_DATA_HOME": temp_dir},
                    clear=True,
                ),
            ):
                result = app_paths.get_app_data_dir()

        self.assertEqual(
            result,
            Path(temp_dir) / "CryptoDesk",
        )

    def test_linux_falls_back_to_local_share(self):
        home = Path("/home/TestUser")

        with (
            patch.object(
                app_paths,
                "IS_WINDOWS",
                False,
            ),
            patch.dict(
                os.environ,
                {},
                clear=True,
            ),
            patch.object(
                Path,
                "home",
                return_value=home,
            ),
        ):
            result = app_paths.get_app_data_dir()

        self.assertEqual(
            result,
            home / ".local" / "share" / "CryptoDesk",
        )


if __name__ == "__main__":
    unittest.main()
