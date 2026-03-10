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
        conversation_id = kwargs.get("conversation_id")

        if agent_id and hasattr(store, "list_cells_scoped"):
            all_cells = store.list_cells_scoped(
                agent_id=agent_id, conversation_id=conversation_id,
                scene=scene, limit=500,
            )
        else:
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

        agent_id = kwargs.get("agent_id")

        try:
            query_embedding = self._embed_fn(query)
            results = self._vector_store.search(query_embedding, top_k=top_k * 3)

            filtered = []
            for r in results:
                if agent_id and store:
                    cell = store.get_cell(r.get("id", ""))
                    if cell:
                        scope = cell.get("scope", "private")
                        cell_agent = cell.get("agent_id", "")
                        if scope == "shared":
                            pass
                        elif scope == "conversation":
                            conv_id = kwargs.get("conversation_id")
                            if cell.get("conversation_id", "") != conv_id:
                                continue
                        elif scope == "private":
                            if cell_agent and cell_agent != agent_id:
                                continue
                filtered.append(r)

            return [
                RecallResultItem(
                    cell_id=r.get("id", ""),
                    content=r.get("content", ""),
                    score=r.get("score", 0.0),
                    source="middle",
                )
                for r in filtered[:top_k]
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
                 config=None, constitution=None,
                 graph_expansion: bool = True):
        from openmemo.config import RecallConfig
        self.store = store
        self._config = config or RecallConfig()
        self._constitution = constitution
        self._graph_expansion = graph_expansion

        if strategies is not None:
            self._strategies = strategies
        else:
            self._strategies = [BM25Strategy(config=self._config)]
            if vector_store and embed_fn:
                self._strategies.append(VectorStrategy(vector_store, embed_fn))

        self._merge_strategy = merge_strategy or DefaultMergeStrategy()

    def set_constitution(self, constitution):
        self._constitution = constitution

    def recall(self, query: str, top_k: int = 10, budget: int = 2000,
               agent_id: str = None, scene: str = None,
               conversation_id: str = None,
               graph: bool = None) -> List[RecallResult]:
        all_results = []
        extra = {"conversation_id": conversation_id} if conversation_id else {}

        if self._constitution and self._constitution.should_prefer_scene_local() and scene:
            for strategy in self._strategies:
                results = strategy.retrieve(
                    query, store=self.store, top_k=top_k * 2,
                    agent_id=agent_id, scene=scene, **extra,
                )
                all_results.extend(results)

            if len(all_results) < top_k:
                global_results = []
                for strategy in self._strategies:
                    results = strategy.retrieve(
                        query, store=self.store, top_k=top_k * 2,
                        agent_id=agent_id, scene=None, **extra,
                    )
                    global_results.extend(results)
                seen_ids = {r.cell_id for r in all_results}
                for r in global_results:
                    if r.cell_id not in seen_ids:
                        r.score *= 0.8
                        all_results.append(r)
        else:
            for strategy in self._strategies:
                results = strategy.retrieve(
                    query, store=self.store, top_k=top_k * 2,
                    agent_id=agent_id, scene=scene, **extra,
                )
                all_results.extend(results)

        merged = self._merge_strategy.merge(all_results, top_k * 3)

        if self._constitution:
            merged = self._apply_constitution_ranking(merged)

        use_graph = graph if graph is not None else self._graph_expansion
        if use_graph and self.store and hasattr(self.store, 'get_edges'):
            merged = self._apply_graph_expansion(
                merged, top_k, agent_id=agent_id,
                conversation_id=conversation_id,
            )

        merged = merged[:top_k]
        return self._apply_budget(merged, budget)

    def _apply_constitution_ranking(self, results: List[RecallResult]) -> List[RecallResult]:
        if not self.store:
            return results

        import time
        now = time.time()
        for r in results:
            cell = self.store.get_cell(r.cell_id)
            if cell:
                priority = self._constitution.get_priority(cell.get("cell_type", "fact"))
                r.score += priority * 0.02

                if self._constitution.should_prefer_recent_high_confidence():
                    age_days = (now - cell.get("created_at", now)) / 86400
                    recency = max(0, 1.0 - (age_days / 30))
                    confidence = cell.get("metadata", {}).get("confidence", 0.5)
                    r.score += recency * 0.1 + confidence * 0.05

        results.sort(key=lambda x: x.score, reverse=True)
        return results

    def _apply_graph_expansion(self, results: List[RecallResult],
                               top_k: int,
                               agent_id: str = None,
                               conversation_id: str = None) -> List[RecallResult]:
        seen_ids = {r.cell_id for r in results}
        expanded = list(results)
        graph_bonus = 0.15

        for r in results[:min(5, len(results))]:
            edges = self.store.get_edges(r.cell_id)
            for edge in edges:
                neighbor_id = (edge["memory_b"]
                               if edge["memory_a"] == r.cell_id
                               else edge["memory_a"])

                if neighbor_id in seen_ids:
                    continue

                cell = self.store.get_cell(neighbor_id)
                if not cell:
                    continue

                if agent_id:
                    scope = cell.get("scope", "private")
                    cell_agent = cell.get("agent_id", "")
                    if scope == "private" and cell_agent and cell_agent != agent_id:
                        continue
                    if scope == "conversation":
                        cell_conv = cell.get("conversation_id", "")
                        if cell_conv != conversation_id:
                            continue

                if edge["relation_type"] == "contradicts":
                    cell_a = self.store.get_cell(edge["memory_a"])
                    cell_b = self.store.get_cell(edge["memory_b"])
                    if cell_a and cell_b:
                        meta_a = cell_a.get("metadata", {})
                        meta_b = cell_b.get("metadata", {})
                        if isinstance(meta_a, str):
                            import json
                            try: meta_a = json.loads(meta_a)
                            except: meta_a = {}
                        if isinstance(meta_b, str):
                            import json
                            try: meta_b = json.loads(meta_b)
                            except: meta_b = {}
                        conf_a = meta_a.get("confidence", 0.5)
                        conf_b = meta_b.get("confidence", 0.5)
                        if (edge["memory_a"] == r.cell_id and conf_a < conf_b) or \
                           (edge["memory_b"] == r.cell_id and conf_b < conf_a):
                            continue

                edge_score = r.score * edge["confidence"] * graph_bonus
                if edge["relation_type"] in ("fixes", "causes"):
                    edge_score *= 2.0
                elif edge["relation_type"] == "supports":
                    edge_score *= 1.5

                expanded.append(RecallResult(
                    cell_id=neighbor_id,
                    content=cell.get("content", ""),
                    score=edge_score,
                    source="graph",
                    metadata={
                        "via_edge": edge["edge_id"],
                        "relation": edge["relation_type"],
                        "from_memory": r.cell_id,
                    },
                ))
                seen_ids.add(neighbor_id)

        expanded.sort(key=lambda x: x.score, reverse=True)
        return expanded

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
