"""
Coding Agent Demo

Demonstrates how a coding agent can use OpenMemo to:
- Remember user preferences
- Track project decisions
- Recall relevant context
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from openmemo import Memory


def main():
    db_path = "coding_agent.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = Memory(db_path=db_path)

    print("=" * 60)
    print("OpenMemo Coding Agent Demo")
    print("=" * 60)

    print("\n[Phase 1] Learning user preferences...")
    memory.add("User prefers Python 3.11+", source="conversation")
    memory.add("Project uses pytest for testing", source="conversation")
    memory.add("User likes type hints in all function signatures", source="conversation")
    memory.add("Code style: black formatter, 88 char line length", source="conversation")
    memory.add("User prefers dataclasses over dictionaries", source="conversation")

    print("\n[Phase 2] Tracking project decisions...")
    memory.add("Decided to use SQLAlchemy 2.0 for ORM", source="decision")
    memory.add("Architecture: clean architecture with dependency injection", source="decision")
    memory.add("API framework: FastAPI with Pydantic models", source="decision")
    memory.add("Database: PostgreSQL for production, SQLite for testing", source="decision")

    print("\n[Phase 3] Recording code patterns...")
    memory.add("Common pattern: use repository pattern for data access", source="code_review")
    memory.add("Error handling: always use custom exception classes", source="code_review")
    memory.add("Logging: use structlog with JSON output", source="code_review")

    print("\n[Phase 4] Recalling context for new tasks...")

    queries = [
        ("writing a new database model", "What patterns should I follow?"),
        ("setting up testing", "What tools does the user prefer?"),
        ("formatting code", "What style rules apply?"),
        ("handling errors", "What approach should I use?"),
    ]

    for task, question in queries:
        print(f"\n  Task: {task}")
        print(f"  Question: {question}")
        results = memory.recall(task, top_k=3)
        for r in results:
            print(f"    -> {r['content'][:70]}")

    print("\n" + "=" * 60)
    stats = memory.stats()
    print(f"Agent Memory Stats: {stats['notes']} notes, {stats['cells']} cells")
    print("=" * 60)

    memory.close()
    os.remove(db_path)
    print("\nCoding agent demo completed!")


if __name__ == "__main__":
    main()
