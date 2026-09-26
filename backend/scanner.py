"""
File Scanner Module
Traverses the selected folder, collects file stats, determines mime/category,
and builds standardized file descriptor payloads.
"""

from pathlib import Path
from datetime import datetime
import os
from typing import List, Dict, Any

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".tiff", ".svg"}
VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv", ".webm", ".flv", ".m4v"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".flac", ".ogg", ".aac", ".wma"}
DOC_EXTS = {".pdf", ".docx", ".doc", ".txt", ".md", ".rtf", ".csv", ".xlsx", ".pptx"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".7z", ".rar"}


def get_file_category(extension: str) -> str:
    ext = extension.lower()
    if ext in IMAGE_EXTS:
        return "Images"
    elif ext in VIDEO_EXTS:
        return "Videos"
    elif ext in AUDIO_EXTS:
        return "Audio"
    elif ext in DOC_EXTS:
        return "Documents"
    elif ext in ARCHIVE_EXTS:
        return "Archives"
    return "Other"


def format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


class FileScanner:
    def __init__(self, root_dir: str | Path):
        self.root_dir = Path(root_dir).resolve()

    def scan(self, recursive: bool = False) -> List[Dict[str, Any]]:
        """
        Scans root directory and returns a list of file info dicts.
        """
        results: List[Dict[str, Any]] = []

        if not self.root_dir.exists() or not self.root_dir.is_dir():
            return results

        walker = self.root_dir.rglob("*") if recursive else self.root_dir.glob("*")

        for item in walker:
            try:
                if not item.is_file():
                    continue

                # Skip hidden files and temp DB lock files
                if item.name.startswith(".") or item.name.endswith(".db-journal"):
                    continue

                stat = item.stat()
                ext = item.suffix.lower()
                category = get_file_category(ext)
                rel_path = str(item.relative_to(self.root_dir)).replace("\\", "/")

                created_dt = datetime.fromtimestamp(stat.st_ctime)
                modified_dt = datetime.fromtimestamp(stat.st_mtime)

                results.append({
                    "name": item.name,
                    "stem": item.stem,
                    "extension": ext,
                    "full_path": str(item.resolve()),
                    "relative_path": rel_path,
                    "parent_dir": str(item.parent.resolve()),
                    "size_bytes": stat.st_size,
                    "size_formatted": format_size(stat.st_size),
                    "created_at": created_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "modified_at": modified_dt.strftime("%Y-%m-%d %H:%M:%S"),
                    "category": category,
                    "is_writable": os.access(item, os.W_OK),
                })
            except (PermissionError, FileNotFoundError, OSError):
                # Safely skip inaccessible files as per Section 19.1
                continue

        # Sort files by name
        results.sort(key=lambda x: x["name"].lower())
        return results
