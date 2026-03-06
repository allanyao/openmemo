"""
Memory Pyramid Engine.

Three-tier memory compression:
- Short-term: Raw notes and recent MemCells
- Mid-term: Category summaries and patterns
- Long-term: Stable user profile and knowledge

Controls token budget by auto-compressing older memories.
"""

import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class PyramidEntry:
    id: str = ""
    tier: str = "short"
    content: str = ""
    source_ids: list = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)


class PyramidEngine:
    SHORT_TERM_MAX = 50
    MID_TERM_MAX = 20
    LONG_TERM_MAX = 10

    def __init__(self, store=None, summarizer=None):
        self.store = store
        self.summarizer = summarizer

    def process(self, cells: List[dict]) -> dict:
        short_term = []
        mid_term = []

        for cell in cells:
            age_hours = (time.time() - cell.get("created_at", time.time())) / 3600

            if age_hours < 24:
                short_term.append(cell)
            else:
                mid_term.append(cell)

        promotions = 0
        if len(short_term) > self.SHORT_TERM_MAX:
            overflow = short_term[self.SHORT_TERM_MAX:]
            short_term = short_term[:self.SHORT_TERM_MAX]

            if self.summarizer:
                for batch in self._batch(overflow, 5):
                    summary = self.summarizer.summarize(batch)
                    mid_term.append({
                        "content": summary,
                        "tier": "mid",
                        "source_ids": [c.get("id", "") for c in batch],
                    })
                    promotions += 1

        return {
            "short_term": len(short_term),
            "mid_term": len(mid_term),
            "promotions": promotions,
        }

    def get_context(self, tier: str = "all", budget: int = 2000) -> List[dict]:
        if not self.store:
            return []

        cells = self.store.list_cells(limit=200)
        result = []
        tokens = 0

        for cell in cells:
            cell_tokens = len(cell.get("content", "").split())
            if tokens + cell_tokens > budget:
                break
            result.append(cell)
            tokens += cell_tokens

        return result

    def _batch(self, items: list, size: int) -> list:
        for i in range(0, len(items), size):
            yield items[i:i + size]
