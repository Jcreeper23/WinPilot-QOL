from __future__ import annotations

import getpass
import platform
import socket
import time
import winreg
from pathlib import Path

from .utils import human_bytes, is_admin, known_folder, run_command, run_powershell

try:
    import psutil
except ImportError:  # pragma: no cover - optional dependency fallback
    psutil = None

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency fallback
    requests = None


def _first_output_line(text: str) -> str:
    for line in text.splitlines():
        line = line.strip()
        if line:
            return line
    return "Unknown"


def _powershell_scalar(script: str, *, timeout: int = 8) -> str:
    result = run_powershell(script, timeout=timeout)
    if result.ok and result.stdout:
        return _first_output_line(result.stdout)
    return "Unknown"


def get_cpu_name() -> str:
    value = _powershell_scalar(
        "(Get-CimInstance Win32_Processor | Select-Object -First 1 -ExpandProperty Name)"
    )
    if value != "Unknown":
        return value
    return platform.processor() or "Unknown"


def get_gpu_names() -> str:
    script = (
        "Get-CimInstance Win32_VideoController | "
        "Where-Object {$_.Name} | Select-Object -ExpandProperty Name"
    )
    result = run_powershell(script, timeout=8)
    if result.ok and result.stdout:
        names = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        return ", ".join(names[:3]) if names else "Unknown"
    return "Unknown"


def get_windows_activation() -> str:
    script = (
        "$p = Get-CimInstance SoftwareLicensingProduct "
        "-Filter \"PartialProductKey IS NOT NULL\" | "
        "Where-Object {$_.Name -like '*Windows*'} | Select-Object -First 1; "
        "if ($p) { @('Unlicensed','Licensed','OOBGrace','OOTGrace','NonGenuineGrace',"
        "'Notification','ExtendedGrace')[$p.LicenseStatus] }"
    )
    return _powershell_scalar(script, timeout=10)


def get_power_plan() -> str:
    result = run_command(["powercfg", "/getactivescheme"], timeout=8)
    if result.ok and result.stdout:
        return result.stdout.replace("Power Scheme GUID:", "").strip()
    return "Unknown"


def get_local_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "Unknown"


def get_public_ip() -> str:
    if requests is None:
        return "requests not installed"
    try:
        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except Exception:
        return "Unavailable"


def is_internet_connected() -> bool:
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2).close()
        return True
    except OSError:
        return False


def get_storage_drives() -> list[dict]:
    drives: list[dict] = []
    if psutil is None:
        return drives

    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
        except (PermissionError, OSError):
            continue
        drives.append(
            {
                "device": part.device,
                "mountpoint": part.mountpoint,
                "fstype": part.fstype,
                "total": usage.total,
                "used": usage.used,
                "free": usage.free,
                "percent": usage.percent,
            }
        )
    return drives


def get_battery_status() -> dict:
    if psutil is None or not hasattr(psutil, "sensors_battery"):
        return {"present": False, "label": "No battery sensor"}
    battery = psutil.sensors_battery()
    if battery is None:
        return {"present": False, "label": "No battery detected"}
    plugged = "charging" if battery.power_plugged else "on battery"
    return {
        "present": True,
        "percent": battery.percent,
        "plugged": battery.power_plugged,
        "secsleft": battery.secsleft,
        "label": f"{battery.percent:.0f}% ({plugged})",
    }


def get_usage_snapshot() -> dict:
    if psutil is None:
        return {
            "cpu_percent": None,
            "ram_percent": None,
            "ram_used": None,
            "ram_total": None,
            "disk_percent": None,
            "network_sent": None,
            "network_recv": None,
        }

    memory = psutil.virtual_memory()
    root_disk = psutil.disk_usage(str(Path.home().anchor or "C:/"))
    net = psutil.net_io_counters()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "ram_percent": memory.percent,
        "ram_used": memory.used,
        "ram_total": memory.total,
        "disk_percent": root_disk.percent,
        "network_sent": net.bytes_sent,
        "network_recv": net.bytes_recv,
    }


