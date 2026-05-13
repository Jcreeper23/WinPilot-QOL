# WinPilot QOL

A compact Windows tray utility for cleanup, updates, performance, privacy, gaming, and everyday PC quality-of-life tools.

This is a practical V1 build from the larger feature list. It favors safe, inspectable actions first: read-only dashboards, previews before cleanup, confirmations for risky actions, admin detection, and reports.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python main.py
```

Without `pystray`, the app still opens as a normal GUI:

```powershell
python main.py --no-tray
```

Start minimized when tray support is installed:

```powershell
python main.py --minimized
```

## Implemented V1 Areas

- Tray menu with dashboard, cleanup, update check, Explorer toggles, settings shortcuts, power commands, and exit.
- Full `customtkinter` GUI with Dashboard, Cleanup, Updates, Performance, Startup, Apps, Network, Storage, Files & Tweaks, Security, Backup, Reports, and Settings.
- Dashboard system cards for Windows version, activation, CPU, GPU, RAM, drives, battery, power plan, uptime, network, admin state, and health warnings.
- Safe cleanup preview and runner for temp files, shader cache, thumbnail cache, crash dumps, DNS cache, Microsoft Store reset, clipboard, and Recycle Bin.
- Windows Update shortcuts, pending update check, update history helper, winget update check/update-all, and common runtime version checks.
- Startup app viewer and CSV export.
- Installed app viewer, filter, CSV export, install folder opener, and uninstaller launcher.
- Performance actions for Explorer restart, Task Manager, Resource Monitor, power plans, service restarts, lock/sleep/restart/shutdown.
- Network info, adapter list, ping test, DNS flush, IP renew/release, Winsock/TCP reset helpers.
- Storage scanner for common folders and large files, with CSV export.
- Explorer and Windows theme registry toggles.
- Windows Security snapshot, Defender quick scan, Defender definitions update, and firewall launcher.
- Restore point creation, restore point status, system restore launcher, settings backup.
- Markdown and JSON health reports.

## Safety Model

Actions are labeled in the UI by placement and confirmation:

- Read-only inventory and reports run directly.
- Cleanup actions preview space first and skip locked files.
- Registry changes are small HKCU Explorer/theme toggles.
- Admin-only repairs return a clear warning when the app is not elevated.
- Restart and shutdown are scheduled with a 60-second delay and can be canceled from the Performance tab.

## Project Structure

```txt
main.py
tray.py
gui.py
requirements.txt

modules/
  apps.py
  backup.py
  cleanup.py
  network.py
  performance.py
  registry_tweaks.py
  reports.py
  security.py
  startup.py
  storage.py
  system_info.py
  updates.py
  utils.py

logs/
reports/
assets/
```

## Notes

Run as administrator for restore points, some cleanup targets, service restarts, Winsock/TCP reset, and other system-level operations. The app is still useful without admin rights; it will simply mark admin-gated actions as unavailable.

