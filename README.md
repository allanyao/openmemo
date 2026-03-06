# OpenMemo

OpenMemo is an AI-native structured memory system for long-term knowledge.

Instead of storing notes as plain text, OpenMemo organizes information into structured data that can be understood, searched, and reused by AI systems.

The goal of OpenMemo is to help individuals and teams build a long-term knowledge layer that works naturally with modern AI tools.

---

## Why OpenMemo

Most notes are written for humans.

But modern AI systems work best when information is structured, contextual, and connected.

OpenMemo helps transform everyday notes into structured knowledge that can power:

- AI-assisted workflows
- Knowledge retrieval
- Long-term memory systems
- Research and documentation

| Feature | Chat History | Vector DB | **OpenMemo** |
|---------|-------------|-----------|-------------|
| Structure | Flat log | Flat embeddings | **Hierarchical (MemCell + MemScene)** |
| Evolution | Append-only | Append-only | **Consolidate, promote, forget** |
| Recall | Last N messages | Top-K similarity | **Tri-brain (fast/mid/slow) + rerank** |
| Governance | None | None | **Conflict detection + version control** |
| Token Budget | Grows forever | Fixed window | **Pyramid auto-compression** |

---

## Features

- Structured note format with atomic fact extraction
- AI-friendly knowledge storage (MemCell + MemScene)
- Searchable memory system with tri-brain recall
- API-ready data model (Python SDK + REST)
- Modular architecture for integrations
- Memory Pyramid for automatic token budget control
- Skill engine for experience-to-skill extraction
- Governance with conflict detection and version management

---

## Getting Started

Install from PyPI:

```bash
pip install openmemo
```

Quick example:

```python
from openmemo import Memory

memory = Memory()

memory.add("User prefers dark mode")
memory.add("Project deadline is March 15")
memory.add("User's favorite language is Python")

results = memory.recall("user preference")
for r in results:
    print(r["content"], r["score"])
```

Or clone the repository:

```bash
git clone https://github.com/allanyao/openmemo.git
cd openmemo
pip install -e ".[dev]"
```

---

## Core Concepts

### MemCell
The atomic unit of memory. Each note is broken down into structured facts with metadata, relationships, and lifecycle stages.

### MemScene
Scene-based containers that group related MemCells by context, enabling narrative-level recall.

### Memory Pyramid
Three-tier compression system:
- **Short-term**: Raw notes and recent facts
- **Mid-term**: Category summaries and patterns
- **Long-term**: User profile and stable knowledge

### Recall Engine
Tri-brain retrieval architecture:
- **Fast Brain**: BM25 keyword matching (~5ms)
- **Middle Brain**: Semantic embedding similarity (~50ms)
- **Slow Brain**: LLM-powered reasoning (~500ms)

Results are merged, reranked, and budget-constrained automatically.

### Skill Engine
Agents learn from experience. Repeated patterns are extracted into reusable skills that improve over time.

### Governance
Memory quality control:
- Conflict detection between contradictory facts
- Version management for evolving knowledge
- Promotion gates for fact reliability

---

## Architecture

```
            add()
              |
    +---------v----------+
    |   Write Pipeline    |
    |  Note -> Facts ->   |
    |  MemCell -> Scene   |
    +-------|-------------+
            |
    +-------v-------------+
    |   Memory Pyramid     |
    |  Short | Mid | Long  |
    +---------|-----------+
              |
    +---------v-----------+
    |   Recall Engine      |
    |  Fast + Mid + Slow   |
    |  -> Rerank -> Budget |
    +---------------------+
```

---

## Examples

### Memory Stress Test
```bash
cd examples/memory_stress_test
python run_demo.py
```

### Coding Agent
```bash
cd examples/coding_agent_demo
python run_demo.py
```

### Research Agent
```bash
cd examples/research_agent
python run_demo.py
```

---

## Docker

```bash
cd docker
docker compose up
```

---

## Project Structure

```
openmemo/
├── openmemo/           # Core library
│   ├── core/           # MemCell, MemScene, Recall, Reconstruct
│   ├── storage/        # Storage adapters (SQLite, Postgres, Vector)
│   ├── pyramid/        # Memory Pyramid engine
│   ├── skill/          # Skill extraction and learning
│   ├── governance/     # Conflict detection, version control
│   └── api/            # Python SDK + REST server
├── adapters/           # External integrations
├── examples/           # Runnable demos
├── cookbooks/          # Complete scenario guides
├── docs/               # Architecture documentation
├── scripts/            # Utilities and benchmarks
└── docker/             # Container deployment
```

---

## Roadmap

- [x] MemCell Engine
- [x] MemScene Engine
- [x] Recall (Tri-brain + Rerank)
- [x] Reconstructive Recall
- [x] Memory Pyramid
- [x] Skill Engine (simplified)
- [ ] Distributed memory sync
- [ ] Multi-agent shared memory
- [ ] Plugin system for custom extractors

---

## License

OpenMemo is licensed under the **AGPLv3 License**.

This means:

- You can use and modify the software.
- If you run a modified version as a network service, you must also release the source code of those modifications.

See the [LICENSE](LICENSE) file for details.

---

## Trademark

OpenMemo is a trademark of the OpenMemo project maintainers.

Forks of this repository must not use the OpenMemo name or branding in a way that implies affiliation with the original project.

---

## Contributing

We welcome contributions from the community.

Please read the [CONTRIBUTING.md](CONTRIBUTING.md) file before submitting pull requests.

---

## Community

If you are interested in building AI-native knowledge systems, OpenMemo aims to be a foundation for that ecosystem.

Stay tuned for updates and roadmap discussions.
