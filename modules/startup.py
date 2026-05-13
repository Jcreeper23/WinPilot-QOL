from __future__ import annotations

import csv
import os
import winreg
from dataclasses import asdict, dataclass
from pathlib import Path

from .utils import REPORT_DIR, ActionResult, known_folder, open_path, timestamp_for_filename


@dataclass
class StartupEntry:
    name: str
    command: str
    source: str
    location: str
    enabled: bool = True
    impact: str = "Unknown"
    publisher: str = "Unknown"


REGISTRY_RUN_KEYS = [
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKCU", winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Run"),
    ("HKLM", winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\RunOnce"),
    (
        "HKLM32",
        winreg.HKEY_LOCAL_MACHINE,
        r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
    ),
]


def _read_run_key(hive_label: str, hive: int, path: str) -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    try:
        with winreg.OpenKey(hive, path) as key:
            index = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(key, index)
                except OSError:
                    break
                entries.append(
                    StartupEntry(
                        name=name,
                        command=str(value),
                        source="Registry",
                        location=f"{hive_label}\\{path}",
                    )
                )
                index += 1
    except FileNotFoundError:
        pass
    except PermissionError:
        pass
    return entries


def _folder_entries(folder: Path, source: str) -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    if not folder.exists():
        return entries
    for child in folder.iterdir():
        if child.is_file():
            entries.append(
                StartupEntry(
                    name=child.stem,
                    command=str(child),
                    source=source,
                    location=str(folder),
                )
            )
    return entries


def list_startup_apps() -> list[StartupEntry]:
    entries: list[StartupEntry] = []
    for hive_label, hive, path in REGISTRY_RUN_KEYS:
        entries.extend(_read_run_key(hive_label, hive, path))

    entries.extend(_folder_entries(known_folder("startup"), "Startup Folder"))
    all_users = Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")) / (
        "Microsoft/Windows/Start Menu/Programs/Startup"
    )
    entries.extend(_folder_entries(all_users, "All Users Startup Folder"))

    entries.sort(key=lambda item: item.name.lower())
    return entries


def export_startup_report() -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"startup-report-{timestamp_for_filename()}.csv"
    entries = list_startup_apps()
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(entries[0]).keys()) if entries else [
            "name",
            "command",
            "source",
            "location",
            "enabled",
            "impact",
            "publisher",
        ])
        writer.writeheader()
        for entry in entries:
            writer.writerow(asdict(entry))
    return ActionResult("Startup Report", True, f"Exported {len(entries)} entries.", str(path))


def open_user_startup_folder() -> ActionResult:
    return open_path(known_folder("startup"))

