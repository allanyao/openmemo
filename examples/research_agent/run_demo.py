"""
Research Agent Demo

Demonstrates how a research agent can use OpenMemo to:
- Accumulate knowledge from multiple sources
- Detect conflicting information
- Build a structured knowledge base
- Recall facts for synthesis
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from openmemo import Memory


def main():
    db_path = "research_agent.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = Memory(db_path=db_path)

    print("=" * 60)
    print("OpenMemo Research Agent Demo")
    print("=" * 60)

    print("\n[Phase 1] Collecting research findings...")
    findings = [
        ("arxiv", "Transformer attention scales quadratically with sequence length"),
        ("arxiv", "Flash Attention reduces memory usage from O(n^2) to O(n)"),
        ("arxiv", "Mixture of Experts models achieve better scaling efficiency"),
        ("blog", "GPT-4 uses a mixture of experts architecture"),
        ("paper", "Retrieval-augmented generation improves factual accuracy"),
        ("paper", "Long-context models can process 100K+ tokens"),
        ("blog", "Fine-tuning small models can outperform larger ones on specific tasks"),
        ("arxiv", "RLHF aligns language models with human preferences"),
        ("paper", "Constitutional AI provides an alternative to RLHF"),
        ("blog", "Prompt engineering is often more effective than fine-tuning"),
    ]

    for source, finding in findings:
        memory.add(finding, source=source)
        print(f"  [{source}] {finding}")

    print("\n[Phase 2] Adding conflicting information...")
    memory.add("Fine-tuning always outperforms prompt engineering", source="claim")
    memory.add("Prompt engineering is often more effective than fine-tuning", source="paper")

    stats = memory.stats()
    print(f"  Conflicts detected: {stats['unresolved_conflicts']}")

    print("\n[Phase 3] Synthesizing knowledge...")

    topics = [
        "attention mechanism efficiency",
        "model scaling approaches",
        "improving factual accuracy",
        "training methodology",
    ]

    for topic in topics:
        print(f"\n  Topic: {topic}")
        result = memory.reconstruct(topic, max_sources=5)
        print(f"  Narrative ({len(result['sources'])} sources):")
        for line in result["narrative"].split("\n"):
            if line.strip():
                print(f"    {line}")

    print("\n" + "=" * 60)
    stats = memory.stats()
    print(f"Research Memory: {stats['notes']} findings, {stats['cells']} cells")
    print("=" * 60)

    memory.close()
    os.remove(db_path)
    print("\nResearch agent demo completed!")


if __name__ == "__main__":
    main()
