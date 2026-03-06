"""
Version Manager - Tracks memory evolution over time.

Maintains version history for MemCells, allowing rollback
and audit of how knowledge changed.
"""

import time
import copy
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class MemoryVersion:
    version_id: str = ""
    cell_id: str = ""
    content: str = ""
    stage: str = ""
    importance: float = 0.0
    timestamp: float = field(default_factory=time.time)
    change_type: str = "update"
    previous_version: str = ""


class VersionManager:
    def __init__(self):
        self._versions = {}

    def snapshot(self, cell: dict, change_type: str = "update") -> MemoryVersion:
        cell_id = cell.get("id", "")
        history = self._versions.get(cell_id, [])
        version_num = len(history) + 1

        version = MemoryVersion(
            version_id=f"{cell_id}_v{version_num}",
            cell_id=cell_id,
            content=cell.get("content", ""),
            stage=cell.get("stage", ""),
            importance=cell.get("importance", 0.0),
            change_type=change_type,
            previous_version=history[-1].version_id if history else "",
        )

        if cell_id not in self._versions:
            self._versions[cell_id] = []
        self._versions[cell_id].append(version)

        return version

    def get_history(self, cell_id: str) -> List[MemoryVersion]:
        return self._versions.get(cell_id, [])

    def get_version(self, version_id: str) -> Optional[MemoryVersion]:
        for history in self._versions.values():
            for v in history:
                if v.version_id == version_id:
                    return v
        return None

    def rollback(self, cell_id: str, version_id: str) -> Optional[dict]:
        version = self.get_version(version_id)
        if not version or version.cell_id != cell_id:
            return None

        return {
            "id": cell_id,
            "content": version.content,
            "stage": version.stage,
            "importance": version.importance,
        }
