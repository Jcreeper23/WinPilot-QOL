from __future__ import annotations

import argparse

from gui import WinPilotApp
from modules.utils import ActionResult, load_config, log_action
from tray import start_tray


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="WinPilot QOL Windows utility")
    parser.add_argument("--no-tray", action="store_true", help="Launch without tray integration")
    parser.add_argument("--minimized", action="store_true", help="Start minimized to tray when tray is available")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_config()
    start_minimized = bool(args.minimized or config.get("launch_minimized", False))
    app = WinPilotApp(start_minimized=start_minimized and not args.no_tray)

    if not args.no_tray:
        controller = start_tray(app)
        if controller:
            log_action("Tray", "Tray integration started.")
        else:
            app.tray_enabled = False
            app.deiconify()
            app.show_result(
                ActionResult(
                    "Tray",
                    False,
                    "pystray is not installed; running as a normal GUI app.",
                    "Install requirements.txt to enable the Show hidden icons tray menu.",
                )
            )

    app.mainloop()


if __name__ == "__main__":
    main()
