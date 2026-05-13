from __future__ import annotations

import ctypes
import winreg

from .utils import ActionResult, log_action, open_uri


EXPLORER_ADVANCED = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced"
PERSONALIZE = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"


def _get_dword(path: str, name: str, default: int) -> int:
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            value, _ = winreg.QueryValueEx(key, name)
            return int(value)
    except FileNotFoundError:
        return default
    except OSError:
        return default


def _set_dword(path: str, name: str, value: int) -> None:
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, path) as key:
        winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, int(value))


def _broadcast_setting_change() -> None:
    try:
        hwnd_broadcast = 0xFFFF
        wm_settingchange = 0x001A
        smto_abortifhung = 0x0002
        result = ctypes.c_ulong()
        ctypes.windll.user32.SendMessageTimeoutW(
            hwnd_broadcast,
            wm_settingchange,
            0,
            "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced",
            smto_abortifhung,
            2000,
            ctypes.byref(result),
        )
    except Exception:
        pass


def get_explorer_settings() -> dict:
    hidden = _get_dword(EXPLORER_ADVANCED, "Hidden", 2)
    hide_ext = _get_dword(EXPLORER_ADVANCED, "HideFileExt", 1)
    return {
        "show_hidden_files": hidden == 1,
        "show_file_extensions": hide_ext == 0,
    }


def set_hidden_files(show: bool) -> ActionResult:
    _set_dword(EXPLORER_ADVANCED, "Hidden", 1 if show else 2)
    _broadcast_setting_change()
    message = "Hidden files are set to show." if show else "Hidden files are set to hide."
    log_action("Hidden Files Toggle", message)
    return ActionResult("Hidden Files", True, message, "Restart Explorer if File Explorer does not refresh.")


def toggle_hidden_files() -> ActionResult:
    current = get_explorer_settings()["show_hidden_files"]
    return set_hidden_files(not current)


def set_file_extensions(show: bool) -> ActionResult:
    _set_dword(EXPLORER_ADVANCED, "HideFileExt", 0 if show else 1)
    _broadcast_setting_change()
    message = "File extensions are set to show." if show else "File extensions are set to hide."
    log_action("File Extensions Toggle", message)
    return ActionResult("File Extensions", True, message, "Restart Explorer if File Explorer does not refresh.")


def toggle_file_extensions() -> ActionResult:
    current = get_explorer_settings()["show_file_extensions"]
    return set_file_extensions(not current)


def get_windows_theme() -> str:
    apps_light = _get_dword(PERSONALIZE, "AppsUseLightTheme", 1)
    return "light" if apps_light else "dark"


def set_windows_theme(mode: str) -> ActionResult:
    normalized = mode.lower().strip()
    if normalized not in {"dark", "light"}:
        return ActionResult("Windows Theme", False, "Theme must be 'dark' or 'light'.")
    value = 1 if normalized == "light" else 0
    _set_dword(PERSONALIZE, "AppsUseLightTheme", value)
    _set_dword(PERSONALIZE, "SystemUsesLightTheme", value)
    _broadcast_setting_change()
    message = f"Windows theme set to {normalized}."
    log_action("Windows Theme", message)
    return ActionResult("Windows Theme", True, message)


def toggle_windows_theme() -> ActionResult:
    return set_windows_theme("dark" if get_windows_theme() == "light" else "light")


def open_night_light_settings() -> ActionResult:
    return open_uri("ms-settings:nightlight")


def open_bluetooth_settings() -> ActionResult:
    return open_uri("ms-settings:bluetooth")


def open_wifi_settings() -> ActionResult:
    return open_uri("ms-settings:network-wifi")


def open_focus_settings() -> ActionResult:
    return open_uri("ms-settings:quiethours")


def open_battery_saver_settings() -> ActionResult:
    return open_uri("ms-settings:batterysaver")


def open_settings_home() -> ActionResult:
    return open_uri("ms-settings:")

