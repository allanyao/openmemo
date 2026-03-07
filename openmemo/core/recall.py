"""
Recall Engine - Pluggable retrieval architecture.

Supports multiple retrieval strategies and scene-based filtering.
Custom strategies can be injected via RecallStrategy interface.
"""

import re
from abc import ABC, abstractmethod
from typing import List
from dataclasses import dataclass, field

from openmemo.protocol.schemas import RecallResultItem


class RecallStrategy(ABC):
    @abstractmethod
    def retrieve(self, query: str, store=None, top_k: int = 10, **kwargs) -> List[RecallResultItem]:
        pass


class BM25Strategy(RecallStrategy):
    def __init__(self, config=None):
        from openmemo.config import RecallConfig
        self._config = config or RecallConfig()

    def retrieve(self, query: str, store=None, top_k: int = 10, **kwargs) -> List[RecallResultItem]:
        if not store:
            return []

        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        agent_id = kwargs.get("agent_id")
        scene = kwargs.get("scene")
        all_cells = store.list_cells(agent_id=agent_id, scene=scene)
        scored = []

        for cell in all_cells:
            score = self._score(keywords, cell.get("content", ""))
            if score > 0:
                scored.append(RecallResultItem(
                    cell_id=cell.get("id", ""),
                    content=cell.get("content", ""),
                    score=score,
                    source="fast",
                ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _extract_keywords(self, query: str) -> List[str]:
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
                      "of", "and", "or", "but", "not", "with", "this", "that", "it", "be", "have",
                      "do", "what", "how", "when", "where", "who", "which", "my", "your", "i"}
        words = re.findall(r'\w+', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _score(self, keywords: List[str], text: str) -> float:
        text_lower = text.lower()
        score = 0.0
        for kw in keywords:
            if kw in text_lower:
                score += 1.0
        return score


class VectorStrategy(RecallStrategy):
    def __init__(self, vector_store=None, embed_fn=None):
        self._vector_store = vector_store
        self._embed_fn = embed_fn

    def retrieve(self, query: str, store=None, top_k: int = 10, **kwargs) -> List[RecallResultItem]:
        if not self._vector_store or not self._embed_fn:
            return []

        try:
            query_embedding = self._embed_fn(query)
            results = self._vector_store.search(query_embedding, top_k=top_k)
            return [
                RecallResultItem(
                    cell_id=r.get("id", ""),
                    content=r.get("content", ""),
                    score=r.get("score", 0.0),
                    source="middle",
                )
                for r in results
            ]
        except Exception:
            return []


@dataclass
class RecallResult:
    cell_id: str = ""
    content: str = ""
    score: float = 0.0
    source: str = "fast"
    metadata: dict = field(default_factory=dict)


class MergeStrategy(ABC):
    @abstractmethod
    def merge(self, results: List[RecallResultItem], top_k: int) -> List[RecallResult]:
        pass


class DefaultMergeStrategy(MergeStrategy):
    def merge(self, results: List[RecallResultItem], top_k: int) -> List[RecallResult]:
        seen = {}
        for r in results:
            if r.cell_id in seen:
                existing = seen[r.cell_id]
                existing.score = max(existing.score, r.score)
            else:
                seen[r.cell_id] = RecallResult(
                    cell_id=r.cell_id,
                    content=r.content,
                    score=r.score,
                    source=r.source,
                )

        merged = list(seen.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]


class RecallEngine:
    def __init__(self, store=None, vector_store=None, embed_fn=None,
                 strategies: List[RecallStrategy] = None,
                 merge_strategy: MergeStrategy = None,
                 config=None):
        from openmemo.config import RecallConfig
        self.store = store
        self._config = config or RecallConfig()

        if strategies is not None:
            self._strategies = strategies
        else:
            self._strategies = [BM25Strategy(config=self._config)]
            if vector_store and embed_fn:
                self._strategies.append(VectorStrategy(vector_store, embed_fn))

        self._merge_strategy = merge_strategy or DefaultMergeStrategy()

    def recall(self, query: str, top_k: int = 10, budget: int = 2000,
               agent_id: str = None, scene: str = None) -> List[RecallResult]:
        all_results = []

        for strategy in self._strategies:
            results = strategy.retrieve(
                query, store=self.store, top_k=top_k * 2,
                agent_id=agent_id, scene=scene,
            )
            all_results.extend(results)

        merged = self._merge_strategy.merge(all_results, top_k)
        return self._apply_budget(merged, budget)

    def _apply_budget(self, results: List[RecallResult], budget: int) -> List[RecallResult]:
        total_tokens = 0
        budgeted = []
        for r in results:
            tokens = len(r.content.split())
            if total_tokens + tokens > budget:
                break
            total_tokens += tokens
            budgeted.append(r)
        return budgeted
