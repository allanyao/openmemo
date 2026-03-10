# OpenMemo Universal Adapter Layer

OpenMemo provides a Universal Adapter Layer that lets any AI agent framework integrate persistent memory with minimal code.

## Architecture

```
Agent Layer                    Adapter Layer                  OpenMemo Core
─────────────────             ─────────────────             ─────────────────
OpenClaw            →         OpenClawMemoryBackend   →
LangChain           →         OpenMemoMemory          →     MemCell Engine
CrewAI              →         CrewAIMemory            →     MemScene Engine
Claude MCP          →         OpenMemoMCPServer       →     Recall Engine
Any HTTP client     →         HTTPMemoryClient        →     Governance Layer
Custom agent        →         BaseMemoryAdapter       →
```

## Quick Start

```python
pip install openmemo
```

### OpenClaw

```python
from openmemo.adapters.openclaw import OpenClawMemoryBackend

backend = OpenClawMemoryBackend(agent_id="my_agent")

backend.write_memory("User prefers Python", scene="coding", memory_type="preference")
results = backend.recall_memory("programming language")
prompt = backend.inject_context("What language should I use?")
```

### LangChain

```python
from openmemo.adapters.langchain import OpenMemoMemory

memory = OpenMemoMemory(agent_id="lc_agent")

memory.save_context(
    {"input": "What database?"},
    {"output": "Use PostgreSQL."},
)

result = memory.load_memory_variables({"input": "database choice"})
```

### CrewAI

```python
from openmemo.adapters.crewai_adapter import CrewAIMemory

researcher = CrewAIMemory(agent_id="researcher", crew_id="dev_team")
coder = CrewAIMemory(agent_id="coder", crew_id="dev_team")

researcher.on_task_start("Research API design patterns")
researcher.on_task_complete("Research API design", "Use REST with OpenAPI")

coder.on_agent_action("coder", "Implemented REST API with Flask")
context = coder.inject_context("How should I build the API?")
```

### MCP (Claude)

```python
from openmemo.adapters.mcp import OpenMemoMCPServer

server = OpenMemoMCPServer()

tools = server.get_tools()

result = server.handle_tool("write_memory", {
    "content": "User prefers TypeScript",
    "scene": "coding",
    "memory_type": "preference",
})

result = server.handle_tool("recall_memory", {
    "query": "programming preferences",
})
```

### HTTP Client

```python
from openmemo.adapters.http_adapter import HTTPMemoryClient

client = HTTPMemoryClient(base_url="http://localhost:8765")

client.write_memory("Deploy using Docker Compose")
results = client.recall_memory("deployment strategy")
prompt = client.inject_context("How to deploy?")
```

## Uniform Interface

All adapters (except HTTP) inherit from `BaseMemoryAdapter` and share these methods:

| Method | Description |
|--------|-------------|
| `write_memory(content, scene, memory_type, confidence)` | Store a memory |
| `recall_memory(query, scene, limit)` | Search memories by query |
| `recall_context(query, scene, limit, mode)` | Get formatted context |
| `inject_context(prompt, query, scene, limit)` | Inject memories into prompt |
| `get_context(query, scene, limit)` | Get context as list |
| `list_scenes()` | List all memory scenes |
| `get_metrics()` | Get adapter performance metrics |
| `close()` | Clean up resources |

## Context Injection

All adapters support automatic context injection — prepending relevant memories to prompts before sending to the LLM:

```python
adapter.write_memory("User prefers Python backend", memory_type="preference")
adapter.write_memory("Deploy with Docker Compose", memory_type="constraint")

original = "How to deploy?"
injected = adapter.inject_context(original, query="deploy backend Docker")
```

Result:
```
Relevant memories:
1. Deploy with Docker Compose
2. User prefers Python backend

How to deploy?
```

## Connection Modes

Every adapter supports three connection modes:

### Local (default)
```python
adapter = OpenClawMemoryBackend(db_path="openmemo.db")
```

### Remote API
```python
adapter = OpenClawMemoryBackend(base_url="https://api.openmemo.ai", api_key="...")
```

### Injected Memory
```python
from openmemo import Memory
memory = Memory(db_path=":memory:")
adapter = OpenClawMemoryBackend(memory=memory)
```

## Logging

All adapters log operations via Python's `logging` module under the `openmemo` logger:

```
[openmemo:openclaw] write_memory scene=coding type=fact latency=12ms
[openmemo:openclaw] recall_memory query=Python scene=coding hits=3 latency=45ms
[openmemo:langchain] inject_context memories=2
```

## Metrics

Track adapter performance with built-in metrics:

```python
metrics = adapter.get_metrics()
# {
#     "writes": 10,
#     "recalls": 25,
#     "injections": 8,
#     "errors": 0,
#     "avg_write_ms": 15.2,
#     "avg_recall_ms": 42.7,
# }
```

## Error Handling

All adapters handle errors gracefully:

- **API timeout**: Returns empty results, logs warning
- **Invalid scene**: Falls back to default scene
- **Memory not found**: Returns empty list
- **Connection failure**: Skips memory, continues without blocking

## Building a Custom Adapter

Extend `BaseMemoryAdapter` for any framework:

```python
from openmemo.adapters.base_adapter import BaseMemoryAdapter

class MyFrameworkMemory(BaseMemoryAdapter):
    adapter_name = "my_framework"

    def on_step(self, step_data: dict):
        self.write_memory(
            content=step_data["output"],
            scene=step_data.get("scene", ""),
            memory_type="observation",
        )

    def prepare_prompt(self, prompt: str) -> str:
        return self.inject_context(prompt)
```
