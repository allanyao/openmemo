import pytest
import os
import tempfile
from openmemo import Memory, MemoryClient, OpenMemo


@pytest.fixture
def memory():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    m = Memory(db_path=path)
    yield m
    m.close()
    os.remove(path)


class TestCoreAPI:
    """Tests for the 5 core Memory APIs defined in the specification."""

    def test_write_memory(self, memory):
        note_id = memory.write_memory("User prefers dark mode", scene="prefs", memory_type="preference")
        assert note_id is not None
        assert len(note_id) > 0

    def test_write_memory_with_confidence(self, memory):
        note_id = memory.write_memory("High confidence fact", confidence=0.95)
        assert note_id is not None

    def test_write_memory_with_all_params(self, memory):
        note_id = memory.write_memory(
            content="Complete test",
            scene="testing",
            memory_type="fact",
            confidence=0.9,
            agent_id="agent_1",
            metadata={"source": "test"},
        )
        assert note_id is not None

    def test_search_memory(self, memory):
        memory.write_memory("Python is great for ML", scene="coding")
        memory.write_memory("JavaScript for web", scene="coding")
        results = memory.search_memory("Python", scene="coding")
        assert isinstance(results, list)
        if results:
            assert "content" in results[0]
            assert "score" in results[0]
            assert "cell_id" in results[0]

    def test_search_memory_with_limit(self, memory):
        for i in range(5):
            memory.write_memory(f"Item {i} about testing", scene="test")
        results = memory.search_memory("testing", limit=2)
        assert len(results) <= 2

    def test_recall_context_kv(self, memory):
        memory.write_memory("User prefers dark mode", scene="prefs")
        memory.write_memory("Project uses Python 3.11", scene="project")
        result = memory.recall_context("dark mode", mode="kv")
        assert "context" in result
        assert isinstance(result["context"], list)
        assert any("dark mode" in c for c in result["context"])

    def test_recall_context_narrative(self, memory):
        memory.write_memory("Python is great", scene="coding")
        memory.write_memory("JavaScript is popular", scene="coding")
        result = memory.recall_context("programming languages", mode="narrative")
        assert "memory_story" in result
        assert "sources" in result
        assert "confidence" in result
        assert isinstance(result["memory_story"], str)

    def test_recall_context_raw(self, memory):
        memory.write_memory("Raw test content", scene="test")
        result = memory.recall_context("raw test", mode="raw")
        assert "context" in result
        assert isinstance(result["context"], list)
        if result["context"]:
            assert "content" in result["context"][0]
            assert "score" in result["context"][0]

    def test_recall_context_default_is_kv(self, memory):
        memory.write_memory("test content")
        result = memory.recall_context("test")
        assert "context" in result

    def test_recall_context_with_scene_filter(self, memory):
        memory.write_memory("coding preference", scene="coding", agent_id="a1")
        memory.write_memory("food preference", scene="personal", agent_id="a1")
        result = memory.recall_context("preference", scene="coding", agent_id="a1")
        assert "context" in result

    def test_list_scenes(self, memory):
        memory.write_memory("item 1", scene="work", agent_id="a1")
        memory.write_memory("item 2", scene="personal", agent_id="a1")
        scenes = memory.list_scenes(agent_id="a1")
        assert isinstance(scenes, list)
        assert len(scenes) == 2
        assert "work" in scenes
        assert "personal" in scenes

    def test_memory_governance_cleanup(self, memory):
        for i in range(5):
            memory.write_memory(f"Memory entry {i}")
        result = memory.memory_governance("cleanup")
        assert result["operation"] == "cleanup"
        assert "total_cells" in result

    def test_memory_governance_dedupe(self, memory):
        memory.write_memory("duplicate content")
        memory.write_memory("duplicate content")
        memory.write_memory("unique content")
        result = memory.memory_governance("dedupe")
        assert result["operation"] == "dedupe"
        assert result["duplicates_removed"] >= 1

    def test_memory_governance_decay(self, memory):
        memory.write_memory("old memory")
        result = memory.memory_governance("decay")
        assert result["operation"] == "decay"
        assert "decayed_cells" in result

    def test_memory_governance_merge(self, memory):
        for i in range(5):
            memory.write_memory(f"Merge test {i}")
        result = memory.memory_governance("merge")
        assert result["operation"] == "merge"


