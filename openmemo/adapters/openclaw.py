"""
OpenClaw Adapter for OpenMemo.

Provides a memory backend for OpenClaw agent sessions.
Hooks into agent lifecycle events (thought, action, observation).

Usage (local):
    from openmemo.adapters.openclaw import OpenClawMemoryBackend
    backend = OpenClawMemoryBackend(agent_id="claw_agent")

Usage (remote):
    from openmemo.adapters.openclaw import OpenClawMemoryBackend
    backend = OpenClawMemoryBackend(
        agent_id="claw_agent",
        base_url="https://api.openmemo.ai",
    )
"""

from typing import List, Dict
from openmemo.adapters.base_adapter import BaseMemoryAdapter


class OpenClawMemoryBackend(BaseMemoryAdapter):
    adapter_name = "openclaw"

    def search_memory(self, query: str, scene: str = "",
                      limit: int = 10) -> List[Dict]:
        return self.recall_memory(query=query, scene=scene, limit=limit)

    def memory_governance(self, operation: str = "cleanup") -> dict:
        try:
            return self._memory.memory_governance(operation=operation)
        except Exception:
            return {"error": "governance failed"}

    def write(self, content: str, scene: str = "", cell_type: str = "fact") -> str:
        return self.write_memory(content=content, scene=scene, memory_type=cell_type)

    def recall(self, query: str, scene: str = "", mode: str = "kv",
               limit: int = 10) -> dict:
        return self.recall_context(query=query, scene=scene, mode=mode, limit=limit)

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        return self.recall_memory(query=query, limit=limit)

    def on_thought(self, thought: str, scene: str = ""):
        pass

    def on_action(self, action: str, scene: str = ""):
        self.write_memory(content=action, scene=scene, memory_type="observation")

    def on_observation(self, observation: str, scene: str = ""):
        self.write_memory(content=observation, scene=scene, memory_type="observation")

    def on_task_complete(self, task: str, result: str, scene: str = ""):
        content = f"{task}: {result}" if result else task
        self.write_memory(content=content, scene=scene, memory_type="decision")
