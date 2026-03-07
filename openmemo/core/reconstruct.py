"""
Reconstructive Recall - Narrative generation from memory.

Supports pluggable reconstruction strategies.
The default implementation provides timeline-based narrative
with conflict detection and annotation.
"""

import time
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass, field


@dataclass
class Reconstruction:
    query: str = ""
    narrative: str = ""
    sources: list = field(default_factory=list)
    confidence: float = 0.0
    conflicts: list = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)


class ReconstructStrategy(ABC):
    @abstractmethod
    def build_narrative(self, query: str, segments: List[str], scores: List[float],
                        cell_data: List[dict] = None) -> Reconstruction:
        pass


class DefaultReconstructStrategy(ReconstructStrategy):
    def build_narrative(self, query: str, segments: List[str], scores: List[float],
                        cell_data: List[dict] = None) -> Reconstruction:
        if not segments:
            return Reconstruction(query=query, narrative="No relevant memories found.")

        conflicts = []
        if cell_data:
            conflicts = self._detect_conflicts(cell_data)

        if len(segments) == 1:
            narrative = segments[0]
        else:
            parts = []
            for i, s in enumerate(segments):
                conflict_marker = ""
                if conflicts:
                    for c in conflicts:
                        if i in c.get("indices", []):
                            conflict_marker = " [CONFLICT]"
                            break
                parts.append(f"- {s}{conflict_marker}")
            narrative = "\n\n".join(parts)

        avg_score = sum(scores) / len(scores) if scores else 0

        return Reconstruction(
            query=query,
            narrative=narrative,
            confidence=min(avg_score, 1.0),
            conflicts=conflicts,
        )

    def _detect_conflicts(self, cell_data: List[dict]) -> list:
        conflicts = []
        for i, cell in enumerate(cell_data):
            if cell.get("has_conflicts") or cell.get("metadata", {}).get("has_conflicts"):
                for j in range(i + 1, len(cell_data)):
                    other = cell_data[j]
                    if self._is_conflicting(cell, other):
                        conflicts.append({
                            "indices": [i, j],
                            "cell_ids": [cell.get("id", ""), other.get("id", "")],
                            "type": "potential_conflict",
                        })
        return conflicts

    def _is_conflicting(self, cell_a: dict, cell_b: dict) -> bool:
        content_a = cell_a.get("content", "").lower()
        content_b = cell_b.get("content", "").lower()
        negation_pairs = [
            ("prefer", "not prefer"), ("like", "dislike"),
            ("enable", "disable"), ("true", "false"),
            ("yes", "no"), ("allow", "deny"),
        ]
        for pos, neg in negation_pairs:
            if (pos in content_a and neg in content_b) or (neg in content_a and pos in content_b):
                return True
        return False


class ReconstructiveRecall:
    def __init__(self, recall_engine=None, store=None, strategy: ReconstructStrategy = None):
        self.recall_engine = recall_engine
        self.store = store
        self._strategy = strategy or DefaultReconstructStrategy()

    def reconstruct(self, query: str, max_sources: int = 10,
                    agent_id: str = None) -> Reconstruction:
        if not self.recall_engine:
            return Reconstruction(query=query, narrative="No recall engine available.")

        results = self.recall_engine.recall(query, top_k=max_sources, agent_id=agent_id)

        if not results:
            return Reconstruction(query=query, narrative="No relevant memories found.")

        sorted_results = sorted(
            results,
            key=lambda r: r.metadata.get("timestamp", 0) if r.metadata else 0
        )

        segments = [r.content for r in sorted_results]
        scores = [r.score for r in sorted_results]

        cell_data = []
        if self.store:
            for r in sorted_results:
                cell = self.store.get_cell(r.cell_id)
                if cell:
                    cell_data.append(cell)

        reconstruction = self._strategy.build_narrative(query, segments, scores, cell_data)
        reconstruction.sources = [r.cell_id for r in sorted_results]

        return reconstruction
