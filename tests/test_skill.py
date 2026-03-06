import pytest
from openmemo.skill.skill_engine import SkillEngine, Skill
from openmemo.skill.skill_extractor import SkillExtractor


class TestSkillEngine:
    def test_observe_and_extract(self):
        engine = SkillEngine()
        for _ in range(5):
            engine.observe("search database", success=True)
        skills = engine.extract_skills()
        assert len(skills) >= 1
        assert skills[0].usage_count == 5

    def test_below_threshold(self):
        engine = SkillEngine()
        engine.observe("rare action")
        skills = engine.extract_skills()
        assert len(skills) == 0

    def test_success_rate(self):
        engine = SkillEngine()
        for _ in range(3):
            engine.observe("test action", success=True)
        engine.observe("test action", success=False)
        skills = engine.extract_skills()
        assert len(skills) == 1
        assert skills[0].success_rate == 0.75


class TestSkill:
    def test_record_usage(self):
        skill = Skill(name="test")
        skill.record_usage(True)
        skill.record_usage(False)
        assert skill.usage_count == 2
        assert skill.success_rate == 0.5


class TestSkillExtractor:
    def test_extract_patterns(self):
        extractor = SkillExtractor(min_frequency=2)
        cells = [
            {"content": "search database query"},
            {"content": "search database records"},
            {"content": "search database tables"},
        ]
        patterns = extractor.extract_patterns(cells)
        assert len(patterns) >= 1
        assert any(p["pattern"] == "search database" for p in patterns)
