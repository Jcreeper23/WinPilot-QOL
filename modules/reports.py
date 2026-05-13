from __future__ import annotations

import json
from pathlib import Path

from . import apps, network, startup, system_info
from .utils import REPORT_DIR, ActionResult, human_bytes, load_config, timestamp_for_filename


def build_health_report() -> dict:
    overview = system_info.get_system_overview(include_public_ip=False)
    usage = overview["usage"]
    drives = [
        {
            "device": drive["device"],
            "mountpoint": drive["mountpoint"],
            "total": human_bytes(drive["total"]),
            "used": human_bytes(drive["used"]),
            "free": human_bytes(drive["free"]),
            "percent": drive["percent"],
        }
        for drive in overview["drives"]
    ]
    installed_apps = apps.list_installed_apps()
    startup_entries = startup.list_startup_apps()
    net = network.get_network_summary(include_public_ip=False)
    return {
        "app": "WinPilot QOL",
        "config": load_config(),
        "system": {
            "pc_name": overview["pc_name"],
            "windows_version": overview["windows_version"],
            "activation": overview["activation"],
            "cpu": overview["cpu"],
            "gpu": overview["gpu"],
            "ram": overview["ram"],
            "power_plan": overview["power_plan"],
            "uptime": overview["uptime"],
            "boot_time": overview["boot_time"],
            "current_user": overview["current_user"],
            "admin": overview["admin"],
            "internet": overview["internet"],
            "local_ip": overview["local_ip"],
            "pending_reboot": overview["pending_reboot"],
        },
        "usage": {
            "cpu_percent": usage.get("cpu_percent"),
            "ram_percent": usage.get("ram_percent"),
            "ram_used": human_bytes(usage.get("ram_used")),
            "ram_total": human_bytes(usage.get("ram_total")),
            "disk_percent": usage.get("disk_percent"),
        },
        "drives": drives,
        "health_cards": system_info.get_health_cards(),
        "counts": {
            "installed_apps": len(installed_apps),
            "startup_entries": len(startup_entries),
            "network_adapters": len(net["adapters"]),
        },
        "network": {
            "local_ip": net["local_ip"],
            "gateway": net["gateway"],
            "dns_servers": net["dns_servers"],
        },
    }


def export_health_report_json() -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"pc-health-{timestamp_for_filename()}.json"
    data = build_health_report()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ActionResult("Health Report JSON", True, "Exported health report.", str(path))


def export_health_report_markdown() -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"pc-health-{timestamp_for_filename()}.md"
    data = build_health_report()
    lines = [
        "# WinPilot QOL PC Health Report",
        "",
        "## System",
    ]
    for key, value in data["system"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")

    lines.extend(["", "## Usage"])
    for key, value in data["usage"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")

    lines.extend(["", "## Drives"])
    for drive in data["drives"]:
        lines.append(
            f"- **{drive['mountpoint']}**: {drive['used']} used / "
            f"{drive['total']} total ({drive['percent']}%)"
        )

    lines.extend(["", "## Health Cards"])
    for card in data["health_cards"]:
        lines.append(f"- **{card['title']}** [{card['level']}]: {card['message']}")

    lines.extend(["", "## Counts"])
    for key, value in data["counts"].items():
        lines.append(f"- **{key.replace('_', ' ').title()}**: {value}")

    path.write_text("\n".join(lines), encoding="utf-8")
    return ActionResult("Health Report Markdown", True, "Exported health report.", str(path))


def open_reports_folder() -> ActionResult:
    from .utils import open_path

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    return open_path(REPORT_DIR)

