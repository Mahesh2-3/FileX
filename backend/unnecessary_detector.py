"""
Unnecessary File Detector Module
Identifies potentially redundant, temporary, or clutter files:
- Copy patterns: 'file (1).ext', 'file - Copy.ext'
- Backup files: '*.bak', '*_backup.*', 'old_copy.*'
- Temp files: 'temp_*', '*.tmp', '~*'
- Empty/Zero-byte files
Flags with transparent diagnostic reasons for user confirmation.
"""

import re
from pathlib import Path
from typing import List, Dict, Any

TEMP_PREFIXES = ("temp_", "tmp_", "~$", "cache_", "thumb_")
TEMP_EXTENSIONS = {".tmp", ".temp", ".log", ".bak", ".swp", ".old", ".part", ".crdownload"}
BACKUP_KEYWORDS = ["backup", "old_copy", "copy_of", "version_old", "_bak", "-backup"]

COPY_PATTERN = re.compile(r"^(.*?)\s*(\(\d+\)|[-_ ]copy(\s*\d+)?)$", re.IGNORECASE)


class UnnecessaryDetector:
    @staticmethod
    def inspect_file(file_info: Dict[str, Any]) -> Dict[str, Any] | None:
        """
        Inspects a single file and returns detection metadata if flagged, or None if clean.
        """
        name = file_info.get("name", "")
        stem = file_info.get("stem", "")
        ext = file_info.get("extension", "").lower()
        size = file_info.get("size_bytes", 0)
        reasons = []
        confidence = "medium"

        # 1. Zero-byte empty files
        if size == 0:
            reasons.append("Empty file (0 bytes)")
            confidence = "high"

        # 2. Temp extension
        if ext in TEMP_EXTENSIONS:
            reasons.append(f"Temporary file extension ({ext})")
            confidence = "high"

        # 3. Temp prefix or pattern
        stem_lower = stem.lower()
        if any(stem_lower.startswith(prefix) for prefix in TEMP_PREFIXES) or stem_lower.startswith("~"):
            reasons.append("Temporary file naming prefix")
            confidence = "high"

        # 4. Copy suffix like "file (1).jpg" or "file - Copy.png"
        match = COPY_PATTERN.match(stem)
        if match:
            reasons.append(f"Redundant numbered copy pattern: '{match.group(2)}'")
            confidence = "medium"

        # 5. Backup keywords in filename
        for kw in BACKUP_KEYWORDS:
            if kw in stem_lower:
                reasons.append(f"Identified as backup/archive copy containing '{kw}'")
                confidence = "medium"
                break

        if reasons:
            return {
                "file": file_info,
                "reasons": reasons,
                "primary_reason": "; ".join(reasons),
                "confidence": confidence,
                "suggested_action": "review_delete",
            }

        return None

    @classmethod
    def scan_for_unnecessary(cls, files: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        unnecessary = []
        for f in files:
            res = cls.inspect_file(f)
            if res:
                unnecessary.append(res)
        return unnecessary
