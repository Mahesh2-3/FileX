"""
Organization Engine and File Operations Module
Prepares, validates, and safely executes approved file system actions:
- Rename
- Move / Categorize into subfolders
- Safe delete / Recycle (using send2trash or local .trash repository)
- Undo / Restore past operations
Guarantees collision avoidance, path safety check, and complete database logging.
"""

from pathlib import Path
import shutil
import uuid
import os
from typing import List, Dict, Any, Optional

try:
    from send2trash import send2trash
except ImportError:
    send2trash = None

from backend.path_controller import PathController, PathSecurityException
from backend.database import Database


class OrganizationEngine:
    def __init__(self, path_controller: PathController, database: Database):
        self.path_controller = path_controller
        self.database = database

    def plan_operation(
        self,
        original_path: str | Path,
        suggested_name: Optional[str] = None,
        suggested_folder: Optional[str] = None,
        action_type: str = "organize",  # 'rename', 'move', 'organize', 'delete'
        ai_suggestion: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a proposed operation object for user review without modifying files.
        """
        orig_p = self.path_controller.validate_path(original_path)
        root = self.path_controller.allowed_root

        final_name = suggested_name.strip() if suggested_name else orig_p.name
        
        # Resolve target directory
        if action_type == "delete":
            target_dir = orig_p.parent
            target_p = orig_p
        elif suggested_folder:
            target_dir = (root / suggested_folder).resolve()
            target_p = target_dir / final_name
        else:
            target_dir = orig_p.parent
            target_p = target_dir / final_name

        # Validate destination within allowed root
        self.path_controller.validate_target_destination(target_p)

        # Check collision and calculate non-destructive target name if needed
        is_collision = target_p.exists() and target_p.resolve() != orig_p.resolve()
        safe_target_path = self._resolve_collision(target_p) if is_collision else target_p

        rel_source = str(orig_p.relative_to(root)).replace("\\", "/")
        rel_target = str(safe_target_path.relative_to(root)).replace("\\", "/") if action_type != "delete" else None

        target_folder_rel = None
        if action_type != "delete":
            try:
                rel = str(target_dir.relative_to(root)).replace("\\", "/")
                target_folder_rel = "" if rel == "." else rel
            except ValueError:
                target_folder_rel = str(target_dir).replace("\\", "/")

        return {
            "id": str(uuid.uuid4()),
            "action_type": action_type,
            "original_path": str(orig_p),
            "original_name": orig_p.name,
            "target_path": str(safe_target_path) if action_type != "delete" else None,
            "target_name": safe_target_path.name if action_type != "delete" else None,
            "target_folder": target_folder_rel,
            "suggested_name": safe_target_path.name if action_type != "delete" else orig_p.name,
            "suggested_folder": target_folder_rel if target_folder_rel is not None else "",
            "relative_source": rel_source,
            "relative_target": rel_target,
            "ai_suggestion": ai_suggestion or f"Move to {rel_target}",
            "ai_reasoning": ai_reasoning or "Contextual organization.",
            "is_collision": is_collision,
            "approved": True,  # Default to staged/selected for user review
        }

    def _resolve_collision(self, target_path: Path) -> Path:
        """
        Generates a non-conflicting filename by appending _1, _2, etc.
        """
        counter = 1
        stem = target_path.stem
        suffix = target_path.suffix
        parent = target_path.parent

        while True:
            candidate = parent / f"{stem}_{counter}{suffix}"
            if not candidate.exists():
                return candidate
            counter += 1

    def execute_batch(self, operations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Executes a batch of user-approved operations.
        """
        batch_id = str(uuid.uuid4())[:8]
        executed_count = 0
        failed_count = 0
        results = []

        for op in operations:
            if not op.get("approved", False):
                continue

            op_type = op.get("action_type", "organize")
            orig_path_str = op.get("original_path")
            target_path_str = op.get("target_path")

            try:
                orig_p = self.path_controller.validate_path(orig_path_str)

                if op_type == "delete":
                    # Safe delete: attempt send2trash, or move to .trash folder
                    backup_location = self._safe_delete(orig_p)
                    self.database.log_operation(
                        batch_id=batch_id,
                        operation_type="delete",
                        original_path=str(orig_p),
                        original_name=orig_p.name,
                        status="executed",
                        backup_location=backup_location,
                        ai_reasoning=op.get("ai_reasoning"),
                    )
                    results.append({"id": op.get("id"), "status": "executed", "action": "delete"})
                    executed_count += 1

                else:
                    # Move or Rename
                    target_p = self.path_controller.validate_target_destination(target_path_str)
                    
                    # Ensure parent folder exists
                    target_p.parent.mkdir(parents=True, exist_ok=True)

                    # Re-check collision before final move
                    if target_p.exists() and target_p.resolve() != orig_p.resolve():
                        target_p = self._resolve_collision(target_p)

                    # Perform file move
                    shutil.move(str(orig_p), str(target_p))

                    self.database.log_operation(
                        batch_id=batch_id,
                        operation_type=op_type,
                        original_path=str(orig_p),
                        original_name=orig_p.name,
                        new_path=str(target_p),
                        new_name=target_p.name,
                        status="executed",
                        ai_suggestion=op.get("ai_suggestion"),
                        ai_reasoning=op.get("ai_reasoning"),
                    )
                    results.append({
                        "id": op.get("id"),
                        "status": "executed",
                        "action": op_type,
                        "new_path": str(target_p),
                        "new_name": target_p.name,
                    })
                    executed_count += 1

            except Exception as e:
                failed_count += 1
                self.database.log_operation(
                    batch_id=batch_id,
                    operation_type=op_type,
                    original_path=orig_path_str,
                    original_name=Path(orig_path_str).name if orig_path_str else "unknown",
                    status="failed",
                    error_message=str(e),
                )
                results.append({"id": op.get("id"), "status": "failed", "error": str(e)})

        return {
            "batch_id": batch_id,
            "executed_count": executed_count,
            "failed_count": failed_count,
            "results": results,
        }

    def _safe_delete(self, path: Path) -> str:
        """
        Moves file to system recycle bin or safe local .trash directory for undoability.
        """
        # We always keep a local trash copy for reliable programmatic undo
        trash_dir = self.path_controller.allowed_root / ".ai_file_manager_trash"
        trash_dir.mkdir(parents=True, exist_ok=True)
        backup_p = trash_dir / f"{uuid.uuid4().hex[:6]}_{path.name}"
        shutil.move(str(path), str(backup_p))
        return str(backup_p)

    def undo_operation(self, op_id: int) -> Dict[str, Any]:
        """
        Reverts an operation from the database history.
        """
        op = self.database.get_operation_by_id(op_id)
        if not op:
            raise ValueError(f"Operation record #{op_id} not found.")

        if op["status"] == "reverted":
            raise ValueError(f"Operation #{op_id} has already been reverted.")

        op_type = op["operation_type"]
        original_path = Path(op["original_path"])
        new_path = Path(op["new_path"]) if op["new_path"] else None

        try:
            if op_type in {"rename", "move", "organize"}:
                if not new_path or not new_path.exists():
                    raise FileNotFoundError(f"Cannot undo: file no longer exists at '{new_path}'")

                # Ensure original directory exists
                original_path.parent.mkdir(parents=True, exist_ok=True)

                # Move back
                dest = original_path
                if dest.exists() and dest.resolve() != new_path.resolve():
                    dest = self._resolve_collision(dest)

                shutil.move(str(new_path), str(dest))
                self.database.mark_reverted(op_id)

                # Clean up empty parent folder if newly created
                try:
                    if new_path.parent != self.path_controller.allowed_root:
                        if not any(new_path.parent.iterdir()):
                            new_path.parent.rmdir()
                except Exception:
                    pass

                return {
                    "success": True,
                    "message": f"Successfully reverted '{new_path.name}' back to '{dest}'",
                    "restored_path": str(dest)
                }

            elif op_type == "delete":
                backup_loc = Path(op["backup_location"]) if op["backup_location"] else None
                if not backup_loc or not backup_loc.exists():
                    raise FileNotFoundError("Backup copy in trash was not found.")

                original_path.parent.mkdir(parents=True, exist_ok=True)
                dest = original_path
                if dest.exists():
                    dest = self._resolve_collision(dest)

                shutil.move(str(backup_loc), str(dest))
                self.database.mark_reverted(op_id)

                return {
                    "success": True,
                    "message": f"Restored deleted file back to '{dest}'",
                    "restored_path": str(dest)
                }

            else:
                raise ValueError(f"Unknown operation type: {op_type}")

        except Exception as e:
            raise RuntimeError(f"Undo failed: {e}")
