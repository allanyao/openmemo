"""
Reconstructive Recall - Narrative generation from memory.

Given a query, reconstructs a coherent narrative by:
1. Recalling relevant MemCells
2. Ordering by timeline
3. Building a structured response
"""

import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Reconstruction:
    query: str = ""
    narrative: str = ""
    sources: list = field(default_factory=list)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)


class ReconstructiveRecall:
    def __init__(self, recall_engine=None, store=None):
        self.recall_engine = recall_engine
        self.store = store

    def reconstruct(self, query: str, max_sources: int = 10) -> Reconstruction:
        if not self.recall_engine:
            return Reconstruction(query=query, narrative="No recall engine available.")

        results = self.recall_engine.recall(query, top_k=max_sources)

        if not results:
            return Reconstruction(query=query, narrative="No relevant memories found.")

        sorted_results = sorted(
            results,
            key=lambda r: r.metadata.get("timestamp", 0) if r.metadata else 0
        )

        segments = []
        for r in sorted_results:
            segments.append(r.content)

        narrative = self._build_narrative(segments)
        avg_score = sum(r.score for r in sorted_results) / len(sorted_results) if sorted_results else 0

        return Reconstruction(
            query=query,
            narrative=narrative,
            sources=[r.cell_id for r in sorted_results],
            confidence=min(avg_score, 1.0),
        )

    def _build_narrative(self, segments: List[str]) -> str:
        if not segments:
            return ""
        if len(segments) == 1:
            return segments[0]
        return "\n\n".join(f"- {s}" for s in segments)
