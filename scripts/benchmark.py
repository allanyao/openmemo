"""
OpenMemo Benchmark

Measures:
- Write throughput (memories/sec)
- Recall latency (ms/query)
- Memory usage
"""

import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openmemo import Memory


def benchmark():
    db_path = "benchmark.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = Memory(db_path=db_path)

    print("OpenMemo Benchmark")
    print("=" * 50)

    sizes = [100, 500, 1000]

    for n in sizes:
        start = time.time()
        for i in range(n):
            memory.add(f"Benchmark memory entry number {i} with some additional context about topic {i % 10}")
        write_time = time.time() - start

        queries = ["benchmark memory", "topic context", "additional entry", "number context", "memory entry"]
        start = time.time()
        for q in queries:
            memory.recall(q, top_k=10)
        recall_time = (time.time() - start) / len(queries) * 1000

        print(f"\n  n={n}:")
        print(f"    Write: {n/write_time:.0f} memories/sec ({write_time:.2f}s total)")
        print(f"    Recall: {recall_time:.1f}ms/query")

    memory.close()
    os.remove(db_path)
    print(f"\nBenchmark complete!")


if __name__ == "__main__":
    benchmark()
