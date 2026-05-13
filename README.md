# WinPilot QOL

**WinPilot QOL** is a compact Windows quality-of-life utility built with Python.  
It gives users a clean dashboard for common PC maintenance, cleanup, updates, performance tools, storage checks, startup management, network tools, and system reports.

The goal is to make everyday Windows maintenance easier from one modern local app.

> This tool is designed for personal PC maintenance, troubleshooting, safe cleanup, and system convenience.

---

## Features

### Dashboard

WinPilot QOL includes a clean dashboard showing useful system information such as:

- PC name
- Windows version
- CPU information
- RAM usage
- Disk usage
- Network status
- Admin status
- Startup item count
- Installed app count
- Security status
- Cleanup targets
- Quick health overview

---

### System Tray Support

WinPilot QOL can run from the Windows system tray / hidden icons area.

Tray actions can include:

- Open dashboard
- Run quick cleanup
- Open common Windows tools
- Restart Explorer
- Exit app

Tray support is optional. If tray dependencies are not installed, the app can still run without tray mode.

Run without tray:

```bash
python main.py --no-tray
