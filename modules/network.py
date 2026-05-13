from __future__ import annotations

import re
import socket
from dataclasses import dataclass

from .cleanup import flush_dns
from .utils import ActionResult, human_bytes, is_admin, open_uri, run_command, run_powershell

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


DNS_PRESETS = {
    "cloudflare": ("1.1.1.1", "1.0.0.1"),
    "google": ("8.8.8.8", "8.8.4.4"),
    "quad9": ("9.9.9.9", "149.112.112.112"),
}


@dataclass
class AdapterInfo:
    name: str
    ipv4: str = ""
    mac: str = ""
    speed_mbps: int = 0
    is_up: bool = False
    sent: int = 0
    received: int = 0


def get_public_ip() -> str:
    try:
        import requests

        return requests.get("https://api.ipify.org", timeout=3).text.strip()
    except Exception:
        return "Unavailable"


def get_default_gateway() -> str:
    result = run_powershell(
        "Get-NetRoute -DestinationPrefix '0.0.0.0/0' | "
        "Sort-Object RouteMetric | Select-Object -First 1 -ExpandProperty NextHop",
        timeout=8,
    )
    return result.stdout.strip() if result.ok and result.stdout else "Unknown"


def get_dns_servers() -> list[str]:
    result = run_powershell(
        "Get-DnsClientServerAddress -AddressFamily IPv4 | "
        "ForEach-Object { $_.ServerAddresses }",
        timeout=8,
    )
    if not result.ok:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def get_adapters() -> list[AdapterInfo]:
    if psutil is None:
        return []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    counters = psutil.net_io_counters(pernic=True)
    adapters: list[AdapterInfo] = []
    for name, addresses in addrs.items():
        adapter = AdapterInfo(name=name)
        for addr in addresses:
            if addr.family == socket.AF_INET:
                adapter.ipv4 = addr.address
            elif str(addr.family).endswith("AF_LINK") or getattr(socket, "AF_LINK", None) == addr.family:
                adapter.mac = addr.address
        if name in stats:
            adapter.is_up = stats[name].isup
            adapter.speed_mbps = stats[name].speed
        if name in counters:
            adapter.sent = counters[name].bytes_sent
            adapter.received = counters[name].bytes_recv
        if adapter.ipv4 or adapter.is_up:
            adapters.append(adapter)
    return sorted(adapters, key=lambda item: (not item.is_up, item.name.lower()))


def get_network_summary(include_public_ip: bool = False) -> dict:
    adapters = get_adapters()
    active = next((adapter for adapter in adapters if adapter.is_up and adapter.ipv4), None)
    return {
        "local_ip": active.ipv4 if active else "Unknown",
        "public_ip": get_public_ip() if include_public_ip else "Click refresh",
        "gateway": get_default_gateway(),
        "dns_servers": get_dns_servers(),
        "adapters": adapters,
    }


def ping_host(host: str = "1.1.1.1", count: int = 4) -> ActionResult:
    safe_host = host.strip() or "1.1.1.1"
    result = run_command(["ping", "-n", str(count), safe_host], timeout=30)
    ok = result.ok
    message = result.stdout or result.stderr
    return ActionResult(f"Ping {safe_host}", ok, message, result.stderr)


def renew_ip() -> ActionResult:
    result = run_command(["ipconfig", "/renew"], timeout=90)
    return ActionResult("Renew IP", result.ok, result.stdout or result.stderr, result.stderr)


def release_ip() -> ActionResult:
    result = run_command(["ipconfig", "/release"], timeout=60)
    return ActionResult("Release IP", result.ok, result.stdout or result.stderr, result.stderr)


def reset_winsock() -> ActionResult:
    if not is_admin():
        return ActionResult("Reset Winsock", False, "Reset Winsock needs administrator permissions.")
    result = run_command(["netsh", "winsock", "reset"], timeout=30)
    return ActionResult("Reset Winsock", result.ok, result.stdout or result.stderr, result.stderr)


def reset_tcp_ip() -> ActionResult:
    if not is_admin():
        return ActionResult("Reset TCP/IP", False, "Reset TCP/IP needs administrator permissions.")
    result = run_command(["netsh", "int", "ip", "reset"], timeout=30)
    return ActionResult("Reset TCP/IP", result.ok, result.stdout or result.stderr, result.stderr)


def set_dns(adapter_name: str, preset: str) -> ActionResult:
    if not is_admin():
        return ActionResult("Set DNS", False, "Changing DNS needs administrator permissions.")
    preset_lower = preset.lower()
    if preset_lower == "automatic":
        script = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ResetServerAddresses"
    else:
        servers = DNS_PRESETS.get(preset_lower)
        if not servers:
            return ActionResult("Set DNS", False, f"Unknown DNS preset: {preset}")
        quoted = ",".join(f"'{server}'" for server in servers)
        script = f"Set-DnsClientServerAddress -InterfaceAlias '{adapter_name}' -ServerAddresses ({quoted})"
    result = run_powershell(script, timeout=20)
    return ActionResult("Set DNS", result.ok, result.stdout or result.stderr or "DNS updated.", result.stderr)


def list_wifi_profiles() -> list[str]:
    result = run_command(["netsh", "wlan", "show", "profiles"], timeout=20)
    if not result.ok:
        return []
    profiles = []
    for line in result.stdout.splitlines():
        match = re.search(r"All User Profile\s*:\s*(.+)$", line)
        if match:
            profiles.append(match.group(1).strip())
    return profiles


def open_network_settings() -> ActionResult:
    return open_uri("ms-settings:network")


def open_firewall_settings() -> ActionResult:
    return open_uri("windowsdefender://network")


def format_adapter(adapter: AdapterInfo) -> str:
    state = "up" if adapter.is_up else "down"
    traffic = f"{human_bytes(adapter.received)} down / {human_bytes(adapter.sent)} up"
    return f"{adapter.name} | {state} | {adapter.ipv4 or 'no IPv4'} | {adapter.speed_mbps} Mbps | {traffic}"

