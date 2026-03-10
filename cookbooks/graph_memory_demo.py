#!/usr/bin/env python3
"""
Graph Memory Demo — Phase 18: Memory Relationship Graph Engine

Demonstrates how OpenMemo's cognitive memory graph enables:
1. Automatic relationship detection between memories
2. Graph-based recall (not just vector search)
3. Conflict detection and resolution
4. Memory clustering for contextual understanding

Scenario: A development team debugging a production incident.
"""

import sys
import os
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openmemo import OpenMemo


def main():
    print("=" * 60)
    print("  OpenMemo — Graph Memory Demo")
    print("  Phase 18: Cognitive Memory Graph")
    print("=" * 60)

    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    memo = OpenMemo(db_path=tmp.name)
    memo._auto_graph = True

    print("\n--- Step 1: Write incident memories ---\n")

    memories = [
        ("Production API returning 500 errors since 14:00 UTC",
         "incident", "deploy", 0.95),
        ("Root cause: database connection pool exhausted due to connection leak",
         "fact", "deploy", 0.9),
        ("Connection leak caused by missing connection.close() in user service",
         "fact", "deploy", 0.85),
        ("Fixed connection leak by adding try-finally block in user_service.py",
         "fact", "deploy", 0.92),
        ("Deployed hotfix v2.3.1 to production at 15:30 UTC",
         "fact", "deploy", 0.95),
        ("Added connection pool monitoring alerts to prevent future incidents",
         "decision", "deploy", 0.88),
    ]

    written_ids = []
    for content, mtype, scene, conf in memories:
        mid = memo.write_memory(content, memory_type=mtype,
                                scene=scene, confidence=conf)
        written_ids.append(mid)
        print(f"  [write] {content[:60]}...")

    print("\n--- Step 2: Check auto-generated edges ---\n")

    edges = memo.list_edges()
    print(f"  Auto-generated edges: {len(edges)}")
    for e in edges[:10]:
        cell_a = memo.store.get_cell(e["memory_a"])
        cell_b = memo.store.get_cell(e["memory_b"])
        a_short = (cell_a.get("content", "")[:40] + "...") if cell_a else "?"
        b_short = (cell_b.get("content", "")[:40] + "...") if cell_b else "?"
        print(f"  [{e['relation_type']:12s}] {a_short} → {b_short} (conf={e['confidence']:.2f})")

    print("\n--- Step 3: Manual edge — link root cause to fix ---\n")

    cells = memo.store.list_cells(limit=20)
    root_cause = next((c for c in cells if "Root cause" in c["content"]), None)
    fix = next((c for c in cells if "Fixed connection" in c["content"]), None)

    if root_cause and fix:
        edge = memo.add_memory_edge(root_cause["id"], fix["id"], "fixes", 0.95)
        print(f"  Added: {root_cause['content'][:50]}")
        print(f"     → fixes → {fix['content'][:50]}")
        print(f"  Edge confidence: {edge['confidence']}")

    print("\n--- Step 4: Graph recall (query = 'database connection problem') ---\n")

    result = memo.recall_context("database connection problem", scene="deploy",
                                 graph=True)
    print(f"  Recalled {len(result['context'])} memories:")
    for i, ctx in enumerate(result["context"], 1):
        print(f"    {i}. {ctx}")

    print("\n--- Step 5: Get memory graph for root cause ---\n")

    if root_cause:
        graph = memo.get_memory_graph(root_cause["id"], depth=2)
        print(f"  Graph nodes: {len(graph['nodes'])}")
        print(f"  Graph edges: {len(graph['edges'])}")
        for node in graph["nodes"]:
            print(f"    [node] {node['content'][:60]}")
        for edge in graph["edges"]:
            print(f"    [edge] {edge['memory_a'][:8]}→{edge['memory_b'][:8]} ({edge['relation_type']})")

    print("\n--- Step 6: Conflict detection ---\n")

    memo.write_memory("We should use Redis for session storage",
                      memory_type="decision", scene="arch", confidence=0.85)
    memo.write_memory("Avoid Redis for session storage, use database instead",
                      memory_type="decision", scene="arch", confidence=0.7)

    cells = memo.store.list_cells(limit=20, scene="arch")
    redis_cells = [c for c in cells if "Redis" in c["content"] or "redis" in c["content"].lower()]
    if len(redis_cells) >= 2:
        memo.add_memory_edge(redis_cells[0]["id"], redis_cells[1]["id"],
                             "contradicts", 0.88)

    conflicts = memo.detect_conflicts()
    print(f"  Detected conflicts: {len(conflicts)}")
    for conflict in conflicts:
        print(f"    A: {conflict['memory_a']['content'][:50]}")
        print(f"    B: {conflict['memory_b']['content'][:50]}")
        winner_id = conflict["winner"]
        winner = conflict["memory_a"] if conflict["memory_a"]["id"] == winner_id else conflict["memory_b"]
        print(f"    Winner: {winner['content'][:50]} (confidence={winner['confidence']})")

    print("\n--- Step 7: Stats ---\n")

    stats = memo.stats()
    print(f"  Total memories: {stats['cells']}")
    print(f"  Total edges: {stats['edges']}")
    print(f"  Edge types: {stats['edge_types']}")
    print(f"  Scenes: {stats['scenes']}")

    memo.close()
    os.unlink(tmp.name)

    print("\n" + "=" * 60)
    print("  Demo complete!")
    print("  OpenMemo now uses Cognitive Memory Graph")
    print("  recall = vector search + graph expansion + conflict detection")
    print("=" * 60)


if __name__ == "__main__":
    main()
