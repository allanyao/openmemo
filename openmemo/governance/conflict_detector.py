"""
Conflict Detector - Identifies contradictory facts in memory.

Detects when new information conflicts with existing knowledge
and flags it for resolution.
"""

import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Conflict:
    id: str = ""
    cell_id_a: str = ""
    cell_id_b: str = ""
    content_a: str = ""
    content_b: str = ""
    conflict_type: str = "contradiction"
    resolved: bool = False
    resolution: str = ""
    detected_at: float = field(default_factory=time.time)


class ConflictDetector:
    NEGATION_PAIRS = [
        ("prefers", "dislikes"), ("likes", "hates"), ("uses", "avoids"),
        ("always", "never"), ("true", "false"), ("yes", "no"),
        ("enabled", "disabled"), ("on", "off"), ("active", "inactive"),
    ]

    def __init__(self):
        self._conflicts = []

    def detect(self, new_cell: dict, existing_cells: List[dict]) -> List[Conflict]:
        new_content = new_cell.get("content", "").lower()
        conflicts = []

        for cell in existing_cells:
            existing_content = cell.get("content", "").lower()
            if self._is_conflicting(new_content, existing_content):
                conflict = Conflict(
                    id=f"conflict_{len(self._conflicts)}",
                    cell_id_a=new_cell.get("id", ""),
                    cell_id_b=cell.get("id", ""),
                    content_a=new_cell.get("content", ""),
                    content_b=cell.get("content", ""),
                )
                conflicts.append(conflict)
                self._conflicts.append(conflict)

        return conflicts

    def _is_conflicting(self, text_a: str, text_b: str) -> bool:
        for pos, neg in self.NEGATION_PAIRS:
            if pos in text_a and neg in text_b:
                shared_words = set(text_a.split()) & set(text_b.split())
                if len(shared_words) >= 2:
                    return True
            if neg in text_a and pos in text_b:
                shared_words = set(text_a.split()) & set(text_b.split())
                if len(shared_words) >= 2:
                    return True

        return False

    def get_unresolved(self) -> List[Conflict]:
        return [c for c in self._conflicts if not c.resolved]

    def resolve(self, conflict_id: str, resolution: str):
        for c in self._conflicts:
            if c.id == conflict_id:
                c.resolved = True
                c.resolution = resolution
                break
