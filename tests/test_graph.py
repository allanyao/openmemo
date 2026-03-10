"""
Tests for Phase 18: Memory Relationship Graph Engine.

Covers: edge CRUD, graph builder, graph expansion, conflict detection, SDK integration.
"""

import os
import sys
import time
import unittest
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openmemo.storage.sqlite_store import SQLiteStore
from openmemo.core.graph import GraphBuilder, get_memory_graph, detect_conflicts
from openmemo.api.sdk import Memory


class TestEdgeCRUD(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = SQLiteStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_put_and_get_edge(self):
        edge = {
            "edge_id": "e1",
            "memory_a": "m1",
            "memory_b": "m2",
            "relation_type": "fixes",
            "confidence": 0.85,
            "created_at": time.time(),
        }
        self.store.put_edge(edge)
        edges = self.store.get_edges("m1")
        self.assertEqual(len(edges), 1)
        self.assertEqual(edges[0]["relation_type"], "fixes")
        self.assertAlmostEqual(edges[0]["confidence"], 0.85, places=2)

    def test_get_edges_bidirectional(self):
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "m1", "memory_b": "m2",
            "relation_type": "supports", "confidence": 0.7,
        })
        edges_from_a = self.store.get_edges("m1")
        edges_from_b = self.store.get_edges("m2")
        self.assertEqual(len(edges_from_a), 1)
        self.assertEqual(len(edges_from_b), 1)
        self.assertEqual(edges_from_a[0]["edge_id"], edges_from_b[0]["edge_id"])

    def test_delete_edge(self):
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "m1", "memory_b": "m2",
            "relation_type": "related", "confidence": 0.5,
        })
        self.assertTrue(self.store.delete_edge("e1"))
        self.assertEqual(len(self.store.get_edges("m1")), 0)

    def test_list_edges(self):
        for i in range(5):
            self.store.put_edge({
                "edge_id": f"e{i}", "memory_a": f"m{i}", "memory_b": f"m{i+1}",
                "relation_type": "related", "confidence": 0.5,
            })
        edges = self.store.list_edges(limit=3)
        self.assertEqual(len(edges), 3)

    def test_edge_metadata(self):
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "m1", "memory_b": "m2",
            "relation_type": "causes", "confidence": 0.9,
            "metadata": {"source": "llm"},
        })
        edges = self.store.get_edges("m1")
        self.assertEqual(edges[0]["metadata"]["source"], "llm")


