"""
LangChain Adapter for OpenMemo.

Provides OpenMemoMemory() that works as a LangChain
BaseMemory compatible memory backend.

Usage (local):
    from openmemo.adapters.langchain import OpenMemoMemory
    memory = OpenMemoMemory(agent_id="my_agent")

Usage (remote):
    from openmemo.adapters.langchain import OpenMemoMemory
    memory = OpenMemoMemory(
        agent_id="my_agent",
        base_url="https://api.openmemo.ai",
    )
"""

from typing import Any, Dict, List
from openmemo.adapters.base_adapter import BaseMemoryAdapter


class OpenMemoMemory(BaseMemoryAdapter):
    adapter_name = "langchain"

    def __init__(self, memory_key: str = "history", **kwargs):
        super().__init__(**kwargs)
        self.memory_key = memory_key

    @property
    def memory_variables(self) -> List[str]:
        return [self.memory_key]

    def load_memory_variables(self, inputs: Dict[str, Any]) -> Dict[str, str]:
        query = inputs.get("input", "")
        if not query:
            return {self.memory_key: ""}

        result = self.recall_context(query=query, limit=5)
        context = result.get("context", [])
        if not context:
            return {self.memory_key: ""}

        return {self.memory_key: "\n".join(context)}

    def save_context(self, inputs: Dict[str, Any], outputs: Dict[str, str]) -> None:
        user_input = inputs.get("input", "")
        ai_output = outputs.get("output", "")

        if user_input:
            self.write_memory(
                content=f"User: {user_input}",
                scene="conversation",
                memory_type="observation",
            )

        if ai_output:
            self.write_memory(
                content=f"Assistant: {ai_output}",
                scene="conversation",
                memory_type="observation",
            )

    def clear(self) -> None:
        pass
