import os
import sys
from pathlib import Path


RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
STARTUP_VALUE_NAME = "CryptoDesk"
AUTOSTART_FILE_NAME = "cryptodesk.desktop"


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


def _get_autostart_file() -> Path:
    config_home = os.getenv("XDG_CONFIG_HOME")

    if config_home:
        base_dir = Path(config_home)
    else:
        base_dir = Path.home() / ".config"

    return (
        base_dir
        / "autostart"
        / AUTOSTART_FILE_NAME
    )


def _get_autostart_entry() -> str:
    return "\n".join(
        (
            "[Desktop Entry]",
            "Type=Application",
            "Version=1.0",
            "Name=CryptoDesk",
            "Comment=Kripto portföy takip uygulaması",
            f"Exec={_get_startup_command()}",
            "Terminal=false",
            "StartupNotify=false",
            "X-GNOME-Autostart-enabled=true",
            "",
        )
    )


def _is_windows_startup_enabled() -> bool:
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


def _set_windows_startup_enabled(
    enabled: bool,
) -> bool:
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


def _set_linux_startup_enabled(
    enabled: bool,
) -> bool:
    autostart_file = _get_autostart_file()

    try:
        if enabled:
            autostart_file.parent.mkdir(
                parents=True,
                exist_ok=True,
            )
            autostart_file.write_text(
                _get_autostart_entry(),
                encoding="utf-8",
            )
        else:
            autostart_file.unlink(
                missing_ok=True,
            )

        return True

    except OSError:
        return False


def is_startup_enabled() -> bool:
    if os.name == "nt":
        return _is_windows_startup_enabled()

    if os.name == "posix":
        return _get_autostart_file().is_file()

    return False


def set_startup_enabled(enabled: bool) -> bool:
    if os.name == "nt":
        return _set_windows_startup_enabled(
            enabled
        )

    if os.name == "posix":
        return _set_linux_startup_enabled(
            enabled
        )

    return False
