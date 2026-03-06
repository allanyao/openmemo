# OpenMemo

**The Memory Architecture for AI Systems.**

Most AI memory systems today are just wrappers around vector databases.

OpenMemo is different.

Instead of storing memory as flat embeddings, OpenMemo introduces a structured memory architecture designed for long-running AI systems.

```
MemCell → MemScene → Memory Pyramid → Reconstructive Recall
```

OpenMemo enables AI agents to remember, evolve, and reason over past experience — rather than simply retrieving text chunks.

---

## Why Another Memory System?

Most AI memory systems today work like this:

```
Store → Embed → Similarity Search → Inject Context
```

This approach works for small contexts but breaks when AI systems run for long periods.

Problems that appear in real systems:

- Memory becomes noisy
- Conflicting facts accumulate
- Context windows explode
- Past reasoning is lost
- Experience cannot evolve

OpenMemo was built to solve these problems.

---

## The OpenMemo Memory Model

OpenMemo introduces a structured memory architecture.

Instead of treating memory as documents, OpenMemo treats memory as **cognitive units**.

```
MemCell
   ↓
MemScene
   ↓
Memory Pyramid
   ↓
Reconstructive Recall
```

---

## MemCell — Atomic Memory

MemCell is the smallest unit of memory.

Each memory is structured rather than stored as raw text.

```
type: preference
subject: user
object: PostgreSQL
context: production database
confidence: 0.92
timestamp: 2026-01-01
```

MemCell allows the system to:

- Detect conflicts
- Update beliefs
- Track evolution

---

## MemScene — Contextual Memory

Memories rarely exist in isolation.

OpenMemo groups related memories into **MemScenes**.

```
coding_scene
research_scene
project_scene
```

Scenes dramatically reduce retrieval noise and improve reasoning quality.

---

## Memory Pyramid — Hierarchical Memory

Long-running systems accumulate huge amounts of data.

OpenMemo organizes memory hierarchically:

```
L0  Profile Memory
L1  Category Memory
L2  Episodic Memory
L3  Raw Events
```

This allows OpenMemo to load only the most relevant information.

Benefits:

- Reduces token usage
- Faster recall
- Better reasoning

---

## Reconstructive Recall

Traditional memory systems simply retrieve text.

OpenMemo does something different. It **reconstructs** memory.

```
retrieve → resolve → reconstruct
```

Instead of returning raw chunks, OpenMemo rebuilds a coherent narrative of past events.

This enables AI systems to answer questions like:

- *Why did we choose this approach earlier?*
- *What caused the previous failure?*
- *What solution worked last time?*

---

## Memory Governance

Long-running AI systems suffer from memory entropy.

OpenMemo introduces governance mechanisms to keep memory healthy:

- Conflict detection
- Memory evolution
- Maintenance workers
- Duplicate cleanup

This ensures memory remains reliable over time.

---

## Quickstart

### Option 1: Install from PyPI

```bash
pip install openmemo
```

```python
from openmemo import Memory

memory = Memory()

memory.add("User prefers PostgreSQL for production")

result = memory.recall("What database does the user prefer?")

print(result)
```

### Option 2: Cloud API (no installation needed)

```bash
# Add a memory
curl -X POST https://api.openmemo.ai/api/memories \
  -H "Content-Type: application/json" \
  -d '{"content": "User prefers PostgreSQL for production"}'

# Recall
curl -X POST https://api.openmemo.ai/api/memories/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "What database does the user prefer?"}'
```

### Option 3: Install from GitHub

```bash
pip install git+https://github.com/openmemoai/openmemo.git
```

### Option 4: Self-hosted REST Server

```bash
pip install "openmemo[server]"
python -m openmemo.api.rest_server
```

---

## Example: Long-Running Agent

OpenMemo enables agents to accumulate experience:

```python
memory.add("Bug fix: TypeError caused by missing config")

# Over time, agents develop reusable knowledge
skills = memory.maintain()
```

---

## Architecture

```
Applications
      │
      ▼
OpenMemo SDK
      │
      ▼
OpenMemo Core
  ├── MemCell Engine
  ├── Scene Manager
  ├── Memory Pyramid
  ├── Recall Engine
  ├── Reconstruct Engine
  └── Governance Layer
```

---

## Ecosystem

OpenMemo is designed to power a wide range of AI systems:

- AI agents
- Developer copilots
- Research assistants
- Customer support systems
- AI hardware devices

Adapters can be built for:

- OpenClaw
- LangGraph
- CrewAI
- Custom Agents

---

## Comparison

| | Vector DB | Chat History | **OpenMemo** |
|---|---|---|---|
| Structure | Flat embeddings | Flat log | **Hierarchical (MemCell + MemScene)** |
| Conflict handling | None | None | **Automatic detection + resolution** |
| Evolution | Append-only | Append-only | **Consolidate, promote, forget** |
| Recall | Top-K similarity | Last N messages | **Tri-brain + reconstructive recall** |
| Token control | Fixed window | Grows forever | **Pyramid auto-compression** |
| Governance | None | None | **Built-in maintenance** |

---

## Use Cases

OpenMemo is useful for systems that require long-term memory:

- Long-running AI agents
- Developer assistants
- Research systems
- Enterprise knowledge systems
- AI hardware devices

---

## Examples

See the `examples/` directory:

```
examples/
  coding_agent_demo/
  research_agent/
  memory_stress_test/
```

---

## Installation

Clone the repository:

```bash
git clone https://github.com/openmemoai/openmemo.git
cd openmemo
pip install -e .
```

Run the demo:

```bash
python examples/memory_stress_test/run_demo.py
```

---

## Philosophy

Memory is not storage.

Memory is a **system**.

To build reliable AI systems, we need more than vector databases.

We need a **memory architecture**.

---

## Roadmap

Upcoming features:

- Agent adapters
- Multi-agent memory
- Memory governance dashboards
- Hardware integrations

---

## Contributing

We welcome community contributions.

Good areas for contribution include:

- New integrations
- Adapters for AI frameworks
- Example cookbooks
- Documentation improvements

Core memory engine changes require review by the maintainers to maintain architectural consistency.

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## License

OpenMemo is released under the **AGPLv3 License**.

This allows anyone to use and modify the software, while ensuring that modifications deployed as a service remain open source.

See the [LICENSE](LICENSE) file for full details.

---

## Community

OpenMemo is an early-stage project exploring long-term memory for AI systems.

Feedback, ideas, and contributions are welcome.
