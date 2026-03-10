"""
Memory Relationship Graph Engine.

Detects and manages relationships between memories:
  supports, contradicts, causes, fixes, related, extends

Enables graph-based recall instead of pure vector search.
"""

import re
import time
import uuid
from typing import List, Dict, Callable, Optional


RELATION_TYPES = {"supports", "contradicts", "causes", "fixes", "related", "extends"}

CONTRADICTION_SIGNALS = [
    (r"\bnot\b", r"\bshould\b"),
    (r"\bavoid\b", r"\buse\b"),
    (r"\bdon'?t\b", r"\bdo\b"),
    (r"\bnever\b", r"\balways\b"),
    (r"\bdeprecated\b", r"\brecommend"),
    (r"\binstead of\b",),
    (r"\breplaced by\b",),
    (r"\bno longer\b",),
]

CAUSAL_KEYWORDS = [
    r"\bbecause\b", r"\bcaused by\b", r"\bdue to\b", r"\bresult of\b",
    r"\bleads to\b", r"\btrigger", r"\broot cause\b",
]

FIX_KEYWORDS = [
    r"\bfix\b", r"\bfixed\b", r"\bsolve[ds]?\b", r"\bresolve[ds]?\b",
    r"\bworkaround\b", r"\bpatch", r"\bhotfix\b", r"\brepair",
]

EXTEND_KEYWORDS = [
    r"\bextend", r"\bbuild on\b", r"\bbuilds upon\b", r"\baddition to\b",
    r"\bfurthermore\b", r"\bmoreover\b", r"\benhance",
]


class GraphBuilder:
    def __init__(self, store=None, llm_fn: Optional[Callable] = None,
                 similarity_threshold: float = 0.3,
                 max_candidates: int = 20):
        self.store = store
        self.llm_fn = llm_fn
        self.similarity_threshold = similarity_threshold
        self.max_candidates = max_candidates

    def detect_relationships(self, new_cell: dict,
                             existing_cells: List[dict]) -> List[dict]:
        edges = []
        new_content = new_cell.get("content", "").lower()
        new_id = new_cell.get("id", "")
        new_keywords = self._extract_keywords(new_content)

        if not new_keywords or not new_id:
            return edges

        candidates = self._find_candidates(new_keywords, existing_cells)

        for candidate in candidates:
            cand_id = candidate.get("id", "")
            if cand_id == new_id:
                continue

            cand_content = candidate.get("content", "").lower()

            relation, confidence = self._classify_relationship(
                new_content, cand_content, new_cell, candidate
            )

            if relation and confidence >= 0.3:
                edge = {
                    "edge_id": str(uuid.uuid4())[:12],
                    "memory_a": new_id,
                    "memory_b": cand_id,
                    "relation_type": relation,
                    "confidence": round(confidence, 3),
                    "created_at": time.time(),
                    "metadata": {},
                }
                edges.append(edge)

        return edges

    def build_edges(self, memory_id: str, store=None) -> List[dict]:
        effective_store = store or self.store
        if not effective_store:
            return []

        cell = effective_store.get_cell(memory_id)
        if not cell:
            return []

        scene = cell.get("scene", "")
        agent_id = cell.get("agent_id", "")

        existing = effective_store.list_cells(
            limit=self.max_candidates * 2,
            agent_id=agent_id or None,
            scene=scene or None,
        )

        edges = self.detect_relationships(cell, existing)

        for edge in edges:
            effective_store.put_edge(edge)

        return edges

    def _find_candidates(self, keywords: List[str],
                         cells: List[dict]) -> List[dict]:
        scored = []
        for cell in cells:
            content = cell.get("content", "").lower()
            overlap = sum(1 for kw in keywords if kw in content)
            if overlap > 0:
                scored.append((overlap, cell))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored[:self.max_candidates]]

    def _classify_relationship(self, text_a: str, text_b: str,
                               cell_a: dict, cell_b: dict) -> tuple:
        if self.llm_fn:
            try:
                result = self.llm_fn(text_a, text_b)
                if isinstance(result, dict):
                    rel = result.get("relation", "")
                    conf = result.get("confidence", 0.5)
                    if rel in RELATION_TYPES:
                        return rel, conf
            except Exception:
                pass

        if self._is_fix(text_a, text_b):
            return "fixes", self._keyword_confidence(text_a, text_b, FIX_KEYWORDS)

        if self._is_contradiction(text_a, text_b):
            return "contradicts", self._contradiction_confidence(text_a, text_b)

        if self._is_causal(text_a, text_b):
            return "causes", self._keyword_confidence(text_a, text_b, CAUSAL_KEYWORDS)

        if self._is_extension(text_a, text_b):
            return "extends", self._keyword_confidence(text_a, text_b, EXTEND_KEYWORDS)

        overlap = self._keyword_overlap(text_a, text_b)
        if overlap >= self.similarity_threshold:
            if self._same_direction(text_a, text_b):
                return "supports", min(0.9, overlap + 0.1)
            return "related", overlap

        return None, 0.0

    def _is_fix(self, text_a: str, text_b: str) -> bool:
        combined = text_a + " " + text_b
        return any(re.search(pat, combined) for pat in FIX_KEYWORDS)

    def _is_contradiction(self, text_a: str, text_b: str) -> bool:
        for signals in CONTRADICTION_SIGNALS:
            if len(signals) == 1:
                if re.search(signals[0], text_a) or re.search(signals[0], text_b):
                    return True
            elif len(signals) >= 2:
                if (re.search(signals[0], text_a) and re.search(signals[1], text_b)) or \
                   (re.search(signals[1], text_a) and re.search(signals[0], text_b)):
                    return True
        return False

    def _is_causal(self, text_a: str, text_b: str) -> bool:
        combined = text_a + " " + text_b
        return any(re.search(pat, combined) for pat in CAUSAL_KEYWORDS)

    def _is_extension(self, text_a: str, text_b: str) -> bool:
        combined = text_a + " " + text_b
        return any(re.search(pat, combined) for pat in EXTEND_KEYWORDS)

    def _keyword_overlap(self, text_a: str, text_b: str) -> float:
        words_a = set(re.findall(r'\w{3,}', text_a))
        words_b = set(re.findall(r'\w{3,}', text_b))
        stop = {"the", "and", "for", "that", "this", "with", "from", "have",
                "are", "was", "were", "been", "not", "but", "can", "will"}
        words_a -= stop
        words_b -= stop
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union) if union else 0.0

    def _same_direction(self, text_a: str, text_b: str) -> bool:
        neg_a = bool(re.search(r"\bnot\b|\bnever\b|\bavoid\b|\bdon'?t\b", text_a))
        neg_b = bool(re.search(r"\bnot\b|\bnever\b|\bavoid\b|\bdon'?t\b", text_b))
        return neg_a == neg_b

    def _keyword_confidence(self, text_a: str, text_b: str,
                            patterns: list) -> float:
        combined = text_a + " " + text_b
        hits = sum(1 for p in patterns if re.search(p, combined))
        return min(0.95, 0.5 + hits * 0.1)

    def _contradiction_confidence(self, text_a: str, text_b: str) -> float:
        hits = 0
        for signals in CONTRADICTION_SIGNALS:
            for sig in signals:
                if re.search(sig, text_a) or re.search(sig, text_b):
                    hits += 1
        return min(0.95, 0.4 + hits * 0.1)

    def _extract_keywords(self, text: str) -> List[str]:
        stop = {"the", "a", "an", "is", "are", "was", "were", "in", "on", "at",
                "to", "for", "of", "and", "or", "but", "not", "with", "this",
                "that", "it", "be", "have", "do", "what", "how", "when",
                "where", "who", "which", "my", "your", "i"}
        words = re.findall(r'\w+', text.lower())
        return [w for w in words if w not in stop and len(w) > 2]


