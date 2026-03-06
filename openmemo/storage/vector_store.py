"""
Vector storage interface for semantic search.

This is an optional extension. Install with: pip install openmemo[vector]
Default implementation uses numpy for basic cosine similarity.
"""

import numpy as np
from typing import List, Optional, Tuple


class VectorStore:
    def __init__(self):
        self._vectors = {}
        self._contents = {}

    def add(self, item_id: str, embedding: List[float], content: str = ""):
        self._vectors[item_id] = np.array(embedding, dtype=np.float32)
        self._contents[item_id] = content

    def search(self, query_embedding: List[float], top_k: int = 10) -> List[dict]:
        if not self._vectors:
            return []

        query = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query)
        if query_norm == 0:
            return []
        query = query / query_norm

        scores = []
        for item_id, vec in self._vectors.items():
            vec_norm = np.linalg.norm(vec)
            if vec_norm == 0:
                continue
            similarity = float(np.dot(query, vec / vec_norm))
            scores.append((item_id, similarity))

        scores.sort(key=lambda x: x[1], reverse=True)

        return [
            {
                "id": item_id,
                "content": self._contents.get(item_id, ""),
                "score": score,
            }
            for item_id, score in scores[:top_k]
        ]

    def remove(self, item_id: str):
        self._vectors.pop(item_id, None)
        self._contents.pop(item_id, None)

    def count(self) -> int:
        return len(self._vectors)
