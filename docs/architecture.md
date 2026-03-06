# OpenMemo Architecture

## Overview

OpenMemo is a Memory Operating System designed for AI agents. It provides structured, evolving, and long-term memory that goes beyond simple chat history or vector retrieval.

## Core Pipeline

```
Input (text)
    |
    v
Note (raw storage)
    |
    v
AtomicFact Extraction
    |
    v
MemCell (structured unit)
    |
    v
MemScene (context grouping)
    |
    v
Memory Pyramid (compression)
```

## Recall Architecture

```
Query
  |
  +---> Fast Brain (BM25, ~5ms)
  |
  +---> Middle Brain (Embedding, ~50ms)
  |
  +---> Slow Brain (LLM, ~500ms, optional)
  |
  v
Merge & Rerank
  |
  v
Token Budget Control
  |
  v
Results
```

## Storage Layer

OpenMemo uses a pluggable storage backend:

- **SQLiteStore** (default): Zero-config local storage
- **BaseStore**: Interface for custom backends
- **VectorStore**: In-memory vector search (numpy)

## Governance

Memory quality is maintained through:

- **ConflictDetector**: Identifies contradictory facts
- **VersionManager**: Tracks how knowledge evolves

## Skill Engine

Repeated patterns in agent behavior are extracted into reusable skills:

1. Observe agent actions
2. Detect frequency patterns
3. Extract skills above threshold
4. Skills improve with usage feedback
