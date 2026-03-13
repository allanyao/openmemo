"""
OpenMemo - The Memory Infrastructure for AI Agents

Provides structured, evolving, and long-term memory
for autonomous AI systems. Now with Constitution Layer
for cognitive governance.
"""

from openmemo.api.sdk import Memory, MemoryClient, OpenMemo
from openmemo.api.remote import RemoteMemory
from openmemo.config import OpenMemoConfig, HybridConfig
from openmemo.core.memcell import CellType
from openmemo.constitution import ConstitutionRuntime, ConstitutionConfig
from openmemo.core.consolidation import ConsolidationEngine, ConsolidationConfig as ConsolidationCfg
from openmemo.sync.memory_router import MemoryRouter
from openmemo.sync.sync_engine import SyncEngine, SyncConfig
from openmemo.skill.skill_engine import SkillEngine, Skill
from openmemo.team.team_router import route_scope, build_namespace, apply_scope_weights, get_scope_weight
from openmemo.team.promotion import PromotionWorker, PromotionConfig

__version__ = "0.11.1"
__all__ = [
    "OpenMemo", "Memory", "MemoryClient", "RemoteMemory",
    "OpenMemoConfig", "HybridConfig", "CellType",
    "ConstitutionRuntime", "ConstitutionConfig",
    "ConsolidationEngine", "ConsolidationCfg",
    "MemoryRouter", "SyncEngine", "SyncConfig",
    "SkillEngine", "Skill",
    "route_scope", "build_namespace", "apply_scope_weights", "get_scope_weight",
    "PromotionWorker", "PromotionConfig",
]
