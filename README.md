# OpenMemo

**The Memory Infrastructure for AI Agents.**

Most AI memory systems today are just wrappers around vector databases.

OpenMemo is different.

Instead of storing memory as flat embeddings, OpenMemo introduces a structured memory architecture designed for long-running AI systems.

```
MemCell → MemScene → Memory Pyramid → Reconstructive Recall
```

OpenMemo enables AI agents to remember, evolve, and reason over past experience — rather than simply retrieving text chunks.

---

## Quickstart

### Install

```bash
pip install openmemo
```

### Python SDK

```python
from openmemo import Memory

memory = Memory()

# Write memories with agent isolation and scenes
memory.add("User prefers PostgreSQL for production",
           agent_id="my_agent",
           scene="infrastructure",
           cell_type="preference")

memory.add("Always run tests before deploying",
           agent_id="my_agent",
           scene="workflow",
           cell_type="constraint")

# Recall with context
results = memory.recall("database preference", agent_id="my_agent")
for r in results:
    print(r["content"], r["score"])

# List scenes
scenes = memory.scenes(agent_id="my_agent")

# Delete a memory
memory.delete(memory_id)
```

### REST API

```bash
# Start local server
pip install "openmemo[server]"
openmemo serve --port 8080

# Or use the cloud API
# Write
curl -X POST https://api.openmemo.ai/memory/write \
  -H "Content-Type: application/json" \
  -d '{
    "content": "User prefers PostgreSQL",
    "agent_id": "my_agent",
    "scene": "infrastructure",
    "cell_type": "preference"
  }'

# Recall
curl -X POST https://api.openmemo.ai/memory/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "database preference", "agent_id": "my_agent"}'

# Search
curl -X POST https://api.openmemo.ai/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "database", "agent_id": "my_agent"}'

# Scenes
curl https://api.openmemo.ai/memory/scenes?agent_id=my_agent

# Delete
curl -X DELETE https://api.openmemo.ai/memory/{id}
```

### MCP Adapter (for Claude)

```python
from openmemo.adapters.mcp import OpenMemoMCPServer

server = OpenMemoMCPServer()
tools = server.get_tools()  # memory_write, memory_recall, memory_search
result = server.handle_tool("memory_write", {"content": "User prefers Python"})
```

### LangChain Adapter

```python
from openmemo.adapters.langchain import OpenMemoMemory

memory = OpenMemoMemory(agent_id="my_agent")
memory.save_context({"input": "hello"}, {"output": "hi"})
history = memory.load_memory_variables({"input": "greeting"})
```

---

## Key Concepts

### agent_id — Multi-Agent Isolation

Each agent gets its own memory namespace. Memories are isolated by `agent_id`.

```python
# Agent A's memories
memory.add("prefers Python", agent_id="agent_a")

# Agent B's memories
memory.add("prefers Rust", agent_id="agent_b")

# Only returns agent_a's memories
memory.recall("language preference", agent_id="agent_a")
```

### scene — Contextual Grouping

Scenes group related memories by context. They are auto-created when you write with a `scene` parameter.

```python
memory.add("Use Flask for API", agent_id="a1", scene="project_setup")
memory.add("Deploy to AWS", agent_id="a1", scene="infrastructure")

# Filter recall by scene
memory.recall("setup", agent_id="a1", scene="project_setup")
```

### cell_type — Typed Memory

MemCells support 5 types for structured memory:

| Type | Use Case |
|------|----------|
| `fact` | Factual information (default) |
| `decision` | Choices and rationale |
| `preference` | User/agent preferences |
| `constraint` | Rules and limitations |
| `observation` | Behavioral observations |

---

## Why OpenMemo?

Most AI memory systems work like this:

```
Store → Embed → Similarity Search → Inject Context
```

This breaks when AI systems run for long periods:

- Memory becomes noisy
- Conflicting facts accumulate
- Context windows explode
- Past reasoning is lost

OpenMemo solves these with a structured memory architecture:

### MemCell — Atomic Memory

Each memory is a structured unit with lifecycle stages, importance scoring, and conflict detection.

### MemScene — Contextual Memory

Related memories are grouped into scenes, reducing retrieval noise.

### Memory Pyramid — Hierarchical Compression

```
L0  Profile Memory
L1  Category Memory
L2  Episodic Memory
L3  Raw Events
```

### Reconstructive Recall

Instead of returning raw chunks, OpenMemo reconstructs coherent narratives with conflict annotations.

### Memory Governance

Conflict detection, memory evolution, maintenance workers, and duplicate cleanup.

### Cognitive Constitution

OpenMemo is governed by a **Constitution** — a policy layer that defines how memory is stored, ranked, reconciled, and evolved.

The Constitution is defined in two files:
- [`constitution.md`](openmemo/constitution/constitution.md) — human-readable policy document
- `constitution.json` — machine-readable configuration

It controls six dimensions of memory behavior:

