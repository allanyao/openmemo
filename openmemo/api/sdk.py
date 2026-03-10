"""
OpenMemo SDK — Memory Core API v1.0

Usage:
    from openmemo import OpenMemo

    memo = OpenMemo()
    memo.write_memory("User prefers Python backend", scene="coding", memory_type="preference")
    result = memo.recall_context("programming language", scene="coding")
    print(result)  # {"context": ["User prefers Python backend"]}

Aliases:
    Memory, MemoryClient — same as OpenMemo
"""

from typing import List, Callable

from openmemo.config import OpenMemoConfig
from openmemo.core.memory import Note
from openmemo.core.memcell import MemCell, LifecycleStage
from openmemo.core.scene import MemScene
from openmemo.core.recall import RecallEngine
from openmemo.core.reconstruct import ReconstructiveRecall
from openmemo.core.graph import GraphBuilder, get_memory_graph, detect_conflicts
from openmemo.storage.sqlite_store import SQLiteStore
from openmemo.storage.vector_store import VectorStore
from openmemo.pyramid.pyramid_engine import PyramidEngine
from openmemo.pyramid.summarizer import Summarizer
from openmemo.skill.skill_engine import SkillEngine
from openmemo.governance.conflict_detector import ConflictDetector
from openmemo.governance.version_manager import VersionManager
from openmemo.constitution.constitution_loader import load_constitution
from openmemo.constitution.constitution_runtime import ConstitutionRuntime
from openmemo.constitution.constitution_registry import ConstitutionRegistry


