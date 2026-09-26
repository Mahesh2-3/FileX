"""
Database and Operation History Module
Uses SQLite to store scanned file analysis, planned operations, and executed action history.
Supports tracking, auditing, and one-click undo/restore.
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

DB_FILE_NAME = "file_manager.db"


class Database:
    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            # Place DB in current project root
            self.db_path = Path(__file__).resolve().parent.parent / DB_FILE_NAME
        else:
            self.db_path = Path(db_path)

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_conn() as conn:
            cursor = conn.cursor()

            # Operations log table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS operations_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id TEXT,
                    operation_type TEXT NOT NULL,      -- rename, move, delete, organize
                    original_path TEXT NOT NULL,
                    original_name TEXT NOT NULL,
                    new_path TEXT,
                    new_name TEXT,
                    status TEXT NOT NULL,              -- executed, reverted, failed
                    ai_suggestion TEXT,
                    ai_reasoning TEXT,
                    backup_location TEXT,              -- for deleted files
                    executed_at TEXT NOT NULL,
                    reverted_at TEXT,
                    error_message TEXT,
                    metadata_json TEXT
                )
            """)

            # Settings table for API keys, offline toggle, custom preferences
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()

    def log_operation(
        self,
        batch_id: str,
        operation_type: str,
        original_path: str,
        original_name: str,
        new_path: Optional[str] = None,
        new_name: Optional[str] = None,
        status: str = "executed",
        ai_suggestion: Optional[str] = None,
        ai_reasoning: Optional[str] = None,
        backup_location: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> int:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_str = json.dumps(metadata or {})

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO operations_history (
                    batch_id, operation_type, original_path, original_name,
                    new_path, new_name, status, ai_suggestion, ai_reasoning,
                    backup_location, executed_at, error_message, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                batch_id, operation_type, original_path, original_name,
                new_path, new_name, status, ai_suggestion, ai_reasoning,
                backup_location, now_str, error_message, meta_str
            ))
            conn.commit()
            return cursor.lastrowid

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM operations_history 
                ORDER BY id DESC LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_operation_by_id(self, op_id: int) -> Optional[Dict[str, Any]]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM operations_history WHERE id = ?", (op_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def mark_reverted(self, op_id: int):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE operations_history 
                SET status = 'reverted', reverted_at = ? 
                WHERE id = ?
            """, (now_str, op_id))
            conn.commit()

    def set_setting(self, key: str, value: str):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO app_settings (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
            """, (key, value, now_str))
            conn.commit()

    def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def get_all_settings(self) -> Dict[str, str]:
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT key, value FROM app_settings")
            rows = cursor.fetchall()
            return {row["key"]: row["value"] for row in rows}
