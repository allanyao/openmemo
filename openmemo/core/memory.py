"""
Core memory data structures.

A Note is the raw input. It gets processed into AtomicFacts,
which are grouped into MemCells, which form MemScenes.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Note:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    source: str = "manual"
    timestamp: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Note":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            content=data.get("content", ""),
            source=data.get("source", "manual"),
            timestamp=data.get("timestamp", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AtomicFact:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    note_id: str = ""
    fact_type: str = "statement"
    confidence: float = 1.0
    timestamp: float = field(default_factory=time.time)
    entities: list = field(default_factory=list)
    relations: list = field(default_factory=list)

    def to_dict(self):
        return {
            "id": self.id,
            "content": self.content,
            "note_id": self.note_id,
            "fact_type": self.fact_type,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "entities": self.entities,
            "relations": self.relations,
        }
