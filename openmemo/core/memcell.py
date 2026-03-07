"""
MemCell Engine - Enhanced memory write units.

A MemCell wraps an AtomicFact with:
- Lifecycle stage (exploration -> consolidation -> mastery -> dormant)
- Cell type (fact, decision, preference, constraint, observation)
- Importance scoring
- Embedding vector
- Connection graph

Evolution thresholds are encapsulated internally.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class LifecycleStage(str, Enum):
    EXPLORATION = "exploration"
    CONSOLIDATION = "consolidation"
    MASTERY = "mastery"
    DORMANT = "dormant"


class CellType(str, Enum):
    FACT = "fact"
    DECISION = "decision"
    PREFERENCE = "preference"
    CONSTRAINT = "constraint"
    OBSERVATION = "observation"


@dataclass
class MemCell:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    note_id: str = ""
    content: str = ""
    cell_type: str = "fact"
    facts: list = field(default_factory=list)
    stage: LifecycleStage = LifecycleStage.EXPLORATION
    importance: float = 0.5
    access_count: int = 0
    last_accessed: float = field(default_factory=time.time)
    created_at: float = field(default_factory=time.time)
    agent_id: str = ""
    scene: str = ""
    embedding: Optional[list] = None
    connections: list = field(default_factory=list)
    metadata: dict = field(default_factory=dict)

    def access(self, evolution_strategy=None):
        self.access_count += 1
        self.last_accessed = time.time()
        if evolution_strategy:
            evolution_strategy.evaluate(self)
        else:
            self._default_evolve()

    def _default_evolve(self):
        from openmemo._internal import get_evolution_params
        params = get_evolution_params()
        if self.access_count >= params["mastery_access"] and self.importance >= params["mastery_importance"]:
            self.stage = LifecycleStage.MASTERY
        elif self.access_count >= params["consolidation_access"]:
            self.stage = LifecycleStage.CONSOLIDATION

        age_days = (time.time() - self.last_accessed) / 86400
        if age_days > params["dormant_days"] and self.stage != LifecycleStage.MASTERY:
            self.stage = LifecycleStage.DORMANT

    def to_dict(self):
        return {
            "id": self.id,
            "note_id": self.note_id,
            "content": self.content,
            "cell_type": self.cell_type,
            "facts": self.facts,
            "stage": self.stage.value,
            "importance": self.importance,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "created_at": self.created_at,
            "agent_id": self.agent_id,
            "scene": self.scene,
            "connections": self.connections,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemCell":
        cell = cls(
            id=data.get("id", str(uuid.uuid4())),
            note_id=data.get("note_id", ""),
            content=data.get("content", ""),
            cell_type=data.get("cell_type", "fact"),
            facts=data.get("facts", []),
            stage=LifecycleStage(data.get("stage", "exploration")),
            importance=data.get("importance", 0.5),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed", time.time()),
            created_at=data.get("created_at", time.time()),
            agent_id=data.get("agent_id", ""),
            scene=data.get("scene", ""),
            connections=data.get("connections", []),
            metadata=data.get("metadata", {}),
        )
        return cell