def get_memory_graph(store, memory_id: str, depth: int = 1) -> dict:
    visited = set()
    nodes = []
    edges_out = []

    seen_edge_ids = set()

    def _expand(mid: str, current_depth: int):
        if mid in visited or current_depth > depth:
            return
        visited.add(mid)

        cell = store.get_cell(mid)
        if cell:
            nodes.append({
                "memory_id": mid,
                "content": cell.get("content", ""),
                "scene": cell.get("scene", ""),
                "memory_type": cell.get("cell_type", "fact"),
            })

        if current_depth >= depth:
            return

        edges = store.get_edges(mid)
        for edge in edges:
            neighbor = edge["memory_b"] if edge["memory_a"] == mid else edge["memory_a"]
            if edge["edge_id"] not in seen_edge_ids:
                seen_edge_ids.add(edge["edge_id"])
                edges_out.append(edge)
            if neighbor not in visited:
                _expand(neighbor, current_depth + 1)

    _expand(memory_id, 0)
    return {"nodes": nodes, "edges": edges_out}


def detect_conflicts(store, agent_id: str = None, scene: str = None) -> List[dict]:
    edges = store.list_edges(limit=1000)
    conflicts = []
    for edge in edges:
        if edge["relation_type"] != "contradicts":
            continue
        cell_a = store.get_cell(edge["memory_a"])
        cell_b = store.get_cell(edge["memory_b"])
        if not cell_a or not cell_b:
            continue
        if agent_id:
            if cell_a.get("agent_id", "") != agent_id and cell_b.get("agent_id", "") != agent_id:
                continue
        if scene:
            if cell_a.get("scene", "") != scene and cell_b.get("scene", "") != scene:
                continue

        meta_a = cell_a.get("metadata", {})
        if isinstance(meta_a, str):
            import json
            try:
                meta_a = json.loads(meta_a)
            except (json.JSONDecodeError, TypeError):
                meta_a = {}
        meta_b = cell_b.get("metadata", {})
        if isinstance(meta_b, str):
            import json
            try:
                meta_b = json.loads(meta_b)
            except (json.JSONDecodeError, TypeError):
                meta_b = {}
        conf_a = meta_a.get("confidence", 0.5)
        conf_b = meta_b.get("confidence", 0.5)

        conflicts.append({
            "edge_id": edge["edge_id"],
            "memory_a": {
                "id": edge["memory_a"],
                "content": cell_a.get("content", ""),
                "confidence": conf_a,
            },
            "memory_b": {
                "id": edge["memory_b"],
                "content": cell_b.get("content", ""),
                "confidence": conf_b,
            },
            "winner": edge["memory_a"] if conf_a >= conf_b else edge["memory_b"],
            "edge_confidence": edge["confidence"],
        })

    return conflicts
