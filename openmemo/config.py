"""
OpenMemo Configuration - Centralized configuration management.

Public configuration exposes only high-level behavioral switches.
Internal tuning parameters are encapsulated within engine
implementations and not exposed through this interface.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional


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
class PyramidConfig:
    enabled: bool = True


@dataclass
class SkillConfig:
    auto_extract: bool = True


@dataclass
class EvolutionConfig:
    enabled: bool = True


@dataclass
class ConstitutionConfigRef:
    enabled: bool = True
    path: Optional[str] = None


@dataclass
class OpenMemoConfig:
    recall: RecallConfig = field(default_factory=RecallConfig)
    governance: GovernanceConfig = field(default_factory=GovernanceConfig)
    evolution: EvolutionConfig = field(default_factory=EvolutionConfig)
    pyramid: PyramidConfig = field(default_factory=PyramidConfig)
    skill: SkillConfig = field(default_factory=SkillConfig)
    constitution: ConstitutionConfigRef = field(default_factory=ConstitutionConfigRef)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenMemoConfig":
        config = cls()
        section_map = {
            "recall": config.recall,
            "governance": config.governance,
            "evolution": config.evolution,
            "pyramid": config.pyramid,
            "skill": config.skill,
            "constitution": config.constitution,
        }
        for section_name, section_obj in section_map.items():
            if section_name in data:
                for k, v in data[section_name].items():
                    if hasattr(section_obj, k):
                        setattr(section_obj, k, v)
        return config
