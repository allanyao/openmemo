"""Tests for OpenMemo Constitution Layer."""
import json
import os
import tempfile
import pytest

from openmemo.constitution.constitution_loader import (
    ConstitutionConfig,
    load_constitution,
    DEFAULT_CONSTITUTION_PATH,
)
from openmemo.constitution.constitution_runtime import ConstitutionRuntime


class TestConstitutionConfig:
    def test_default_config(self):
        config = ConstitutionConfig()
        assert config.version == "1.0"
        assert config.memory_philosophy.store_meaning_not_noise is True
        assert config.priority_policy.order[0] == "decision"
        assert config.conflict_policy.min_confidence_gap_for_override == 0.15
        assert config.promotion_policy.minimum_occurrences == 2

    def test_from_dict(self):
        data = {
            "version": "2.0",
            "memory_philosophy": {"store_meaning_not_noise": False},
            "priority_policy": {"order": ["fact", "decision"]},
            "conflict_policy": {"min_confidence_gap_for_override": 0.3},
        }
        config = ConstitutionConfig.from_dict(data)
        assert config.version == "2.0"
        assert config.memory_philosophy.store_meaning_not_noise is False
        assert config.priority_policy.order == ["fact", "decision"]
        assert config.conflict_policy.min_confidence_gap_for_override == 0.3

    def test_to_dict(self):
        config = ConstitutionConfig()
        d = config.to_dict()
        assert d["version"] == "1.0"
        assert "memory_philosophy" in d
        assert "priority_policy" in d
        assert "recall_policy" in d
        assert "conflict_policy" in d
        assert "retention_policy" in d
        assert "promotion_policy" in d

    def test_summary(self):
        config = ConstitutionConfig()
        s = config.summary()
        assert "memory_priority" in s
        assert "recall_mode" in s
        assert "conflict_policy" in s
        assert s["recall_mode"] == "scene_aware"

    def test_roundtrip(self):
        config = ConstitutionConfig()
        d = config.to_dict()
        config2 = ConstitutionConfig.from_dict(d)
        assert config2.to_dict() == d


