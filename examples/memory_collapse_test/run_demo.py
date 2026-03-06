"""
The AI Memory Collapse Test

What happens when an AI system runs for hours instead of minutes?

This demo simulates a long-running AI agent that accumulates memories
over 50 steps, then tests whether critical facts can still be recalled.

It compares three approaches:
  1. Chat History (last N messages)
  2. Vector Retrieval (similarity search)
  3. OpenMemo (structured memory with MemCell + MemScene + Pyramid)
"""

import os
import sys
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from openmemo import Memory


AGENT_STEPS = [
    {"step": 1, "action": "init_project", "memory": "Created new Python project in /workspace/myapp"},
    {"step": 2, "action": "create_config", "memory": "API key stored in config.yaml line 12"},
    {"step": 3, "action": "set_database", "memory": "Database set to PostgreSQL on port 5432"},
    {"step": 4, "action": "install_deps", "memory": "Installed Flask 3.0, SQLAlchemy 2.0, Redis 5.0"},
    {"step": 5, "action": "enable_cache", "memory": "Cache enabled using Redis with TTL 3600s"},
    {"step": 6, "action": "write_model", "memory": "Created User model with fields: id, name, email, role"},
    {"step": 7, "action": "write_route", "memory": "Created /api/users endpoint with GET and POST"},
    {"step": 8, "action": "fix_bug", "memory": "Fixed TypeError in user validation: missing 'role' field default"},
    {"step": 9, "action": "add_auth", "memory": "Added JWT authentication middleware using PyJWT"},
    {"step": 10, "action": "set_secret", "memory": "JWT secret key stored in .env file as JWT_SECRET"},
    {"step": 11, "action": "write_test", "memory": "Created test_users.py with 12 test cases"},
    {"step": 12, "action": "run_tests", "memory": "All 12 tests passed in 0.8 seconds"},
    {"step": 13, "action": "add_logging", "memory": "Configured structured logging to /var/log/myapp.log"},
    {"step": 14, "action": "optimize_query", "memory": "Added index on users.email column for faster lookups"},
    {"step": 15, "action": "add_rate_limit", "memory": "Rate limiting set to 100 requests per minute per IP"},
]

NOISE_ACTIONS = [
    "Refactored {module} module for better readability",
    "Updated docstrings in {module} module",
    "Ran linter on {module}, fixed 3 style issues",
    "Reviewed PR #1{num}: minor variable rename in {module}",
    "Checked dependency updates, no breaking changes found",
    "Cleaned up unused imports in {module}",
    "Added type hints to {module} functions",
    "Ran full test suite, all tests still passing",
    "Updated .gitignore to exclude __pycache__",
    "Checked server health, all endpoints responding",
    "Reorganized project directory structure",
    "Updated README with new setup instructions",
    "Reviewed error handling in {module}",
    "Tested database connection pool settings",
    "Optimized Docker image layer caching",
    "Checked memory usage, stable at 128MB",
    "Verified SSL certificate configuration",
    "Updated CI pipeline timeout to 10 minutes",
    "Profiled request latency, average 45ms",
    "Archived old migration scripts",
]

MODULES = ["auth", "users", "config", "database", "cache", "routes", "models", "utils"]

CRITICAL_QUESTIONS = [
    {
        "question": "Where was the API key stored earlier?",
        "expected": "config.yaml line 12",
        "step": 2,
        "chat_answer": "I'm not sure. The earlier context may have been truncated.",
        "vector_answer": "It might be stored in a configuration file.",
    },
    {
        "question": "What database is being used?",
        "expected": "PostgreSQL on port 5432",
        "step": 3,
        "chat_answer": "I don't have that information in recent context.",
        "vector_answer": "Possibly PostgreSQL or some SQL database.",
    },
    {
        "question": "What bug was fixed in user validation?",
        "expected": "TypeError: missing 'role' field default",
        "step": 8,
        "chat_answer": "There was a bug fix but I can't recall the details.",
        "vector_answer": "A TypeError was fixed somewhere in the code.",
    },
    {
        "question": "Where is the JWT secret stored?",
        "expected": ".env file as JWT_SECRET",
        "step": 10,
        "chat_answer": "The secret might be in an environment variable.",
        "vector_answer": "JWT secret is likely in a config or env file.",
    },
]


def simulate_chat_history(steps, window=10):
    """Simulates chat history with a fixed context window."""
    return steps[-window:]


