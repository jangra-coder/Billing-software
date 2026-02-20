"""
SQLite connection manager — thread-safe singleton with WAL mode.
"""

import sqlite3
import threading
from pathlib import Path

from config import DB_PATH, DB_JOURNAL_MODE, DB_FOREIGN_KEYS, DB_BUSY_TIMEOUT_MS


class DatabaseConnection:
    """Thread-safe singleton that hands out ONE connection per thread."""

    _instances: dict[int, sqlite3.Connection] = {}
    _lock = threading.Lock()

    @classmethod
    def get(cls, db_path: Path | str = DB_PATH) -> sqlite3.Connection:
        """Return the connection for the calling thread, creating it if needed."""
        tid = threading.get_ident()
        if tid not in cls._instances or cls._instances[tid] is None:
            with cls._lock:
                # Double-check after acquiring lock
                if tid not in cls._instances or cls._instances[tid] is None:
                    conn = sqlite3.connect(
                        str(db_path),
                        timeout=DB_BUSY_TIMEOUT_MS / 1000,
                        check_same_thread=False,
                    )
                    conn.row_factory = sqlite3.Row
                    conn.execute(f"PRAGMA journal_mode={DB_JOURNAL_MODE}")
                    if DB_FOREIGN_KEYS:
                        conn.execute("PRAGMA foreign_keys=ON")
                    conn.execute("PRAGMA busy_timeout=5000")
                    cls._instances[tid] = conn
        return cls._instances[tid]

    @classmethod
    def close_all(cls) -> None:
        """Close every open connection (call on app shutdown)."""
        with cls._lock:
            for conn in cls._instances.values():
                try:
                    conn.close()
                except Exception:
                    pass
            cls._instances.clear()

    @classmethod
    def close_current(cls) -> None:
        """Close the connection belonging to the calling thread."""
        tid = threading.get_ident()
        with cls._lock:
            conn = cls._instances.pop(tid, None)
            if conn:
                try:
                    conn.close()
                except Exception:
                    pass


def get_db() -> sqlite3.Connection:
    """Convenience shortcut used throughout the codebase."""
    return DatabaseConnection.get()
