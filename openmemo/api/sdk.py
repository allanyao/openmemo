"""
OpenMemo SDK - Simple Python API.

Usage:
    from openmemo import Memory

    memory = Memory()
    memory.write("User prefers dark mode", agent_id="agent_1", scene="preferences")
    results = memory.recall("user preference", agent_id="agent_1")
    print(results)

    # Or use MemoryClient alias
    from openmemo import MemoryClient
    mem = MemoryClient()
    mem.write("User prefers Python")
    mem.recall("Which language?")
"""

from typing import List, Callable, Union

from openmemo.config import OpenMemoConfig
from openmemo.core.memory import Note
from openmemo.core.memcell import MemCell, LifecycleStage
from openmemo.core.scene import MemScene
from openmemo.core.recall import RecallEngine
from openmemo.core.reconstruct import ReconstructiveRecall
from openmemo.storage.sqlite_store import SQLiteStore
from openmemo.storage.vector_store import VectorStore
from openmemo.pyramid.pyramid_engine import PyramidEngine
from openmemo.pyramid.summarizer import Summarizer
from openmemo.skill.skill_engine import SkillEngine
from openmemo.governance.conflict_detector import ConflictDetector
from openmemo.governance.version_manager import VersionManager


class Memory:
    """
    The main entry point for OpenMemo.

    Provides a simple API for writing, recalling, searching,
    and managing memories.

    Args:
        db_path: Path to SQLite database file. Default: "openmemo.db"
        store: Custom storage backend (must implement BaseStore interface)
        embed_fn: Optional embedding function for vector search.
        config: Optional OpenMemoConfig for customizing engine behavior.
    """

    def __init__(self, db_path: str = "openmemo.db", store=None,
                 embed_fn: Callable = None, config: OpenMemoConfig = None):
        self._config = config or OpenMemoConfig()
        self.store = store or SQLiteStore(db_path)
        self.embed_fn = embed_fn
        self.vector_store = VectorStore() if embed_fn else None
        self.recall_engine = RecallEngine(
            store=self.store,
            vector_store=self.vector_store,
            embed_fn=self.embed_fn,
            config=self._config.recall,
        )
        self.reconstructor = ReconstructiveRecall(
            recall_engine=self.recall_engine,
            store=self.store,
        )
        self.pyramid = PyramidEngine(
            store=self.store,
            summarizer=Summarizer(),
            config=self._config.pyramid,
        )
        self.skill_engine = SkillEngine(
            store=self.store,
            config=self._config.skill,
        )
        self.conflict_detector = ConflictDetector(config=self._config.governance)
        self.version_manager = VersionManager()

    def write(self, content: str, agent_id: str = "", scene: str = "",
              cell_type: str = "fact", source: str = "manual",
              metadata: dict = None) -> str:
        return self.add(
            content=content, source=source, agent_id=agent_id,
            scene=scene, cell_type=cell_type, metadata=metadata,
        )

    def add(self, content: str, source: str = "manual", agent_id: str = "",
            scene: str = "", cell_type: str = "fact", metadata: dict = None) -> str:
        from openmemo._internal import get_evolution_params

        note = Note(content=content, source=source, metadata=metadata or {})
        note_dict = note.to_dict()
        note_dict["agent_id"] = agent_id
        note_dict["scene"] = scene
        self.store.put_note(note_dict)

        cell = MemCell(
            note_id=note.id,
            content=content,
            cell_type=cell_type,
            stage=LifecycleStage.EXPLORATION,
            importance=get_evolution_params()["default_importance"],
            agent_id=agent_id,
            scene=scene,
        )

        existing_cells = self.store.list_cells(limit=50, agent_id=agent_id or None)
        conflicts = self.conflict_detector.detect(cell.to_dict(), existing_cells)
        if conflicts:
            cell.metadata["has_conflicts"] = True
            cell.metadata["conflict_count"] = len(conflicts)

        self.version_manager.snapshot(cell.to_dict(), change_type="create")
        self.store.put_cell(cell.to_dict())

        if scene:
            self._ensure_scene(scene, cell.id, agent_id)

        if self.vector_store and self.embed_fn:
            try:
                embedding = self.embed_fn(content)
                self.vector_store.add(cell.id, embedding, content)
            except Exception:
                pass

        return note.id

    def recall(self, query: str, agent_id: str = "", scene: str = "",
               mode: str = "kv", top_k: int = None, limit: int = None,
               budget: int = 2000) -> Union[dict, List[dict]]:
        effective_limit = limit or top_k or 10

        if mode == "narrative":
            result = self.reconstructor.reconstruct(
                query, max_sources=effective_limit,
                agent_id=agent_id or None,
            )
            return {
                "memory_story": result.narrative,
                "sources": result.sources,
                "confidence": result.confidence,
            }

        results = self.recall_engine.recall(
            query, top_k=effective_limit, budget=budget,
            agent_id=agent_id or None, scene=scene or None,
        )

        for r in results:
            cell = self.store.get_cell(r.cell_id)
            if cell:
                cell_obj = MemCell.from_dict(cell)
                cell_obj.access()
                self.store.put_cell(cell_obj.to_dict())

        return {
            "memories": [r.content for r in results],
        }

    def recall_raw(self, query: str, agent_id: str = "", scene: str = "",
                   top_k: int = 10, budget: int = 2000) -> List[dict]:
        results = self.recall_engine.recall(
            query, top_k=top_k, budget=budget,
            agent_id=agent_id or None, scene=scene or None,
        )

        for r in results:
            cell = self.store.get_cell(r.cell_id)
            if cell:
                cell_obj = MemCell.from_dict(cell)
                cell_obj.access()
                self.store.put_cell(cell_obj.to_dict())

        return [
            {
                "content": r.content,
                "score": r.score,
                "source": r.source,
                "cell_id": r.cell_id,
            }
            for r in results
        ]

    def search(self, query: str, agent_id: str = "",
               top_k: int = None, limit: int = None) -> List[dict]:
        effective_limit = limit or top_k or 10
        results = self.recall_engine.recall(
            query, top_k=effective_limit, budget=50000,
            agent_id=agent_id or None,
        )
        return [
            {
                "content": r.content,
                "score": r.score,
                "cell_id": r.cell_id,
            }
            for r in results
        ]

    def context(self, query: str, agent_id: str = "", scene: str = "",
                limit: int = 3) -> List[str]:
        results = self.recall_engine.recall(
            query, top_k=limit, budget=2000,
            agent_id=agent_id or None, scene=scene or None,
        )
        return [r.content for r in results]

    def reconstruct(self, query: str, agent_id: str = "", max_sources: int = 10) -> dict:
        result = self.reconstructor.reconstruct(
            query, max_sources=max_sources,
            agent_id=agent_id or None,
        )
        return {
            "query": result.query,
            "narrative": result.narrative,
            "sources": result.sources,
            "confidence": result.confidence,
        }

    def scenes(self, agent_id: str = "") -> List[str]:
        raw_scenes = self.store.list_scenes(agent_id=agent_id or None)
        return [s.get("title", "") for s in raw_scenes if s.get("title")]

    def scenes_detail(self, agent_id: str = "") -> List[dict]:
        return self.store.list_scenes(agent_id=agent_id or None)

    def delete(self, memory_id: str) -> bool:
        cell_deleted = self.store.delete_cell(memory_id)
        if cell_deleted:
            return True
        return self.store.delete_note(memory_id)

    def maintain(self) -> dict:
        cells = self.store.list_cells(limit=500)
        pyramid_result = self.pyramid.process(cells)
        skills = self.skill_engine.extract_skills()
        return {
            "pyramid": pyramid_result,
            "new_skills": len(skills),
            "total_cells": len(cells),
        }

    def stats(self) -> dict:
        notes = self.store.list_notes(limit=10000)
        cells = self.store.list_cells(limit=10000)
        scenes = self.store.list_scenes(limit=10000)
        skills = self.store.list_skills()

        stage_counts = {}
        for c in cells:
            stage = c.get("stage", "unknown")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        conflicts = self.conflict_detector.get_unresolved()

        return {
            "notes": len(notes),
            "cells": len(cells),
            "scenes": len(scenes),
            "skills": len(skills),
            "stages": stage_counts,
            "unresolved_conflicts": len(conflicts),
        }

    def _ensure_scene(self, scene_name: str, cell_id: str, agent_id: str = ""):
        all_scenes = self.store.list_scenes(agent_id=agent_id or None)
        for s in all_scenes:
            if s.get("title") == scene_name:
                scene_obj = MemScene.from_dict(s)
                scene_obj.add_cell(cell_id)
                self.store.put_scene(scene_obj.to_dict())
                return

        new_scene = MemScene(title=scene_name, theme=scene_name)
        new_scene.add_cell(cell_id)
        scene_dict = new_scene.to_dict()
        scene_dict["agent_id"] = agent_id
        self.store.put_scene(scene_dict)

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


MemoryClient = Memory