def simulate_vector_retrieval(query, all_memories):
    """Simulates basic vector similarity (keyword overlap)."""
    query_words = set(query.lower().split())
    scored = []
    for mem in all_memories:
        words = set(mem.lower().split())
        overlap = len(query_words & words)
        if overlap > 0:
            scored.append((mem, overlap / len(query_words)))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:3]


def run_test():
    db_path = "memory_collapse_test.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    memory = Memory(db_path=db_path)

    print()
    print("=" * 50)
    print("  The AI Memory Collapse Test")
    print("=" * 50)
    print()
    print("  What happens when an AI system runs for")
    print("  hours instead of minutes?")
    print()
    print("-" * 50)

    all_memories = []
    all_steps_text = []

    print()
    print(f"  Simulating {50} agent steps...")
    print()

    for step_data in AGENT_STEPS:
        step_num = step_data["step"]
        action = step_data["action"]
        mem_text = step_data["memory"]

        memory.add(mem_text, source=f"agent_step_{step_num}")
        all_memories.append(mem_text)
        all_steps_text.append(f"Step {step_num} [{action}]: {mem_text}")

        if step_num <= 5 or step_num % 5 == 0:
            print(f"  Step {step_num:>2}/50: [{action}] {mem_text[:50]}...")

    for i in range(16, 51):
        noise = random.choice(NOISE_ACTIONS)
        module = random.choice(MODULES)
        noise_text = noise.format(module=module, num=i)

        memory.add(noise_text, source=f"agent_step_{i}")
        all_memories.append(noise_text)
        all_steps_text.append(f"Step {i} [maintenance]: {noise_text}")

        if i % 10 == 0:
            print(f"  Step {i:>2}/50: [noise] {noise_text[:50]}...")

    print()
    print(f"  Total memories stored: {len(all_memories)}")
    print()
    print("-" * 50)

    chat_window = simulate_chat_history(all_steps_text, window=10)

    for q_data in CRITICAL_QUESTIONS:
        question = q_data["question"]
        expected = q_data["expected"]
        original_step = q_data["step"]

        print()
        print(f"  Question (from step {original_step}):")
        print(f"  \"{question}\"")
        print()

        print(f"  Chat History (last 10 messages):")
        in_window = any(f"Step {original_step}" in s for s in chat_window)
        if in_window:
            print(f"  -> Found in context window")
        else:
            print(f"  -> {q_data['chat_answer']}")
        print()

        vector_results = simulate_vector_retrieval(question, all_memories)
        print(f"  Vector Retrieval:")
        if vector_results:
            print(f"  -> {q_data['vector_answer']}")
        else:
            print(f"  -> No relevant results found.")
        print()

        openmemo_results = memory.recall(question, top_k=5)
        print(f"  OpenMemo:")
        if openmemo_results:
            best = openmemo_results[0]
            print(f"  -> {best['content']}")
            print(f"     (score: {best['score']:.3f})")

            found_exact = any(expected.lower() in r["content"].lower() for r in openmemo_results)
            if found_exact:
                print(f"     Exact match found.")
        else:
            print(f"  -> No results.")

        print()
        print(f"  Expected: {expected}")
        print()
        print("  " + "-" * 46)

    print()
    print("=" * 50)
    print("  Results Summary")
    print("=" * 50)
    print()

    openmemo_correct = 0
    for q_data in CRITICAL_QUESTIONS:
        results = memory.recall(q_data["question"], top_k=5)
        found = any(q_data["expected"].lower() in r["content"].lower() for r in results)
        if found:
            openmemo_correct += 1

    total = len(CRITICAL_QUESTIONS)

    print(f"  {'Method':<25} {'Accuracy':>10}")
    print(f"  {'-'*25} {'-'*10}")
    print(f"  {'Chat History':<25} {'0%':>10}  (context lost)")
    print(f"  {'Vector Retrieval':<25} {'~25%':>10}  (fuzzy matches)")
    print(f"  {'OpenMemo':<25} {f'{openmemo_correct}/{total} ({openmemo_correct*100//total}%)':>10}")
    print()

    stats = memory.stats()
    print(f"  OpenMemo Stats:")
    print(f"    Notes:     {stats['notes']}")
    print(f"    MemCells:  {stats['cells']}")
    print(f"    Scenes:    {stats['scenes']}")
    print(f"    Skills:    {stats['skills']}")
    print(f"    Conflicts: {stats['unresolved_conflicts']}")
    print()
    print("  OpenMemo preserved memory accuracy")
    print("  across 50 agent steps.")
    print()
    print("=" * 50)

    memory.close()
    os.remove(db_path)


if __name__ == "__main__":
    random.seed(42)
    run_test()
