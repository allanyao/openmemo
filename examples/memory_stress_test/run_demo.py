"""
Memory Stress Test Demo

Tests OpenMemo's core capabilities:
- Adding many memories rapidly
- Recall accuracy under load
- Memory lifecycle transitions
- Conflict detection
"""

import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from openmemo import Memory


def main():
    db_path = "stress_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = Memory(db_path=db_path)

    print("=" * 60)
    print("OpenMemo Memory Stress Test")
    print("=" * 60)

    print("\n[1/4] Adding 100 memories...")
    start = time.time()

    topics = [
        "Python is great for data science",
        "JavaScript dominates web development",
        "Rust provides memory safety without garbage collection",
        "Go excels at concurrent programming",
        "TypeScript adds static typing to JavaScript",
        "Docker containers simplify deployment",
        "Kubernetes orchestrates container workloads",
        "PostgreSQL is a powerful relational database",
        "Redis provides fast in-memory caching",
        "GraphQL offers flexible API queries",
    ]

    for i in range(100):
        topic = topics[i % len(topics)]
        memory.add(f"{topic} (observation #{i+1})", source="stress_test")

    elapsed = time.time() - start
    print(f"   Done in {elapsed:.2f}s ({100/elapsed:.0f} memories/sec)")

    print("\n[2/4] Testing recall...")
    start = time.time()

    queries = [
        "programming language for web",
        "database technology",
        "container deployment",
        "memory safety",
        "caching solution",
    ]

    for q in queries:
        results = memory.recall(q, top_k=5)
        print(f"   Query: '{q}' -> {len(results)} results")
        if results:
            print(f"     Top: {results[0]['content'][:60]}... (score: {results[0]['score']:.3f})")

    elapsed = time.time() - start
    print(f"   Total recall time: {elapsed:.2f}s")

    print("\n[3/4] Testing conflict detection...")
    memory.add("User prefers dark mode")
    memory.add("User dislikes dark mode")
    stats = memory.stats()
    print(f"   Unresolved conflicts: {stats['unresolved_conflicts']}")

    print("\n[4/4] Running maintenance...")
    result = memory.maintain()
    print(f"   Pyramid: {result['pyramid']}")
    print(f"   Total cells: {result['total_cells']}")

    print("\n" + "=" * 60)
    final_stats = memory.stats()
    print(f"Final Stats:")
    print(f"  Notes: {final_stats['notes']}")
    print(f"  Cells: {final_stats['cells']}")
    print(f"  Stages: {final_stats['stages']}")
    print("=" * 60)

    memory.close()
    os.remove(db_path)
    print("\nStress test completed successfully!")


if __name__ == "__main__":
    main()
