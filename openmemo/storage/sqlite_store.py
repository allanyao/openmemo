"""
SQLite storage backend - the default store.

Stores notes, MemCells, MemScenes, and skills in a local SQLite database.
Zero configuration, works out of the box.
"""

import json
import sqlite3
import os
from typing import List, Optional
from openmemo.storage.base_store import BaseStore


class SQLiteStore(BaseStore):
    def __init__(self, db_path: str = "openmemo.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                timestamp REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS cells (
                id TEXT PRIMARY KEY,
                note_id TEXT,
                content TEXT NOT NULL,
                facts TEXT DEFAULT '[]',
                stage TEXT DEFAULT 'exploration',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                created_at REAL,
                connections TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT,
                cell_ids TEXT DEFAULT '[]',
                theme TEXT,
                created_at REAL,
                updated_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                pattern TEXT,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                created_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS pyramid (
                id TEXT PRIMARY KEY,
                tier TEXT,
                content TEXT,
                source_ids TEXT DEFAULT '[]',
                created_at REAL,
                metadata TEXT DEFAULT '{}'
            );
        """)
        self.conn.commit()

    def put_note(self, note: dict) -> str:
        note_id = note.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO notes (id, content, source, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
            (note_id, note.get("content", ""), note.get("source", "manual"),
             note.get("timestamp", 0), json.dumps(note.get("metadata", {})))
        )
        self.conn.commit()
        return note_id

    def get_note(self, note_id: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes WHERE id = ?", (note_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_note(row)

    def list_notes(self, limit: int = 100, offset: int = 0) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM notes ORDER BY timestamp DESC LIMIT ? OFFSET ?", (limit, offset))
        return [self._row_to_note(row) for row in cursor.fetchall()]

    def delete_note(self, note_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def put_cell(self, cell: dict) -> str:
        cell_id = cell.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO cells
            (id, note_id, content, facts, stage, importance, access_count, last_accessed, created_at, connections, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cell_id, cell.get("note_id", ""), cell.get("content", ""),
             json.dumps(cell.get("facts", [])), cell.get("stage", "exploration"),
             cell.get("importance", 0.5), cell.get("access_count", 0),
             cell.get("last_accessed", 0), cell.get("created_at", 0),
             json.dumps(cell.get("connections", [])), json.dumps(cell.get("metadata", {})))
        )
        self.conn.commit()
        return cell_id

    def get_cell(self, cell_id: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cells WHERE id = ?", (cell_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_cell(row)

    def list_cells(self, limit: int = 100, offset: int = 0) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM cells ORDER BY created_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [self._row_to_cell(row) for row in cursor.fetchall()]

    def put_scene(self, scene: dict) -> str:
        scene_id = scene.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO scenes
            (id, title, summary, cell_ids, theme, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (scene_id, scene.get("title", ""), scene.get("summary", ""),
             json.dumps(scene.get("cell_ids", [])), scene.get("theme", ""),
             scene.get("created_at", 0), scene.get("updated_at", 0),
             json.dumps(scene.get("metadata", {})))
        )
        self.conn.commit()
        return scene_id

    def get_scene(self, scene_id: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scenes WHERE id = ?", (scene_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_scene(row)

    def list_scenes(self, limit: int = 100, offset: int = 0) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM scenes ORDER BY updated_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [self._row_to_scene(row) for row in cursor.fetchall()]

    def put_skill(self, skill: dict) -> str:
        skill_id = skill.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO skills
            (id, name, description, pattern, usage_count, success_rate, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, skill.get("name", ""), skill.get("description", ""),
             skill.get("pattern", ""), skill.get("usage_count", 0),
             skill.get("success_rate", 0.0), skill.get("created_at", 0),
             json.dumps(skill.get("metadata", {})))
        )
        self.conn.commit()
        return skill_id

    def list_skills(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM skills ORDER BY usage_count DESC")
        return [self._row_to_skill(row) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()

    def _row_to_note(self, row) -> dict:
        return {
            "id": row["id"], "content": row["content"], "source": row["source"],
            "timestamp": row["timestamp"], "metadata": json.loads(row["metadata"] or "{}"),
        }

    def _row_to_cell(self, row) -> dict:
        return {
            "id": row["id"], "note_id": row["note_id"], "content": row["content"],
            "facts": json.loads(row["facts"] or "[]"), "stage": row["stage"],
            "importance": row["importance"], "access_count": row["access_count"],
            "last_accessed": row["last_accessed"], "created_at": row["created_at"],
            "connections": json.loads(row["connections"] or "[]"),
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    def _row_to_scene(self, row) -> dict:
        return {
            "id": row["id"], "title": row["title"], "summary": row["summary"],
            "cell_ids": json.loads(row["cell_ids"] or "[]"), "theme": row["theme"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    def _row_to_skill(self, row) -> dict:
        return {
            "id": row["id"], "name": row["name"], "description": row["description"],
            "pattern": row["pattern"], "usage_count": row["usage_count"],
            "success_rate": row["success_rate"], "created_at": row["created_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