def get_uptime() -> dict:
    if psutil is None:
        return {"boot_time": "Unknown", "uptime": "Unknown"}
    boot_epoch = psutil.boot_time()
    uptime_seconds = int(time.time() - boot_epoch)
    days, rem = divmod(uptime_seconds, 86400)
    hours, rem = divmod(rem, 3600)
    minutes, _ = divmod(rem, 60)
    uptime = f"{days}d {hours}h {minutes}m" if days else f"{hours}h {minutes}m"
    return {
        "boot_time": time.strftime("%Y-%m-%d %H:%M", time.localtime(boot_epoch)),
        "uptime": uptime,
    }


def pending_reboot() -> bool:
    key_paths = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"),
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager"),
    ]
    for hive, key_path in key_paths:
        try:
            with winreg.OpenKey(hive, key_path) as key:
                if key_path.endswith("Session Manager"):
                    try:
                        value, _ = winreg.QueryValueEx(key, "PendingFileRenameOperations")
                        if value:
                            return True
                    except FileNotFoundError:
                        continue
                else:
                    return True
        except FileNotFoundError:
            continue
        except PermissionError:
            continue
    return False


def get_system_overview(*, include_public_ip: bool = False) -> dict:
    usage = get_usage_snapshot()
    uptime = get_uptime()
    drives = get_storage_drives()
    battery = get_battery_status()
    memory_total = usage.get("ram_total")

    overview = {
        "pc_name": platform.node(),
        "windows_version": platform.platform(),
        "activation": get_windows_activation(),
        "cpu": get_cpu_name(),
        "gpu": get_gpu_names(),
        "ram": human_bytes(memory_total),
        "drives": drives,
        "battery": battery,
        "power_plan": get_power_plan(),
        "uptime": uptime["uptime"],
        "boot_time": uptime["boot_time"],
        "current_user": getpass.getuser(),
        "admin": is_admin(),
        "internet": is_internet_connected(),
        "local_ip": get_local_ip(),
        "public_ip": get_public_ip() if include_public_ip else "Click refresh",
        "usage": usage,
        "pending_reboot": pending_reboot(),
    }
    return overview


def get_health_cards(config: dict | None = None) -> list[dict]:
    cards: list[dict] = []
    usage = get_usage_snapshot()
    drives = get_storage_drives()
    battery = get_battery_status()

    for drive in drives:
        if drive["percent"] >= 90:
            cards.append(
                {
                    "level": "warning",
                    "title": "Low Disk Space",
                    "message": f"{drive['mountpoint']} is {drive['percent']:.0f}% full.",
                }
            )

    ram_percent = usage.get("ram_percent")
    if isinstance(ram_percent, (int, float)) and ram_percent >= 85:
        cards.append(
            {
                "level": "warning",
                "title": "High RAM Usage",
                "message": f"Memory usage is {ram_percent:.0f}%.",
            }
        )

    if battery.get("present") and not battery.get("plugged") and battery.get("percent", 100) < 20:
        cards.append(
            {
                "level": "warning",
                "title": "Battery Low",
                "message": f"Battery is at {battery.get('percent'):.0f}%.",
            }
        )

    if pending_reboot():
        cards.append(
            {
                "level": "info",
                "title": "Pending Restart",
                "message": "Windows has changes waiting for a reboot.",
            }
        )

    if not is_internet_connected():
        cards.append(
            {
                "level": "warning",
                "title": "Network Disconnected",
                "message": "The internet connection check failed.",
            }
        )

    temp_size = known_folder("temp")
    temp_bytes = 0
    try:
        from .utils import get_folder_size

        temp_bytes = get_folder_size(temp_size, limit_seconds=2)
    except Exception:
        temp_bytes = 0
    if temp_bytes >= 1024 * 1024 * 1024:
        cards.append(
            {
                "level": "info",
                "title": "Large Temp Folder",
                "message": f"User temp files are using about {human_bytes(temp_bytes)}.",
            }
        )

    if not cards:
        cards.append(
            {
                "level": "ok",
                "title": "No Major Issues",
                "message": "Quick health checks look good.",
            }
        )
    return cards

