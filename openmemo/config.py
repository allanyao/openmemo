"""
OpenMemo Configuration - Centralized configuration management.

All tunable parameters are managed through OpenMemoConfig.
This allows the engine behavior to be customized without
modifying source code.

Default values are intentionally generic baselines.
For production tuning, provide a custom config via
OpenMemoConfig.from_dict() or environment variables.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class RecallConfig:
    fast_brain_enabled: bool = True
    middle_brain_enabled: bool = True
    default_top_k: int = 10
    default_budget: int = 2000


@dataclass
class GovernanceConfig:
    conflict_detection_enabled: bool = True


@dataclass
class EvolutionConfig:
    mastery_min_access: int = 5
    mastery_min_importance: float = 0.6
    consolidation_min_access: int = 2
    dormant_days: int = 30
    default_importance: float = 0.5


@dataclass
class PyramidConfig:
    short_term_max: int = 50
    short_term_hours: int = 24
    batch_size: int = 5


@dataclass
class SkillConfig:
    pattern_threshold: int = 3
    auto_extract: bool = True


@dataclass
class OpenMemoConfig:
    recall: RecallConfig = field(default_factory=RecallConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    pyramid: PyramidConfig = field(default_factory=PyramidConfig)
    skill: SkillConfig = field(default_factory=SkillConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMemoConfig":
        config = cls()
        section_map = {
            "recall": config.recall,
            "governance": config.governance,
            "evolution": config.evolution,
            "pyramid": config.pyramid,
            "skill": config.skill,
        }
        for section_name, section_obj in section_map.items():
            if section_name in data:
                for k, v in data[section_name].items():
                    if hasattr(section_obj, k):
                        setattr(section_obj, k, v)
        return config
