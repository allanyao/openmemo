# MemCell

## Overview

A MemCell is the atomic unit of structured memory in OpenMemo. It wraps raw notes with lifecycle management, importance scoring, and connection tracking.

## Lifecycle Stages

```
Exploration → Consolidation → Mastery → Dormant
```

- **Exploration**: New memory, < 3 accesses
- **Consolidation**: Active memory, 3-9 accesses
- **Mastery**: Well-established, 10+ accesses with high importance
- **Dormant**: Not accessed for 30+ days (unless Mastery stage)

## Fields

| Field | Type | Description |
|-------|------|-------------|
| id | string | Unique identifier |
| content | string | The memory content |
| facts | list | Extracted atomic facts |
| stage | enum | Lifecycle stage |
| importance | float | 0.0 - 1.0 importance score |
| access_count | int | Number of recalls |
| connections | list | Related MemCell IDs |

## Usage

```python
from openmemo.core.memcell import MemCell, LifecycleStage

cell = MemCell(content="User prefers Python")
cell.access()  # Updates count and stage
```
