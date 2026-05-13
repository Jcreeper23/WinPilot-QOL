from __future__ import annotations

import csv
import re
import subprocess
import winreg
from dataclasses import asdict, dataclass
from pathlib import Path

from .utils import REPORT_DIR, ActionResult, human_bytes, open_path, timestamp_for_filename


@dataclass
class InstalledApp:
    name: str
    version: str = ""
    publisher: str = ""
    install_date: str = ""
    size_bytes: int = 0
    install_location: str = ""
    uninstall_string: str = ""
    registry_location: str = ""


UNINSTALL_KEYS = [
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    (
        "HKLM32",
        winreg.HKEY_LOCAL_MACHINE,
        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
    ),
]


COMMON_BLOAT_HINTS = {
    "clipchamp",
    "feedback hub",
    "mixed reality",
    "solitaire",
    "candy crush",
    "people",
    "tips",
}


def _read_string(key, name: str) -> str:
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value)
    except OSError:
        return ""


def _read_int(key, name: str) -> int:
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return int(value)
    except OSError:
        return 0


def _format_install_date(value: str) -> str:
    if re.fullmatch(r"\d{8}", value):
        return f"{value[0:4]}-{value[4:6]}-{value[6:8]}"
    return value


def _read_uninstall_key(hive_label: str, hive: int, path: str) -> list[InstalledApp]:
    apps: list[InstalledApp] = []
    try:
        with winreg.OpenKey(hive, path) as parent:
            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(parent, index)
                except OSError:
                    break
                index += 1
                try:
                    with winreg.OpenKey(parent, subkey_name) as key:
                        name = _read_string(key, "DisplayName")
                        if not name:
                            continue
                        size_kb = _read_int(key, "EstimatedSize")
                        apps.append(
                            InstalledApp(
                                name=name,
                                version=_read_string(key, "DisplayVersion"),
                                publisher=_read_string(key, "Publisher"),
                                install_date=_format_install_date(_read_string(key, "InstallDate")),
                                size_bytes=size_kb * 1024,
                                install_location=_read_string(key, "InstallLocation"),
                                uninstall_string=_read_string(key, "QuietUninstallString")
                                or _read_string(key, "UninstallString"),
                                registry_location=f"{hive_label}\\{path}\\{subkey_name}",
                            )
                        )
                except OSError:
                    continue
    except FileNotFoundError:
        pass
    except PermissionError:
        pass
    return apps


def list_installed_apps() -> list[InstalledApp]:
    by_key: dict[tuple[str, str], InstalledApp] = {}
    for hive_label, hive, path in UNINSTALL_KEYS:
        for app in _read_uninstall_key(hive_label, hive, path):
            key = (app.name.lower(), app.version.lower())
            existing = by_key.get(key)
            if existing is None or (not existing.size_bytes and app.size_bytes):
                by_key[key] = app
    return sorted(by_key.values(), key=lambda item: item.name.lower())


def detect_bloatware(apps: list[InstalledApp] | None = None) -> list[InstalledApp]:
    apps = apps or list_installed_apps()
    matches = []
    for app in apps:
        lower = app.name.lower()
        if any(hint in lower for hint in COMMON_BLOAT_HINTS):
            matches.append(app)
    return matches


def detect_large_apps(min_size_bytes: int = 1024 * 1024 * 1024) -> list[InstalledApp]:
    return [app for app in list_installed_apps() if app.size_bytes >= min_size_bytes]


def export_installed_apps_report() -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"installed-apps-{timestamp_for_filename()}.csv"
    apps = list_installed_apps()
    base_fields = list(asdict(apps[0]).keys()) if apps else [
            "name",
            "version",
            "publisher",
            "install_date",
            "size_bytes",
            "install_location",
            "uninstall_string",
            "registry_location",
        ]
    fieldnames = base_fields + ["size_human"]
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        for app in apps:
            row = asdict(app)
            row["size_human"] = human_bytes(app.size_bytes)
            writer.writerow(row)
    return ActionResult("Installed Apps Report", True, f"Exported {len(apps)} apps.", str(path))


def open_install_location(app: InstalledApp) -> ActionResult:
    if app.install_location and Path(app.install_location).exists():
        return open_path(app.install_location)
    return ActionResult("Install Location", False, "Install location is unavailable.")


def run_uninstaller(app: InstalledApp) -> ActionResult:
    if not app.uninstall_string:
        return ActionResult("Uninstall App", False, f"No uninstall command found for {app.name}.")
    try:
        subprocess.Popen(app.uninstall_string, shell=True)
        return ActionResult("Uninstall App", True, f"Started uninstaller for {app.name}.")
    except Exception as exc:
        return ActionResult("Uninstall App", False, f"Could not start uninstaller for {app.name}.", str(exc))
