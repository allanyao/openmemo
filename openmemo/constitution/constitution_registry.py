"""
Constitution Registry — multi-constitution manager with profile switching.

Manages named constitution profiles (default, engineering, research, creative, etc.).
Supports loading built-in profiles, custom profiles, and runtime switching.
"""

import json
import logging
import os
from typing import Dict, List, Optional

from openmemo.constitution.constitution_loader import ConstitutionConfig, load_constitution
from openmemo.constitution.constitution_runtime import ConstitutionRuntime

logger = logging.getLogger("openmemo")

PROFILES_DIR = os.path.join(os.path.dirname(__file__), "profiles")


class ConstitutionRegistry:
    def __init__(self):
        self._profiles: Dict[str, ConstitutionConfig] = {}
        self._active_name: str = "default"
        self._load_builtin_profiles()

    def _load_builtin_profiles(self):
        self._profiles["default"] = load_constitution()

        if os.path.isdir(PROFILES_DIR):
            for fname in os.listdir(PROFILES_DIR):
                if fname.endswith(".json"):
                    name = fname.replace(".json", "")
                    path = os.path.join(PROFILES_DIR, fname)
                    try:
                        self._profiles[name] = load_constitution(path)
                        logger.debug("[openmemo] loaded profile: %s", name)
                    except Exception as e:
                        logger.warning("[openmemo] failed to load profile %s: %s", name, e)

    def register(self, name: str, config: ConstitutionConfig):
        self._profiles[name] = config
        logger.info("[openmemo] registered constitution profile: %s", name)

    def register_from_dict(self, name: str, data: dict):
        config = ConstitutionConfig.from_dict(data)
        self.register(name, config)

    def register_from_file(self, name: str, path: str):
        config = load_constitution(path)
        self.register(name, config)

    def get(self, name: str) -> Optional[ConstitutionConfig]:
        return self._profiles.get(name)

    def get_runtime(self, name: str) -> Optional[ConstitutionRuntime]:
        config = self.get(name)
        if config:
            return ConstitutionRuntime(config)
        return None

    def switch(self, name: str) -> ConstitutionRuntime:
        if name not in self._profiles:
            raise ValueError(f"Unknown constitution profile: {name}. "
                             f"Available: {list(self._profiles.keys())}")
        self._active_name = name
        logger.info("[openmemo] switched constitution to: %s", name)
        return self.active_runtime()

    @property
    def active_name(self) -> str:
        return self._active_name

    def active_config(self) -> ConstitutionConfig:
        return self._profiles[self._active_name]

    def active_runtime(self) -> ConstitutionRuntime:
        return ConstitutionRuntime(self.active_config())

    def list_profiles(self) -> List[dict]:
        result = []
        for name, config in self._profiles.items():
            result.append({
                "name": name,
                "version": config.version,
                "active": name == self._active_name,
                "summary": config.summary(),
            })
        return result

    def profile_names(self) -> List[str]:
        return list(self._profiles.keys())

    def remove(self, name: str) -> bool:
        if name == "default":
            return False
        if name in self._profiles:
            del self._profiles[name]
            if self._active_name == name:
                self._active_name = "default"
            return True
        return False

    def export_profile(self, name: str) -> Optional[dict]:
        config = self.get(name)
        if config:
            return config.to_dict()
        return None

    def status(self) -> dict:
        return {
            "active": self._active_name,
            "total_profiles": len(self._profiles),
            "available": self.profile_names(),
        }
