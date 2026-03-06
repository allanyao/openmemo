"""
Skill Engine - Experience to skill extraction.

Detects repeated patterns in agent behavior and extracts
them into reusable skills that improve over time.
"""

import uuid
import time
from typing import List, Optional
from dataclasses import dataclass, field


@dataclass
class Skill:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    pattern: str = ""
    usage_count: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def record_usage(self, success: bool):
        self.usage_count += 1
        total_success = self.success_rate * (self.usage_count - 1) + (1.0 if success else 0.0)
        self.success_rate = total_success / self.usage_count

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "pattern": self.pattern,
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class SkillEngine:
    PATTERN_THRESHOLD = 3

    def __init__(self, store=None):
        self.store = store
        self._pattern_counts = {}

    def observe(self, action: str, context: str = "", success: bool = True):
        key = self._normalize(action)
        if key not in self._pattern_counts:
            self._pattern_counts[key] = {"count": 0, "successes": 0, "context": context}

        self._pattern_counts[key]["count"] += 1
        if success:
            self._pattern_counts[key]["successes"] += 1

    def extract_skills(self) -> List[Skill]:
        new_skills = []

        for pattern, data in self._pattern_counts.items():
            if data["count"] >= self.PATTERN_THRESHOLD:
                skill = Skill(
                    name=pattern,
                    description=f"Learned from {data['count']} observations",
                    pattern=pattern,
                    usage_count=data["count"],
                    success_rate=data["successes"] / data["count"] if data["count"] > 0 else 0,
                )
                new_skills.append(skill)

                if self.store:
                    self.store.put_skill(skill.to_dict())

        return new_skills

    def get_relevant_skills(self, context: str, top_k: int = 5) -> List[Skill]:
        if not self.store:
            return []

        all_skills = self.store.list_skills()
        context_lower = context.lower()

        scored = []
        for s in all_skills:
            relevance = 0.0
            if s.get("pattern", "").lower() in context_lower:
                relevance = 1.0
            elif any(w in context_lower for w in s.get("name", "").lower().split()):
                relevance = 0.5

            if relevance > 0:
                scored.append((Skill(**{k: v for k, v in s.items() if k in Skill.__dataclass_fields__}), relevance))

        scored.sort(key=lambda x: x[1] * x[0].success_rate, reverse=True)
        return [s for s, _ in scored[:top_k]]

    def _normalize(self, action: str) -> str:
        return action.strip().lower()
