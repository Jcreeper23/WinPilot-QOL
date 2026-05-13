from __future__ import annotations

from datetime import datetime

from .utils import (
    ActionResult,
    command_exists,
    load_config,
    log_action,
    open_uri,
    run_command,
    run_powershell,
    save_config,
)


def open_windows_update() -> ActionResult:
    return open_uri("ms-settings:windowsupdate")


def open_optional_updates() -> ActionResult:
    return open_uri("ms-settings:windowsupdate-optionalupdates")


def trigger_windows_update_scan() -> ActionResult:
    result = run_command(["UsoClient", "StartScan"], timeout=10)
    ok = result.ok or result.returncode in (0, 1)
    message = "Windows Update scan requested." if ok else result.stderr or "Could not request scan."
    log_action("Windows Update Scan", message, ok=ok)
    return ActionResult("Windows Update Scan", ok, message, result.stderr)


def get_pending_windows_updates() -> ActionResult:
    script = (
        "$session = New-Object -ComObject Microsoft.Update.Session; "
        "$searcher = $session.CreateUpdateSearcher(); "
        "$result = $searcher.Search(\"IsInstalled=0 and Type='Software'\"); "
        "$result.Updates | ForEach-Object { $_.Title }"
    )
    result = run_powershell(script, timeout=120)
    if result.ok:
        message = result.stdout or "No pending Windows software updates found."
        return ActionResult("Pending Windows Updates", True, message)
    return ActionResult("Pending Windows Updates", False, "Could not check Windows Update.", result.stderr)


def get_installed_update_history(limit: int = 20) -> ActionResult:
    script = (
        f"Get-HotFix | Sort-Object InstalledOn -Descending | "
        f"Select-Object -First {limit} HotFixID,Description,InstalledOn | "
        "Format-Table -AutoSize | Out-String"
    )
    result = run_powershell(script, timeout=30)
    if result.ok:
        return ActionResult("Installed Updates", True, result.stdout or "No hotfix history returned.")
    return ActionResult("Installed Updates", False, "Could not read update history.", result.stderr)


def winget_available() -> bool:
    return command_exists("winget")


def check_winget_updates() -> ActionResult:
    if not winget_available():
        return ActionResult("winget Updates", False, "winget is not installed or not on PATH.")
    result = run_command(["winget", "upgrade", "--accept-source-agreements"], timeout=90)
    ok = result.ok or bool(result.stdout)
    config = load_config()
    config["last_update_check"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_config(config)
    message = result.stdout or result.stderr or "No winget output returned."
    log_action("winget Update Check", "Completed winget upgrade check.", ok=ok)
    return ActionResult("winget Updates", ok, message, result.stderr)


def update_all_winget_apps() -> ActionResult:
    if not winget_available():
        return ActionResult("Update winget Apps", False, "winget is not installed or not on PATH.")
    result = run_command(
        [
            "winget",
            "upgrade",
            "--all",
            "--include-unknown",
            "--accept-source-agreements",
            "--accept-package-agreements",
        ],
        timeout=1800,
    )
    ok = result.ok
    message = result.stdout or result.stderr or "winget update command finished."
    log_action("Update winget Apps", message[:300], ok=ok)
    return ActionResult("Update winget Apps", ok, message, result.stderr)


def _version_command(title: str, command: list[str]) -> dict:
    result = run_command(command, timeout=12)
    output = result.stdout or result.stderr
    return {
        "name": title,
        "installed": result.ok or bool(output),
        "version": output.splitlines()[0].strip() if output else "Not found",
    }


def get_runtime_versions() -> list[dict]:
    checks = [
        ("Python", ["python", "--version"]),
        ("pip", ["python", "-m", "pip", "--version"]),
        ("Node.js", ["node", "--version"]),
        ("npm", ["npm", "--version"]),
        ("Git", ["git", "--version"]),
        ("Java", ["java", "-version"]),
        ("PowerShell", ["powershell", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"]),
        ("winget", ["winget", "--version"]),
        ("Chocolatey", ["choco", "--version"]),
        ("Scoop", ["scoop", "--version"]),
    ]
    return [_version_command(title, command) for title, command in checks]


def install_missing_runtime(runtime: str) -> ActionResult:
    packages = {
        "python": "Python.Python.3.12",
        "git": "Git.Git",
        "node": "OpenJS.NodeJS.LTS",
        "vscode": "Microsoft.VisualStudioCode",
        "powershell": "Microsoft.PowerShell",
        "webview2": "Microsoft.EdgeWebView2Runtime",
        "dotnet": "Microsoft.DotNet.DesktopRuntime.8",
        "vcredist": "Microsoft.VCRedist.2015+.x64",
    }
    package_id = packages.get(runtime.lower())
    if not package_id:
        return ActionResult("Install Runtime", False, f"No package mapping for {runtime}.")
    if not winget_available():
        return ActionResult("Install Runtime", False, "winget is not installed or not on PATH.")
    result = run_command(
        [
            "winget",
            "install",
            "--id",
            package_id,
            "--accept-source-agreements",
            "--accept-package-agreements",
        ],
        timeout=1800,
    )
    return ActionResult(
        f"Install {runtime}",
        result.ok,
        result.stdout or result.stderr or "Install command finished.",
        result.stderr,
    )

