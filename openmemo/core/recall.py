"""
Recall Engine - Tri-brain retrieval architecture.

Three retrieval strategies:
- Fast Brain: keyword/BM25 matching
- Middle Brain: semantic embedding similarity
- Slow Brain: LLM-powered reasoning (optional)

Results are merged and reranked with token budget control.
"""

import re
import math
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class RecallResult:
    cell_id: str = ""
    content: str = ""
    score: float = 0.0
    source: str = "fast"
    metadata: dict = field(default_factory=dict)


class RecallEngine:
    def __init__(self, store=None):
        self.store = store

    def recall(self, query: str, top_k: int = 10, budget: int = 2000) -> List[RecallResult]:
        results = []

        fast_results = self._fast_brain(query, top_k * 2)
        results.extend(fast_results)

        mid_results = self._middle_brain(query, top_k * 2)
        results.extend(mid_results)

        merged = self._merge_and_rerank(results, top_k)
        return self._apply_budget(merged, budget)

    def _fast_brain(self, query: str, top_k: int) -> List[RecallResult]:
        if not self.store:
            return []

        keywords = self._extract_keywords(query)
        if not keywords:
            return []

        all_cells = self.store.list_cells()
        scored = []

        for cell in all_cells:
            score = self._bm25_score(keywords, cell.get("content", ""))
            if score > 0:
                scored.append(RecallResult(
                    cell_id=cell.get("id", ""),
                    content=cell.get("content", ""),
                    score=score,
                    source="fast",
                ))

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def _middle_brain(self, query: str, top_k: int) -> List[RecallResult]:
        if not self.store or not hasattr(self.store, "search_by_embedding"):
            return []

        results = self.store.search_by_embedding(query, top_k)
        return [
            RecallResult(
                cell_id=r.get("id", ""),
                content=r.get("content", ""),
                score=r.get("score", 0.0),
                source="middle",
            )
            for r in results
        ]

    def _merge_and_rerank(self, results: List[RecallResult], top_k: int) -> List[RecallResult]:
        seen = {}
        for r in results:
            if r.cell_id in seen:
                existing = seen[r.cell_id]
                existing.score = max(existing.score, r.score) * 1.2
            else:
                seen[r.cell_id] = r

        merged = list(seen.values())
        merged.sort(key=lambda x: x.score, reverse=True)
        return merged[:top_k]

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

    def _extract_keywords(self, query: str) -> List[str]:
        stop_words = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at", "to", "for",
                      "of", "and", "or", "but", "not", "with", "this", "that", "it", "be", "have",
                      "do", "what", "how", "when", "where", "who", "which", "my", "your", "i"}
        words = re.findall(r'\w+', query.lower())
        return [w for w in words if w not in stop_words and len(w) > 1]

    def _bm25_score(self, keywords: List[str], text: str, k1: float = 1.5, b: float = 0.75) -> float:
        text_lower = text.lower()
        words = text_lower.split()
        doc_len = len(words)
        avg_len = 100

        score = 0.0
        for kw in keywords:
            tf = text_lower.count(kw)
            if tf > 0:
                idf = math.log(2.0)
                tf_norm = (tf * (k1 + 1)) / (tf + k1 * (1 - b + b * doc_len / avg_len))
                score += idf * tf_norm

        return score
