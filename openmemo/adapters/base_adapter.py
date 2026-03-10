"""
Base Memory Adapter — Universal interface for all agent framework integrations.

All adapters must inherit from BaseMemoryAdapter and implement:
- write_memory()
- recall_memory()
- inject_context()
"""

import logging
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("openmemo")


@dataclass
class AdapterMetrics:
    writes: int = 0
    recalls: int = 0
    injections: int = 0
    errors: int = 0
    total_write_ms: float = 0
    total_recall_ms: float = 0

    @property
    def avg_write_ms(self) -> float:
        return self.total_write_ms / self.writes if self.writes else 0

    @property
    def avg_recall_ms(self) -> float:
        return self.total_recall_ms / self.recalls if self.recalls else 0

    def summary(self) -> dict:
        return {
            "writes": self.writes,
            "recalls": self.recalls,
            "injections": self.injections,
            "errors": self.errors,
            "avg_write_ms": round(self.avg_write_ms, 1),
            "avg_recall_ms": round(self.avg_recall_ms, 1),
        }


class BaseMemoryAdapter:
    adapter_name: str = "base"

    def __init__(self, db_path: str = "openmemo.db", agent_id: str = "",
                 memory=None, base_url: str = None, api_key: str = None,
                 default_scene: str = "", recall_limit: int = 5):
        self.agent_id = agent_id
        self.default_scene = default_scene
        self.recall_limit = recall_limit
        self.metrics = AdapterMetrics()

        if memory:
            self._memory = memory
        elif base_url:
            from openmemo.api.remote import RemoteMemory
            self._memory = RemoteMemory(base_url=base_url, api_key=api_key)
        else:
            from openmemo.api.sdk import Memory
            self._memory = Memory(db_path=db_path)

    def write_memory(self, content: str, scene: str = None,
                     memory_type: str = "fact", confidence: float = 0.8,
                     metadata: dict = None) -> str:
        effective_scene = scene or self.default_scene
        start = time.time()
        try:
            result = self._memory.write_memory(
                content=content,
                scene=effective_scene,
                memory_type=memory_type,
                confidence=confidence,
                agent_id=self.agent_id,
                metadata=metadata,
            )
            elapsed = (time.time() - start) * 1000
            self.metrics.writes += 1
            self.metrics.total_write_ms += elapsed
            logger.info("[openmemo:%s] write_memory scene=%s type=%s latency=%.0fms",
                        self.adapter_name, effective_scene, memory_type, elapsed)
            return result
        except Exception as e:
            self.metrics.errors += 1
            logger.warning("[openmemo:%s] write_memory failed: %s", self.adapter_name, e)
            return ""

    def recall_memory(self, query: str, scene: str = None,
                      limit: int = None) -> List[Dict]:
        effective_scene = scene or self.default_scene
        effective_limit = limit or self.recall_limit
        start = time.time()
        try:
            results = self._memory.search_memory(
                query=query,
                scene=effective_scene,
                agent_id=self.agent_id,
                limit=effective_limit,
            )
            elapsed = (time.time() - start) * 1000
            self.metrics.recalls += 1
            self.metrics.total_recall_ms += elapsed
            logger.info("[openmemo:%s] recall_memory query=%s scene=%s hits=%d latency=%.0fms",
                        self.adapter_name, query[:30], effective_scene, len(results), elapsed)
            return results
        except Exception as e:
            self.metrics.errors += 1
            logger.warning("[openmemo:%s] recall_memory failed: %s", self.adapter_name, e)
            return []

    def recall_context(self, query: str, scene: str = None,
                       limit: int = None, mode: str = "kv") -> dict:
        effective_scene = scene or self.default_scene
        effective_limit = limit or self.recall_limit
        start = time.time()
        try:
            result = self._memory.recall_context(
                query=query,
                scene=effective_scene,
                agent_id=self.agent_id,
                limit=effective_limit,
                mode=mode,
            )
            elapsed = (time.time() - start) * 1000
            self.metrics.recalls += 1
            self.metrics.total_recall_ms += elapsed
            return result
        except Exception as e:
            self.metrics.errors += 1
            logger.warning("[openmemo:%s] recall_context failed: %s", self.adapter_name, e)
            return {"context": []}

    def inject_context(self, prompt: str, query: str = None,
                       scene: str = None, limit: int = None) -> str:
        effective_query = query or prompt
        result = self.recall_context(effective_query, scene=scene, limit=limit)
        context = result.get("context", [])

        if not context:
            return prompt

        self.metrics.injections += 1

        memory_block = "Relevant memories:\n"
        for i, mem in enumerate(context, 1):
            memory_block += f"{i}. {mem}\n"

        injected = f"{memory_block}\n{prompt}"
        logger.info("[openmemo:%s] inject_context memories=%d",
                    self.adapter_name, len(context))
        return injected

    def get_context(self, query: str, scene: str = None,
                    limit: int = 3) -> List[str]:
        result = self.recall_context(query, scene=scene, limit=limit)
        return result.get("context", [])

    def list_scenes(self) -> List[str]:
        try:
            return self._memory.list_scenes(agent_id=self.agent_id)
        except Exception as e:
            logger.warning("[openmemo:%s] list_scenes failed: %s", self.adapter_name, e)
            return []

    def get_metrics(self) -> dict:
        return self.metrics.summary()

    def close(self):
        if hasattr(self._memory, 'close'):
            self._memory.close()
