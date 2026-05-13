from __future__ import annotations

import threading
from typing import Callable

from modules import cleanup, performance, registry_tweaks, updates
from modules.utils import ActionResult, known_folder, open_path

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:  # pragma: no cover - optional tray support
    pystray = None
    Image = None
    ImageDraw = None


class TrayController:
    def __init__(self, app) -> None:
        self.app = app
        self.icon = None

    def start(self) -> bool:
        if pystray is None or Image is None or ImageDraw is None:
            return False

        self.icon = pystray.Icon(
            "WinPilot QOL",
            self._build_icon(),
            "WinPilot QOL",
            self._build_menu(),
        )
        self.app.tray_icon = self.icon
        self.app.tray_enabled = True
        try:
            self.icon.run_detached()
        except Exception:
            threading.Thread(target=self.icon.run, daemon=True).start()
        return True

    def _build_icon(self):
        image = Image.new("RGBA", (64, 64), (18, 24, 38, 255))
        draw = ImageDraw.Draw(image)
        draw.rounded_rectangle((6, 6, 58, 58), radius=12, fill=(47, 125, 246, 255))
        draw.rectangle((18, 18, 24, 46), fill=(255, 255, 255, 255))
        draw.rectangle((30, 26, 36, 46), fill=(255, 255, 255, 255))
        draw.rectangle((42, 18, 48, 46), fill=(255, 255, 255, 255))
        return image

    def _ui(self, callback: Callable[[], None]) -> None:
        self.app.after(0, callback)

    def _show(self, page: Callable[[], None] | None = None) -> None:
        def action() -> None:
            self.app.show_window()
            if page:
                page()

        self._ui(action)

    def _run_action(self, title: str, func: Callable[[], ActionResult]) -> None:
        def action() -> None:
            self.app.show_window()
            self.app.run_task(title, func)

        self._ui(action)

    def _build_menu(self):
        return pystray.Menu(
            pystray.MenuItem("Open full dashboard", lambda: self._show(self.app.show_dashboard)),
            pystray.MenuItem("Run quick PC cleanup", lambda: self._ui(self.app.quick_cleanup_from_tray)),
            pystray.MenuItem("Run quick update check", lambda: self._run_action("winget check", updates.check_winget_updates)),
            pystray.MenuItem("Toggle app dark/light mode", lambda: self._ui(self.app.toggle_app_theme)),
            pystray.MenuItem("Toggle Windows dark/light mode", lambda: self._run_action("Windows theme", registry_tweaks.toggle_windows_theme)),
            pystray.MenuItem("Night light settings", lambda: self._run_action("Night light", registry_tweaks.open_night_light_settings)),
            pystray.MenuItem("Bluetooth settings", lambda: self._run_action("Bluetooth", registry_tweaks.open_bluetooth_settings)),
            pystray.MenuItem("Wi-Fi settings", lambda: self._run_action("Wi-Fi", registry_tweaks.open_wifi_settings)),
            pystray.MenuItem("Performance mode", lambda: self._run_action("High performance", lambda: performance.set_power_plan("high performance"))),
            pystray.MenuItem("Battery saver settings", lambda: self._run_action("Battery saver", registry_tweaks.open_battery_saver_settings)),
            pystray.MenuItem("Focus settings", lambda: self._run_action("Focus", registry_tweaks.open_focus_settings)),
            pystray.MenuItem("Toggle hidden files", lambda: self._run_action("Hidden files", registry_tweaks.toggle_hidden_files)),
            pystray.MenuItem("Toggle file extensions", lambda: self._run_action("File extensions", registry_tweaks.toggle_file_extensions)),
            pystray.MenuItem("Open downloads folder", lambda: self._run_action("Downloads", lambda: open_path(known_folder("downloads")))),
            pystray.MenuItem("Open startup apps", lambda: self._run_action("Startup apps", performance.open_startup_apps)),
            pystray.MenuItem("Open task manager", lambda: self._run_action("Task Manager", performance.open_task_manager)),
            pystray.MenuItem("Open settings", lambda: self._run_action("Settings", registry_tweaks.open_settings_home)),
            pystray.MenuItem("Restart Explorer", lambda: self._run_action("Restart Explorer", performance.restart_explorer)),
            pystray.MenuItem("Flush DNS", lambda: self._run_action("Flush DNS", cleanup.flush_dns)),
            pystray.MenuItem("Lock PC", lambda: self._run_action("Lock PC", performance.lock_pc)),
            pystray.MenuItem("Sleep PC", lambda: self._ui(self.app.sleep_confirm)),
            pystray.MenuItem("Restart PC in 60s", lambda: self._ui(self.app.restart_confirm)),
            pystray.MenuItem("Shut down PC in 60s", lambda: self._ui(self.app.shutdown_confirm)),
            pystray.MenuItem("Exit app", lambda: self._ui(self.app.exit_app)),
        )


def start_tray(app) -> TrayController | None:
    controller = TrayController(app)
    if controller.start():
        return controller
    return None

