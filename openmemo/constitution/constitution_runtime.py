"""
Constitution Runtime — executable policy layer.

Transforms static constitution config into runtime decision functions
used by write, recall, governance, and maintenance pipelines.
"""

import logging
from typing import List

from openmemo.constitution.constitution_loader import ConstitutionConfig, load_constitution

logger = logging.getLogger("openmemo")

NOISE_PATTERNS = [
    "hi", "hello", "hey", "ok", "okay", "sure", "thanks", "thank you",
    "bye", "goodbye", "yes", "no", "yeah", "nope", "yep", "hmm",
    "lol", "haha", "hehe", "wow", "cool", "nice", "great",
]


class ConstitutionRuntime:
    def __init__(self, config: ConstitutionConfig = None):
        self._config = config or load_constitution()

    @property
    def config(self) -> ConstitutionConfig:
        return self._config

    @property
    def version(self) -> str:
        return self._config.version

    def should_store(self, memory_type: str, content: str) -> bool:
        if not self._config.memory_philosophy.store_meaning_not_noise:
            return True

        stripped = content.strip().lower().rstrip("!?.,")
        if stripped in NOISE_PATTERNS:
            return False

        if len(content.strip()) < 5:
            return False

        if self._config.memory_philosophy.prefer_durable_knowledge:
            if memory_type == "conversation" and len(content.strip().split()) < 4:
                return False

        return True

    def get_priority(self, memory_type: str) -> int:
        order = self._config.priority_policy.order
        try:
            return len(order) - order.index(memory_type)
        except ValueError:
            return 0

    def get_priority_order(self) -> List[str]:
        return list(self._config.priority_policy.order)

    def should_prefer_scene_local(self) -> bool:
        return self._config.recall_policy.prefer_scene_local

    def should_prefer_recent_high_confidence(self) -> bool:
        return self._config.recall_policy.prefer_recent_high_confidence

    def allow_conflict_override(self, old_confidence: float,
                                 new_confidence: float) -> bool:
        if not self._config.conflict_policy.prefer_newer_memory:
            return False

        gap = new_confidence - old_confidence
        threshold = self._config.conflict_policy.min_confidence_gap_for_override

        if gap >= threshold:
            return True

        if gap >= 0 and gap < threshold:
            return False

        return False

    def allow_unresolved_conflict(self) -> bool:
        return self._config.conflict_policy.allow_unresolved_conflict

    def should_decay_fast(self, memory_type: str, confidence: float = 1.0,
                          access_count: int = 0) -> bool:
        if memory_type == "conversation":
            return self._config.retention_policy.decay_transient_conversation

        if self._config.retention_policy.decay_low_confidence_first and confidence < 0.4:
            return True

        if self._config.retention_policy.reinforced_memories_decay_slower and access_count >= 3:
            return False

        return False

    def get_decay_factor(self, memory_type: str, confidence: float = 1.0,
                         access_count: int = 0) -> float:
        if self.should_decay_fast(memory_type, confidence, access_count):
            return 0.7

        if self._config.retention_policy.reinforced_memories_decay_slower and access_count >= 3:
            return 0.98

        priority = self.get_priority(memory_type)
        if priority >= 5:
            return 0.95
        elif priority >= 3:
            return 0.9
        else:
            return 0.85

    def can_promote(self, occurrences: int, success_signals: int) -> bool:
        pp = self._config.promotion_policy

        if not pp.require_reinforcement:
            return True

        if occurrences < pp.minimum_occurrences:
            return False

        if success_signals < pp.minimum_success_signals:
            return False

        return True

    def can_promote_anecdote(self) -> bool:
        return self._config.promotion_policy.promote_one_off_anecdotes

    def summary(self) -> dict:
        return self._config.summary()

    def status(self) -> dict:
        return {
            "version": self.version,
            "philosophy": {
                "store_meaning_not_noise": self._config.memory_philosophy.store_meaning_not_noise,
                "prefer_durable": self._config.memory_philosophy.prefer_durable_knowledge,
            },
            "priority_order": self._config.priority_policy.order,
            "recall_scene_local": self._config.recall_policy.prefer_scene_local,
            "conflict_confidence_gap": self._config.conflict_policy.min_confidence_gap_for_override,
        }