class TestAliases:
    """Tests for backward-compatible aliases."""

    def test_openmemo_alias(self):
        assert OpenMemo is Memory

    def test_memory_client_alias(self):
        assert MemoryClient is Memory

    def test_write_alias(self, memory):
        note_id = memory.write("test via write alias")
        assert note_id is not None

    def test_add_alias(self, memory):
        note_id = memory.add("test via add alias")
        assert note_id is not None

    def test_recall_alias(self, memory):
        memory.write_memory("recall alias test")
        result = memory.recall("recall alias")
        assert "context" in result

    def test_search_alias(self, memory):
        memory.write_memory("search alias test")
        results = memory.search("search alias")
        assert isinstance(results, list)

    def test_context_alias(self, memory):
        memory.write_memory("context alias test", scene="test")
        context = memory.context("context alias")
        assert isinstance(context, list)
        assert all(isinstance(c, str) for c in context)

    def test_scenes_alias(self, memory):
        memory.write_memory("scenes alias test", scene="demo")
        scenes = memory.scenes()
        assert "demo" in scenes

    def test_maintain_alias(self, memory):
        memory.write_memory("maintain test")
        result = memory.maintain()
        assert "operation" in result


class TestMemoryOperations:
    """Tests for additional memory operations."""

    def test_delete(self, memory):
        memory.write_memory("to be deleted")
        cells = memory.store.list_cells()
        cell_id = cells[0]["id"]
        deleted = memory.delete(cell_id)
        assert deleted is True

    def test_stats(self, memory):
        memory.write_memory("First meaningful memory entry")
        memory.write_memory("Second meaningful memory entry")
        stats = memory.stats()
        assert stats["notes"] == 2
        assert stats["cells"] == 2
        assert "stages" in stats

    def test_reconstruct(self, memory):
        memory.write_memory("Python is great")
        result = memory.reconstruct("programming")
        assert "query" in result
        assert "narrative" in result

    def test_scenes_detail(self, memory):
        memory.write_memory("detail test", scene="work", agent_id="a1")
        scenes = memory.scenes_detail(agent_id="a1")
        assert isinstance(scenes, list)
        assert len(scenes) == 1
        assert "title" in scenes[0]

    def test_context_manager(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        with Memory(db_path=path) as m:
            m.write_memory("context manager test")
            stats = m.stats()
            assert stats["notes"] == 1
        os.remove(path)

    def test_conflict_detection(self, memory):
        memory.write_memory("User prefers dark mode")
        memory.write_memory("User dislikes dark mode")
        stats = memory.stats()
        all_conflicts = memory.conflict_detector._conflicts
        assert len(all_conflicts) >= 1

    def test_with_vector_store(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        def simple_embed(text):
            words = text.lower().split()
            return [1.0 if "python" in words else 0.0,
                    1.0 if "java" in words else 0.0,
                    1.0 if "rust" in words else 0.0]

        m = Memory(db_path=path, embed_fn=simple_embed)
        m.write_memory("Python is great")
        m.write_memory("Java is popular")
        result = m.recall_context("Python programming")
        assert len(result["context"]) > 0
        m.close()
        os.remove(path)

    def test_agent_id_isolation(self, memory):
        memory.write_memory("fact for agent A", agent_id="agent_a")
        memory.write_memory("fact for agent B", agent_id="agent_b")
        result = memory.recall_context("fact", agent_id="agent_a")
        assert len(result["context"]) >= 1

    def test_memory_types(self, memory):
        memory.write_memory("user prefers Python", memory_type="preference")
        memory.write_memory("must use HTTPS", memory_type="constraint")
        memory.write_memory("chose Flask over Django", memory_type="decision")
        stats = memory.stats()
        assert stats["cells"] == 3
