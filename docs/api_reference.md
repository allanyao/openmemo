# API Reference

## Python SDK

### Memory

The main entry point.

```python
from openmemo import Memory

memory = Memory(db_path="my_agent.db")
```

#### memory.add(content, source, metadata) -> str
Add a new memory. Returns note ID.

```python
note_id = memory.add("User prefers dark mode", source="conversation")
```

#### memory.recall(query, top_k, budget) -> List[dict]
Recall relevant memories.

```python
results = memory.recall("user preference", top_k=5, budget=1000)
for r in results:
    print(r["content"], r["score"])
```

#### memory.reconstruct(query, max_sources) -> dict
Generate a narrative from memory.

```python
result = memory.reconstruct("What do I know about the user?")
print(result["narrative"])
```

#### memory.maintain() -> dict
Run maintenance (pyramid compression, skill extraction).

```python
result = memory.maintain()
```

#### memory.stats() -> dict
Get memory statistics.

```python
stats = memory.stats()
print(f"Notes: {stats['notes']}, Cells: {stats['cells']}")
```

---

## REST API

Start the server:

```bash
python -m openmemo.api.rest_server
```

### POST /api/memories
Add a memory.

```json
{"content": "User prefers dark mode", "source": "api"}
```

### POST /api/memories/recall
Recall memories.

```json
{"query": "user preference", "top_k": 5}
```

### POST /api/memories/reconstruct
Reconstruct narrative.

```json
{"query": "What do I know about the user?"}
```

### POST /api/maintain
Run maintenance.

### GET /api/stats
Get statistics.
