"""
SQLite storage backend - the default store.

Stores notes, MemCells, MemScenes, skills, agents, conversations,
and memory edges in a local SQLite database. Zero configuration, works out of the box.

Thread-safety: Each thread gets its own SQLite connection via threading.local().
WAL mode is enabled so readers and writers don't block each other.
"""

import json
import sqlite3
import threading
import time
from typing import List, Optional
from openmemo.storage.base_store import BaseStore


class SQLiteStore(BaseStore):
    def __init__(self, db_path: str = "openmemo.db", check_same_thread: bool = True):
        self.db_path = db_path
        self._local = threading.local()
        self._create_tables()

    @property
    def conn(self) -> sqlite3.Connection:
        """Return a thread-local SQLite connection, creating one if needed."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            c = sqlite3.connect(self.db_path, check_same_thread=False)
            c.row_factory = sqlite3.Row
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA foreign_keys=ON")
            self._local.conn = c
        return self._local.conn

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT DEFAULT 'manual',
                agent_id TEXT DEFAULT '',
                scene TEXT DEFAULT '',
                scope TEXT DEFAULT 'private',
                conversation_id TEXT DEFAULT '',
                timestamp REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS cells (
                id TEXT PRIMARY KEY,
                note_id TEXT,
                content TEXT NOT NULL,
                cell_type TEXT DEFAULT 'fact',
                facts TEXT DEFAULT '[]',
                stage TEXT DEFAULT 'exploration',
                importance REAL DEFAULT 0.5,
                access_count INTEGER DEFAULT 0,
                last_accessed REAL,
                created_at REAL,
                agent_id TEXT DEFAULT '',
                scene TEXT DEFAULT '',
                scope TEXT DEFAULT 'private',
                conversation_id TEXT DEFAULT '',
                connections TEXT DEFAULT '[]',
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                title TEXT,
                summary TEXT,
                cell_ids TEXT DEFAULT '[]',
                theme TEXT,
                agent_id TEXT DEFAULT '',
                created_at REAL,
                updated_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT,
                description TEXT,
                pattern TEXT,
                scene TEXT DEFAULT '',
                trigger TEXT DEFAULT '',
                steps TEXT DEFAULT '[]',
                tools TEXT DEFAULT '[]',
                confidence REAL DEFAULT 0.0,
                usage_count INTEGER DEFAULT 0,
                success_rate REAL DEFAULT 0.0,
                skill_version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'active',
                created_at REAL,
                updated_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS skill_feedback (
                feedback_id TEXT PRIMARY KEY,
                skill_id TEXT,
                result TEXT DEFAULT '',
                success INTEGER DEFAULT 0,
                timestamp REAL
            );

            CREATE TABLE IF NOT EXISTS pyramid (
                id TEXT PRIMARY KEY,
                tier TEXT,
                content TEXT,
                source_ids TEXT DEFAULT '[]',
                created_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                agent_type TEXT DEFAULT '',
                description TEXT DEFAULT '',
                created_at REAL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                agent_id TEXT DEFAULT '',
                scene TEXT DEFAULT '',
                started_at REAL,
                metadata TEXT DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS memory_edges (
                edge_id TEXT PRIMARY KEY,
                memory_a TEXT NOT NULL,
                memory_b TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence REAL DEFAULT 0.5,
                created_at REAL,
                metadata TEXT DEFAULT '{}'
            );
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        cursor = self.conn.cursor()
        for table, col, col_def in [
            ("notes", "agent_id", "TEXT DEFAULT ''"),
            ("notes", "scene", "TEXT DEFAULT ''"),
            ("notes", "scope", "TEXT DEFAULT 'private'"),
            ("notes", "conversation_id", "TEXT DEFAULT ''"),
            ("cells", "agent_id", "TEXT DEFAULT ''"),
            ("cells", "scene", "TEXT DEFAULT ''"),
            ("cells", "cell_type", "TEXT DEFAULT 'fact'"),
            ("cells", "scope", "TEXT DEFAULT 'private'"),
            ("cells", "conversation_id", "TEXT DEFAULT ''"),
            ("scenes", "agent_id", "TEXT DEFAULT ''"),
            ("notes", "team_id", "TEXT DEFAULT ''"),
            ("notes", "task_id", "TEXT DEFAULT ''"),
            ("cells", "team_id", "TEXT DEFAULT ''"),
            ("cells", "task_id", "TEXT DEFAULT ''"),
            ("skills", "scene", "TEXT DEFAULT ''"),
            ("skills", "trigger", "TEXT DEFAULT ''"),
            ("skills", "steps", "TEXT DEFAULT '[]'"),
            ("skills", "tools", "TEXT DEFAULT '[]'"),
            ("skills", "confidence", "REAL DEFAULT 0.0"),
            ("skills", "skill_version", "INTEGER DEFAULT 1"),
            ("skills", "status", "TEXT DEFAULT 'active'"),
            ("skills", "updated_at", "REAL"),
        ]:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            except sqlite3.OperationalError:
                pass

        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS skill_feedback (
                feedback_id TEXT PRIMARY KEY,
                skill_id TEXT,
                result TEXT DEFAULT '',
                success INTEGER DEFAULT 0,
                timestamp REAL
            );
        """)
        self.conn.commit()

    def put_note(self, note: dict) -> str:
        note_id = note.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO notes (id, content, source, agent_id, scene, scope, conversation_id, team_id, task_id, timestamp, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (note_id, note.get("content", ""), note.get("source", "manual"),
             note.get("agent_id", ""), note.get("scene", ""),
             note.get("scope", "private"), note.get("conversation_id", ""),
             note.get("team_id", ""), note.get("task_id", ""),
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

    def list_notes(self, limit: int = 100, offset: int = 0, agent_id: str = None) -> List[dict]:
        cursor = self.conn.cursor()
        if agent_id:
            cursor.execute("SELECT * FROM notes WHERE agent_id = ? ORDER BY timestamp DESC LIMIT ? OFFSET ?",
                           (agent_id, limit, offset))
        else:
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
            (id, note_id, content, cell_type, facts, stage, importance, access_count,
             last_accessed, created_at, agent_id, scene, scope, conversation_id,
             team_id, task_id, connections, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (cell_id, cell.get("note_id", ""), cell.get("content", ""),
             cell.get("cell_type", "fact"),
             json.dumps(cell.get("facts", [])), cell.get("stage", "exploration"),
             cell.get("importance", 0.5), cell.get("access_count", 0),
             cell.get("last_accessed", 0), cell.get("created_at", 0),
             cell.get("agent_id", ""), cell.get("scene", ""),
             cell.get("scope", "private"), cell.get("conversation_id", ""),
             cell.get("team_id", ""), cell.get("task_id", ""),
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

    def list_cells(self, limit: int = 100, offset: int = 0,
                   agent_id: str = None, scene: str = None) -> List[dict]:
        cursor = self.conn.cursor()
        conditions = []
        params = []
        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if scene:
            conditions.append("scene = ?")
            params.append(scene)

        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        params.extend([limit, offset])
        cursor.execute(f"SELECT * FROM cells{where} ORDER BY created_at DESC LIMIT ? OFFSET ?", params)
        return [self._row_to_cell(row) for row in cursor.fetchall()]

    def list_cells_scoped(self, agent_id: str = None, conversation_id: str = None,
                          scene: str = None, limit: int = 100,
                          team_id: str = None, task_id: str = None) -> List[dict]:
        cursor = self.conn.cursor()
        scope_conditions = []
        params = []

        if agent_id:
            scope_conditions.append("(agent_id = ? AND scope = 'private')")
            params.append(agent_id)

        if conversation_id:
            scope_conditions.append("(conversation_id = ? AND scope = 'conversation')")
            params.append(conversation_id)

        scope_conditions.append("scope = 'shared'")

        if team_id:
            scope_conditions.append("(team_id = ? AND scope = 'team')")
            params.append(team_id)
        else:
            scope_conditions.append("scope = 'team'")

        scope_clause = " OR ".join(scope_conditions)

        extra_conditions = []
        if scene:
            extra_conditions.append("scene = ?")
            params.append(scene)
        if task_id:
            extra_conditions.append("(task_id = ? OR scope = 'team')")
            params.append(task_id)

        where = f" WHERE ({scope_clause})"
        if extra_conditions:
            where += " AND " + " AND ".join(extra_conditions)

        params.append(limit)
        cursor.execute(f"SELECT * FROM cells{where} ORDER BY created_at DESC LIMIT ?", params)
        return [self._row_to_cell(row) for row in cursor.fetchall()]

    def delete_cell(self, cell_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM cells WHERE id = ?", (cell_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def put_scene(self, scene: dict) -> str:
        scene_id = scene.get("id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO scenes
            (id, title, summary, cell_ids, theme, agent_id, created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (scene_id, scene.get("title", ""), scene.get("summary", ""),
             json.dumps(scene.get("cell_ids", [])), scene.get("theme", ""),
             scene.get("agent_id", ""),
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

    def list_scenes(self, limit: int = 100, offset: int = 0, agent_id: str = None) -> List[dict]:
        cursor = self.conn.cursor()
        if agent_id:
            cursor.execute("SELECT * FROM scenes WHERE agent_id = ? ORDER BY updated_at DESC LIMIT ? OFFSET ?",
                           (agent_id, limit, offset))
        else:
            cursor.execute("SELECT * FROM scenes ORDER BY updated_at DESC LIMIT ? OFFSET ?", (limit, offset))
        return [self._row_to_scene(row) for row in cursor.fetchall()]

    def put_skill(self, skill: dict) -> str:
        skill_id = skill.get("id", "")
        cursor = self.conn.cursor()
        steps = skill.get("steps", [])
        tools = skill.get("tools", [])
        cursor.execute(
            """INSERT OR REPLACE INTO skills
            (id, name, description, pattern, scene, trigger, steps, tools,
             confidence, usage_count, success_rate, skill_version, status,
             created_at, updated_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (skill_id, skill.get("name", ""), skill.get("description", ""),
             skill.get("pattern", ""), skill.get("scene", ""),
             skill.get("trigger", ""),
             json.dumps(steps) if isinstance(steps, list) else steps,
             json.dumps(tools) if isinstance(tools, list) else tools,
             skill.get("confidence", 0.0),
             skill.get("usage_count", 0), skill.get("success_rate", 0.0),
             skill.get("skill_version", 1), skill.get("status", "active"),
             skill.get("created_at", 0), skill.get("updated_at", 0),
             json.dumps(skill.get("metadata", {})))
        )
        self.conn.commit()
        return skill_id

    def get_skill(self, skill_id: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM skills WHERE id = ?", (skill_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_skill(row)

    def list_skills(self, scene: str = "", status: str = "") -> List[dict]:
        cursor = self.conn.cursor()
        conditions = []
        params = []
        if scene:
            conditions.append("scene = ?")
            params.append(scene)
        if status:
            conditions.append("status = ?")
            params.append(status)

        query = "SELECT * FROM skills"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY usage_count DESC"
        cursor.execute(query, params)
        return [self._row_to_skill(row) for row in cursor.fetchall()]

    def delete_skill(self, skill_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def put_skill_feedback(self, feedback: dict) -> str:
        fid = feedback.get("feedback_id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO skill_feedback
            (feedback_id, skill_id, result, success, timestamp)
            VALUES (?, ?, ?, ?, ?)""",
            (fid, feedback.get("skill_id", ""), feedback.get("result", ""),
             1 if feedback.get("success") else 0,
             feedback.get("timestamp", 0))
        )
        self.conn.commit()
        return fid

    def list_skill_feedback(self, skill_id: str = "") -> List[dict]:
        cursor = self.conn.cursor()
        if skill_id:
            cursor.execute(
                "SELECT * FROM skill_feedback WHERE skill_id = ? ORDER BY timestamp DESC",
                (skill_id,))
        else:
            cursor.execute("SELECT * FROM skill_feedback ORDER BY timestamp DESC")
        results = []
        for row in cursor.fetchall():
            results.append({
                "feedback_id": row["feedback_id"],
                "skill_id": row["skill_id"],
                "result": row["result"],
                "success": bool(row["success"]),
                "timestamp": row["timestamp"],
            })
        return results

    def put_agent(self, agent: dict) -> str:
        agent_id = agent.get("agent_id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO agents (agent_id, agent_type, description, created_at) VALUES (?, ?, ?, ?)",
            (agent_id, agent.get("agent_type", ""), agent.get("description", ""),
             agent.get("created_at", time.time()))
        )
        self.conn.commit()
        return agent_id

    def get_agent(self, agent_id: str) -> Optional[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents WHERE agent_id = ?", (agent_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "agent_id": row["agent_id"],
            "agent_type": row["agent_type"],
            "description": row["description"],
            "created_at": row["created_at"],
        }

    def list_agents(self) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")
        return [{
            "agent_id": row["agent_id"],
            "agent_type": row["agent_type"],
            "description": row["description"],
            "created_at": row["created_at"],
        } for row in cursor.fetchall()]

    def delete_agent(self, agent_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM agents WHERE agent_id = ?", (agent_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def put_conversation(self, conversation: dict) -> str:
        conv_id = conversation.get("conversation_id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO conversations (conversation_id, agent_id, scene, started_at, metadata) VALUES (?, ?, ?, ?, ?)",
            (conv_id, conversation.get("agent_id", ""), conversation.get("scene", ""),
             conversation.get("started_at", time.time()),
             json.dumps(conversation.get("metadata", {})))
        )
        self.conn.commit()
        return conv_id

    def list_conversations(self, agent_id: str = None) -> List[dict]:
        cursor = self.conn.cursor()
        if agent_id:
            cursor.execute("SELECT * FROM conversations WHERE agent_id = ? ORDER BY started_at DESC", (agent_id,))
        else:
            cursor.execute("SELECT * FROM conversations ORDER BY started_at DESC")
        return [{
            "conversation_id": row["conversation_id"],
            "agent_id": row["agent_id"],
            "scene": row["scene"],
            "started_at": row["started_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        } for row in cursor.fetchall()]

    def put_edge(self, edge: dict) -> str:
        edge_id = edge.get("edge_id", "")
        cursor = self.conn.cursor()
        cursor.execute(
            """INSERT OR REPLACE INTO memory_edges
            (edge_id, memory_a, memory_b, relation_type, confidence, created_at, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (edge_id, edge.get("memory_a", ""), edge.get("memory_b", ""),
             edge.get("relation_type", "related"), edge.get("confidence", 0.5),
             edge.get("created_at", time.time()),
             json.dumps(edge.get("metadata", {})))
        )
        self.conn.commit()
        return edge_id

    def get_edges(self, memory_id: str) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM memory_edges WHERE memory_a = ? OR memory_b = ?",
            (memory_id, memory_id)
        )
        return [self._row_to_edge(row) for row in cursor.fetchall()]

    def delete_edge(self, edge_id: str) -> bool:
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM memory_edges WHERE edge_id = ?", (edge_id,))
        self.conn.commit()
        return cursor.rowcount > 0

    def list_edges(self, limit: int = 100) -> List[dict]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM memory_edges ORDER BY created_at DESC LIMIT ?", (limit,))
        return [self._row_to_edge(row) for row in cursor.fetchall()]

    def close(self):
        if hasattr(self._local, "conn") and self._local.conn is not None:
            self._local.conn.close()
            self._local.conn = None

    def _row_to_edge(self, row) -> dict:
        return {
            "edge_id": row["edge_id"],
            "memory_a": row["memory_a"],
            "memory_b": row["memory_b"],
            "relation_type": row["relation_type"],
            "confidence": row["confidence"],
            "created_at": row["created_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }

    def _row_to_note(self, row) -> dict:
        d = {
            "id": row["id"], "content": row["content"], "source": row["source"],
            "timestamp": row["timestamp"], "metadata": json.loads(row["metadata"] or "{}"),
        }
        try:
            d["agent_id"] = row["agent_id"] or ""
            d["scene"] = row["scene"] or ""
        except (IndexError, KeyError):
            d["agent_id"] = ""
            d["scene"] = ""
        try:
            d["scope"] = row["scope"] or "private"
            d["conversation_id"] = row["conversation_id"] or ""
        except (IndexError, KeyError):
            d["scope"] = "private"
            d["conversation_id"] = ""
        try:
            d["team_id"] = row["team_id"] or ""
            d["task_id"] = row["task_id"] or ""
        except (IndexError, KeyError):
            d["team_id"] = ""
            d["task_id"] = ""
        return d

    def _row_to_cell(self, row) -> dict:
        d = {
            "id": row["id"], "note_id": row["note_id"], "content": row["content"],
            "facts": json.loads(row["facts"] or "[]"), "stage": row["stage"],
            "importance": row["importance"], "access_count": row["access_count"],
            "last_accessed": row["last_accessed"], "created_at": row["created_at"],
            "connections": json.loads(row["connections"] or "[]"),
            "metadata": json.loads(row["metadata"] or "{}"),
        }
        try:
            d["agent_id"] = row["agent_id"] or ""
            d["scene"] = row["scene"] or ""
            d["cell_type"] = row["cell_type"] or "fact"
        except (IndexError, KeyError):
            d["agent_id"] = ""
            d["scene"] = ""
            d["cell_type"] = "fact"
        try:
            d["scope"] = row["scope"] or "private"
            d["conversation_id"] = row["conversation_id"] or ""
        except (IndexError, KeyError):
            d["scope"] = "private"
            d["conversation_id"] = ""
        try:
            d["team_id"] = row["team_id"] or ""
            d["task_id"] = row["task_id"] or ""
        except (IndexError, KeyError):
            d["team_id"] = ""
            d["task_id"] = ""
        return d

    def _row_to_scene(self, row) -> dict:
        d = {
            "id": row["id"], "title": row["title"], "summary": row["summary"],
            "cell_ids": json.loads(row["cell_ids"] or "[]"), "theme": row["theme"],
            "created_at": row["created_at"], "updated_at": row["updated_at"],
            "metadata": json.loads(row["metadata"] or "{}"),
        }
        try:
            d["agent_id"] = row["agent_id"] or ""
        except (IndexError, KeyError):
            d["agent_id"] = ""
        return d

    def _row_to_skill(self, row) -> dict:
        steps_raw = row["steps"] if "steps" in row.keys() else "[]"
        tools_raw = row["tools"] if "tools" in row.keys() else "[]"
        return {
            "id": row["id"], "name": row["name"], "description": row["description"],
            "pattern": row["pattern"],
            "scene": row["scene"] if "scene" in row.keys() else "",
            "trigger": row["trigger"] if "trigger" in row.keys() else "",
            "steps": json.loads(steps_raw) if isinstance(steps_raw, str) else steps_raw,
            "tools": json.loads(tools_raw) if isinstance(tools_raw, str) else tools_raw,
            "confidence": row["confidence"] if "confidence" in row.keys() else 0.0,
            "usage_count": row["usage_count"],
            "success_rate": row["success_rate"],
            "skill_version": row["skill_version"] if "skill_version" in row.keys() else 1,
            "status": row["status"] if "status" in row.keys() else "active",
            "created_at": row["created_at"],
            "updated_at": row["updated_at"] if "updated_at" in row.keys() else 0,
            "metadata": json.loads(row["metadata"] or "{}"),
        }
