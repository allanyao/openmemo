"""
OpenMemo - The Memory Infrastructure for AI Agents

Provides structured, evolving, and long-term memory
for autonomous AI systems. Now with Constitution Layer
for cognitive governance.
"""

from openmemo.api.sdk import Memory, MemoryClient, OpenMemo
from openmemo.api.remote import RemoteMemory
from openmemo.config import OpenMemoConfig
from openmemo.core.memcell import CellType
from openmemo.constitution import ConstitutionRuntime, ConstitutionConfig

__version__ = "0.7.0"
__all__ = [
    "OpenMemo", "Memory", "MemoryClient", "RemoteMemory",
    "OpenMemoConfig", "CellType",
    "ConstitutionRuntime", "ConstitutionConfig",
]
