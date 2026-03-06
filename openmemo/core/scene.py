"""
MemScene Engine - Scene-based memory containers.

A MemScene groups related MemCells by context,
enabling narrative-level recall and summarization.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class MemScene:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    summary: str = ""
    cell_ids: list = field(default_factory=list)
    theme: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def add_cell(self, cell_id: str):
        if cell_id not in self.cell_ids:
            self.cell_ids.append(cell_id)
            self.updated_at = time.time()

    def remove_cell(self, cell_id: str):
        if cell_id in self.cell_ids:
            self.cell_ids.remove(cell_id)
            self.updated_at = time.time()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "cell_ids": self.cell_ids,
            "theme": self.theme,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "MemScene":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            title=data.get("title", ""),
            summary=data.get("summary", ""),
            cell_ids=data.get("cell_ids", []),
            theme=data.get("theme", ""),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )
