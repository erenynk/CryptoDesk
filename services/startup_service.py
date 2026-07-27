import os
import sys
from pathlib import Path


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "CryptoDesk"


def _get_python_executable() -> Path:
    executable = Path(sys.executable)

    if executable.name.lower() == "python.exe":
        pythonw = executable.with_name("pythonw.exe")

        if pythonw.exists():
            return pythonw

    return executable


def _get_startup_command() -> str:
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'

    project_root = Path(__file__).resolve().parent.parent
    app_path = project_root / "app.py"
    executable = _get_python_executable()

    return f'"{executable}" "{app_path}"'


def is_startup_enabled() -> bool:
    if os.name != "nt":
        return False

    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_READ,
        ) as key:
            value, _ = winreg.QueryValueEx(
                key,
                STARTUP_VALUE_NAME,
            )

        return bool(str(value).strip())

    except (FileNotFoundError, OSError):
        return False


def set_startup_enabled(enabled: bool) -> bool:
    if os.name != "nt":
        return False

    try:
        import winreg

        with winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER,
            RUN_KEY_PATH,
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(
                    key,
                    STARTUP_VALUE_NAME,
                    0,
                    winreg.REG_SZ,
                    _get_startup_command(),
                )
            else:
                try:
                    winreg.DeleteValue(
                        key,
                        STARTUP_VALUE_NAME,
                    )
                except FileNotFoundError:
                    pass

        return True

    except OSError:
        return False