class TestLoadConstitution:
    def test_load_default(self):
        config = load_constitution()
        assert config.version == "1.0"
        assert len(config.priority_policy.order) == 6

    def test_load_from_file(self):
        data = {
            "version": "custom",
            "memory_philosophy": {"store_meaning_not_noise": True, "prefer_durable_knowledge": False, "prefer_structured_memory": True},
            "priority_policy": {"order": ["constraint", "fact"]},
            "recall_policy": {"prefer_scene_local": False, "prefer_recent_high_confidence": True, "prefer_coherent_sets": True, "default_mode": "kv"},
            "conflict_policy": {"prefer_newer_memory": True, "min_confidence_gap_for_override": 0.2, "allow_unresolved_conflict": True},
            "retention_policy": {"decay_transient_conversation": True, "decay_low_confidence_first": True, "reinforced_memories_decay_slower": True},
            "promotion_policy": {"require_reinforcement": True, "minimum_occurrences": 3, "minimum_success_signals": 2, "promote_one_off_anecdotes": False},
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            path = f.name
        try:
            config = load_constitution(path)
            assert config.version == "custom"
            assert config.priority_policy.order == ["constraint", "fact"]
            assert config.promotion_policy.minimum_occurrences == 3
        finally:
            os.unlink(path)

    def test_load_missing_file(self):
        config = load_constitution("/nonexistent/path.json")
        assert config.version == "1.0"

    def test_load_invalid_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not valid json {{{")
            path = f.name
        try:
            config = load_constitution(path)
            assert config.version == "1.0"
        finally:
            os.unlink(path)

    def test_default_file_exists(self):
        assert os.path.exists(DEFAULT_CONSTITUTION_PATH)


class TestConstitutionRuntime:
    @pytest.fixture
    def runtime(self):
        return ConstitutionRuntime()

    def test_should_store_meaningful(self, runtime):
        assert runtime.should_store("fact", "User prefers Python for backend development") is True

    def test_should_not_store_noise(self, runtime):
        assert runtime.should_store("conversation", "hi") is False
        assert runtime.should_store("conversation", "ok") is False
        assert runtime.should_store("conversation", "thanks") is False

    def test_should_not_store_short(self, runtime):
        assert runtime.should_store("fact", "hi") is False
        assert runtime.should_store("fact", "ok") is False

    def test_should_not_store_short_conversation(self, runtime):
        assert runtime.should_store("conversation", "yes it is") is False

    def test_should_store_decision(self, runtime):
        assert runtime.should_store("decision", "Use PostgreSQL for the database") is True

    def test_get_priority(self, runtime):
        assert runtime.get_priority("decision") > runtime.get_priority("observation")
        assert runtime.get_priority("constraint") > runtime.get_priority("preference")
        assert runtime.get_priority("unknown_type") == 0

    def test_get_priority_order(self, runtime):
        order = runtime.get_priority_order()
        assert order[0] == "decision"
        assert len(order) == 6

    def test_should_prefer_scene_local(self, runtime):
        assert runtime.should_prefer_scene_local() is True

    def test_allow_conflict_override_high_confidence(self, runtime):
        assert runtime.allow_conflict_override(0.5, 0.8) is True

    def test_allow_conflict_override_low_confidence(self, runtime):
        assert runtime.allow_conflict_override(0.9, 0.5) is False

    def test_allow_conflict_override_close(self, runtime):
        assert runtime.allow_conflict_override(0.7, 0.6) is True

    def test_allow_conflict_override_much_lower(self, runtime):
        assert runtime.allow_conflict_override(0.9, 0.3) is False

    def test_allow_conflict_override_equal(self, runtime):
        assert runtime.allow_conflict_override(0.7, 0.7) is True

    def test_allow_unresolved_conflict(self, runtime):
        assert runtime.allow_unresolved_conflict() is True

    def test_should_decay_fast_conversation(self, runtime):
        assert runtime.should_decay_fast("conversation") is True

    def test_should_decay_fast_low_confidence(self, runtime):
        assert runtime.should_decay_fast("observation", confidence=0.2) is True

    def test_should_not_decay_fast_reinforced(self, runtime):
        assert runtime.should_decay_fast("fact", confidence=0.8, access_count=5) is False

    def test_should_not_decay_fast_normal(self, runtime):
        assert runtime.should_decay_fast("decision") is False

    def test_get_decay_factor_conversation(self, runtime):
        assert runtime.get_decay_factor("conversation") == 0.7

    def test_get_decay_factor_reinforced(self, runtime):
        assert runtime.get_decay_factor("fact", access_count=5) == 0.98

    def test_get_decay_factor_high_priority(self, runtime):
        factor = runtime.get_decay_factor("decision")
        assert factor >= 0.9

    def test_can_promote(self, runtime):
        assert runtime.can_promote(occurrences=3, success_signals=2) is True
        assert runtime.can_promote(occurrences=1, success_signals=0) is False
        assert runtime.can_promote(occurrences=2, success_signals=0) is False
        assert runtime.can_promote(occurrences=2, success_signals=1) is True

    def test_can_promote_anecdote(self, runtime):
        assert runtime.can_promote_anecdote() is False

    def test_summary(self, runtime):
        s = runtime.summary()
        assert "memory_priority" in s
        assert "recall_mode" in s

    def test_status(self, runtime):
        st = runtime.status()
        assert st["version"] == "1.0"
        assert "priority_order" in st

    def test_disabled_philosophy(self):
        config = ConstitutionConfig()
        config.memory_philosophy.store_meaning_not_noise = False
        rt = ConstitutionRuntime(config)
        assert rt.should_store("conversation", "hi") is True

    def test_disabled_conflict_override(self):
        config = ConstitutionConfig()
        config.conflict_policy.prefer_newer_memory = False
        rt = ConstitutionRuntime(config)
        assert rt.allow_conflict_override(0.3, 0.9) is False


class TestConstitutionIntegration:
    def test_sdk_has_constitution(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        assert memo.constitution is not None
        assert memo.constitution.version == "1.0"

    def test_sdk_constitution_disabled(self):
        from openmemo import OpenMemo, OpenMemoConfig
        config = OpenMemoConfig()
        config.constitution.enabled = False
        memo = OpenMemo(db_path=":memory:", config=config)
        assert memo.constitution is None

    def test_write_filters_noise(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        result = memo.write_memory("hi", memory_type="conversation")
        assert result == ""

    def test_write_accepts_meaningful(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        result = memo.write_memory("Use PostgreSQL for the user database", memory_type="decision")
        assert result != ""

    def test_priority_boosts_importance(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        memo.write_memory("Use PostgreSQL", memory_type="decision", confidence=0.8)
        memo.write_memory("The sky is blue", memory_type="observation", confidence=0.8)
        cells = memo.store.list_cells(limit=10)
        decision_cell = next((c for c in cells if c.get("cell_type") == "decision"), None)
        observation_cell = next((c for c in cells if c.get("cell_type") == "observation"), None)
        if decision_cell and observation_cell:
            assert decision_cell["importance"] >= observation_cell["importance"]

    def test_recall_with_constitution(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        memo.write_memory("Python is fast for prototyping", memory_type="fact")
        memo.write_memory("Use React for frontend", memory_type="decision")
        result = memo.recall_context("programming language", limit=5)
        assert "context" in result
        assert isinstance(result["context"], list)

    def test_constitution_summary_api(self):
        from openmemo import OpenMemo
        memo = OpenMemo(db_path=":memory:")
        summary = memo.constitution.summary()
        assert summary["recall_mode"] == "scene_aware"
        assert "memory_priority" in summary
        assert "conflict_policy" in summary
