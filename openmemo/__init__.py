"""
OpenMemo - The Memory Infrastructure for AI Agents

Provides structured, evolving, and long-term memory
for autonomous AI systems.
"""

from openmemo.api.sdk import Memory, MemoryClient, OpenMemo
from openmemo.api.remote import RemoteMemory
from openmemo.config import OpenMemoConfig
from openmemo.core.memcell import CellType

__version__ = "0.6.0"
__all__ = ["OpenMemo", "Memory", "MemoryClient", "RemoteMemory", "OpenMemoConfig", "CellType"]
