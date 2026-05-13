from __future__ import annotations

import csv
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from .utils import REPORT_DIR, ActionResult, get_folder_size, human_bytes, known_folder, timestamp_for_filename


@dataclass
class FileFinding:
    path: str
    size_bytes: int
    modified: str
    category: str

    @property
    def size_human(self) -> str:
        return human_bytes(self.size_bytes)


def common_scan_folders() -> dict[str, Path]:
    return {
        "Downloads": known_folder("downloads"),
        "Desktop": known_folder("desktop"),
        "Documents": known_folder("documents"),
        "Pictures": known_folder("pictures"),
        "Videos": known_folder("videos"),
        "AppData Cache": known_folder("localappdata"),
    }


def categorize_file(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".exe", ".msi", ".msix", ".appx"}:
        return "Installers"
    if suffix in {".zip", ".rar", ".7z", ".tar", ".gz"}:
        return "Archives"
    if suffix in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
        return "Large media"
    if suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp"}:
        return "Images"
    if suffix in {".bak", ".old", ".backup"}:
        return "Backups"
    if suffix in {".log", ".tmp", ".temp", ".dmp"}:
        return "Safe to delete"
    return "Unknown"


def find_large_files(
    root: Path,
    *,
    min_size_mb: int = 100,
    limit: int = 100,
    older_than_days: int | None = None,
) -> list[FileFinding]:
    findings: list[FileFinding] = []
    min_size = min_size_mb * 1024 * 1024
    cutoff = time.time() - older_than_days * 86400 if older_than_days else None

    if not root.exists():
        return findings

    for current_root, dirs, files in os.walk(root, onerror=lambda _: None):
        dirs[:] = [name for name in dirs if name not in {"node_modules", ".git", "__pycache__"}]
        for file_name in files:
            path = Path(current_root) / file_name
            try:
                stat = path.stat()
            except OSError:
                continue
            if stat.st_size < min_size:
                continue
            if cutoff and stat.st_mtime > cutoff:
                continue
            findings.append(
                FileFinding(
                    path=str(path),
                    size_bytes=stat.st_size,
                    modified=time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
                    category=categorize_file(path),
                )
            )
            findings.sort(key=lambda item: item.size_bytes, reverse=True)
            if len(findings) > limit * 2:
                findings = findings[:limit]
    return sorted(findings, key=lambda item: item.size_bytes, reverse=True)[:limit]


def find_duplicate_candidates(root: Path, *, min_size_mb: int = 10, limit: int = 100) -> list[tuple[str, list[str]]]:
    seen: dict[tuple[str, int], list[str]] = {}
    min_size = min_size_mb * 1024 * 1024
    if not root.exists():
        return []
    for current_root, dirs, files in os.walk(root, onerror=lambda _: None):
        dirs[:] = [name for name in dirs if name not in {"node_modules", ".git", "__pycache__"}]
        for file_name in files:
            path = Path(current_root) / file_name
            try:
                size = path.stat().st_size
            except OSError:
                continue
            if size < min_size:
                continue
            seen.setdefault((file_name.lower(), size), []).append(str(path))
    duplicates = [(name, paths) for (name, _), paths in seen.items() if len(paths) > 1]
    duplicates.sort(key=lambda item: len(item[1]), reverse=True)
    return duplicates[:limit]


def folder_size_summary() -> list[dict]:
    rows = []
    for name, path in common_scan_folders().items():
        rows.append(
            {
                "name": name,
                "path": str(path),
                "size_bytes": get_folder_size(path, limit_seconds=8),
            }
        )
    return sorted(rows, key=lambda row: row["size_bytes"], reverse=True)


def export_large_files_report(root: Path, findings: list[FileFinding]) -> ActionResult:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"large-files-{root.name or 'drive'}-{timestamp_for_filename()}.csv"
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=["path", "size_bytes", "size_human", "modified", "category"])
        writer.writeheader()
        for finding in findings:
            row = asdict(finding)
            row["size_human"] = finding.size_human
            writer.writerow(row)
    return ActionResult("Large Files Report", True, f"Exported {len(findings)} files.", str(path))

