from __future__ import annotations

import subprocess

from .utils import ActionResult, open_uri, run_powershell


def get_security_snapshot() -> dict:
    defender = run_powershell(
        "$s = Get-MpComputerStatus; "
        "[pscustomobject]@{"
        "RealTimeProtection=$s.RealTimeProtectionEnabled;"
        "AntivirusEnabled=$s.AntivirusEnabled;"
        "AntispywareEnabled=$s.AntispywareEnabled;"
        "NISEnabled=$s.NISEnabled"
        "} | ConvertTo-Json -Compress",
        timeout=20,
    )
    firewall = run_powershell(
        "Get-NetFirewallProfile | Select-Object Name,Enabled | ConvertTo-Json -Compress",
        timeout=15,
    )
    secure_boot = run_powershell(
        "try { Confirm-SecureBootUEFI } catch { 'Unavailable' }",
        timeout=10,
    )
    tpm = run_powershell(
        "try { (Get-Tpm).TpmPresent } catch { 'Unavailable' }",
        timeout=10,
    )
    return {
        "defender_raw": defender.stdout if defender.ok else defender.stderr,
        "firewall_raw": firewall.stdout if firewall.ok else firewall.stderr,
        "secure_boot": secure_boot.stdout.strip() if secure_boot.stdout else "Unknown",
        "tpm": tpm.stdout.strip() if tpm.stdout else "Unknown",
    }


def open_windows_security() -> ActionResult:
    return open_uri("windowsdefender:")


def run_defender_quick_scan() -> ActionResult:
    result = run_powershell("Start-MpScan -ScanType QuickScan", timeout=120)
    return ActionResult("Defender Quick Scan", result.ok, result.stdout or result.stderr or "Quick scan started.", result.stderr)


def update_defender_definitions() -> ActionResult:
    result = run_powershell("Update-MpSignature", timeout=180)
    return ActionResult("Defender Definitions", result.ok, result.stdout or result.stderr or "Definition update requested.", result.stderr)


def open_advanced_firewall() -> ActionResult:
    try:
        subprocess.Popen(["mmc.exe", "wf.msc"])
        return ActionResult("Advanced Firewall", True, "Opened advanced firewall.")
    except Exception as exc:
        return ActionResult("Advanced Firewall", False, "Could not open advanced firewall.", str(exc))
