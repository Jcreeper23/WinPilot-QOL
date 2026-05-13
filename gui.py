from __future__ import annotations

import threading
import tkinter as tk
import traceback
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from modules import (
    apps,
    backup,
    cleanup,
    network,
    performance,
    registry_tweaks,
    reports,
    security,
    startup,
    storage,
    system_info,
    updates,
)
from modules.utils import (
    ActionResult,
    BASE_DIR,
    human_bytes,
    is_admin,
    known_folder,
    load_config,
    log_action,
    open_path,
    save_config,
)


class WinPilotApp(ctk.CTk):
    def __init__(self, *, start_minimized: bool = False) -> None:
        self.config_data = load_config()
        ctk.set_appearance_mode(self.config_data.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.title("WinPilot QOL")
        self.geometry("1180x760")
        self.minsize(980, 620)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.tray_icon = None
        self.tray_enabled = False
        self.current_page_name = "Dashboard"
        self._render_generation = 0
        self.cleanup_targets: list[cleanup.CleanupTarget] = []
        self.cleanup_checks: dict[str, ctk.BooleanVar] = {}
        self.current_apps: list[apps.InstalledApp] = []
        self.current_startup: list[startup.StartupEntry] = []
        self.storage_findings: list[storage.FileFinding] = []
        self.storage_root = known_folder("downloads")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_shell()
        self.show_dashboard()

        if start_minimized:
            self.withdraw()

    def _build_shell(self) -> None:
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(20, weight=1)

        title = ctk.CTkLabel(
            self.sidebar,
            text="WinPilot QOL",
            font=ctk.CTkFont(size=22, weight="bold"),
        )
        title.grid(row=0, column=0, padx=18, pady=(20, 4), sticky="w")
        subtitle = "Admin" if is_admin() else "Standard user"
        ctk.CTkLabel(self.sidebar, text=subtitle, text_color="#9ca3af").grid(
            row=1, column=0, padx=18, pady=(0, 14), sticky="w"
        )

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", lambda *_: self._filter_nav())
        search = ctk.CTkEntry(self.sidebar, placeholder_text="Search tools", textvariable=self.search_var)
        search.grid(row=2, column=0, padx=14, pady=(0, 12), sticky="ew")

        self.nav_items = [
            ("Dashboard", self.show_dashboard),
            ("Cleanup", self.show_cleanup),
            ("Updates", self.show_updates),
            ("Performance", self.show_performance),
            ("Startup", self.show_startup),
            ("Apps", self.show_apps),
            ("Network", self.show_network),
            ("Storage", self.show_storage),
            ("Files & Tweaks", self.show_files_tweaks),
            ("Security", self.show_security),
            ("Backup", self.show_backup),
            ("Reports", self.show_reports),
            ("Settings", self.show_settings),
        ]
        self.nav_buttons: dict[str, ctk.CTkButton] = {}
        for index, (label, command) in enumerate(self.nav_items, start=3):
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                anchor="w",
                height=34,
                corner_radius=6,
                fg_color="transparent",
                hover_color=("#dbeafe", "#1f2937"),
                command=command,
            )
            button.grid(row=index, column=0, padx=12, pady=2, sticky="ew")
            self.nav_buttons[label] = button

        self.status_label = ctk.CTkLabel(self.sidebar, text="Ready", text_color="#9ca3af", wraplength=180)
        self.status_label.grid(row=21, column=0, padx=14, pady=(10, 8), sticky="ew")

        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        self.page = ctk.CTkScrollableFrame(self.content, corner_radius=0, fg_color="transparent")
        self.page.grid(row=0, column=0, sticky="nsew", padx=18, pady=(18, 8))

        self.output = ctk.CTkTextbox(self.content, height=120, corner_radius=6)
        self.output.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 18))
        self.output.insert("end", "Logs and command results will appear here.\n")
        self.output.configure(state="disabled")

    def _filter_nav(self) -> None:
        query = self.search_var.get().strip().lower()
        visible_row = 3
        for label, _ in self.nav_items:
            button = self.nav_buttons[label]
            if not query or query in label.lower():
                button.grid(row=visible_row, column=0, padx=12, pady=2, sticky="ew")
                visible_row += 1
            else:
                button.grid_remove()

    def _select_nav(self, name: str) -> None:
        self.current_page_name = name
        for label, button in self.nav_buttons.items():
            if label == name:
                button.configure(fg_color=("#bfdbfe", "#1d4ed8"))
            else:
                button.configure(fg_color="transparent")

    def _widget_alive(self, widget) -> bool:
        try:
            return widget is not None and bool(widget.winfo_exists())
        except Exception:
            return False

    def _safe_clear_frame(self, frame, skip: int = 0) -> bool:
        if not self._widget_alive(frame):
            return False

        try:
            children = frame.winfo_children()
        except Exception:
            return False

        for child in children[skip:]:
            try:
                if child.winfo_exists():
                    child.destroy()
            except Exception:
                pass

        return True

    def _clear_page(self) -> None:
        self._render_generation += 1
        self._safe_clear_frame(getattr(self, "page", None))

    def _header(self, title: str, subtitle: str = "") -> None:
        ctk.CTkLabel(
            self.page,
            text=title,
            font=ctk.CTkFont(size=28, weight="bold"),
        ).pack(anchor="w", pady=(0, 4))
        if subtitle:
            ctk.CTkLabel(self.page, text=subtitle, text_color="#9ca3af", wraplength=860).pack(
                anchor="w", pady=(0, 16)
            )

    def _section(self, title: str) -> ctk.CTkFrame:
        ctk.CTkLabel(
            self.page,
            text=title,
            font=ctk.CTkFont(size=17, weight="bold"),
        ).pack(anchor="w", pady=(14, 8))
        frame = ctk.CTkFrame(self.page, corner_radius=8)
        frame.pack(fill="x", pady=(0, 8))
        return frame

    def _button_row(self, parent: ctk.CTkFrame | None = None) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent or self.page, fg_color="transparent")
        row.pack(fill="x", pady=(4, 10))
        return row

    def _add_button(
        self,
        parent: ctk.CTkFrame,
        text: str,
        command,
        *,
        danger: bool = False,
        width: int = 150,
    ) -> ctk.CTkButton:
        color = "#b91c1c" if danger else None
        hover = "#991b1b" if danger else None
        button = ctk.CTkButton(
            parent,
            text=text,
            command=command,
            width=width,
            height=34,
            corner_radius=6,
            fg_color=color,
            hover_color=hover,
        )
        button.pack(side="left", padx=(0, 8), pady=4)
        return button

    def _card(self, parent: ctk.CTkFrame, title: str, value: str, detail: str = "") -> ctk.CTkFrame:
        card = ctk.CTkFrame(parent, corner_radius=8)
        card.pack(side="left", fill="both", expand=True, padx=6, pady=6)
        ctk.CTkLabel(card, text=title, text_color="#9ca3af", anchor="w").pack(
            anchor="w", padx=12, pady=(10, 2)
        )
        ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=18, weight="bold"),
            wraplength=220,
            anchor="w",
        ).pack(anchor="w", padx=12, pady=(0, 4))
        if detail:
            ctk.CTkLabel(card, text=detail, text_color="#9ca3af", wraplength=220, anchor="w").pack(
                anchor="w", padx=12, pady=(0, 10)
            )
        else:
            ctk.CTkLabel(card, text="", height=10).pack()
        return card

    def _set_status(self, text: str) -> None:
        if not self._widget_alive(getattr(self, "status_label", None)):
            return
        try:
            self.status_label.configure(text=text)
        except tk.TclError:
            return

    def _append_output(self, text: str) -> None:
        if not self._widget_alive(getattr(self, "output", None)):
            return
        try:
            self.output.configure(state="normal")
            self.output.insert("end", text.rstrip() + "\n")
            self.output.see("end")
            self.output.configure(state="disabled")
        except tk.TclError:
            return

    def _format_result(self, result: ActionResult) -> str:
        status = "OK" if result.ok else "FAILED"
        text = f"[{status}] {result.title}: {result.message}"
        if result.details:
            text += f"\n{result.details}"
        return text

    def show_result(self, result: ActionResult | list[ActionResult]) -> None:
        if isinstance(result, list):
            for item in result:
                self._append_output(self._format_result(item))
            failed = sum(1 for item in result if not item.ok)
            self._set_status(f"Finished with {failed} issue(s)" if failed else "Finished")
            return
        self._append_output(self._format_result(result))
        self._set_status("Done" if result.ok else "Needs attention")

    def run_task(self, title: str, func, *, on_done=None, show_output: bool = True) -> None:
        generation = self._render_generation
        self._set_status(f"{title}...")

        def worker() -> None:
            try:
                result = func()
            except Exception:
                details = traceback.format_exc()
                log_action(title, f"Task failed: {details}", ok=False)
                result = ActionResult(title, False, "Task failed.", details)

            def finish() -> None:
                if generation != self._render_generation:
                    return
                if not self._widget_alive(self):
                    return
                try:
                    if show_output:
                        self.show_result(result)
                    else:
                        self._set_status("Ready")
                    if on_done:
                        on_done(result)
                except tk.TclError:
                    return
                except Exception:
                    details = traceback.format_exc()
                    log_action(title, f"Task render failed: {details}", ok=False)
                    try:
                        self.show_result(ActionResult(title, False, "Task render failed.", details))
                    except Exception:
                        pass

            try:
                self.after(0, finish)
            except (tk.TclError, RuntimeError):
                return

        threading.Thread(target=worker, daemon=True).start()

    def confirm(self, title: str, message: str) -> bool:
        if not self.config_data.get("confirm_risky_actions", True):
            return True
        return bool(messagebox.askyesno(title, message, parent=self))

    def on_close(self) -> None:
        if self.tray_enabled and self.config_data.get("close_to_tray", True):
            self.withdraw()
            self._set_status("Hidden in tray")
        else:
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
            self.destroy()

    def show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()

    def exit_app(self) -> None:
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
        self.destroy()

    def show_dashboard(self, *, include_public_ip: bool = False) -> None:
        self._select_nav("Dashboard")
        self._clear_page()
        self._header(
            "Dashboard",
            "Fast system overview, health cards, usage, drives, and the safest quick actions.",
        )
        loading = ctk.CTkLabel(self.page, text="Loading system overview...")
        loading.pack(anchor="w", pady=12)

        def load():
            return (
                system_info.get_system_overview(include_public_ip=include_public_ip),
                system_info.get_health_cards(self.config_data),
                load_config(),
            )

        self.run_task("Refresh dashboard", load, on_done=self._render_dashboard, show_output=False)

    def _render_dashboard(self, payload) -> None:
        if not self._widget_alive(getattr(self, "page", None)):
            return
        if isinstance(payload, ActionResult):
            self.show_result(payload)
            return
        overview, health_cards, config = payload
        self._clear_page()
        if not self._widget_alive(getattr(self, "page", None)):
            return
        self._header(
            "Dashboard",
            "Fast system overview, health cards, usage, drives, and the safest quick actions.",
        )
        row = self._button_row()
        self._add_button(row, "Refresh", lambda: self.show_dashboard())
        self._add_button(row, "Refresh Public IP", lambda: self.show_dashboard(include_public_ip=True), width=170)
        self._add_button(row, "Quick Cleanup", self.quick_cleanup_from_gui)
        self._add_button(row, "Export Report", lambda: self.run_task("Export report", reports.export_health_report_markdown))

        usage = overview["usage"]
        row1 = ctk.CTkFrame(self.page, fg_color="transparent")
        row1.pack(fill="x")
        self._card(row1, "PC", overview["pc_name"], overview["windows_version"])
        self._card(row1, "CPU", f"{usage.get('cpu_percent', 'N/A')}%", overview["cpu"])
        self._card(row1, "Memory", f"{usage.get('ram_percent', 'N/A')}%", overview["ram"])
        self._card(row1, "Power", overview["power_plan"][:34], f"Uptime: {overview['uptime']}")

        row2 = ctk.CTkFrame(self.page, fg_color="transparent")
        row2.pack(fill="x")
        self._card(row2, "GPU", overview["gpu"], "Usage requires vendor tooling")
        self._card(row2, "Battery", overview["battery"]["label"], "Current battery sensor")
        self._card(row2, "Network", overview["local_ip"], f"Public: {overview['public_ip']}")
        admin_label = "Administrator" if overview["admin"] else "Standard user"
        self._card(row2, "User", overview["current_user"], admin_label)

        health_frame = self._section("Health Cards")
        for card in health_cards:
            color = {"ok": "#16a34a", "info": "#2563eb", "warning": "#d97706"}.get(card["level"], "#64748b")
            line = ctk.CTkFrame(health_frame, fg_color="transparent")
            line.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(line, text=card["title"], text_color=color, width=170, anchor="w").pack(side="left")
            ctk.CTkLabel(line, text=card["message"], anchor="w", wraplength=760).pack(side="left", fill="x", expand=True)

        drive_frame = self._section("Storage Drives")
        for drive in overview["drives"]:
            line = ctk.CTkFrame(drive_frame, fg_color="transparent")
            line.pack(fill="x", padx=10, pady=6)
            ctk.CTkLabel(line, text=drive["mountpoint"], width=80, anchor="w").pack(side="left")
            progress = ctk.CTkProgressBar(line, width=220)
            progress.set(drive["percent"] / 100)
            progress.pack(side="left", padx=8)
            label = f"{human_bytes(drive['used'])} used / {human_bytes(drive['total'])} ({drive['percent']:.0f}%)"
            ctk.CTkLabel(line, text=label, anchor="w").pack(side="left", fill="x", expand=True)

        footer = self._section("Recent Activity")
        ctk.CTkLabel(
            footer,
            text=(
                f"Last cleanup: {config.get('last_cleanup') or 'Never'}    "
                f"Last update check: {config.get('last_update_check') or 'Never'}    "
                f"Boot time: {overview['boot_time']}"
            ),
            anchor="w",
        ).pack(fill="x", padx=10, pady=10)

    def show_cleanup(self) -> None:
        self._select_nav("Cleanup")
        self._clear_page()
        self._header("Cleanup", "Preview safe cleanup targets before removing temp files or caches.")
        row = self._button_row()
        self._add_button(row, "Preview Cleanup", self.load_cleanup_preview)
        self._add_button(row, "Quick Cleanup", self.quick_cleanup_from_gui)
        self._add_button(row, "Empty Recycle Bin", self.empty_recycle_bin_confirm)
        self._add_button(row, "Flush DNS", lambda: self.run_task("Flush DNS", cleanup.flush_dns))
        self._add_button(row, "Clear Clipboard", lambda: self.run_task("Clear clipboard", cleanup.clear_clipboard))
        self.cleanup_frame = self._section("Cleanup Targets")
        ctk.CTkLabel(self.cleanup_frame, text="Click Preview Cleanup to estimate space.").pack(
            anchor="w", padx=10, pady=10
        )

    def load_cleanup_preview(self) -> None:
        self.run_task("Preview cleanup", cleanup.preview_cleanup, on_done=self._render_cleanup_targets, show_output=False)

    def _render_cleanup_targets(self, targets) -> None:
        frame = getattr(self, "cleanup_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(targets, ActionResult):
            self.show_result(targets)
            return
        self.cleanup_targets = targets
        if not self._safe_clear_frame(frame):
            return
        self.cleanup_checks = {}
        total = sum(target.size for target in targets)
        ctk.CTkLabel(
            frame,
            text=f"Estimated space: {human_bytes(total)}",
            font=ctk.CTkFont(weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 6))
        for target in targets:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=4)
            var = ctk.BooleanVar(value=target.safe and not (target.needs_admin and not is_admin()))
            self.cleanup_checks[target.key] = var
            ctk.CTkCheckBox(row, text="", variable=var, width=28).pack(side="left")
            admin = " | admin required" if target.needs_admin else ""
            size = human_bytes(target.size) if target.path else "Action"
            ctk.CTkLabel(row, text=target.title, width=190, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=f"{size}{admin}", width=160, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=target.note, anchor="w", wraplength=520).pack(side="left", fill="x", expand=True)
        row = ctk.CTkFrame(frame, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(8, 10))
        self._add_button(row, "Run Selected", self.run_selected_cleanup)

    def run_selected_cleanup(self) -> None:
        selected = [
            target
            for target in self.cleanup_targets
            if self.cleanup_checks.get(target.key) and self.cleanup_checks[target.key].get()
        ]
        if not selected:
            messagebox.showinfo("Cleanup", "Select at least one cleanup target.", parent=self)
            return
        estimate = human_bytes(sum(target.size for target in selected))
        if not self.confirm("Run cleanup", f"Run selected cleanup targets?\nEstimated space: {estimate}"):
            return
        self.run_task("Run selected cleanup", lambda: [cleanup.clear_target(target) for target in selected])

    def quick_cleanup_from_gui(self) -> None:
        if not self.confirm("Quick cleanup", "Run safe cleanup targets and empty the Recycle Bin?"):
            return
        self.run_task("Quick cleanup", cleanup.quick_cleanup)

    def quick_cleanup_from_tray(self) -> None:
        self.show_window()
        self.quick_cleanup_from_gui()

    def empty_recycle_bin_confirm(self) -> None:
        if self.confirm("Empty Recycle Bin", "Empty the Recycle Bin now?"):
            self.run_task("Empty Recycle Bin", cleanup.empty_recycle_bin)

    def show_updates(self) -> None:
        self._select_nav("Updates")
        self._clear_page()
        self._header("Updates", "Check Windows, winget apps, and common runtime versions.")
        row = self._button_row()
        self._add_button(row, "Windows Update", lambda: self.run_task("Open Windows Update", updates.open_windows_update))
        self._add_button(row, "Trigger Scan", lambda: self.run_task("Trigger update scan", updates.trigger_windows_update_scan))
        self._add_button(row, "Pending Updates", lambda: self.run_task("Pending updates", updates.get_pending_windows_updates))
        self._add_button(row, "winget Check", lambda: self.run_task("winget check", updates.check_winget_updates))
        self._add_button(row, "Update All winget", self.update_all_winget_confirm, danger=True, width=170)

        runtime = self._section("Runtime Versions")
        self.runtime_frame = runtime
        self._add_button(self._button_row(runtime), "Refresh Versions", self.load_runtime_versions)
        self.load_runtime_versions()

    def update_all_winget_confirm(self) -> None:
        if self.confirm("Update all winget apps", "Install all available winget app updates now?"):
            self.run_task("Update all winget apps", updates.update_all_winget_apps)

    def load_runtime_versions(self) -> None:
        self.run_task("Runtime versions", updates.get_runtime_versions, on_done=self._render_runtime_versions, show_output=False)

    def _render_runtime_versions(self, rows) -> None:
        frame = getattr(self, "runtime_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(rows, ActionResult):
            self.show_result(rows)
            return
        if not self._safe_clear_frame(frame, skip=1):
            return
        for row_data in rows:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(row, text=row_data["name"], width=160, anchor="w").pack(side="left")
            status = "Installed" if row_data["installed"] else "Missing"
            color = "#16a34a" if row_data["installed"] else "#d97706"
            ctk.CTkLabel(row, text=status, text_color=color, width=100, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=row_data["version"], anchor="w", wraplength=650).pack(side="left", fill="x", expand=True)

    def show_performance(self) -> None:
        self._select_nav("Performance")
        self._clear_page()
        self._header("Performance", "Quick repair actions, power plans, service restarts, and guarded power commands.")
        row = self._button_row()
        self._add_button(row, "Restart Explorer", lambda: self.run_task("Restart Explorer", performance.restart_explorer))
        self._add_button(row, "Task Manager", lambda: self.run_task("Task Manager", performance.open_task_manager))
        self._add_button(row, "Resource Monitor", lambda: self.run_task("Resource Monitor", performance.open_resource_monitor))
        self._add_button(row, "Flush DNS", lambda: self.run_task("Flush DNS", cleanup.flush_dns))

        power_frame = self._section("Power Plans")
        for plan in performance.get_power_plans():
            label = f"{plan['name']}{' (active)' if plan['active'] else ''}"
            self._add_button(
                self._button_row(power_frame),
                label,
                lambda name=plan["name"]: self.run_task("Set power plan", lambda: performance.set_power_plan(name)),
                width=240,
            )
        row = self._button_row(power_frame)
        self._add_button(row, "Balanced", lambda: self.run_task("Balanced", lambda: performance.set_power_plan("balanced")))
        self._add_button(row, "High Performance", lambda: self.run_task("High performance", lambda: performance.set_power_plan("high performance")), width=180)
        self._add_button(row, "Ultimate Performance", self.ultimate_performance_confirm, width=190)

        services = self._section("Service Restarts")
        row = self._button_row(services)
        self._add_button(row, "Audio Service", lambda: self.run_task("Restart audio", performance.restart_audio_service))
        self._add_button(row, "Print Spooler", lambda: self.run_task("Restart spooler", performance.restart_print_spooler))
        self._add_button(row, "Windows Update", lambda: self.run_task("Restart update service", performance.restart_windows_update_service), width=170)

        danger = self._section("Power Commands")
        row = self._button_row(danger)
        self._add_button(row, "Lock PC", lambda: self.run_task("Lock PC", performance.lock_pc))
        self._add_button(row, "Sleep PC", self.sleep_confirm)
        self._add_button(row, "Restart in 60s", self.restart_confirm, danger=True, width=160)
        self._add_button(row, "Shut Down in 60s", self.shutdown_confirm, danger=True, width=170)
        self._add_button(row, "Cancel Shutdown", lambda: self.run_task("Cancel shutdown", performance.abort_power_action), width=160)

    def ultimate_performance_confirm(self) -> None:
        if self.confirm("Ultimate Performance", "Enable and switch to the Ultimate Performance power plan?"):
            self.run_task("Ultimate Performance", performance.enable_ultimate_performance)

    def sleep_confirm(self) -> None:
        if self.confirm("Sleep PC", "Put the PC to sleep now?"):
            self.run_task("Sleep PC", performance.sleep_pc)

    def restart_confirm(self) -> None:
        if self.confirm("Restart PC", "Schedule a restart in 60 seconds? Use Cancel Shutdown to abort."):
            self.run_task("Restart PC", performance.restart_pc)

    def shutdown_confirm(self) -> None:
        if self.confirm("Shut Down PC", "Schedule a shutdown in 60 seconds? Use Cancel Shutdown to abort."):
            self.run_task("Shut Down PC", performance.shutdown_pc)

    def show_startup(self) -> None:
        self._select_nav("Startup")
        self._clear_page()
        self._header("Startup", "View startup entries from Run keys and Startup folders.")
        row = self._button_row()
        self._add_button(row, "Refresh", self.load_startup_entries)
        self._add_button(row, "Export CSV", lambda: self.run_task("Startup report", startup.export_startup_report))
        self._add_button(row, "Startup Folder", lambda: self.run_task("Open startup folder", startup.open_user_startup_folder), width=160)
        self._add_button(row, "Startup Settings", lambda: self.run_task("Startup settings", performance.open_startup_apps), width=170)
        self.startup_frame = self._section("Entries")
        self.load_startup_entries()

    def load_startup_entries(self) -> None:
        self.run_task("Load startup entries", startup.list_startup_apps, on_done=self._render_startup_entries, show_output=False)

    def _render_startup_entries(self, entries) -> None:
        frame = getattr(self, "startup_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(entries, ActionResult):
            self.show_result(entries)
            return
        self.current_startup = entries
        if not self._safe_clear_frame(frame):
            return
        ctk.CTkLabel(frame, text=f"{len(entries)} startup entries found.").pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        for entry in entries[:120]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=entry.name, width=210, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=entry.source, width=130, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=entry.command, anchor="w", wraplength=620).pack(side="left", fill="x", expand=True)
        if len(entries) > 120:
            ctk.CTkLabel(frame, text="Showing first 120 entries. Export CSV for the full list.").pack(
                anchor="w", padx=10, pady=8
            )

    def show_apps(self) -> None:
        self._select_nav("Apps")
        self._clear_page()
        self._header("Apps", "Installed app inventory, size hints, bloatware hints, export, and safe uninstall launchers.")
        top = self._button_row()
        self._add_button(top, "Refresh", self.load_installed_apps)
        self._add_button(top, "Export CSV", lambda: self.run_task("Installed apps report", apps.export_installed_apps_report))
        self.app_search = ctk.StringVar()
        self.app_search.trace_add("write", lambda *_: self._render_apps(self.current_apps))
        ctk.CTkEntry(top, placeholder_text="Filter apps", textvariable=self.app_search, width=260).pack(
            side="left", padx=(8, 0), pady=4
        )
        self.apps_frame = self._section("Installed Apps")
        self.load_installed_apps()

    def load_installed_apps(self) -> None:
        self.run_task("Load installed apps", apps.list_installed_apps, on_done=self._render_apps, show_output=False)

    def _render_apps(self, app_rows) -> None:
        frame = getattr(self, "apps_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(app_rows, ActionResult):
            self.show_result(app_rows)
            return
        self.current_apps = app_rows
        search_var = getattr(self, "app_search", None)
        query = search_var.get().strip().lower() if search_var else ""
        filtered = [
            app for app in app_rows if not query or query in app.name.lower() or query in app.publisher.lower()
        ]
        if not self._safe_clear_frame(frame):
            return
        ctk.CTkLabel(
            frame,
            text=f"{len(filtered)} shown of {len(app_rows)} installed apps.",
        ).pack(anchor="w", padx=10, pady=(10, 6))
        for app in filtered[:150]:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=app.name, width=250, anchor="w", wraplength=240).pack(side="left")
            ctk.CTkLabel(row, text=app.version or "-", width=100, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=human_bytes(app.size_bytes), width=90, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=app.publisher or "-", anchor="w", wraplength=260).pack(side="left", fill="x", expand=True)
            if app.install_location:
                ctk.CTkButton(
                    row,
                    text="Open",
                    width=64,
                    height=28,
                    corner_radius=6,
                    command=lambda item=app: self.run_task("Open app folder", lambda: apps.open_install_location(item)),
                ).pack(side="left", padx=(6, 0))
            if app.uninstall_string:
                ctk.CTkButton(
                    row,
                    text="Uninstall",
                    width=82,
                    height=28,
                    corner_radius=6,
                    fg_color="#b91c1c",
                    hover_color="#991b1b",
                    command=lambda item=app: self.uninstall_confirm(item),
                ).pack(side="left", padx=(6, 0))
        if len(filtered) > 150:
            ctk.CTkLabel(frame, text="Showing first 150 matches. Filter or export for more.").pack(
                anchor="w", padx=10, pady=8
            )

    def uninstall_confirm(self, app: apps.InstalledApp) -> None:
        if self.confirm("Uninstall app", f"Start the uninstaller for {app.name}?"):
            self.run_task("Uninstall app", lambda: apps.run_uninstaller(app))

    def show_network(self) -> None:
        self._select_nav("Network")
        self._clear_page()
        self._header("Network", "Network info, ping tests, DNS flush, and guarded repair commands.")
        top = self._button_row()
        self._add_button(top, "Refresh", lambda: self.load_network())
        self._add_button(top, "Public IP", lambda: self.load_network(include_public_ip=True))
        self._add_button(top, "Flush DNS", lambda: self.run_task("Flush DNS", network.flush_dns))
        self._add_button(top, "Network Settings", lambda: self.run_task("Network settings", network.open_network_settings), width=170)
        self.network_frame = self._section("Network Summary")
        ping = self._section("Ping Test")
        ping_row = self._button_row(ping)
        self.ping_host_var = ctk.StringVar(value="1.1.1.1")
        ctk.CTkEntry(ping_row, textvariable=self.ping_host_var, width=220).pack(side="left", padx=(0, 8), pady=4)
        self._add_button(ping_row, "Ping", lambda: self.run_task("Ping", lambda: network.ping_host(self.ping_host_var.get())))
        repair = self._section("Repair")
        row = self._button_row(repair)
        self._add_button(row, "Renew IP", lambda: self.run_task("Renew IP", network.renew_ip))
        self._add_button(row, "Release IP", lambda: self.run_task("Release IP", network.release_ip))
        self._add_button(row, "Reset Winsock", self.reset_winsock_confirm, danger=True, width=150)
        self._add_button(row, "Reset TCP/IP", self.reset_tcp_confirm, danger=True, width=150)
        self._add_button(row, "Firewall", lambda: self.run_task("Firewall settings", network.open_firewall_settings))
        self.load_network()

    def load_network(self, *, include_public_ip: bool = False) -> None:
        self.run_task(
            "Load network",
            lambda: network.get_network_summary(include_public_ip=include_public_ip),
            on_done=self._render_network,
            show_output=False,
        )

    def _render_network(self, summary) -> None:
        frame = getattr(self, "network_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(summary, ActionResult):
            self.show_result(summary)
            return
        if not self._safe_clear_frame(frame):
            return
        rows = [
            ("Local IP", summary["local_ip"]),
            ("Public IP", summary["public_ip"]),
            ("Gateway", summary["gateway"]),
            ("DNS", ", ".join(summary["dns_servers"]) or "Unknown"),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w", wraplength=720).pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(frame, text="Adapters", font=ctk.CTkFont(weight="bold")).pack(
            anchor="w", padx=10, pady=(12, 4)
        )
        for adapter in summary["adapters"]:
            ctk.CTkLabel(
                frame,
                text=network.format_adapter(adapter),
                anchor="w",
                wraplength=880,
            ).pack(fill="x", padx=10, pady=3)

    def reset_winsock_confirm(self) -> None:
        if self.confirm("Reset Winsock", "Reset Winsock? A restart is usually needed afterward."):
            self.run_task("Reset Winsock", network.reset_winsock)

    def reset_tcp_confirm(self) -> None:
        if self.confirm("Reset TCP/IP", "Reset TCP/IP? A restart is usually needed afterward."):
            self.run_task("Reset TCP/IP", network.reset_tcp_ip)

    def show_storage(self) -> None:
        self._select_nav("Storage")
        self._clear_page()
        self._header("Storage", "Scan common folders, find large files, and export storage reports.")
        row = self._button_row()
        self._add_button(row, "Folder Summary", self.load_folder_summary)
        self._add_button(row, "Choose Folder", self.choose_storage_folder)
        self._add_button(row, "Scan Large Files", self.scan_large_files, width=170)
        self._add_button(row, "Export Results", self.export_large_files_results, width=160)
        scan_row = self._button_row()
        ctk.CTkLabel(scan_row, text="Root:").pack(side="left", padx=(0, 6))
        self.storage_root_label = ctk.CTkLabel(scan_row, text=str(self.storage_root), anchor="w", wraplength=650)
        self.storage_root_label.pack(side="left", fill="x", expand=True)
        self.min_size_var = ctk.StringVar(value="100")
        ctk.CTkLabel(scan_row, text="Min MB").pack(side="left", padx=(8, 4))
        ctk.CTkEntry(scan_row, textvariable=self.min_size_var, width=80).pack(side="left")
        self.storage_frame = self._section("Storage Results")
        self.load_folder_summary()

    def choose_storage_folder(self) -> None:
        selected = filedialog.askdirectory(parent=self, initialdir=str(self.storage_root))
        if selected:
            self.storage_root = Path(selected)
            self.storage_root_label.configure(text=str(self.storage_root))

    def load_folder_summary(self) -> None:
        self.run_task("Folder summary", storage.folder_size_summary, on_done=self._render_folder_summary, show_output=False)

    def _render_folder_summary(self, rows) -> None:
        frame = getattr(self, "storage_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(rows, ActionResult):
            self.show_result(rows)
            return
        if not self._safe_clear_frame(frame):
            return
        for row_data in rows:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(row, text=row_data["name"], width=140, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=human_bytes(row_data["size_bytes"]), width=110, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=row_data["path"], anchor="w", wraplength=640).pack(side="left", fill="x", expand=True)

    def scan_large_files(self) -> None:
        try:
            min_mb = max(1, int(self.min_size_var.get()))
        except ValueError:
            min_mb = 100
            self.min_size_var.set("100")
        self.run_task(
            "Scan large files",
            lambda: storage.find_large_files(self.storage_root, min_size_mb=min_mb),
            on_done=self._render_large_files,
            show_output=False,
        )

    def _render_large_files(self, findings) -> None:
        frame = getattr(self, "storage_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(findings, ActionResult):
            self.show_result(findings)
            return
        self.storage_findings = findings
        if not self._safe_clear_frame(frame):
            return
        ctk.CTkLabel(frame, text=f"{len(findings)} large file(s) found.").pack(
            anchor="w", padx=10, pady=(10, 6)
        )
        for finding in findings:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=3)
            ctk.CTkLabel(row, text=finding.size_human, width=100, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=finding.category, width=120, anchor="w").pack(side="left")
            ctk.CTkLabel(row, text=finding.path, anchor="w", wraplength=680).pack(side="left", fill="x", expand=True)

    def export_large_files_results(self) -> None:
        if not self.storage_findings:
            messagebox.showinfo("Storage", "Run a large file scan first.", parent=self)
            return
        self.run_task(
            "Export large files",
            lambda: storage.export_large_files_report(self.storage_root, self.storage_findings),
        )

    def show_files_tweaks(self) -> None:
        self._select_nav("Files & Tweaks")
        self._clear_page()
        self._header("Files & Tweaks", "Explorer toggles, useful folders, display shortcuts, and Windows theme controls.")
        settings = registry_tweaks.get_explorer_settings()
        status = self._section("Explorer Status")
        ctk.CTkLabel(
            status,
            text=(
                f"Hidden files: {'shown' if settings['show_hidden_files'] else 'hidden'}    "
                f"File extensions: {'shown' if settings['show_file_extensions'] else 'hidden'}    "
                f"Windows theme: {registry_tweaks.get_windows_theme()}"
            ),
            anchor="w",
        ).pack(fill="x", padx=10, pady=10)
        row = self._button_row()
        self._add_button(row, "Toggle Hidden Files", self.toggle_hidden_files, width=190)
        self._add_button(row, "Toggle Extensions", self.toggle_file_extensions, width=180)
        self._add_button(row, "Toggle Windows Theme", self.toggle_windows_theme, width=200)
        self._add_button(row, "Restart Explorer", lambda: self.run_task("Restart Explorer", performance.restart_explorer), width=170)

        folders = self._section("Useful Folders")
        row = self._button_row(folders)
        for label, folder in [
            ("Downloads", "downloads"),
            ("Desktop", "desktop"),
            ("Documents", "documents"),
            ("AppData", "appdata"),
            ("LocalAppData", "localappdata"),
            ("Temp", "temp"),
        ]:
            self._add_button(row, label, lambda key=folder: self.run_task("Open folder", lambda: open_path(known_folder(key))), width=130)

        windows = self._section("Windows Shortcuts")
        row = self._button_row(windows)
        self._add_button(row, "Night Light", lambda: self.run_task("Night Light", registry_tweaks.open_night_light_settings))
        self._add_button(row, "Bluetooth", lambda: self.run_task("Bluetooth", registry_tweaks.open_bluetooth_settings))
        self._add_button(row, "Wi-Fi", lambda: self.run_task("Wi-Fi", registry_tweaks.open_wifi_settings))
        self._add_button(row, "Focus", lambda: self.run_task("Focus", registry_tweaks.open_focus_settings))
        self._add_button(row, "Settings", lambda: self.run_task("Settings", registry_tweaks.open_settings_home))

    def toggle_hidden_files(self) -> None:
        self.run_task("Toggle hidden files", registry_tweaks.toggle_hidden_files, on_done=lambda _: self.show_files_tweaks())

    def toggle_file_extensions(self) -> None:
        self.run_task("Toggle file extensions", registry_tweaks.toggle_file_extensions, on_done=lambda _: self.show_files_tweaks())

    def toggle_windows_theme(self) -> None:
        self.run_task("Toggle Windows theme", registry_tweaks.toggle_windows_theme, on_done=lambda _: self.show_files_tweaks())

    def show_security(self) -> None:
        self._select_nav("Security")
        self._clear_page()
        self._header("Security", "Defender, firewall, TPM, Secure Boot, and Windows Security launchers.")
        row = self._button_row()
        self._add_button(row, "Snapshot", self.load_security_snapshot)
        self._add_button(row, "Windows Security", lambda: self.run_task("Windows Security", security.open_windows_security), width=170)
        self._add_button(row, "Quick Scan", lambda: self.run_task("Defender Quick Scan", security.run_defender_quick_scan))
        self._add_button(row, "Update Defender", lambda: self.run_task("Defender definitions", security.update_defender_definitions), width=170)
        self._add_button(row, "Advanced Firewall", lambda: self.run_task("Advanced firewall", security.open_advanced_firewall), width=170)
        self.security_frame = self._section("Security Snapshot")
        self.load_security_snapshot()

    def load_security_snapshot(self) -> None:
        self.run_task("Security snapshot", security.get_security_snapshot, on_done=self._render_security_snapshot, show_output=False)

    def _render_security_snapshot(self, snapshot) -> None:
        frame = getattr(self, "security_frame", None)
        if not self._widget_alive(frame):
            return
        if isinstance(snapshot, ActionResult):
            self.show_result(snapshot)
            return
        if not self._safe_clear_frame(frame):
            return
        rows = [
            ("Defender", snapshot["defender_raw"]),
            ("Firewall", snapshot["firewall_raw"]),
            ("Secure Boot", snapshot["secure_boot"]),
            ("TPM", snapshot["tpm"]),
        ]
        for label, value in rows:
            row = ctk.CTkFrame(frame, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(row, text=label, width=120, anchor="w", text_color="#9ca3af").pack(side="left")
            ctk.CTkLabel(row, text=value or "Unknown", anchor="w", wraplength=760).pack(side="left", fill="x", expand=True)

    def show_backup(self) -> None:
        self._select_nav("Backup")
        self._clear_page()
        self._header("Backup", "Restore points and WinPilot settings backups before bigger changes.")
        row = self._button_row()
        self._add_button(row, "Create Restore Point", self.restore_point_confirm, width=200)
        self._add_button(row, "Restore Point Status", lambda: self.run_task("Restore point status", backup.get_restore_point_status), width=190)
        self._add_button(row, "System Restore", lambda: self.run_task("System restore", backup.open_system_restore), width=160)
        self._add_button(row, "Backup Settings", lambda: self.run_task("Backup settings", backup.backup_tool_settings), width=170)
        info = self._section("Safety Notes")
        ctk.CTkLabel(
            info,
            text=(
                "Registry tweaks and repair commands are easier to trust when a restore point exists. "
                "Windows may limit restore point creation frequency."
            ),
            wraplength=820,
            anchor="w",
        ).pack(fill="x", padx=10, pady=10)

    def restore_point_confirm(self) -> None:
        if self.confirm("Create Restore Point", "Create a Windows restore point now?"):
            self.run_task("Create restore point", backup.create_restore_point)

    def show_reports(self) -> None:
        self._select_nav("Reports")
        self._clear_page()
        self._header("Reports", "Export PC health, startup, apps, storage, and open the reports folder.")
        row = self._button_row()
        self._add_button(row, "Health MD", lambda: self.run_task("Health report", reports.export_health_report_markdown))
        self._add_button(row, "Health JSON", lambda: self.run_task("Health JSON", reports.export_health_report_json))
        self._add_button(row, "Startup CSV", lambda: self.run_task("Startup report", startup.export_startup_report))
        self._add_button(row, "Apps CSV", lambda: self.run_task("Apps report", apps.export_installed_apps_report))
        self._add_button(row, "Open Reports", lambda: self.run_task("Open reports", reports.open_reports_folder))
        info = self._section("Output")
        ctk.CTkLabel(info, text=f"Reports are saved under {BASE_DIR / 'reports'}", anchor="w", wraplength=850).pack(
            fill="x", padx=10, pady=10
        )

    def show_settings(self) -> None:
        self._select_nav("Settings")
        self._clear_page()
        self._header("Settings", "App behavior, theme, confirmations, and safety preferences.")
        frame = self._section("App Settings")
        self.theme_var = ctk.StringVar(value=self.config_data.get("theme", "dark"))
        self.close_to_tray_var = ctk.BooleanVar(value=self.config_data.get("close_to_tray", True))
        self.beginner_var = ctk.BooleanVar(value=self.config_data.get("beginner_mode", True))
        self.confirm_var = ctk.BooleanVar(value=self.config_data.get("confirm_risky_actions", True))
        self.recycle_var = ctk.BooleanVar(value=self.config_data.get("use_recycle_bin_by_default", True))

        theme_row = ctk.CTkFrame(frame, fg_color="transparent")
        theme_row.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(theme_row, text="Theme", width=180, anchor="w").pack(side="left")
        ctk.CTkSegmentedButton(theme_row, values=["dark", "light"], variable=self.theme_var).pack(side="left")

        for text, var in [
            ("Close to tray", self.close_to_tray_var),
            ("Beginner mode", self.beginner_var),
            ("Confirm risky actions", self.confirm_var),
            ("Use Recycle Bin by default", self.recycle_var),
        ]:
            ctk.CTkCheckBox(frame, text=text, variable=var).pack(anchor="w", padx=10, pady=6)

        row = self._button_row(frame)
        self._add_button(row, "Save Settings", self.save_settings)
        self._add_button(row, "Backup Settings", lambda: self.run_task("Backup settings", backup.backup_tool_settings), width=170)

    def save_settings(self) -> None:
        self.config_data.update(
            {
                "theme": self.theme_var.get(),
                "close_to_tray": self.close_to_tray_var.get(),
                "beginner_mode": self.beginner_var.get(),
                "confirm_risky_actions": self.confirm_var.get(),
                "use_recycle_bin_by_default": self.recycle_var.get(),
            }
        )
        save_config(self.config_data)
        ctk.set_appearance_mode(self.config_data["theme"])
        self.show_result(ActionResult("Settings", True, "Settings saved."))

    def toggle_app_theme(self) -> None:
        current = self.config_data.get("theme", "dark")
        new_theme = "light" if current == "dark" else "dark"
        self.config_data["theme"] = new_theme
        save_config(self.config_data)
        ctk.set_appearance_mode(new_theme)
        self.show_result(ActionResult("Theme", True, f"App theme changed to {new_theme}."))
