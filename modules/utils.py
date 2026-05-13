from __future__ import annotations

import ctypes
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence


APP_NAME = "WinPilot QOL"
BASE_DIR = Path(__file__).resolve().parents[1]
LOG_DIR = BASE_DIR / "logs"
REPORT_DIR = BASE_DIR / "reports"
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG = {
    "theme": "dark",
    "accent_color": "#2f7df6",
    "launch_minimized": False,
    "close_to_tray": True,
    "beginner_mode": True,
    "confirm_risky_actions": True,
    "always_make_restore_point": False,
    "use_recycle_bin_by_default": True,
    "last_cleanup": None,
    "last_update_check": None,
}


@dataclass
class RunResult:
    command: str
    ok: bool
    stdout: str
    stderr: str
    returncode: int


@dataclass
class ActionResult:
    title: str
    ok: bool
    message: str
    details: str = ""


def ensure_app_dirs() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)


def setup_logging() -> logging.Logger:
    ensure_app_dirs()
    logger = logging.getLogger(APP_NAME)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
        )
        file_handler = logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    return logger


logger = setup_logging()


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG.copy())
        return DEFAULT_CONFIG.copy()

    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Config could not be read; using defaults.")
        return DEFAULT_CONFIG.copy()

    merged = DEFAULT_CONFIG.copy()
    merged.update(data)
    return merged


def save_config(config: dict) -> None:
    ensure_app_dirs()
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")


def is_windows() -> bool:
    return platform.system().lower() == "windows"


def is_admin() -> bool:
    if not is_windows():
        return os.geteuid() == 0 if hasattr(os, "geteuid") else False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def human_bytes(num: int | float | None) -> str:
    if num is None:
        return "Unknown"
    try:
        value = float(num)
    except (TypeError, ValueError):
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0:
            return f"{value:3.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def short_bool(value: bool | None) -> str:
    if value is None:
        return "Unknown"
    return "Yes" if value else "No"


def run_command(
    command: Sequence[str] | str,
    *,
    timeout: int = 60,
    shell: bool = False,
    cwd: Path | str | None = None,
) -> RunResult:
    command_text = command if isinstance(command, str) else " ".join(command)
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=shell,
            cwd=str(cwd) if cwd else None,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError as exc:
        return RunResult(command_text, False, "", str(exc), 127)
    except subprocess.TimeoutExpired as exc:
        return RunResult(command_text, False, exc.stdout or "", "Command timed out", 124)
    except Exception as exc:
        return RunResult(command_text, False, "", str(exc), 1)

    return RunResult(
        command_text,
        completed.returncode == 0,
        completed.stdout.strip(),
        completed.stderr.strip(),
        completed.returncode,
    )


def run_powershell(script: str, *, timeout: int = 60) -> RunResult:
    return run_command(
        [
            "powershell",
            "-NoLogo",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            script,
        ],
        timeout=timeout,
    )


def command_exists(command: str) -> bool:
    return shutil.which(command) is not None


def open_path(path: str | Path) -> ActionResult:
    try:
        os.startfile(str(path))  # type: ignore[attr-defined]
        return ActionResult("Open path", True, f"Opened {path}")
    except Exception as exc:
        return ActionResult("Open path", False, f"Could not open {path}", str(exc))


def open_uri(uri: str) -> ActionResult:
    try:
        os.startfile(uri)  # type: ignore[attr-defined]
        return ActionResult("Open link", True, f"Opened {uri}")
    except Exception as exc:
        return ActionResult("Open link", False, f"Could not open {uri}", str(exc))


def known_folder(name: str) -> Path:
    home = Path.home()
    folders = {
        "home": home,
        "desktop": home / "Desktop",
        "downloads": home / "Downloads",
        "documents": home / "Documents",
        "pictures": home / "Pictures",
        "videos": home / "Videos",
        "music": home / "Music",
        "appdata": Path(os.environ.get("APPDATA", home / "AppData" / "Roaming")),
        "localappdata": Path(os.environ.get("LOCALAPPDATA", home / "AppData" / "Local")),
        "programdata": Path(os.environ.get("PROGRAMDATA", "C:/ProgramData")),
        "temp": Path(os.environ.get("TEMP", home / "AppData" / "Local" / "Temp")),
        "startup": Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
        / "Microsoft"
        / "Windows"
        / "Start Menu"
        / "Programs"
        / "Startup",
    }
    return folders[name.lower()]


def get_folder_size(path: Path, *, limit_seconds: float | None = None) -> int:
    start = time.monotonic()
    total = 0
    if not path.exists():
        return 0
    for root, _, files in os.walk(path, onerror=lambda _: None):
        if limit_seconds and time.monotonic() - start > limit_seconds:
            break
        for file_name in files:
            file_path = Path(root) / file_name
            try:
                total += file_path.stat().st_size
            except OSError:
                continue
    return total


def safe_unlink(path: Path) -> tuple[bool, str]:
    try:
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=False)
        else:
            path.unlink(missing_ok=True)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def delete_directory_contents(path: Path) -> tuple[int, int, list[str]]:
    deleted = 0
    failed = 0
    errors: list[str] = []
    if not path.exists() or not path.is_dir():
        return deleted, failed, errors

    for child in path.iterdir():
        ok, error = safe_unlink(child)
        if ok:
            deleted += 1
        else:
            failed += 1
            errors.append(f"{child}: {error}")
    return deleted, failed, errors[:20]


def log_action(title: str, message: str, *, ok: bool = True) -> None:
    if ok:
        logger.info("%s | %s", title, message)
    else:
        logger.warning("%s | %s", title, message)


def timestamp_for_filename() -> str:
    return time.strftime("%Y%m%d-%H%M%S")

