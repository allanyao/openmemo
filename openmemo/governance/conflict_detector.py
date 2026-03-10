"""
Conflict Detector - Identifies contradictory facts in memory.

Supports pluggable conflict detection strategies.
The default implementation provides basic negation-based detection.
Detection rules are fully encapsulated within strategy implementations.
"""

import time
from abc import ABC, abstractmethod
from typing import List
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


class ConflictStrategy(ABC):
    @abstractmethod
    def is_conflicting(self, text_a: str, text_b: str) -> bool:
        pass


class DefaultConflictStrategy(ConflictStrategy):
    def __init__(self, config=None):
        pass

    def is_conflicting(self, text_a: str, text_b: str) -> bool:
        words_a = set(text_a.lower().split())
        words_b = set(text_b.lower().split())

        shared = words_a & words_b
        if len(shared) < 2:
            return False

        diff_a = words_a - shared
        diff_b = words_b - shared

        negation_markers = {"not", "no", "never", "don't", "doesn't", "didn't",
                            "won't", "wouldn't", "can't", "cannot", "isn't", "aren't"}

        a_has_neg = bool(words_a & negation_markers)
        b_has_neg = bool(words_b & negation_markers)
        if a_has_neg != b_has_neg:
            return True

        if len(diff_a) <= 2 and len(diff_b) <= 2 and diff_a != diff_b:
            return True

        return False


class ConflictDetector:
    def __init__(self, strategy: ConflictStrategy = None, config=None,
                 constitution=None):
        self._strategy = strategy or DefaultConflictStrategy(config=config)
        self._conflicts = []
        self._constitution = constitution

    def set_constitution(self, constitution):
        self._constitution = constitution

    def detect(self, new_cell: dict, existing_cells: List[dict]) -> List[Conflict]:
        new_content = new_cell.get("content", "")
        new_confidence = new_cell.get("metadata", {}).get("confidence", 0.5)
        conflicts = []

        for cell in existing_cells:
            existing_content = cell.get("content", "")
            if self._strategy.is_conflicting(new_content, existing_content):
                old_confidence = cell.get("metadata", {}).get("confidence", 0.5)

                auto_resolved = False
                resolution = ""
                if self._constitution:
                    if self._constitution.allow_conflict_override(old_confidence, new_confidence):
                        auto_resolved = True
                        resolution = "constitution_override"

                conflict = Conflict(
                    id=f"conflict_{len(self._conflicts)}",
                    cell_id_a=new_cell.get("id", ""),
                    cell_id_b=cell.get("id", ""),
                    content_a=new_content,
                    content_b=existing_content,
                    resolved=auto_resolved,
                    resolution=resolution,
                )
                conflicts.append(conflict)
                self._conflicts.append(conflict)

        return conflicts

    def get_unresolved(self) -> List[Conflict]:
        return [c for c in self._conflicts if not c.resolved]

    def resolve(self, conflict_id: str, resolution: str):
        for c in self._conflicts:
            if c.id == conflict_id:
                c.resolved = True
                c.resolution = resolution
                break
