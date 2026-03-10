"""
OpenMemo Adapters — Universal Agent Memory Integration Layer.

Provides adapters for all major agent frameworks:
- OpenClaw: OpenClawMemoryBackend
- LangChain: OpenMemoMemory
- CrewAI: CrewAIMemory
- MCP (Claude): OpenMemoMCPServer
- HTTP: HTTPMemoryClient
"""

from openmemo.adapters.base_adapter import BaseMemoryAdapter
from openmemo.adapters.openclaw import OpenClawMemoryBackend
from openmemo.adapters.langchain import OpenMemoMemory
from openmemo.adapters.crewai_adapter import CrewAIMemory
from openmemo.adapters.mcp import OpenMemoMCPServer
from openmemo.adapters.http_adapter import HTTPMemoryClient

__all__ = [
    "BaseMemoryAdapter",
    "OpenClawMemoryBackend",
    "OpenMemoMemory",
    "CrewAIMemory",
    "OpenMemoMCPServer",
    "HTTPMemoryClient",
]
