"""
Constitution Loader — loads and validates constitution configuration.

Loads from:
1. Custom path (user-provided JSON file)
2. Default constitution.json (bundled with package)
"""

import json
import logging
import os
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("openmemo")

DEFAULT_CONSTITUTION_PATH = os.path.join(
    os.path.dirname(__file__), "constitution.json"
)


@dataclass
class MemoryPhilosophy:
    store_meaning_not_noise: bool = True
    prefer_durable_knowledge: bool = True
    prefer_structured_memory: bool = True


@dataclass
class PriorityPolicy:
    order: list = field(default_factory=lambda: [
        "decision", "constraint", "fact",
        "preference", "observation", "conversation",
    ])


@dataclass
class RecallPolicy:
    prefer_scene_local: bool = True
    prefer_recent_high_confidence: bool = True
    prefer_coherent_sets: bool = True
    default_mode: str = "kv"


@dataclass
class ConflictPolicy:
    prefer_newer_memory: bool = True
    min_confidence_gap_for_override: float = 0.15
    allow_unresolved_conflict: bool = True


@dataclass
class RetentionPolicy:
    decay_transient_conversation: bool = True
    decay_low_confidence_first: bool = True
    reinforced_memories_decay_slower: bool = True


@dataclass
class PromotionPolicy:
    require_reinforcement: bool = True
    minimum_occurrences: int = 2
    minimum_success_signals: int = 1
    promote_one_off_anecdotes: bool = False


@dataclass
class ConstitutionConfig:
    version: str = "1.0"
    memory_philosophy: MemoryPhilosophy = field(default_factory=MemoryPhilosophy)
    priority_policy: PriorityPolicy = field(default_factory=PriorityPolicy)
    recall_policy: RecallPolicy = field(default_factory=RecallPolicy)
    conflict_policy: ConflictPolicy = field(default_factory=ConflictPolicy)
    retention_policy: RetentionPolicy = field(default_factory=RetentionPolicy)
    promotion_policy: PromotionPolicy = field(default_factory=PromotionPolicy)

    @classmethod
    def from_dict(cls, data: dict) -> "ConstitutionConfig":
        config = cls()
        config.version = data.get("version", "1.0")

        if "memory_philosophy" in data:
            for k, v in data["memory_philosophy"].items():
                if hasattr(config.memory_philosophy, k):
                    setattr(config.memory_philosophy, k, v)

        if "priority_policy" in data:
            pp = data["priority_policy"]
            if "order" in pp:
                config.priority_policy.order = pp["order"]

        section_map = {
            "recall_policy": config.recall_policy,
            "conflict_policy": config.conflict_policy,
            "retention_policy": config.retention_policy,
            "promotion_policy": config.promotion_policy,
        }
        for section_name, section_obj in section_map.items():
            if section_name in data:
                for k, v in data[section_name].items():
                    if hasattr(section_obj, k):
                        setattr(section_obj, k, v)

        return config

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "memory_philosophy": {
                "store_meaning_not_noise": self.memory_philosophy.store_meaning_not_noise,
                "prefer_durable_knowledge": self.memory_philosophy.prefer_durable_knowledge,
                "prefer_structured_memory": self.memory_philosophy.prefer_structured_memory,
            },
            "priority_policy": {
                "order": self.priority_policy.order,
            },
            "recall_policy": {
                "prefer_scene_local": self.recall_policy.prefer_scene_local,
                "prefer_recent_high_confidence": self.recall_policy.prefer_recent_high_confidence,
                "prefer_coherent_sets": self.recall_policy.prefer_coherent_sets,
                "default_mode": self.recall_policy.default_mode,
            },
            "conflict_policy": {
                "prefer_newer_memory": self.conflict_policy.prefer_newer_memory,
                "min_confidence_gap_for_override": self.conflict_policy.min_confidence_gap_for_override,
                "allow_unresolved_conflict": self.conflict_policy.allow_unresolved_conflict,
            },
            "retention_policy": {
                "decay_transient_conversation": self.retention_policy.decay_transient_conversation,
                "decay_low_confidence_first": self.retention_policy.decay_low_confidence_first,
                "reinforced_memories_decay_slower": self.retention_policy.reinforced_memories_decay_slower,
            },
            "promotion_policy": {
                "require_reinforcement": self.promotion_policy.require_reinforcement,
                "minimum_occurrences": self.promotion_policy.minimum_occurrences,
                "minimum_success_signals": self.promotion_policy.minimum_success_signals,
                "promote_one_off_anecdotes": self.promotion_policy.promote_one_off_anecdotes,
            },
        }

    def summary(self) -> dict:
        return {
            "memory_priority": self.priority_policy.order[:4],
            "recall_mode": "scene_aware" if self.recall_policy.prefer_scene_local else "global",
            "conflict_policy": "newer_with_confidence_threshold" if self.conflict_policy.prefer_newer_memory else "manual",
        }


def load_constitution(path: Optional[str] = None) -> ConstitutionConfig:
    target = path or DEFAULT_CONSTITUTION_PATH

    try:
        with open(target, "r", encoding="utf-8") as f:
            data = json.load(f)
        config = ConstitutionConfig.from_dict(data)
        logger.info("[openmemo] constitution loaded (version=%s, source=%s)",
                    config.version, target)
        return config
    except FileNotFoundError:
        logger.warning("[openmemo] constitution file not found: %s, using defaults", target)
        return ConstitutionConfig()
    except json.JSONDecodeError as e:
        logger.warning("[openmemo] invalid constitution JSON: %s, using defaults", e)
        return ConstitutionConfig()
    except Exception as e:
        logger.warning("[openmemo] failed to load constitution: %s, using defaults", e)
        return ConstitutionConfig()
