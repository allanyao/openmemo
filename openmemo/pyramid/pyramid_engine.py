"""
Memory Pyramid Engine.

Three-tier memory compression with configurable parameters.
Compression strategy is pluggable via CompressionStrategy interface.
Tier boundaries and batch sizes are managed through PyramidConfig.
"""

import time
from abc import ABC, abstractmethod
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


class CompressionStrategy(ABC):
    @abstractmethod
    def compress(self, cells: List[dict]) -> str:
        pass


class DefaultCompressionStrategy(CompressionStrategy):
    def __init__(self, summarizer=None):
        self._summarizer = summarizer

    def compress(self, cells: List[dict]) -> str:
        if self._summarizer:
            return self._summarizer.summarize(cells)
        contents = [c.get("content", "") for c in cells]
        return " | ".join(contents)


class PyramidEngine:
    def __init__(self, store=None, summarizer=None,
                 compression: CompressionStrategy = None, config=None):
        from openmemo.config import PyramidConfig
        self.store = store
        self._config = config or PyramidConfig()
        self._compression = compression or DefaultCompressionStrategy(summarizer)

    def process(self, cells: List[dict]) -> dict:
        short_term = []
        mid_term = []

        for cell in cells:
            age_hours = (time.time() - cell.get("created_at", time.time())) / 3600

            if age_hours < self._config.short_term_hours:
                short_term.append(cell)
            else:
                mid_term.append(cell)

        promotions = 0
        if len(short_term) > self._config.short_term_max:
            overflow = short_term[self._config.short_term_max:]
            short_term = short_term[:self._config.short_term_max]

            for batch in self._batch(overflow, self._config.batch_size):
                summary = self._compression.compress(batch)
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