class Memory:
    """
    The main entry point for OpenMemo.

    Provides 5 core APIs:
        write_memory()       — Write a memory
        search_memory()      — Basic search
        recall_context()     — Agent reasoning context (most important)
        list_scenes()        — List memory scenes
        memory_governance()  — Memory cleanup & governance

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

        if self._config.constitution.enabled:
            constitution_config = load_constitution(self._config.constitution.path)
            self.constitution = ConstitutionRuntime(constitution_config)
        else:
            self.constitution = None

        self.recall_engine = RecallEngine(
            store=self.store,
            vector_store=self.vector_store,
            embed_fn=self.embed_fn,
            config=self._config.recall,
            constitution=self.constitution,
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
        self.conflict_detector = ConflictDetector(
            config=self._config.governance,
            constitution=self.constitution,
        )
        self.version_manager = VersionManager()
        self._registry = ConstitutionRegistry()
        self.graph_builder = GraphBuilder(store=self.store)
        self._auto_graph = True

    # ─── Constitution Profile API ───

    def load_profile(self, name: str) -> dict:
        runtime = self._registry.switch(name)
        self.constitution = runtime
        self.recall_engine.set_constitution(runtime)
        self.conflict_detector.set_constitution(runtime)
        return {
            "profile": name,
            "status": "active",
            "summary": runtime.summary(),
        }

    def list_profiles(self) -> list:
        return self._registry.list_profiles()

    def register_profile(self, name: str, config_dict: dict):
        self._registry.register_from_dict(name, config_dict)

    def active_profile(self) -> str:
        return self._registry.active_name

    SHARED_TYPES = {"rules", "playbook", "pattern", "convention", "policy"}

    # ─── Core API 1: write_memory ───

    def write_memory(self, content: str, scene: str = "",
                     memory_type: str = "fact", confidence: float = 0.8,
                     agent_id: str = "", metadata: dict = None,
                     scope: str = "", conversation_id: str = "") -> str:
        effective_scope = scope
        if not effective_scope:
            effective_scope = "shared" if memory_type in self.SHARED_TYPES else "private"
        return self._write_impl(
            content=content, scene=scene, cell_type=memory_type,
            confidence=confidence, agent_id=agent_id,
            source="manual", metadata=metadata,
            scope=effective_scope, conversation_id=conversation_id,
        )

    # ─── Core API 2: search_memory ───

    def search_memory(self, query: str, scene: str = "",
                      agent_id: str = "", limit: int = 10,
                      conversation_id: str = "") -> List[dict]:
        results = self.recall_engine.recall(
            query, top_k=limit, budget=50000,
            agent_id=agent_id or None, scene=scene or None,
            conversation_id=conversation_id or None,
        )
        items = [
            {
                "content": r.content,
                "score": r.score,
                "cell_id": r.cell_id,
            }
            for r in results
        ]
        return items

    # ─── Core API 3: recall_context (most important) ───

    def recall_context(self, query: str, scene: str = "",
                       agent_id: str = "", limit: int = 5,
                       mode: str = "kv", conversation_id: str = "",
                       graph: bool = None) -> dict:
        if mode == "narrative":
            result = self.reconstructor.reconstruct(
                query, max_sources=limit,
                agent_id=agent_id or None,
            )
            return {
                "memory_story": result.narrative,
                "sources": result.sources,
                "confidence": result.confidence,
            }

        if mode == "raw":
            return {
                "context": self._recall_raw_impl(
                    query, agent_id=agent_id, scene=scene,
                    top_k=limit, conversation_id=conversation_id,
                ),
            }

        results = self.recall_engine.recall(
            query, top_k=limit, budget=2000,
            agent_id=agent_id or None, scene=scene or None,
            conversation_id=conversation_id or None,
            graph=graph,
        )

        for r in results:
            cell = self.store.get_cell(r.cell_id)
            if cell:
                cell_obj = MemCell.from_dict(cell)
                cell_obj.access()
                self.store.put_cell(cell_obj.to_dict())

        return {
            "context": [r.content for r in results],
        }

    # ─── Core API 4: list_scenes ───

    def list_scenes(self, agent_id: str = "") -> List[str]:
        raw_scenes = self.store.list_scenes(agent_id=agent_id or None)
        return [s.get("title", "") for s in raw_scenes if s.get("title")]

    # ─── Core API 5: memory_governance ───

    def memory_governance(self, operation: str = "cleanup") -> dict:
        cells = self.store.list_cells(limit=500)

        if operation == "dedupe":
            return self._governance_dedupe(cells)
        elif operation == "merge":
            return self._governance_merge(cells)
        elif operation == "decay":
            return self._governance_decay(cells)
        elif operation == "cleanup":
            return self._governance_cleanup(cells)
        else:
            return {"error": f"Unknown operation: {operation}"}

    # ─── Agent & Conversation Management ───

    def register_agent(self, agent_id: str, agent_type: str = "",
                       description: str = "") -> dict:
        self.store.put_agent({
            "agent_id": agent_id,
            "agent_type": agent_type,
            "description": description,
        })
        return {"agent_id": agent_id, "status": "registered"}

    def list_agents(self) -> List[dict]:
        return self.store.list_agents()

    def start_conversation(self, conversation_id: str, agent_id: str = "",
                           scene: str = "") -> dict:
        self.store.put_conversation({
            "conversation_id": conversation_id,
            "agent_id": agent_id,
            "scene": scene,
        })
        return {"conversation_id": conversation_id, "status": "started"}

    def list_conversations(self, agent_id: str = "") -> List[dict]:
        return self.store.list_conversations(agent_id=agent_id or None)

    # ─── Shared Memory Promotion ───

    def promote_shared_memories(self) -> dict:
        cells = self.store.list_cells(limit=1000)
        promoted = 0
        for c in cells:
            if c.get("scope") == "shared":
                continue
            confidence = c.get("metadata", {}).get("confidence", 0.5)
            access_count = c.get("access_count", 0)
            if confidence > 0.9 and access_count >= 3:
                cell_obj = MemCell.from_dict(c)
                cell_obj.scope = "shared"
                cell_obj.metadata["promoted_to_shared"] = True
                self.store.put_cell(cell_obj.to_dict())
                promoted += 1
        return {"promoted": promoted}

    def decay_shared_memories(self, max_age_days: int = 90) -> dict:
        import time
        now = time.time()
        cells = self.store.list_cells(limit=1000)
        decayed = 0
        for c in cells:
            if c.get("scope") != "shared":
                continue
            last_access = c.get("last_accessed", c.get("created_at", now))
            age_days = (now - last_access) / 86400
            if age_days > max_age_days:
                self.store.delete_cell(c["id"])
                decayed += 1
        return {"decayed": decayed}

    # ─── Memory Graph API ───

    def add_memory_edge(self, memory_a: str, memory_b: str,
                        relation_type: str = "related",
                        confidence: float = 0.7) -> dict:
        import uuid
        import time as _time
        edge = {
            "edge_id": str(uuid.uuid4())[:12],
            "memory_a": memory_a,
            "memory_b": memory_b,
            "relation_type": relation_type,
            "confidence": confidence,
            "created_at": _time.time(),
            "metadata": {},
        }
        self.store.put_edge(edge)
        return edge

    def get_memory_graph(self, memory_id: str, depth: int = 1) -> dict:
        resolved_id = self._resolve_memory_id(memory_id)
        return get_memory_graph(self.store, resolved_id, depth=depth)

    def detect_conflicts(self, agent_id: str = "",
                         scene: str = "") -> List[dict]:
        return detect_conflicts(
            self.store,
            agent_id=agent_id or None,
            scene=scene or None,
        )

    def list_edges(self, limit: int = 100) -> List[dict]:
        return self.store.list_edges(limit=limit)

    # ─── Backward-compatible aliases ───

    def write(self, content: str, agent_id: str = "", scene: str = "",
              cell_type: str = "fact", source: str = "manual",
              metadata: dict = None) -> str:
        return self._write_impl(
            content=content, scene=scene, cell_type=cell_type,
            confidence=0.8, agent_id=agent_id,
            source=source, metadata=metadata,
        )

    def add(self, content: str, source: str = "manual", agent_id: str = "",
            scene: str = "", cell_type: str = "fact", metadata: dict = None) -> str:
        return self._write_impl(
            content=content, scene=scene, cell_type=cell_type,
            confidence=0.8, agent_id=agent_id,
            source=source, metadata=metadata,
        )

    def recall(self, query: str, agent_id: str = "", scene: str = "",
               mode: str = "kv", top_k: int = None, limit: int = None,
               budget: int = 2000) -> dict:
        effective_limit = limit or top_k or 5
        return self.recall_context(
            query=query, scene=scene, agent_id=agent_id,
            limit=effective_limit, mode=mode,
        )

    def recall_raw(self, query: str, agent_id: str = "", scene: str = "",
                   top_k: int = 10, budget: int = 2000) -> List[dict]:
        return self._recall_raw_impl(query, agent_id, scene, top_k, budget)

    def search(self, query: str, agent_id: str = "",
               top_k: int = None, limit: int = None) -> List[dict]:
        effective_limit = limit or top_k or 10
        return self.search_memory(query, agent_id=agent_id, limit=effective_limit)

    def context(self, query: str, agent_id: str = "", scene: str = "",
                limit: int = 3) -> List[str]:
        result = self.recall_context(query, scene=scene, agent_id=agent_id, limit=limit)
        return result.get("context", [])

    def scenes(self, agent_id: str = "") -> List[str]:
        return self.list_scenes(agent_id=agent_id)

    def scenes_detail(self, agent_id: str = "") -> List[dict]:
        return self.store.list_scenes(agent_id=agent_id or None)

    def maintain(self) -> dict:
        return self.memory_governance("cleanup")

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

    def delete(self, memory_id: str) -> bool:
        cell_deleted = self.store.delete_cell(memory_id)
        if cell_deleted:
            return True
        return self.store.delete_note(memory_id)

    def stats(self) -> dict:
        notes = self.store.list_notes(limit=10000)
        cells = self.store.list_cells(limit=10000)
        scenes_list = self.store.list_scenes(limit=10000)
        skills = self.store.list_skills()
        edges = self.store.list_edges(limit=10000)

        stage_counts = {}
        for c in cells:
            stage = c.get("stage", "unknown")
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        edge_type_counts = {}
        for e in edges:
            rt = e.get("relation_type", "unknown")
            edge_type_counts[rt] = edge_type_counts.get(rt, 0) + 1

        conflicts = self.conflict_detector.get_unresolved()

        return {
            "notes": len(notes),
            "cells": len(cells),
            "scenes": len(scenes_list),
            "skills": len(skills),
            "edges": len(edges),
            "edge_types": edge_type_counts,
            "stages": stage_counts,
            "unresolved_conflicts": len(conflicts),
        }

    def _resolve_memory_id(self, memory_id: str) -> str:
        cell = self.store.get_cell(memory_id)
        if cell:
            return memory_id
        cells = self.store.list_cells(limit=500)
        for c in cells:
            if c.get("note_id") == memory_id:
                return c["id"]
        return memory_id

    # ─── Internal implementations ───

    def _write_impl(self, content: str, scene: str, cell_type: str,
                    confidence: float, agent_id: str,
                    source: str, metadata: dict,
                    scope: str = "private", conversation_id: str = "") -> str:
        from openmemo._internal import get_evolution_params

        if self.constitution and not self.constitution.should_store(cell_type, content):
            return ""

        note = Note(content=content, source=source, metadata=metadata or {})
        note_dict = note.to_dict()
        note_dict["agent_id"] = agent_id
        note_dict["scene"] = scene
        note_dict["scope"] = scope
        note_dict["conversation_id"] = conversation_id
        self.store.put_note(note_dict)

        importance = confidence if confidence else get_evolution_params()["default_importance"]

        if self.constitution:
            priority = self.constitution.get_priority(cell_type)
            importance = min(1.0, importance + priority * 0.02)

        cell = MemCell(
            note_id=note.id,
            content=content,
            cell_type=cell_type,
            stage=LifecycleStage.EXPLORATION,
            importance=importance,
            agent_id=agent_id,
            scene=scene,
            scope=scope,
            conversation_id=conversation_id,
        )
        cell.metadata["confidence"] = confidence

        existing_cells = self.store.list_cells(limit=50, agent_id=agent_id or None)
        conflicts = self.conflict_detector.detect(cell.to_dict(), existing_cells)
        if conflicts and self.constitution:
            for conflict in conflicts:
                old_cell = next(
                    (c for c in existing_cells if c.get("id") == conflict.cell_id_b),
                    None,
                )
                old_conf = old_cell.get("metadata", {}).get("confidence", 0.5) if old_cell else 0.5
                if self.constitution.allow_conflict_override(old_conf, confidence):
                    cell.metadata["conflict_resolved"] = "override"
                elif self.constitution.allow_unresolved_conflict():
                    cell.metadata["has_conflicts"] = True
                    cell.metadata["conflict_count"] = len(conflicts)
                else:
                    cell.metadata["has_conflicts"] = True
                    cell.metadata["conflict_count"] = len(conflicts)
        elif conflicts:
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

        if self._auto_graph:
            try:
                self.graph_builder.build_edges(cell.id, store=self.store)
            except Exception:
                pass

        return note.id

    def _recall_raw_impl(self, query: str, agent_id: str = "", scene: str = "",
                         top_k: int = 10, budget: int = 2000,
                         conversation_id: str = "") -> List[dict]:
        results = self.recall_engine.recall(
            query, top_k=top_k, budget=budget,
            agent_id=agent_id or None, scene=scene or None,
            conversation_id=conversation_id or None,
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

    def _governance_dedupe(self, cells: list) -> dict:
        seen = {}
        duplicates = []
        for c in cells:
            content = c.get("content", "").strip().lower()
            if content in seen:
                duplicates.append(c["id"])
                self.store.delete_cell(c["id"])
            else:
                seen[content] = c["id"]
        return {
            "operation": "dedupe",
            "duplicates_removed": len(duplicates),
            "total_cells": len(cells),
        }

    def _governance_merge(self, cells: list) -> dict:
        pyramid_result = self.pyramid.process(cells)
        return {
            "operation": "merge",
            "pyramid": pyramid_result,
            "total_cells": len(cells),
        }

    def _governance_decay(self, cells: list) -> dict:
        import time
        now = time.time()
        decayed = 0
        for c in cells:
            last_access = c.get("last_access", c.get("created_at", now))
            age_days = (now - last_access) / 86400
            if age_days > 30:
                cell_obj = MemCell.from_dict(c)
                if self.constitution:
                    factor = self.constitution.get_decay_factor(
                        cell_obj.cell_type,
                        confidence=c.get("metadata", {}).get("confidence", 0.5),
                        access_count=cell_obj.access_count,
                    )
                else:
                    factor = 0.9
                cell_obj.importance = max(0.1, cell_obj.importance * factor)
                self.store.put_cell(cell_obj.to_dict())
                decayed += 1
        return {
            "operation": "decay",
            "decayed_cells": decayed,
            "total_cells": len(cells),
        }

    def _governance_cleanup(self, cells: list) -> dict:
        dedupe_result = self._governance_dedupe(cells)
        remaining_cells = self.store.list_cells(limit=500)
        merge_result = self._governance_merge(remaining_cells)
        skills = self.skill_engine.extract_skills()

        promoted = 0
        if self.constitution:
            for c in remaining_cells:
                cell_obj = MemCell.from_dict(c)
                access = cell_obj.access_count
                success = c.get("metadata", {}).get("success_signals", 0)
                if (cell_obj.stage != LifecycleStage.MASTERY and
                        self.constitution.can_promote(access, success)):
                    cell_obj.stage = LifecycleStage.MASTERY
                    cell_obj.importance = min(1.0, cell_obj.importance * 1.1)
                    self.store.put_cell(cell_obj.to_dict())
                    promoted += 1

        shared_result = self.promote_shared_memories()
        decay_result = self.decay_shared_memories()

        orphaned_edges = 0
        all_edges = self.store.list_edges(limit=1000)
        for edge in all_edges:
            cell_a = self.store.get_cell(edge["memory_a"])
            cell_b = self.store.get_cell(edge["memory_b"])
            if not cell_a or not cell_b:
                self.store.delete_edge(edge["edge_id"])
                orphaned_edges += 1

        return {
            "operation": "cleanup",
            "duplicates_removed": dedupe_result["duplicates_removed"],
            "pyramid": merge_result["pyramid"],
            "new_skills": len(skills),
            "promoted": promoted,
            "shared_promoted": shared_result["promoted"],
            "shared_decayed": decay_result["decayed"],
            "orphaned_edges_removed": orphaned_edges,
            "total_cells": len(remaining_cells),
        }

    def close(self):
        self.store.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


OpenMemo = Memory
MemoryClient = Memory
