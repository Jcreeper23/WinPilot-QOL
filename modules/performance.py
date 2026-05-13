from __future__ import annotations

import ctypes
import re
import subprocess

from .utils import ActionResult, is_admin, log_action, open_uri, run_command, run_powershell


POWER_PLAN_ALIASES = {
    "balanced": "SCHEME_BALANCED",
    "high performance": "SCHEME_MIN",
    "power saver": "SCHEME_MAX",
}


def restart_explorer() -> ActionResult:
    stop = run_command(["taskkill", "/f", "/im", "explorer.exe"], timeout=20)
    try:
        subprocess.Popen(["explorer.exe"])
        ok = True
    except Exception as exc:
        return ActionResult("Restart Explorer", False, "Explorer was stopped but could not restart.", str(exc))
    message = "Windows Explorer restarted."
    details = stop.stderr if stop.stderr else ""
    log_action("Restart Explorer", message, ok=ok)
    return ActionResult("Restart Explorer", ok, message, details)


def open_task_manager() -> ActionResult:
    try:
        subprocess.Popen(["taskmgr.exe"])
        return ActionResult("Task Manager", True, "Opened Task Manager.")
    except Exception as exc:
        return ActionResult("Task Manager", False, "Could not open Task Manager.", str(exc))


def open_resource_monitor() -> ActionResult:
    try:
        subprocess.Popen(["resmon.exe"])
        return ActionResult("Resource Monitor", True, "Opened Resource Monitor.")
    except Exception as exc:
        return ActionResult("Resource Monitor", False, "Could not open Resource Monitor.", str(exc))


def open_performance_monitor() -> ActionResult:
    try:
        subprocess.Popen(["perfmon.exe"])
        return ActionResult("Performance Monitor", True, "Opened Performance Monitor.")
    except Exception as exc:
        return ActionResult("Performance Monitor", False, "Could not open Performance Monitor.", str(exc))


def get_power_plans() -> list[dict]:
    result = run_command(["powercfg", "/list"], timeout=12)
    plans: list[dict] = []
    if not result.ok:
        return plans
    pattern = re.compile(r"Power Scheme GUID:\s+([a-f0-9-]+)\s+\((.+?)\)(\s+\*)?", re.I)
    for line in result.stdout.splitlines():
        match = pattern.search(line)
        if match:
            plans.append(
                {
                    "guid": match.group(1),
                    "name": match.group(2),
                    "active": bool(match.group(3)),
                }
            )
    return plans


def set_power_plan(plan_name_or_guid: str) -> ActionResult:
    requested = plan_name_or_guid.strip()
    alias = POWER_PLAN_ALIASES.get(requested.lower(), requested)
    plans = get_power_plans()
    selected_guid = None

    if re.fullmatch(r"[a-fA-F0-9-]{36}", requested):
        selected_guid = requested
    else:
        for plan in plans:
            if plan["name"].lower() == requested.lower():
                selected_guid = plan["guid"]
                break

    if selected_guid is None and alias.startswith("SCHEME_"):
        selected_guid = alias
    if selected_guid is None:
        return ActionResult("Power Plan", False, f"Power plan not found: {plan_name_or_guid}")

    result = run_command(["powercfg", "/setactive", selected_guid], timeout=12)
    ok = result.ok
    message = f"Switched power plan to {plan_name_or_guid}." if ok else result.stderr
    log_action("Power Plan", message, ok=ok)
    return ActionResult("Power Plan", ok, message, result.stderr)


def enable_ultimate_performance() -> ActionResult:
    result = run_command(
        ["powercfg", "-duplicatescheme", "e9a42b02-d5df-448d-aa00-03f14749eb61"],
        timeout=12,
    )
    if not result.ok and "already exists" not in result.stderr.lower():
        return ActionResult("Ultimate Performance", False, "Could not create Ultimate Performance plan.", result.stderr)
    return set_power_plan("Ultimate Performance")


def restart_service(service_name: str, display_name: str | None = None) -> ActionResult:
    if not is_admin():
        return ActionResult(
            display_name or service_name,
            False,
            "Restarting this service needs administrator permissions.",
        )
    result = run_powershell(
        f"Restart-Service -Name '{service_name}' -Force -ErrorAction Stop",
        timeout=30,
    )
    ok = result.ok
    title = display_name or service_name
    message = f"{title} restarted." if ok else result.stderr
    log_action(f"Restart {title}", message, ok=ok)
    return ActionResult(f"Restart {title}", ok, message, result.stderr)


def restart_audio_service() -> ActionResult:
    return restart_service("Audiosrv", "Windows Audio")


def restart_print_spooler() -> ActionResult:
    return restart_service("Spooler", "Print Spooler")


def restart_windows_update_service() -> ActionResult:
    return restart_service("wuauserv", "Windows Update")


def lock_pc() -> ActionResult:
    try:
        ok = bool(ctypes.windll.user32.LockWorkStation())
        return ActionResult("Lock PC", ok, "PC lock requested." if ok else "Could not lock PC.")
    except Exception as exc:
        return ActionResult("Lock PC", False, "Could not lock PC.", str(exc))


def sleep_pc() -> ActionResult:
    result = run_command(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], timeout=5)
    ok = result.ok or result.returncode == 0
    return ActionResult("Sleep PC", ok, "Sleep requested.", result.stderr)


def restart_pc(delay_seconds: int = 60) -> ActionResult:
    result = run_command(
        [
            "shutdown",
            "/r",
            "/t",
            str(delay_seconds),
            "/c",
            "Restart scheduled by WinPilot QOL. Run shutdown /a to cancel.",
        ],
        timeout=10,
    )
    return ActionResult("Restart PC", result.ok, result.stdout or result.stderr, result.stderr)


def shutdown_pc(delay_seconds: int = 60) -> ActionResult:
    result = run_command(
        [
            "shutdown",
            "/s",
            "/t",
            str(delay_seconds),
            "/c",
            "Shutdown scheduled by WinPilot QOL. Run shutdown /a to cancel.",
        ],
        timeout=10,
    )
    return ActionResult("Shut Down PC", result.ok, result.stdout or result.stderr, result.stderr)


def abort_power_action() -> ActionResult:
    result = run_command(["shutdown", "/a"], timeout=10)
    return ActionResult("Cancel Shutdown", result.ok, result.stdout or result.stderr, result.stderr)


def open_power_settings() -> ActionResult:
    return open_uri("ms-settings:powersleep")


def open_startup_apps() -> ActionResult:
    return open_uri("ms-settings:startupapps")

