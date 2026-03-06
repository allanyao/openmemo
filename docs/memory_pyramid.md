# Memory Pyramid

## Overview

The Memory Pyramid is a three-tier compression system that manages token budgets automatically.

## Tiers

### Short-term (< 24 hours)
- Raw notes and recent MemCells
- Full detail preserved
- Max 50 entries

### Mid-term (24 hours - 7 days)
- Category summaries
- Pattern aggregations
- Max 20 entries

### Long-term (> 7 days)
- Stable user profile
- Core knowledge
- Max 10 entries

## Promotion

When short-term overflows:
1. Oldest entries are batched (5 per group)
2. Summarizer compresses each batch
3. Summary is promoted to mid-term
4. Original entries are archived

## Token Budget

The `get_context()` method returns memories within a token budget:

```python
context = pyramid.get_context(budget=2000)
```

This ensures LLM context windows are never exceeded.
