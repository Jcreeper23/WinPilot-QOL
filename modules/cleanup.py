from __future__ import annotations

import ctypes
import os
from dataclasses import dataclass
from pathlib import Path

from .utils import (
    ActionResult,
    delete_directory_contents,
    get_folder_size,
    human_bytes,
    is_admin,
    known_folder,
    load_config,
    log_action,
    run_command,
    save_config,
)


@dataclass
class CleanupTarget:
    key: str
    title: str
    path: Path | None
    size: int
    safe: bool
    needs_admin: bool = False
    note: str = ""


def _path_from_env(name: str, fallback: str) -> Path:
    return Path(os.environ.get(name, fallback))


def get_cleanup_targets() -> list[CleanupTarget]:
    local_appdata = known_folder("localappdata")
    targets = [
        CleanupTarget(
            "user_temp",
            "User temp files",
            known_folder("temp"),
            0,
            True,
            note="Clears files apps left in your user temp folder.",
        ),
        CleanupTarget(
            "windows_temp",
            "Windows temp files",
            Path(os.environ.get("WINDIR", "C:/Windows")) / "Temp",
            0,
            True,
            needs_admin=True,
            note="May skip locked system files.",
        ),
        CleanupTarget(
            "directx_shader",
            "DirectX shader cache",
            local_appdata / "D3DSCache",
            0,
            True,
            note="Games and apps can rebuild this cache.",
        ),
        CleanupTarget(
            "thumbnail_cache",
            "Thumbnail cache",
            local_appdata / "Microsoft" / "Windows" / "Explorer",
            0,
            True,
            note="Windows may recreate thumbnail databases.",
        ),
        CleanupTarget(
            "crash_dumps",
            "Crash dumps",
            local_appdata / "CrashDumps",
            0,
            True,
            note="Removes old app crash dumps.",
        ),
        CleanupTarget(
            "wer_reports",
            "Windows error reports",
            Path(os.environ.get("PROGRAMDATA", "C:/ProgramData"))
            / "Microsoft"
            / "Windows"
            / "WER",
            0,
            True,
            needs_admin=True,
            note="Removes old Windows Error Reporting files.",
        ),
        CleanupTarget(
            "store_cache",
            "Microsoft Store cache launcher",
            None,
            0,
            True,
            note="Uses wsreset when run.",
        ),
        CleanupTarget(
            "dns_cache",
            "DNS cache",
            None,
            0,
            True,
            note="Runs ipconfig /flushdns.",
        ),
    ]
    return targets


def preview_cleanup() -> list[CleanupTarget]:
    targets = get_cleanup_targets()
    for target in targets:
        if target.path is None:
            continue
        if target.key == "thumbnail_cache":
            target.size = _matching_files_size(target.path, "thumbcache_*.db")
        else:
            target.size = get_folder_size(target.path, limit_seconds=5)
    return targets


def _matching_files_size(path: Path, pattern: str) -> int:
    if not path.exists():
        return 0
    total = 0
    for file_path in path.glob(pattern):
        try:
            total += file_path.stat().st_size
        except OSError:
            continue
    return total


def _delete_matching(path: Path, pattern: str) -> tuple[int, int, list[str]]:
    deleted = 0
    failed = 0
    errors: list[str] = []
    if not path.exists():
        return deleted, failed, errors
    for file_path in path.glob(pattern):
        try:
            file_path.unlink(missing_ok=True)
            deleted += 1
        except Exception as exc:
            failed += 1
            errors.append(f"{file_path}: {exc}")
    return deleted, failed, errors[:20]


def empty_recycle_bin() -> ActionResult:
    try:
        flags = 0x00000001 | 0x00000002 | 0x00000004
        result = ctypes.windll.shell32.SHEmptyRecycleBinW(None, None, flags)
        ok = result == 0
        message = "Recycle Bin emptied." if ok else f"Recycle Bin returned code {result}."
        log_action("Empty Recycle Bin", message, ok=ok)
        return ActionResult("Empty Recycle Bin", ok, message)
    except Exception as exc:
        return ActionResult("Empty Recycle Bin", False, "Could not empty Recycle Bin.", str(exc))


def flush_dns() -> ActionResult:
    result = run_command(["ipconfig", "/flushdns"], timeout=20)
    ok = result.ok
    message = result.stdout or result.stderr or "DNS flush finished."
    log_action("Flush DNS", message, ok=ok)
    return ActionResult("Flush DNS", ok, message, result.stderr)


def clear_clipboard() -> ActionResult:
    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.clipboard_clear()
        root.update()
        root.destroy()
        log_action("Clear Clipboard", "Clipboard cleared.")
        return ActionResult("Clear Clipboard", True, "Clipboard cleared.")
    except Exception as exc:
        return ActionResult("Clear Clipboard", False, "Could not clear clipboard.", str(exc))


def run_wsreset() -> ActionResult:
    result = run_command(["wsreset.exe"], timeout=5)
    ok = result.ok or result.returncode == 124
    message = "Microsoft Store reset started." if ok else result.stderr or "Could not start wsreset."
    log_action("Microsoft Store Reset", message, ok=ok)
    return ActionResult("Microsoft Store Reset", ok, message, result.stderr)


def clear_target(target: CleanupTarget) -> ActionResult:
    if target.needs_admin and not is_admin():
        return ActionResult(
            target.title,
            False,
            f"{target.title} needs administrator permissions.",
            "Restart WinPilot QOL as administrator to run this cleanup.",
        )
    if target.key == "dns_cache":
        return flush_dns()
    if target.key == "store_cache":
        return run_wsreset()
    if target.path is None:
        return ActionResult(target.title, False, "This cleanup target has no path.")
    if target.key == "thumbnail_cache":
        deleted, failed, errors = _delete_matching(target.path, "thumbcache_*.db")
    else:
        deleted, failed, errors = delete_directory_contents(target.path)

    ok = failed == 0
    message = f"Deleted {deleted} item(s); {failed} failed."
    log_action(target.title, message, ok=ok)
    return ActionResult(target.title, ok, message, "\n".join(errors))


def quick_cleanup(include_recycle_bin: bool = True) -> list[ActionResult]:
    results: list[ActionResult] = []
    targets = preview_cleanup()
    for target in targets:
        if target.safe:
            results.append(clear_target(target))
    if include_recycle_bin:
        results.append(empty_recycle_bin())

    config = load_config()
    from datetime import datetime

    config["last_cleanup"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_config(config)
    return results


def cleanup_summary_text(targets: list[CleanupTarget]) -> str:
    total = sum(target.size for target in targets)
    lines = [f"Estimated cleanup space: {human_bytes(total)}", ""]
    for target in targets:
        label = human_bytes(target.size) if target.path else "Action"
        admin = " | admin" if target.needs_admin else ""
        lines.append(f"- {target.title}: {label}{admin}")
    return "\n".join(lines)

