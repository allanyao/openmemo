import pytest
import os
import tempfile
from openmemo.core.recall import RecallEngine, RecallResult
from openmemo.storage.sqlite_store import SQLiteStore
from openmemo.storage.vector_store import VectorStore


@pytest.fixture
def store_with_data():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    s = SQLiteStore(db_path=path)

    cells = [
        ("c1", "Python is great for data science and machine learning"),
        ("c2", "JavaScript dominates web development and frontend"),
        ("c3", "Rust provides memory safety without garbage collection"),
        ("c4", "PostgreSQL is a powerful relational database"),
        ("c5", "Docker containers simplify deployment and operations"),
    ]
    for cid, content in cells:
        s.put_cell({
            "id": cid, "note_id": "", "content": content,
            "facts": [], "stage": "exploration", "importance": 0.5,
            "access_count": 0, "last_accessed": 1.0, "created_at": 1.0,
            "connections": [], "metadata": {}
        })

    yield s
    s.close()
    os.remove(path)


class TestRecallEngine:
    def test_fast_brain_returns_results(self, store_with_data):
        engine = RecallEngine(store=store_with_data)
        results = engine.recall("Python data science")
        assert len(results) > 0
        assert results[0].content.startswith("Python")

    def test_fast_brain_empty_query(self, store_with_data):
        engine = RecallEngine(store=store_with_data)
        results = engine.recall("the is a")
        assert len(results) == 0

    def test_budget_control(self, store_with_data):
        engine = RecallEngine(store=store_with_data)
        results = engine.recall("Python JavaScript Rust Docker database", budget=10)
        total_words = sum(len(r.content.split()) for r in results)
        assert total_words <= 10

    def test_top_k_limit(self, store_with_data):
        engine = RecallEngine(store=store_with_data)
        results = engine.recall("Python JavaScript Rust", top_k=2)
        assert len(results) <= 2

    def test_no_store(self):
        engine = RecallEngine()
        results = engine.recall("anything")
        assert results == []


class TestVectorStore:
    def test_add_and_search(self):
        vs = VectorStore()
        vs.add("item1", [1.0, 0.0, 0.0], "content 1")
        vs.add("item2", [0.0, 1.0, 0.0], "content 2")
        vs.add("item3", [0.7, 0.7, 0.0], "content 3")

        results = vs.search([1.0, 0.0, 0.0], top_k=2)
        assert len(results) == 2
        assert results[0]["id"] == "item1"
        assert results[0]["score"] > 0.9

    def test_empty_search(self):
        vs = VectorStore()
        results = vs.search([1.0, 0.0], top_k=5)
        assert results == []

    def test_remove(self):
        vs = VectorStore()
        vs.add("item1", [1.0, 0.0], "c1")
        vs.remove("item1")
        assert vs.count() == 0

    def test_count(self):
        vs = VectorStore()
        vs.add("a", [1.0], "x")
        vs.add("b", [0.0], "y")
        assert vs.count() == 2


class TestRecallWithVectorStore:
    def test_middle_brain_integration(self, store_with_data):
        vs = VectorStore()
        vs.add("c1", [1.0, 0.0, 0.0], "Python is great for data science and machine learning")
        vs.add("c2", [0.0, 1.0, 0.0], "JavaScript dominates web development and frontend")

        def mock_embed(text):
            if "python" in text.lower() or "data" in text.lower():
                return [0.9, 0.1, 0.0]
            return [0.1, 0.9, 0.0]

        engine = RecallEngine(store=store_with_data, vector_store=vs, embed_fn=mock_embed)
        results = engine.recall("Python data science")

        assert len(results) > 0
        has_middle = any(r.source == "middle" or r.score > 1.0 for r in results)
        has_fast = any(r.source == "fast" for r in results)
        assert has_fast
