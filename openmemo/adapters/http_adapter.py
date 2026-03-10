"""
HTTP Adapter for OpenMemo.

Provides the simplest possible interface for any HTTP client.
Wraps the OpenMemo REST API with a Python client.

Usage:
    from openmemo.adapters.http_adapter import HTTPMemoryClient

    client = HTTPMemoryClient(base_url="http://localhost:8765")
    client.write_memory("User prefers Python")
    results = client.recall_memory("programming language")
    prompt = client.inject_context("What language should I use?")
"""

import json
import logging
import time
from typing import List, Dict
from urllib.request import Request, urlopen
from urllib.error import URLError

from openmemo.adapters.base_adapter import AdapterMetrics

logger = logging.getLogger("openmemo")


class HTTPMemoryClient:
    adapter_name = "http"

    def __init__(self, base_url: str = "http://localhost:8765",
                 agent_id: str = "", default_scene: str = "",
                 recall_limit: int = 5, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.agent_id = agent_id
        self.default_scene = default_scene
        self.recall_limit = recall_limit
        self.timeout = timeout
        self.metrics = AdapterMetrics()

    def _request(self, path: str, data: dict = None, method: str = "POST") -> dict:
        url = f"{self.base_url}{path}"
        if data:
            body = json.dumps(data).encode("utf-8")
            req = Request(url, data=body, method=method)
            req.add_header("Content-Type", "application/json")
        else:
            req = Request(url, method=method)

        try:
            with urlopen(req, timeout=self.timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except URLError as e:
            logger.warning("[openmemo:http] request failed: %s %s → %s", method, path, e)
            self.metrics.errors += 1
            return {}
        except Exception as e:
            logger.warning("[openmemo:http] unexpected error: %s", e)
            self.metrics.errors += 1
            return {}

    def write_memory(self, content: str, scene: str = None,
                     memory_type: str = "fact", confidence: float = 0.8,
                     metadata: dict = None) -> str:
        effective_scene = scene or self.default_scene
        start = time.time()
        result = self._request("/memory/write", {
            "content": content,
            "scene": effective_scene,
            "type": memory_type,
            "confidence": confidence,
            "agent_id": self.agent_id,
            "metadata": metadata or {},
        })
        elapsed = (time.time() - start) * 1000
        self.metrics.writes += 1
        self.metrics.total_write_ms += elapsed
        logger.info("[openmemo:http] write_memory scene=%s latency=%.0fms",
                    effective_scene, elapsed)
        return result.get("memory_id", "")

    def recall_memory(self, query: str, scene: str = None,
                      limit: int = None) -> List[Dict]:
        effective_scene = scene or self.default_scene
        effective_limit = limit or self.recall_limit
        start = time.time()
        result = self._request("/memory/search", {
            "query": query,
            "scene": effective_scene,
            "agent_id": self.agent_id,
            "limit": effective_limit,
        })
        elapsed = (time.time() - start) * 1000
        self.metrics.recalls += 1
        self.metrics.total_recall_ms += elapsed
        logger.info("[openmemo:http] recall_memory query=%s hits=%d latency=%.0fms",
                    query[:30], len(result.get("results", [])), elapsed)
        return result.get("results", [])

    def recall_context(self, query: str, scene: str = None,
                       limit: int = None, mode: str = "kv") -> dict:
        effective_scene = scene or self.default_scene
        effective_limit = limit or self.recall_limit
        start = time.time()
        result = self._request("/memory/recall", {
            "query": query,
            "scene": effective_scene,
            "agent_id": self.agent_id,
            "limit": effective_limit,
            "mode": mode,
        })
        elapsed = (time.time() - start) * 1000
        self.metrics.recalls += 1
        self.metrics.total_recall_ms += elapsed
        return result if result else {"context": []}

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

        return f"{memory_block}\n{prompt}"

    def get_context(self, query: str, scene: str = None,
                    limit: int = 3) -> List[str]:
        result = self.recall_context(query, scene=scene, limit=limit)
        return result.get("context", [])

    def list_scenes(self) -> List[str]:
        result = self._request("/memory/scenes", method="GET")
        return result.get("scenes", [])

    def get_metrics(self) -> dict:
        return self.metrics.summary()

    def close(self):
        pass
