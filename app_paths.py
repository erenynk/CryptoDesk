import os
from pathlib import Path


APP_NAME = "CryptoDesk"
IS_WINDOWS = os.name == "nt"


def get_app_data_dir() -> Path:
    if IS_WINDOWS:
        local_app_data = os.getenv("LOCALAPPDATA")

        if local_app_data:
            return Path(local_app_data) / APP_NAME

        return (
            Path.home()
            / "AppData"
            / "Local"
            / APP_NAME
        )

    xdg_data_home = os.getenv("XDG_DATA_HOME")

    if xdg_data_home:
        return Path(xdg_data_home) / APP_NAME

    return (
        Path.home()
        / ".local"
        / "share"
        / APP_NAME
    )
