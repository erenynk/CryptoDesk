import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

import services.startup_service as startup_service


class StartupServiceTestCase(unittest.TestCase):
    def make_winreg(
        self,
        *,
        open_key=None,
        create_key=None,
        query_value=None,
        set_value=None,
        delete_value=None,
    ):
        return SimpleNamespace(
            HKEY_CURRENT_USER=object(),
            KEY_READ=0x20019,
            KEY_SET_VALUE=0x0002,
            REG_SZ=1,
            OpenKey=(
                open_key
                if open_key is not None
                else Mock()
            ),
            CreateKeyEx=(
                create_key
                if create_key is not None
                else Mock()
            ),
            QueryValueEx=(
                query_value
                if query_value is not None
                else Mock()
            ),
            SetValueEx=(
                set_value
                if set_value is not None
                else Mock()
            ),
            DeleteValue=(
                delete_value
                if delete_value is not None
                else Mock()
            ),
        )

    @staticmethod
    def make_context_key():
        key = object()
        context = MagicMock()
        context.__enter__.return_value = key
        context.__exit__.return_value = False
        return context, key

    def test_python_executable_prefers_pythonw_for_python_exe(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            folder = Path(temp_dir)
            python_exe = folder / "python.exe"
            pythonw_exe = folder / "pythonw.exe"
            python_exe.touch()
            pythonw_exe.touch()

            with patch.object(
                startup_service.sys,
                "executable",
                str(python_exe),
            ):
                result = (
                    startup_service
                    ._get_python_executable()
                )

        self.assertEqual(result, pythonw_exe)

    def test_python_executable_keeps_python_when_pythonw_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            python_exe = Path(temp_dir) / "python.exe"
            python_exe.touch()

            with patch.object(
                startup_service.sys,
                "executable",
                str(python_exe),
            ):
                result = (
                    startup_service
                    ._get_python_executable()
                )

        self.assertEqual(result, python_exe)

    def test_python_executable_keeps_non_python_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "caspian.exe"
            executable.touch()

            with patch.object(
                startup_service.sys,
                "executable",
                str(executable),
            ):
                result = (
                    startup_service
                    ._get_python_executable()
                )

        self.assertEqual(result, executable)

    def test_startup_command_uses_frozen_executable(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            executable = Path(temp_dir) / "Caspian.exe"
            executable.touch()

            with (
                patch.object(
                    startup_service.sys,
                    "frozen",
                    True,
                    create=True,
                ),
                patch.object(
                    startup_service.sys,
                    "executable",
                    str(executable),
                ),
            ):
                result = (
                    startup_service
                    ._get_startup_command()
                )

        self.assertEqual(
            result,
            f'"{executable.resolve()}"',
        )

    def test_startup_command_uses_python_and_app_path(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            service_path = (
                root
                / "services"
                / "startup_service.py"
            )
            service_path.parent.mkdir()
            service_path.touch()
            executable = root / "pythonw.exe"
            executable.touch()

            expected_app_path = (
                service_path.resolve()
                .parent
                .parent
                / "app.py"
            )

            with (
                patch.object(
                    startup_service.sys,
                    "frozen",
                    False,
                    create=True,
                ),
                patch.object(
                    startup_service,
                    "__file__",
                    str(service_path),
                ),
                patch.object(
                    startup_service,
                    "_get_python_executable",
                    return_value=executable,
                ),
            ):
                result = (
                    startup_service
                    ._get_startup_command()
                )

        self.assertEqual(
            result,
            f'"{executable}" "{expected_app_path}"',
        )

    def test_is_startup_enabled_returns_false_outside_windows(self):
        with patch.object(
            startup_service.os,
            "name",
            "posix",
        ):
            result = (
                startup_service
                .is_startup_enabled()
            )

        self.assertFalse(result)

    def test_is_startup_enabled_returns_true_for_nonempty_value(self):
        context, key = self.make_context_key()
        query_value = Mock(
            return_value=(
                '"C:\\Caspian\\Caspian.exe"',
                1,
            )
        )
        winreg = self.make_winreg(
            open_key=Mock(return_value=context),
            query_value=query_value,
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .is_startup_enabled()
            )

        self.assertTrue(result)
        winreg.OpenKey.assert_called_once_with(
            winreg.HKEY_CURRENT_USER,
            startup_service.RUN_KEY_PATH,
            0,
            winreg.KEY_READ,
        )
        query_value.assert_called_once_with(
            key,
            startup_service.STARTUP_VALUE_NAME,
        )
        context.__exit__.assert_called_once()

    def test_is_startup_enabled_returns_false_for_blank_value(self):
        context, _ = self.make_context_key()
        winreg = self.make_winreg(
            open_key=Mock(return_value=context),
            query_value=Mock(
                return_value=("   ", 1)
            ),
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .is_startup_enabled()
            )

        self.assertFalse(result)

    def test_is_startup_enabled_handles_missing_registry_value(self):
        winreg = self.make_winreg(
            open_key=Mock(
                side_effect=FileNotFoundError
            )
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .is_startup_enabled()
            )

        self.assertFalse(result)

    def test_is_startup_enabled_handles_registry_error(self):
        context, _ = self.make_context_key()
        winreg = self.make_winreg(
            open_key=Mock(return_value=context),
            query_value=Mock(
                side_effect=OSError(
                    "registry unavailable"
                )
            ),
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .is_startup_enabled()
            )

        self.assertFalse(result)

    def test_set_startup_enabled_returns_false_outside_windows(self):
        with patch.object(
            startup_service.os,
            "name",
            "posix",
        ):
            result = (
                startup_service
                .set_startup_enabled(True)
            )

        self.assertFalse(result)

    def test_set_startup_enabled_writes_startup_command(self):
        context, key = self.make_context_key()
        set_value = Mock()
        winreg = self.make_winreg(
            create_key=Mock(return_value=context),
            set_value=set_value,
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.object(
                startup_service,
                "_get_startup_command",
                return_value='"C:\\Caspian\\Caspian.exe"',
            ) as get_command,
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(True)
            )

        self.assertTrue(result)
        winreg.CreateKeyEx.assert_called_once_with(
            winreg.HKEY_CURRENT_USER,
            startup_service.RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        )
        get_command.assert_called_once_with()
        set_value.assert_called_once_with(
            key,
            startup_service.STARTUP_VALUE_NAME,
            0,
            winreg.REG_SZ,
            '"C:\\Caspian\\Caspian.exe"',
        )
        winreg.DeleteValue.assert_not_called()
        context.__exit__.assert_called_once()

    def test_set_startup_disabled_deletes_registry_value(self):
        context, key = self.make_context_key()
        delete_value = Mock()
        winreg = self.make_winreg(
            create_key=Mock(return_value=context),
            delete_value=delete_value,
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(False)
            )

        self.assertTrue(result)
        delete_value.assert_called_once_with(
            key,
            startup_service.STARTUP_VALUE_NAME,
        )
        winreg.SetValueEx.assert_not_called()

    def test_set_startup_disabled_accepts_missing_registry_value(self):
        context, key = self.make_context_key()
        delete_value = Mock(
            side_effect=FileNotFoundError
        )
        winreg = self.make_winreg(
            create_key=Mock(return_value=context),
            delete_value=delete_value,
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(False)
            )

        self.assertTrue(result)
        delete_value.assert_called_once_with(
            key,
            startup_service.STARTUP_VALUE_NAME,
        )

    def test_set_startup_enabled_handles_create_key_error(self):
        winreg = self.make_winreg(
            create_key=Mock(
                side_effect=OSError(
                    "access denied"
                )
            )
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(True)
            )

        self.assertFalse(result)

    def test_set_startup_enabled_handles_write_error(self):
        context, _ = self.make_context_key()
        winreg = self.make_winreg(
            create_key=Mock(return_value=context),
            set_value=Mock(
                side_effect=OSError(
                    "write failed"
                )
            ),
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.object(
                startup_service,
                "_get_startup_command",
                return_value='"C:\\Caspian\\Caspian.exe"',
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(True)
            )

        self.assertFalse(result)

    def test_set_startup_disabled_handles_delete_error(self):
        context, _ = self.make_context_key()
        winreg = self.make_winreg(
            create_key=Mock(return_value=context),
            delete_value=Mock(
                side_effect=OSError(
                    "delete failed"
                )
            ),
        )

        with (
            patch.object(
                startup_service.os,
                "name",
                "nt",
            ),
            patch.dict(
                sys.modules,
                {
                    "winreg": winreg,
                },
            ),
        ):
            result = (
                startup_service
                .set_startup_enabled(False)
            )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
