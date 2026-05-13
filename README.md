# WinPilot QOL

**WinPilot QOL** is a compact Windows quality-of-life utility built with Python and CustomTkinter.

It gives users one clean dashboard for common PC maintenance, cleanup, update checks, performance shortcuts, startup management, installed app review, storage scanning, network tools, security checks, backups, and local system reports.

> WinPilot QOL is designed around safe, inspectable actions first: read-only dashboards, previews before cleanup, confirmations for risky actions, admin detection, and local reports.

---

## Table of Contents

- [Overview](#overview)
- [Screenshots](#screenshots)
- [Main Features](#main-features)
- [Implemented V1 Areas](#implemented-v1-areas)
- [Safety Model](#safety-model)
- [Requirements](#requirements)
- [Quick Start](#quick-start)
- [Run Options](#run-options)
- [Project Structure](#project-structure)
- [Feature Breakdown](#feature-breakdown)
- [Admin Notes](#admin-notes)
- [Reports](#reports)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [Security and Privacy](#security-and-privacy)
- [License](#license)
- [Disclaimer](#disclaimer)

---

## Overview

WinPilot QOL is a local Windows utility app that brings common maintenance and troubleshooting tools into one modern interface.

Instead of jumping between Task Manager, Settings, Control Panel, Windows Security, PowerShell, Disk Cleanup, Update settings, and File Explorer, WinPilot QOL gives you a central place to inspect and manage your PC.

It is useful for:

- Cleaning temporary files
- Checking PC health
- Reviewing startup apps
- Finding large files and folders
- Checking installed programs
- Troubleshooting network issues
- Opening Windows tools faster
- Creating local system reports
- Running basic maintenance from one dashboard
- Managing common Windows quality-of-life settings

---

## Screenshots

Add screenshots later to make the GitHub page look more professional.

Recommended screenshot path:

```txt
assets/screenshot.png
```

After adding a screenshot, use:

```md
![WinPilot QOL Screenshot](assets/screenshot.png)
```

Recommended screenshots to include:

- Dashboard
- Cleanup page
- Storage scanner
- Network tools
- Reports page
- Tray menu

---

## Main Features

WinPilot QOL includes:

- Modern CustomTkinter GUI
- Optional system tray support
- Dashboard with system health cards
- Cleanup preview and cleanup runner
- Windows Update helpers
- Winget update checks
- Runtime version checks
- Startup app viewer
- Installed app viewer
- Performance shortcuts
- Network troubleshooting tools
- Storage scanner
- Large file finder
- Explorer quality-of-life toggles
- Windows theme toggles
- Security snapshot
- Defender quick scan launcher
- Restore point tools
- Backup helpers
- Markdown and JSON reports
- CSV exports
- Admin detection
- Safety warnings
- Logs and reports folders

---

## Implemented V1 Areas

This is a practical V1 build from a larger Windows QOL tool concept. It focuses on useful, realistic, and safer features first.

### Tray Menu

The tray menu can include quick access to:

- Open dashboard
- Run quick cleanup
- Run update check
- Explorer toggles
- Settings shortcuts
- Power commands
- Exit app

Tray support is optional. The app can still run as a normal GUI without tray support.

---

### Full GUI

The app includes a full CustomTkinter interface with sections such as:

- Dashboard
- Cleanup
- Updates
- Performance
- Startup
- Apps
- Network
- Storage
- Files & Tweaks
- Security
- Backup
- Reports
- Settings

---

### Dashboard

The dashboard shows system cards and health information, including:

- Windows version
- Windows activation status
- CPU information
- GPU information
- RAM usage
- Drive usage
- Battery status
- Current power plan
- Uptime
- Network state
- Admin state
- Health warnings
- Startup app count
- Installed app count
- Cleanup target summary

---

### Cleanup

Cleanup tools are designed to preview space before running.

Cleanup targets can include:

- Windows temp files
- User temp files
- Shader cache
- Thumbnail cache
- Crash dumps
- DNS cache
- Microsoft Store reset
- Clipboard clear
- Recycle Bin cleanup

Cleanup behavior:

- Preview before cleanup
- Skip locked files
- Avoid silent deletion of personal files
- Show cleanup results
- Keep actions understandable

---

### Updates

Update features include:

- Windows Update shortcut
- Pending update check
- Update history helper
- Winget update check
- Winget update-all helper
- Runtime version checks

Runtime checks can include:

- Python
- Git
- Node.js
- PowerShell
- Visual C++ runtimes
- .NET runtimes
- Other common developer/runtime tools

---

### Startup Manager

Startup tools include:

- View startup apps
- Read startup folder entries
- Read registry startup entries
- Export startup list to CSV
- Review startup impact manually
- Identify unnecessary startup clutter

---

### Installed Apps

The installed apps page can:

- List installed apps
- Filter/search installed apps
- Show app names
- Show versions when available
- Show publishers when available
- Export installed apps to CSV
- Open install folders when available
- Launch uninstall entries

---

### Performance

Performance actions include:

- Restart Windows Explorer
- Open Task Manager
- Open Resource Monitor
- Switch power plans
- Restart selected Windows services
- Lock PC
- Sleep PC
- Restart PC
- Shut down PC

Restart and shutdown actions are scheduled with a delay so they can be canceled.

---

### Network

Network tools include:

- Network information display
- Adapter list
- Ping test
- DNS flush
- IP renew
- IP release
- Winsock reset helper
- TCP/IP reset helper

Admin-required actions return warnings when the app is not elevated.

---

### Storage

Storage tools include:

- Common folder scanner
- Large file finder
- Large folder review
- CSV export
- Downloads folder scan
- Desktop/Documents scan options
- Storage reports

This helps users figure out what is taking space before deleting anything.

---

### Files & Tweaks

Explorer and Windows theme quality-of-life toggles include:

- Show hidden files
- Hide hidden files
- Show file extensions
- Hide file extensions
- Toggle dark/light app theme
- Toggle Windows theme settings
- Open useful folders
- Open useful Windows settings pages

Registry changes are kept small and focused on HKCU Explorer/theme settings.

---

### Security

Security tools are defensive and local.

Security features include:

- Windows Security snapshot
- Defender status check
- Defender quick scan launcher
- Defender definitions update
- Firewall launcher
- Admin status check
- Security report support

---

### Backup

Backup and restore helpers include:

- Create restore point
- Check restore point status
- Open System Restore
- Backup app settings
- Restore app settings
- Save reports locally

---

### Reports

WinPilot QOL can generate local system reports.

Report formats include:

- Markdown
- JSON
- CSV exports for specific areas

Reports may include:

- Full PC health summary
- Startup apps
- Installed apps
- Storage scan results
- Network information
- Security snapshot
- Cleanup results

---

## Safety Model

WinPilot QOL is designed around safer PC maintenance.

The app follows these safety rules:

- Read-only inventory and reports run directly
- Cleanup actions preview space first
- Cleanup skips locked files
- Registry changes are small HKCU Explorer/theme toggles
- Admin-only repairs return clear warnings when not elevated
- Restart and shutdown are scheduled with a 60-second delay when possible
- Risky actions should require confirmation
- Personal files are not silently deleted
- Reports are saved locally
- Logs are kept for troubleshooting

Recommended labels for future tools:

```txt
SAFE
ADMIN REQUIRED
RESTART REQUIRED
ADVANCED
RISKY
BACKUP FIRST
INTERNET REQUIRED
EXPERIMENTAL
```

---

## Requirements

WinPilot QOL is designed for:

- Windows 10
- Windows 11
- Python 3.10+
- pip

Python packages may include:

- customtkinter
- psutil
- pystray
- Pillow
- send2trash
- pywin32
- wmi
- requests

Install dependencies using:

```bash
pip install -r requirements.txt
```

---

## Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/YOUR-USERNAME/WinPilot-QOL.git
cd WinPilot-QOL
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Command Prompt:

```bat
.venv\Scripts\activate.bat
```

### 4. Install requirements

```bash
pip install -r requirements.txt
```

### 5. Run the app

```bash
python main.py
```

---

## Run Options

### Normal launch

```bash
python main.py
```

### Run without tray mode

Use this if `pystray` is not installed or you do not want tray support:

```bash
python main.py --no-tray
```

### Start minimized

When tray support is installed:

```bash
python main.py --minimized
```

---

## Project Structure

```txt
WinPilot-QOL/
│
├─ main.py
├─ tray.py
├─ gui.py
├─ requirements.txt
│
├─ modules/
│  ├─ __init__.py
│  ├─ apps.py
│  ├─ backup.py
│  ├─ cleanup.py
│  ├─ network.py
│  ├─ performance.py
│  ├─ registry_tweaks.py
│  ├─ reports.py
│  ├─ security.py
│  ├─ startup.py
│  ├─ storage.py
│  ├─ system_info.py
│  ├─ updates.py
│  └─ utils.py
│
├─ logs/
│  └─ .gitkeep
│
├─ reports/
│  └─ .gitkeep
│
└─ assets/
   └─ README.md
```

---

## Feature Breakdown

### Dashboard Features

- PC name
- Windows version
- Windows activation status
- CPU information
- GPU information
- RAM amount
- Storage drive usage
- Battery status
- Current power plan
- Uptime
- Boot time
- Current user
- Admin status
- Internet connection status
- Disk usage summary
- Health warning cards

---

### Cleanup Features

- Empty Recycle Bin
- Clear Windows temp files
- Clear user temp files
- Clear shader cache
- Clear thumbnail cache
- Clear crash dumps
- Clear DNS cache
- Clear clipboard
- Reset Microsoft Store cache
- Preview cleanup size
- Skip locked files
- Export cleanup report

---

### Update Features

- Open Windows Update
- Check pending updates
- View update history helper
- Check winget updates
- Run winget update-all
- Check common runtime versions
- Check Python version
- Check Git version
- Check Node.js version
- Check PowerShell version
- Check .NET/runtime status where supported

---

### Startup Features

- Show startup apps
- Show registry startup entries
- Show startup folder entries
- Export startup report
- Review startup clutter
- Help improve boot time manually

---

### App Manager Features

- List installed apps
- Search installed apps
- Filter installed apps
- Show app version
- Show publisher when available
- Open install location
- Launch uninstall command
- Export app list to CSV

---

### Performance Features

- Restart Explorer
- Open Task Manager
- Open Resource Monitor
- Switch to Balanced power plan
- Switch to High Performance power plan
- Switch to Ultimate Performance if available
- Restart selected services
- Lock PC
- Sleep PC
- Restart PC
- Shut down PC
- Cancel scheduled shutdown/restart

---

### Network Features

- Show local network info
- Show adapter list
- Ping test
- Flush DNS
- Renew IP
- Release IP
- Reset Winsock
- Reset TCP/IP stack
- Open network settings
- Export network report

---

### Storage Features

- Show drive usage
- Scan common folders
- Find large files
- Find large folders
- Analyze Downloads
- Analyze Desktop
- Analyze Documents
- Export storage CSV
- Generate storage report

---

### Files & Tweaks Features

- Show hidden files
- Hide hidden files
- Show file extensions
- Hide file extensions
- Toggle dark app theme
- Toggle light app theme
- Open Downloads folder
- Open Desktop folder
- Open Documents folder
- Open AppData
- Open LocalAppData
- Open Windows settings shortcuts

---

### Security Features

- Show Defender status
- Show firewall status
- Show admin status
- Open Windows Security
- Run Defender quick scan
- Update Defender definitions
- Open firewall settings
- Export security report

---

### Backup Features

- Create system restore point
- Check restore point status
- Open System Restore
- Backup app settings
- Restore app settings
- Export reports

---

## Admin Notes

Some features require administrator permissions.

Admin-only or admin-preferred features may include:

- Creating restore points
- Restarting system services
- Winsock reset
- TCP/IP reset
- Some cleanup targets
- Defender commands
- Some update commands
- Some repair actions
- Some power/user-level operations

The app is still useful without administrator rights. Admin-gated actions will show a warning or become unavailable.

---

## Reports

Reports are saved locally in:

```txt
reports/
```

Possible report types:

- Health report
- Cleanup report
- Startup report
- Installed apps report
- Storage report
- Network report
- Security report

Possible formats:

- Markdown
- JSON
- CSV

---

## Logs

Logs are saved locally in:

```txt
logs/
```

Logs are useful for debugging errors and checking what actions were run.

---

## Testing

Run a compile check:

```bash
python -m compileall -q .
```

Run without tray mode:

```bash
python main.py --no-tray
```

Suggested manual tests:

- Open the dashboard
- Run a health report
- Open Cleanup and preview cleanup targets
- Open Startup and export CSV
- Open Apps and search installed apps
- Run a ping test
- Open Storage and scan a folder
- Generate a Markdown report
- Run without admin rights and confirm warnings appear
- Run as admin and confirm admin tools become available
- Close the app while tasks are running and confirm no callback errors appear

---

## Troubleshooting

### PowerShell will not activate the virtual environment

Run PowerShell as user and use:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again:

```powershell
.\.venv\Scripts\Activate.ps1
```

---

### Tray mode does not work

Install requirements:

```bash
pip install -r requirements.txt
```

Or run without tray mode:

```bash
python main.py --no-tray
```

---

### Some actions say admin required

Close the app and reopen Command Prompt or PowerShell as Administrator, then run:

```bash
python main.py
```

---

### Winget checks do not work

Make sure App Installer / winget is installed on Windows.

You can check with:

```bash
winget --version
```

---

### Cleanup skips some files

That is expected. Locked or protected files are skipped for safety.

---

## Roadmap

Planned future improvements:

- Better one-click cleanup profiles
- More cleanup categories
- Safer cleanup preview UI
- Better storage scanner
- Duplicate file finder
- Gaming boost profile
- Developer setup profile
- More backup options
- App update automation
- Better report viewer
- Notification system
- Settings page improvements
- Theme customization
- More tray quick actions
- More detailed security checks
- More detailed battery/laptop tools
- Controller/XInput checker
- Xbox app repair helper
- Browser cache tools
- Driver info tools
- Scheduled maintenance profiles
- Export full PC diagnostic package

---

## Possible Future Profiles

### Clean My PC

- Temp cleanup
- Recycle Bin cleanup
- Shader cache cleanup
- Thumbnail cache cleanup
- DNS flush

### Speed Up Boot

- Startup scan
- Startup report
- Suggestions for apps to disable

### Fix Internet

- Flush DNS
- Renew IP
- Reset Winsock
- Restart adapter helper
- Ping test

### Gaming Boost

- High performance power plan
- Game Mode shortcut
- Disable captures helper
- Clear shader cache
- Close selected background apps

### Privacy Boost

- Disable advertising ID helper
- Clear activity history helper
- Clear clipboard
- Disable recent files helper

### Repair Windows

- SFC scan launcher
- DISM restore health launcher
- Windows Update repair helper
- Microsoft Store reset

### Developer Setup

- Check Python/Git/Node
- Fix PATH helper
- Create project templates
- Clear pip/npm caches

### Storage Finder

- Scan biggest folders
- Find large videos
- Find old downloads
- Export storage report

---

## Contributing

Contributions are welcome for non-commercial improvements.

Good contribution ideas:

- New safe cleanup targets
- Better dashboard cards
- Better report formatting
- UI improvements
- Bug fixes
- More Windows shortcuts
- More storage scanner features
- Better error handling
- More admin checks
- Better settings page
- Better tray actions

Please keep contributions focused on safe PC maintenance, troubleshooting, and quality-of-life tools.

Do not add:

- Malware-like behavior
- Credential stealing
- Security bypasses
- Anti-cheat bypass tools
- Hardware spoofing
- Token tools
- Destructive cleanup without confirmation
- Silent registry/system modifications

---

## Security and Privacy

WinPilot QOL is intended to run locally.

Design goals:

- No account required
- No cloud dashboard required
- No selling user data
- Reports are generated locally
- Cleanup actions are user-triggered
- Risky actions should require confirmation

If internet features are added, they should be clearly labeled.

---

## Recommended GitHub Topics

```txt
windows
python
customtkinter
pc-utility
qol
windows-tools
cleanup
system-info
tray-app
performance
network-tools
storage-scanner
startup-manager
windows-maintenance
```

---

## Repository Description

Use this as the GitHub repo description:

```txt
A compact Windows tray utility for cleanup, updates, performance, storage, network, security, and everyday PC quality-of-life tools.
```

---

## License

This project uses a custom non-commercial license.

You may use, copy, modify, and share this software for personal, educational, and non-commercial purposes only.

You may not sell this software, include it in a paid product, resell modified versions, or use it for commercial services without written permission from the creator.

See the `LICENSE` file for full details.

---

## Disclaimer

WinPilot QOL is provided as-is.

Use cleanup, registry, startup, update, repair, and power tools carefully. The creator is not responsible for data loss, system issues, or damage caused by use or misuse.

Always review actions before applying changes. For advanced repairs, registry changes, service changes, or system-level cleanup, create a restore point first.

---

## Credits

Built with:

- Python
- CustomTkinter
- psutil
- pystray
- Pillow
- Windows command-line tools
- Windows registry/user settings helpers

Created as a practical Windows QOL dashboard for everyday PC maintenance.
