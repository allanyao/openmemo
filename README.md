# OpenMemo

OpenMemo gives AI systems long-term memory.

OpenMemo is an open-source memory layer designed for AI agents, assistants, and AI-driven workflows.
Instead of storing information as plain text, OpenMemo structures knowledge so AI systems can remember, resolve conflicts, and retrieve reliable facts over time.

---

## Why OpenMemo

Most AI systems forget.

Traditional prompts only hold temporary context. Once a session ends, information disappears or becomes inconsistent.

OpenMemo solves this by providing a structured memory layer that allows AI systems to:

- Store knowledge persistently
- Resolve conflicting information
- Recall updated facts
- Build long-term contextual understanding

**Without OpenMemo:**
AI tools rely on short prompts and lose context quickly.

**With OpenMemo:**
AI systems maintain structured memory that evolves over time.

---

## Demo

Below is a simple example showing how OpenMemo handles conflicting information and reconstructs the latest truth.

```python
from openmemo import Memory

memory = Memory()

memory.add("User prefers dark mode")
memory.add("User changed preference to light mode")

results = memory.recall("What theme does the user prefer?")
print(results)
```

```
Output:
User preference: light mode
(conflict resolved from newer memory)
```

OpenMemo automatically detects conflicts and keeps the most reliable version of the knowledge.

---

## Key Features

- Structured memory storage for AI systems
- Conflict-aware knowledge updates
- Reliable memory recall
- Lightweight API for AI workflows
- Designed for AI agents and assistants

---

## Example Use Cases

OpenMemo can power memory for many AI applications:

- AI assistants that remember user preferences
- Customer support agents with persistent context
- Research tools that track evolving knowledge
- AI workflows that require reliable memory

---

## Built with OpenMemo

Example projects and cookbooks:

```
cookbooks/
  ai-assistant/
  customer-support/
  coding-agent/
```

These examples show how OpenMemo can be used as the memory layer for real AI systems.

---

## Integrations

OpenMemo is designed to work with existing AI frameworks.

Planned and upcoming integrations include:

- LangChain
- LlamaIndex
- Model Context Protocol (MCP)

---

## Getting Started

Clone the repository:

```bash
git clone https://github.com/openmemoai/openmemo.git
```

Install dependencies:

```bash
pip install -e .
```

Run the example:

```bash
python examples/memory_stress_test/run_demo.py
```

---

## Project Structure

```
openmemo/
  core/          # Memory engine
  storage/       # Storage backends
  pyramid/       # Memory compression
  skill/         # Skill extraction
  governance/    # Conflict detection
  api/           # SDK and REST server
cookbooks/       # Usage examples
docs/            # Architecture documentation
examples/        # Demo scripts
```

---

## Roadmap

Upcoming development plans:

- Knowledge graph visualization
- Memory summarization
- Advanced conflict resolution
- Distributed memory systems
- Agent-native memory APIs

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