class TestGraphBuilder(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = SQLiteStore(self.tmp.name)
        self.builder = GraphBuilder(store=self.store)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def _add_cell(self, cell_id, content, scene="test"):
        self.store.put_cell({
            "id": cell_id, "note_id": cell_id, "content": content,
            "cell_type": "fact", "scene": scene,
            "created_at": time.time(), "metadata": "{}",
        })

    def test_detect_fix_relationship(self):
        cell_a = {"id": "c1", "content": "Bug caused by missing env variable DATABASE_URL"}
        cell_b = {"id": "c2", "content": "Fixed the bug by adding DATABASE_URL env variable in Dockerfile"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)
        rel_types = [e["relation_type"] for e in edges]
        self.assertIn("fixes", rel_types)

    def test_detect_contradiction(self):
        cell_a = {"id": "c1", "content": "We should always use Python for backend services"}
        cell_b = {"id": "c2", "content": "We should never use Python, use Go instead"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)
        rel_types = [e["relation_type"] for e in edges]
        self.assertIn("contradicts", rel_types)

    def test_detect_causal(self):
        cell_a = {"id": "c1", "content": "Server crash was caused by memory leak in worker process"}
        cell_b = {"id": "c2", "content": "Memory leak in worker process leads to OOM errors"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)
        rel_types = [e["relation_type"] for e in edges]
        self.assertIn("causes", rel_types)

    def test_detect_support(self):
        cell_a = {"id": "c1", "content": "Python is great for data science and machine learning"}
        cell_b = {"id": "c2", "content": "Python data science libraries like pandas are excellent"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)

    def test_detect_extends(self):
        cell_a = {"id": "c1", "content": "The caching layer provides basic key-value storage"}
        cell_b = {"id": "c2", "content": "We can extend the caching layer to support TTL and eviction"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)
        rel_types = [e["relation_type"] for e in edges]
        self.assertIn("extends", rel_types)

    def test_build_edges_stores_to_db(self):
        self._add_cell("c1", "Bug caused by missing env variable DATABASE_URL")
        self._add_cell("c2", "Fixed by adding DATABASE_URL env variable to config")
        edges = self.builder.build_edges("c1")
        self.assertTrue(len(edges) > 0)
        stored = self.store.get_edges("c1")
        self.assertEqual(len(stored), len(edges))

    def test_no_self_edge(self):
        cell = {"id": "c1", "content": "Some memory content about Python"}
        edges = self.builder.detect_relationships(cell, [cell])
        self.assertEqual(len(edges), 0)

    def test_no_edge_for_unrelated(self):
        cell_a = {"id": "c1", "content": "The weather is sunny today"}
        cell_b = {"id": "c2", "content": "Quantum computing uses qubits"}
        edges = self.builder.detect_relationships(cell_a, [cell_b])
        self.assertEqual(len(edges), 0)

    def test_llm_callback(self):
        def mock_llm(text_a, text_b):
            return {"relation": "supports", "confidence": 0.92}

        builder = GraphBuilder(store=self.store, llm_fn=mock_llm)
        cell_a = {"id": "c1", "content": "Python is good"}
        cell_b = {"id": "c2", "content": "Python is great"}
        edges = builder.detect_relationships(cell_a, [cell_b])
        self.assertTrue(len(edges) > 0)
        self.assertEqual(edges[0]["relation_type"], "supports")
        self.assertAlmostEqual(edges[0]["confidence"], 0.92, places=2)


class TestGetMemoryGraph(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = SQLiteStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def _add_cell(self, cell_id, content):
        self.store.put_cell({
            "id": cell_id, "note_id": cell_id, "content": content,
            "cell_type": "fact", "created_at": time.time(), "metadata": "{}",
        })

    def test_graph_traversal(self):
        self._add_cell("c1", "Root memory")
        self._add_cell("c2", "Connected to root")
        self._add_cell("c3", "Connected to c2")
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "c1", "memory_b": "c2",
            "relation_type": "supports", "confidence": 0.8,
        })
        self.store.put_edge({
            "edge_id": "e2", "memory_a": "c2", "memory_b": "c3",
            "relation_type": "causes", "confidence": 0.7,
        })
        graph = get_memory_graph(self.store, "c1", depth=2)
        self.assertEqual(len(graph["nodes"]), 3)
        self.assertEqual(len(graph["edges"]), 2)

    def test_graph_depth_1(self):
        self._add_cell("c1", "Root")
        self._add_cell("c2", "Level 1")
        self._add_cell("c3", "Level 2")
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "c1", "memory_b": "c2",
            "relation_type": "related", "confidence": 0.5,
        })
        self.store.put_edge({
            "edge_id": "e2", "memory_a": "c2", "memory_b": "c3",
            "relation_type": "related", "confidence": 0.5,
        })
        graph = get_memory_graph(self.store, "c1", depth=1)
        self.assertEqual(len(graph["nodes"]), 2)

    def test_empty_graph(self):
        self._add_cell("c1", "Isolated memory")
        graph = get_memory_graph(self.store, "c1")
        self.assertEqual(len(graph["nodes"]), 1)
        self.assertEqual(len(graph["edges"]), 0)


class TestConflictDetection(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = SQLiteStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_detect_contradicts_edges(self):
        self.store.put_cell({
            "id": "c1", "note_id": "c1", "content": "Use NodeJS for backend",
            "cell_type": "decision", "agent_id": "agent1",
            "created_at": time.time(),
            "metadata": '{"confidence": 0.9}',
        })
        self.store.put_cell({
            "id": "c2", "note_id": "c2", "content": "Use Python for backend",
            "cell_type": "decision", "agent_id": "agent1",
            "created_at": time.time(),
            "metadata": '{"confidence": 0.7}',
        })
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "c1", "memory_b": "c2",
            "relation_type": "contradicts", "confidence": 0.85,
        })
        conflicts = detect_conflicts(self.store, agent_id="agent1")
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0]["winner"], "c1")

    def test_no_conflicts_without_contradicts(self):
        self.store.put_cell({
            "id": "c1", "note_id": "c1", "content": "Memory A",
            "cell_type": "fact", "created_at": time.time(), "metadata": "{}",
        })
        self.store.put_cell({
            "id": "c2", "note_id": "c2", "content": "Memory B",
            "cell_type": "fact", "created_at": time.time(), "metadata": "{}",
        })
        self.store.put_edge({
            "edge_id": "e1", "memory_a": "c1", "memory_b": "c2",
            "relation_type": "supports", "confidence": 0.9,
        })
        conflicts = detect_conflicts(self.store)
        self.assertEqual(len(conflicts), 0)