| Policy | What it governs |
|--------|----------------|
| **Memory Philosophy** | What to store vs. filter as noise |
| **Priority Policy** | Ranking order: decision > constraint > fact > preference > observation > conversation |
| **Recall Policy** | Prefer scene-local, recent, high-confidence memories |
| **Conflict Policy** | Auto-resolve when confidence gap ≥ 0.15 |
| **Retention Policy** | Transient conversation decays fast; reinforced memories persist |
| **Promotion Policy** | Requires ≥ 2 occurrences + 1 success signal to promote to stable knowledge |

The Constitution is loaded at startup and wired into the write pipeline, recall engine, conflict detector, and governance worker — making OpenMemo a **policy-driven cognitive memory system**.

```python
from openmemo import Memory

memory = Memory()

# Constitution is active by default
# Noise is filtered automatically
memory.write_memory("hi")  # → "" (filtered)
memory.write_memory("Use PostgreSQL for production", memory_type="decision")  # → stored with priority boost

# Recall is constitution-aware (scene-local priority, confidence ranking)
result = memory.recall_context("database", scene="infra")
```

---

## Architecture

```
Applications / Agents
      │
      ▼
OpenMemo SDK (Memory class)
      │
      ▼
OpenMemo Core
  ├── Constitution (cognitive policy layer)
  ├── MemCell Engine (typed cells, lifecycle, evolution)
  ├── Scene Manager (auto-detection, grouping)
  ├── Recall Engine (BM25 + Vector, constitution-aware ranking)
  ├── Reconstruct Engine (narrative + conflict annotation)
  ├── Memory Pyramid (hierarchical compression)
  ├── Skill Engine (pattern extraction)
  └── Governance Layer (conflict detection, promotion, versioning)
      │
      ▼
Storage (SQLite default, pluggable)
```

### Adapters

| Adapter | Status | Usage |
|---------|--------|-------|
| MCP (Claude) | Available | `from openmemo.adapters.mcp import OpenMemoMCPServer` |
| LangChain | Available | `from openmemo.adapters.langchain import OpenMemoMemory` |
| OpenClaw | Available | `from openmemo.adapters.openclaw import OpenClawMemoryBackend` |

---

## API Reference

### REST Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/memory/write` | Write a memory |
| `POST` | `/memory/recall` | Recall relevant memories |
| `POST` | `/memory/search` | Search memories (raw top-K) |
| `GET` | `/memory/scenes` | List all scenes |
| `DELETE` | `/memory/{id}` | Delete a memory |
| `POST` | `/memory/reconstruct` | Reconstruct narrative |
| `POST` | `/api/maintain` | Run maintenance |
| `GET` | `/api/stats` | Get statistics |
| `GET` | `/constitution` | Get constitution summary |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | API documentation |

### SDK Methods

```python
memory = Memory(db_path="openmemo.db")

memory.add(content, agent_id="", scene="", cell_type="fact")
memory.recall(query, agent_id="", scene="", top_k=10, budget=2000)
memory.search(query, agent_id="", top_k=10)
memory.reconstruct(query, agent_id="")
memory.scenes(agent_id="")
memory.delete(memory_id)
memory.maintain()
memory.stats()
```

---

## Cookbooks

See `cookbooks/` for complete examples:

- `coding_assistant.py` — Programming assistant with project context
- `customer_support.py` — Support agent with customer history
- `personal_memory.py` — Personal assistant with evolving knowledge

---

## Comparison

| | Vector DB | Chat History | **OpenMemo** |
|---|---|---|---|
| Structure | Flat embeddings | Flat log | **Hierarchical (MemCell + MemScene)** |
| Conflict handling | None | None | **Automatic detection + resolution** |
| Evolution | Append-only | Append-only | **Consolidate, promote, forget** |
| Recall | Top-K similarity | Last N messages | **Hybrid retrieval + reconstructive recall** |
| Token control | Fixed window | Grows forever | **Pyramid auto-compression** |
| Agent isolation | Manual | None | **Built-in agent_id** |
| Governance | None | None | **Built-in maintenance** |

---

## Installation

### From PyPI

```bash
pip install openmemo           # Core SDK
pip install "openmemo[server]" # With REST server
```

### From GitHub

```bash
pip install git+https://github.com/openmemoai/openmemo.git
```

### Development

```bash
git clone https://github.com/openmemoai/openmemo.git
cd openmemo
pip install -e ".[dev]"
pytest tests/
```

---

## Contributing

We welcome community contributions.

Good areas for contribution include:

- New adapters for AI frameworks
- Example cookbooks
- Storage backends
- Documentation improvements

Core memory engine changes require review by the maintainers.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

OpenMemo is released under the **Apache License 2.0**.

See the [LICENSE](LICENSE) file for full details.

---

## Community

OpenMemo is an early-stage project exploring long-term memory for AI systems.

Feedback, ideas, and contributions are welcome.
