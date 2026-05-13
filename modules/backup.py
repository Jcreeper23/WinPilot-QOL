from __future__ import annotations

import shutil
from pathlib import Path

from .utils import CONFIG_PATH, REPORT_DIR, ActionResult, is_admin, run_powershell, timestamp_for_filename


def create_restore_point(description: str = "WinPilot QOL restore point") -> ActionResult:
    if not is_admin():
        return ActionResult("Create Restore Point", False, "Creating restore points needs administrator permissions.")
    escaped = description.replace("'", "''")
    script = (
        f"Checkpoint-Computer -Description '{escaped}' "
        "-RestorePointType 'MODIFY_SETTINGS' -ErrorAction Stop"
    )
    result = run_powershell(script, timeout=120)
    if result.ok:
        return ActionResult("Create Restore Point", True, "Restore point created.")
    return ActionResult("Create Restore Point", False, "Could not create restore point.", result.stderr)


def get_restore_point_status() -> ActionResult:
    script = (
        "Get-ComputerRestorePoint | Sort-Object CreationTime -Descending | "
        "Select-Object -First 5 Description,CreationTime,RestorePointType | "
        "Format-Table -AutoSize | Out-String"
    )
    result = run_powershell(script, timeout=30)
    if result.ok:
        return ActionResult("Restore Points", True, result.stdout or "No restore points returned.")
    return ActionResult("Restore Points", False, "Could not read restore points.", result.stderr)


def open_system_restore() -> ActionResult:
    result = run_powershell("Start-Process SystemPropertiesProtection.exe", timeout=10)
    return ActionResult("System Restore", result.ok, "Opened System Protection.", result.stderr)


def backup_tool_settings() -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    destination = REPORT_DIR / f"config-backup-{timestamp_for_filename()}.json"
    if not CONFIG_PATH.exists():
        return ActionResult("Backup Settings", False, "No config file exists yet.")
    shutil.copy2(CONFIG_PATH, destination)
    return ActionResult("Backup Settings", True, "Tool settings backed up.", str(destination))


def restore_tool_settings(path: str | Path) -> ActionResult:
    source = Path(path)
    if not source.exists():
        return ActionResult("Restore Settings", False, "Backup file does not exist.")
    shutil.copy2(source, CONFIG_PATH)
    return ActionResult("Restore Settings", True, "Tool settings restored.")

