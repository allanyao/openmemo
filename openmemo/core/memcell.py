"""
MemCell Engine - Enhanced memory write units.

A MemCell wraps an AtomicFact with:
- Lifecycle stage (exploration -> consolidation -> mastery -> dormant)
- Importance scoring
- Embedding vector
- Connection graph

Evolution thresholds are configurable via EvolutionConfig.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class LifecycleStage(str, Enum):
    EXPLORATION = "exploration"
    CONSOLIDATION = "consolidation"
    MASTERY = "mastery"
    DORMANT = "dormant"


@dataclass
class MemCell:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    note_id: str = ""
    content: str = ""
    facts: list = field(default_factory=list)
    stage: LifecycleStage = LifecycleStage.EXPLORATION
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    embedding: Optional[list] = None
    connections: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def access(self, evolution_config=None):
        self.access_count += 1
        self.last_accessed = time.time()
        self._update_stage(evolution_config)

    def _update_stage(self, config=None):
        from openmemo.config import EvolutionConfig
        cfg = config or EvolutionConfig()

        if self.access_count >= cfg.mastery_min_access and self.importance >= cfg.mastery_min_importance:
            self.stage = LifecycleStage.MASTERY
        elif self.access_count >= cfg.consolidation_min_access:
            self.stage = LifecycleStage.CONSOLIDATION

        age_days = (time.time() - self.last_accessed) / 86400
        if age_days > cfg.dormant_days and self.stage != LifecycleStage.MASTERY:
            self.stage = LifecycleStage.DORMANT

    def to_dict(self):
        return {
            "id": self.id,
            "note_id": self.note_id,
            "content": self.content,
            "facts": self.facts,
            "stage": self.stage.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "connections": self.connections,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemCell":
        cell = cls(
            id=data.get("id", str(uuid.uuid4())),
            note_id=data.get("note_id", ""),
            content=data.get("content", ""),
            facts=data.get("facts", []),
            stage=LifecycleStage(data.get("stage", "exploration")),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
            created_at=data.get("created_at", time.time()),
            connections=data.get("connections", []),
            metadata=data.get("metadata", {}),
        )
        return cell
