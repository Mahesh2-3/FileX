"""
Path Controller Module
Enforces strict security boundaries to restrict all operations to the user-selected folder.
Prevents path traversal, unauthorized access to system root folders or restricted directories.
"""

from pathlib import Path
import os
import sys

# Sensitive or dangerous system directories on Windows/Unix that must be blocked
FORBIDDEN_PATTERNS = [
    r"c:\windows",
    r"c:\program files",
    r"c:\program files (x86)",
    r"c:\system volume information",
    r"c:\recovery",
    r"/bin",
    r"/sbin",
    r"/usr",
    r"/etc",
    r"/var",
    r"/sys",
    r"/proc",
    r"/dev",
]


class PathSecurityException(Exception):
    pass


class PathController:
    def __init__(self, allowed_root: str | Path | None = None):
        self.allowed_root: Path | None = None
        if allowed_root:
            self.set_allowed_root(allowed_root)

    def set_allowed_root(self, root_path: str | Path) -> Path:
        """
        Validates and sets the allowed root folder for all subsequent operations.
        """
        try:
            path = Path(root_path).resolve()
        except Exception as e:
            raise PathSecurityException(f"Invalid path format: {e}")

        if not path.exists():
            raise PathSecurityException(f"Directory does not exist: {path}")

        if not path.is_dir():
            raise PathSecurityException(f"Specified path is not a directory: {path}")

        # Check if root is system drive root or restricted folder
        norm_str = str(path).lower().rstrip("/\\")
        
        # Check if it's a drive root like 'C:\'
        if path.parent == path:
            raise PathSecurityException(
                "Access to entire drive root (e.g., C:\\) is restricted for safety. Please select a specific folder."
            )

        for forbidden in FORBIDDEN_PATTERNS:
            if norm_str == forbidden or norm_str.startswith(forbidden + "\\") or norm_str.startswith(forbidden + "/"):
                raise PathSecurityException(
                    f"Access to protected system location '{path}' is blocked for safety."
                )

        self.allowed_root = path
        return self.allowed_root

    def validate_path(self, target_path: str | Path) -> Path:
        """
        Validates that target_path exists and is strictly inside the allowed_root boundary.
        """
        if self.allowed_root is None:
            raise PathSecurityException("No working directory has been selected or validated yet.")

        try:
            resolved = Path(target_path).resolve()
        except Exception as e:
            raise PathSecurityException(f"Invalid path: {e}")

        # Path must be equal to or a sub-path of allowed_root
        try:
            resolved.relative_to(self.allowed_root)
        except ValueError:
            raise PathSecurityException(
                f"Path '{resolved}' violates the security boundary and is outside the allowed directory '{self.allowed_root}'."
            )

        return resolved

    def validate_target_destination(self, dest_path: str | Path) -> Path:
        """
        Validates a new target destination path (which may not exist yet) to ensure
        it resides strictly within allowed_root.
        """
        if self.allowed_root is None:
            raise PathSecurityException("No working directory has been selected or validated yet.")

        try:
            resolved = Path(dest_path).resolve()
        except Exception as e:
            raise PathSecurityException(f"Invalid destination path: {e}")

        try:
            resolved.relative_to(self.allowed_root)
        except ValueError:
            raise PathSecurityException(
                f"Destination path '{resolved}' is outside the allowed directory '{self.allowed_root}'."
            )

        return resolved