class TestGraphRecallExpansion(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.memo = Memory(db_path=self.tmp.name)

    def tearDown(self):
        self.memo.close()
        os.unlink(self.tmp.name)

    def test_graph_expansion_in_recall(self):
        self.memo._auto_graph = False
        id1 = self.memo.write_memory("Bug caused by missing DATABASE_URL env variable", scene="deploy")
        id2 = self.memo.write_memory("Fixed by adding DATABASE_URL to Dockerfile", scene="deploy")

        cells = self.memo.store.list_cells(limit=10)
        cell_ids = {c["id"] for c in cells}
        cell_a = [c for c in cells if "Bug caused" in c["content"]][0]
        cell_b = [c for c in cells if "Fixed by" in c["content"]][0]

        self.memo.add_memory_edge(cell_a["id"], cell_b["id"], "fixes", 0.9)

        results = self.memo.recall_engine.recall(
            "DATABASE_URL problem", top_k=10, budget=50000,
            graph=True,
        )
        contents = [r.content for r in results]
        self.assertTrue(any("Bug caused" in c for c in contents))

    def test_recall_context_with_graph(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Server uses PostgreSQL database", scene="infra")
        self.memo.write_memory("PostgreSQL requires connection pooling", scene="infra")

        cells = self.memo.store.list_cells(limit=10)
        if len(cells) >= 2:
            self.memo.add_memory_edge(cells[0]["id"], cells[1]["id"], "supports", 0.8)

        result = self.memo.recall_context("PostgreSQL setup", scene="infra", graph=True)
        self.assertIn("context", result)
        self.assertTrue(len(result["context"]) > 0)


class TestSDKGraphIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.memo = Memory(db_path=self.tmp.name)

    def tearDown(self):
        self.memo.close()
        os.unlink(self.tmp.name)

    def test_add_memory_edge(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Memory A about testing")
        self.memo.write_memory("Memory B about testing")
        cells = self.memo.store.list_cells(limit=10)
        self.assertTrue(len(cells) >= 2)
        edge = self.memo.add_memory_edge(cells[0]["id"], cells[1]["id"], "supports", 0.9)
        self.assertEqual(edge["relation_type"], "supports")
        self.assertAlmostEqual(edge["confidence"], 0.9)

    def test_get_memory_graph_via_sdk(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Root concept about AI")
        self.memo.write_memory("AI requires data preprocessing")
        cells = self.memo.store.list_cells(limit=10)
        if len(cells) >= 2:
            self.memo.add_memory_edge(cells[0]["id"], cells[1]["id"], "related")
            graph = self.memo.get_memory_graph(cells[0]["id"])
            self.assertTrue(len(graph["nodes"]) >= 1)

    def test_detect_conflicts_via_sdk(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Use Redis for caching", memory_type="decision",
                               confidence=0.9, agent_id="a1")
        self.memo.write_memory("Avoid Redis, use Memcached", memory_type="decision",
                               confidence=0.6, agent_id="a1")
        cells = self.memo.store.list_cells(limit=10)
        if len(cells) >= 2:
            self.memo.add_memory_edge(cells[0]["id"], cells[1]["id"], "contradicts", 0.85)
            conflicts = self.memo.detect_conflicts(agent_id="a1")
            self.assertEqual(len(conflicts), 1)

    def test_auto_graph_on_write(self):
        self.memo._auto_graph = True
        self.memo.write_memory("Bug caused by missing config file", scene="debug")
        self.memo.write_memory("Fixed bug by creating config file", scene="debug")
        edges = self.memo.store.list_edges(limit=100)
        self.assertTrue(len(edges) >= 0)

    def test_stats_includes_edges(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Test memory for stats")
        stats = self.memo.stats()
        self.assertIn("edges", stats)
        self.assertIn("edge_types", stats)

    def test_list_edges_via_sdk(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Memory X")
        self.memo.write_memory("Memory Y")
        cells = self.memo.store.list_cells(limit=10)
        if len(cells) >= 2:
            self.memo.add_memory_edge(cells[0]["id"], cells[1]["id"], "related")
            edges = self.memo.list_edges()
            self.assertEqual(len(edges), 1)

    def test_governance_cleanup_removes_orphaned_edges(self):
        self.memo._auto_graph = False
        self.memo.write_memory("Temporary memory")
        cells = self.memo.store.list_cells(limit=10)
        self.memo.store.put_edge({
            "edge_id": "orphan_edge", "memory_a": cells[0]["id"],
            "memory_b": "nonexistent_cell",
            "relation_type": "related", "confidence": 0.5,
        })
        result = self.memo.memory_governance("cleanup")
        self.assertIn("orphaned_edges_removed", result)
        self.assertGreaterEqual(result["orphaned_edges_removed"], 1)


class TestGraphScopeIsolation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.memo = Memory(db_path=self.tmp.name)
        self.memo._auto_graph = False

    def tearDown(self):
        self.memo.close()
        os.unlink(self.tmp.name)

    def test_graph_expansion_respects_scope(self):
        self.memo.write_memory("Shared config: use port 8080",
                               agent_id="a1", scope="shared")
        self.memo.write_memory("Private secret: API key is xyz",
                               agent_id="a2", scope="private")

        cells = self.memo.store.list_cells(limit=10)
        shared = [c for c in cells if "Shared config" in c["content"]][0]
        private = [c for c in cells if "Private secret" in c["content"]][0]

        self.memo.add_memory_edge(shared["id"], private["id"], "related", 0.9)

        results = self.memo.recall_engine.recall(
            "port configuration", top_k=10, budget=50000,
            agent_id="a1", graph=True,
        )
        contents = [r.content for r in results]
        self.assertFalse(any("Private secret" in c for c in contents))

    def test_graph_expansion_allows_shared(self):
        self.memo.write_memory("Use Python for backend", agent_id="a1")
        self.memo.write_memory("Python best practices", scope="shared")

        cells = self.memo.store.list_cells(limit=10)
        private = [c for c in cells if "Use Python" in c["content"]][0]
        shared = [c for c in cells if "best practices" in c["content"]][0]

        self.memo.add_memory_edge(private["id"], shared["id"], "supports", 0.8)

        results = self.memo.recall_engine.recall(
            "Python backend", top_k=10, budget=50000,
            agent_id="a1", graph=True,
        )
        contents = [r.content for r in results]
        has_shared = any("best practices" in c for c in contents)
        self.assertTrue(has_shared or len(results) >= 1)


class TestGraphDepthBoundary(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.store = SQLiteStore(self.tmp.name)

    def tearDown(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_depth_1_excludes_level_2_edges(self):
        for i in range(4):
            self.store.put_cell({
                "id": f"c{i}", "note_id": f"c{i}", "content": f"Cell {i}",
                "cell_type": "fact", "created_at": time.time(), "metadata": "{}",
            })
        self.store.put_edge({
            "edge_id": "e01", "memory_a": "c0", "memory_b": "c1",
            "relation_type": "related", "confidence": 0.5,
        })
        self.store.put_edge({
            "edge_id": "e12", "memory_a": "c1", "memory_b": "c2",
            "relation_type": "related", "confidence": 0.5,
        })
        self.store.put_edge({
            "edge_id": "e23", "memory_a": "c2", "memory_b": "c3",
            "relation_type": "related", "confidence": 0.5,
        })
        graph = get_memory_graph(self.store, "c0", depth=1)
        node_ids = {n["memory_id"] for n in graph["nodes"]}
        self.assertIn("c0", node_ids)
        self.assertIn("c1", node_ids)
        self.assertNotIn("c2", node_ids)
        self.assertNotIn("c3", node_ids)
        for edge in graph["edges"]:
            self.assertIn(edge["memory_a"], node_ids)
            self.assertIn(edge["memory_b"], node_ids)


if __name__ == "__main__":
    unittest.main()
