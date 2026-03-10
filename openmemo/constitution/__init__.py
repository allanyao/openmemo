"""
OpenMemo Constitution Layer — Cognitive Constitution for Memory Systems.

The Constitution Layer defines how OpenMemo stores, ranks, reconciles,
and evolves memory. It is the policy layer that governs memory behavior.
"""

from openmemo.constitution.constitution_loader import load_constitution, ConstitutionConfig
from openmemo.constitution.constitution_runtime import ConstitutionRuntime
from openmemo.constitution.constitution_registry import ConstitutionRegistry

__all__ = [
    "load_constitution",
    "ConstitutionConfig",
    "ConstitutionRuntime",
    "ConstitutionRegistry",
]
