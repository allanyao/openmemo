"""
Schema Migration Framework for OpenMemo.

Provides idempotent schema migrations for the SQLite storage backend.
Migrations are safe to run repeatedly — each migration checks preconditions
before applying changes.
"""

import logging
import sqlite3
import time
from typing import Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("openmemo.migration")

CURRENT_SCHEMA_VERSION = 2

Migration = Callable[[sqlite3.Connection], None]


def _migration_v1_to_v2(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()

    alterations: List[Tuple[str, str, str]] = [
        ("notes", "memory_type", "TEXT DEFAULT 'raw'"),
        ("notes", "scene", "TEXT DEFAULT ''"),
        ("notes", "fingerprint", "TEXT DEFAULT ''"),
        ("cells", "memory_type", "TEXT DEFAULT 'fact'"),
        ("cells", "scene", "TEXT DEFAULT ''"),
        ("cells", "fingerprint", "TEXT DEFAULT ''"),
    ]

    for table, column, col_def in alterations:
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")
        except sqlite3.OperationalError:
            pass

    conn.commit()


MIGRATIONS: Dict[int, Migration] = {
    2: _migration_v1_to_v2,
}


class SchemaMigrator:
    def __init__(self, db_path: str = "openmemo.db"):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_version_table(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schema_version (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                version INTEGER NOT NULL,
                updated_at REAL
            )
        """)
        cursor.execute("SELECT version FROM schema_version WHERE id = 1")
        row = cursor.fetchone()
        if row is None:
            cursor.execute(
                "INSERT INTO schema_version (id, version, updated_at) VALUES (1, 1, ?)",
                (time.time(),),
            )
        conn.commit()

    def get_schema_version(self, conn: Optional[sqlite3.Connection] = None) -> int:
        own_conn = conn is None
        if own_conn:
            conn = self._connect()
        try:
            self._ensure_version_table(conn)
            cursor = conn.cursor()
            cursor.execute("SELECT version FROM schema_version WHERE id = 1")
            row = cursor.fetchone()
            return int(row["version"]) if row else 1
        finally:
            if own_conn:
                conn.close()

    def run_migrations(self, target_version: Optional[int] = None) -> List[int]:
        if target_version is None:
            target_version = CURRENT_SCHEMA_VERSION

        conn = self._connect()
        try:
            current = self.get_schema_version(conn)
            applied: List[int] = []

            if current >= target_version:
                logger.info(
                    "Schema already at version %d (target %d), nothing to do.",
                    current,
                    target_version,
                )
                return applied

            for version in range(current + 1, target_version + 1):
                migration_fn = MIGRATIONS.get(version)
                if migration_fn is None:
                    raise ValueError(f"No migration found for version {version}")

                logger.info("Applying migration v%d → v%d …", version - 1, version)
                migration_fn(conn)

                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE schema_version SET version = ?, updated_at = ? WHERE id = 1",
                    (version, time.time()),
                )
                conn.commit()
                applied.append(version)
                logger.info("Migration to v%d complete.", version)

            return applied
        finally:
            conn.close()

    def rollback(self, target_version: int) -> int:
        conn = self._connect()
        try:
            current = self.get_schema_version(conn)

            if target_version >= current:
                logger.info(
                    "Current version %d is already at or below target %d, nothing to rollback.",
                    current,
                    target_version,
                )
                return current

            if target_version < 1:
                raise ValueError("Cannot rollback below version 1")

            logger.info(
                "Rolling back schema version from %d to %d (metadata only).",
                current,
                target_version,
            )

            cursor = conn.cursor()
            cursor.execute(
                "UPDATE schema_version SET version = ?, updated_at = ? WHERE id = 1",
                (target_version, time.time()),
            )
            conn.commit()

            logger.warning(
                "Schema version set to %d. Column additions from migrations are not removed "
                "(SQLite does not support DROP COLUMN in older versions). "
                "Re-run migrations to re-apply changes.",
                target_version,
            )

            return target_version
        finally:
            conn.close()
