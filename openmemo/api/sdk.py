"""
OpenMemo SDK - Simple Python API.

Usage:
    from openmemo import Memory

    memory = Memory()
    memory.add("User prefers dark mode")
    result = memory.recall("user preference")
    print(result)
"""

import uuid
import time
from typing import List, Optional

from openmemo.core.memory import Note
from openmemo.core.memcell import MemCell, LifecycleStage
from openmemo.core.scene import MemScene
from openmemo.core.recall import RecallEngine
from openmemo.core.reconstruct import ReconstructiveRecall
from openmemo.storage.sqlite_store import SQLiteStore
from openmemo.pyramid.pyramid_engine import PyramidEngine
from openmemo.pyramid.summarizer import Summarizer
from openmemo.skill.skill_engine import SkillEngine
from openmemo.governance.conflict_detector import ConflictDetector
from openmemo.governance.version_manager import VersionManager


class Memory:
    """
    The main entry point for OpenMemo.

    Provides a simple API for adding, recalling, and managing memories.
    """

    def __init__(self, db_path: str = "openmemo.db", store=None):
        self.store = store or SQLiteStore(db_path)
        self.recall_engine = RecallEngine(store=self.store)
        self.reconstructor = ReconstructiveRecall(
            recall_engine=self.recall_engine,
            store=self.store,
        )
        self.pyramid = PyramidEngine(
            store=self.store,
            summarizer=Summarizer(),
        )
        self.skill_engine = SkillEngine(store=self.store)
        self.conflict_detector = ConflictDetector()
        self.version_manager = VersionManager()

    def add(self, content: str, source: str = "manual", metadata: dict = None) -> str:
        note = Note(content=content, source=source, metadata=metadata or {})
        self.store.put_note(note.to_dict())

        cell = MemCell(
            note_id=note.id,
            content=content,
            stage=LifecycleStage.EXPLORATION,
        )

        existing_cells = self.store.list_cells(limit=50)
        conflicts = self.conflict_detector.detect(cell.to_dict(), existing_cells)
        if conflicts:
            cell.metadata["has_conflicts"] = True
            cell.metadata["conflict_count"] = len(conflicts)

        self.version_manager.snapshot(cell.to_dict(), change_type="create")
        self.store.put_cell(cell.to_dict())

        return note.id

    def recall(self, query: str, top_k: int = 10, budget: int = 2000) -> List[dict]:
        results = self.recall_engine.recall(query, top_k=top_k, budget=budget)

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

    def reconstruct(self, query: str, max_sources: int = 10) -> dict:
        result = self.reconstructor.reconstruct(query, max_sources=max_sources)
        return {
            "query": result.query,
            "narrative": result.narrative,
            "sources": result.sources,
            "confidence": result.confidence,
        }

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

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
