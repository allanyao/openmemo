"""
OpenMemo Remote Client — HTTP-based Memory API.

Connects to a remote OpenMemo server (e.g., api.openmemo.ai)
instead of using a local database.

Usage:
    from openmemo import RemoteMemory

    mem = RemoteMemory(base_url="https://api.openmemo.ai")
    mem.write("User prefers Python", agent_id="agent_1")
    result = mem.recall("language preference", agent_id="agent_1")
    print(result)

Install with:
    pip install openmemo[remote]
"""

from typing import List

try:
    import requests
except ImportError:
    requests = None

DEFAULT_BASE_URL = "https://api.openmemo.ai"


class RemoteMemory:
    """
    HTTP client for OpenMemo REST API.

    Provides the same interface as Memory (local SDK) but
    calls a remote server over HTTP.

    Args:
        base_url: Server URL. Default: https://api.openmemo.ai
        api_key: Optional API key for authentication (future use).
        timeout: Request timeout in seconds. Default: 30.
    """

    def __init__(self, base_url: str = None, api_key: str = None,
                 timeout: int = 30):
        if requests is None:
            raise ImportError(
                "Install remote dependencies: pip install openmemo[remote]"
            )
        self.base_url = (base_url or DEFAULT_BASE_URL).rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers["Content-Type"] = "application/json"
        if api_key:
            self._session.headers["Authorization"] = f"Bearer {api_key}"

    def _post(self, path: str, data: dict) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.post(url, json=data, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict = None) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.get(url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _delete(self, path: str) -> dict:
        url = f"{self.base_url}{path}"
        resp = self._session.delete(url, timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def write(self, content: str, agent_id: str = "", scene: str = "",
              cell_type: str = "fact", source: str = "api",
              metadata: dict = None) -> str:
        data = {
            "content": content,
            "agent_id": agent_id,
            "scene": scene,
            "cell_type": cell_type,
            "source": source,
        }
        if metadata:
            data["metadata"] = metadata
        result = self._post("/memory/write", data)
        return result.get("memory_id", "")

    def add(self, content: str, source: str = "api", agent_id: str = "",
            scene: str = "", cell_type: str = "fact",
            metadata: dict = None) -> str:
        return self.write(
            content=content, agent_id=agent_id, scene=scene,
            cell_type=cell_type, source=source, metadata=metadata,
        )

    def recall(self, query: str, agent_id: str = "", scene: str = "",
               mode: str = "kv", top_k: int = None, limit: int = None,
               budget: int = 2000) -> dict:
        data = {
            "query": query,
            "agent_id": agent_id,
            "mode": mode,
            "budget": budget,
        }
        if scene:
            data["scene"] = scene
        if limit:
            data["limit"] = limit
        elif top_k:
            data["top_k"] = top_k
        return self._post("/memory/recall", data)

    def context(self, query: str, agent_id: str = "", scene: str = "",
                limit: int = 3) -> List[str]:
        data = {
            "query": query,
            "agent_id": agent_id,
            "limit": limit,
        }
        if scene:
            data["scene"] = scene
        result = self._post("/agent/context", data)
        return result.get("memory_context", [])

    def search(self, query: str, agent_id: str = "",
               top_k: int = None, limit: int = None) -> List[dict]:
        data = {
            "query": query,
            "agent_id": agent_id,
        }
        if limit:
            data["limit"] = limit
        elif top_k:
            data["top_k"] = top_k
        result = self._post("/memory/search", data)
        return result.get("results", [])

    def scenes(self, agent_id: str = "") -> List[str]:
        params = {}
        if agent_id:
            params["agent_id"] = agent_id
        result = self._get("/memory/scenes", params=params)
        return result.get("scenes", [])

    def delete(self, memory_id: str) -> bool:
        try:
            self._delete(f"/memory/{memory_id}")
            return True
        except Exception:
            return False

    def reconstruct(self, query: str, agent_id: str = "",
                    max_sources: int = 10) -> dict:
        data = {
            "query": query,
            "agent_id": agent_id,
            "max_sources": max_sources,
        }
        return self._post("/memory/reconstruct", data)

    def health(self) -> dict:
        return self._get("/health")

    def stats(self) -> dict:
        return self._get("/api/stats")

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
