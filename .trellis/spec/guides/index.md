# Thinking Guides

> Guides to help think through complex development scenarios.

---

## Available Guides

| Guide | Description | Status |
|-------|-------------|--------|
| [Cross-Layer Thinking Guide](./cross-layer-thinking-guide.md) | Data flow analysis across boundaries | Done |
| [Code Reuse Thinking Guide](./code-reuse-thinking-guide.md) | When and how to extract shared code | Existing |

---

## Project-Specific Cross-Layer Notes

### Data Flow: Frontend to Backend

```
Next.js Page
  -> SWR hook (lib/swr.ts)
    -> fetch with auth (lib/api.ts)
      -> Next.js API proxy (app/api/[...path]/route.ts)
        -> FastAPI router (backend/api/)
          -> Service (backend/services/)
            -> SQLite (backend/database.py)
            -> Bilibili API (backend/core/)
```

### Key Boundaries

| Boundary | Format |
|----------|--------|
| Frontend types vs Backend schemas | Manual sync (types.ts vs schemas/*.py) |
| Dates | Python datetime -> JSON ISO string -> TS string |
| JSON columns | SQLite TEXT -> Python dict -> TS Record<string, unknown> |
| Booleans | SQLite INTEGER (0/1) -> Python bool -> JSON true/false |
| Pagination | `{ items, total, page, page_size }` contract |

### Common Cross-Layer Gotchas

#### Gotcha: Global Statistics vs Pagination Filtering

**Problem**: Frontend calculates statistics from paginated data, showing incorrect totals.

**Symptom**: Statistics show "20 total targets" when there are actually 396 in the database.

**Cause**: Frontend filters `targetData?.items` (only 20 items from current page) instead of querying global statistics.

```typescript
// Bad — statistics from paginated data
const { data: targetData } = useTargets({ page: 1, page_size: 20 });
const total = targetData?.items.length ?? 0;  // Always ≤20!
```

**Solution**: Add dedicated backend endpoint for global statistics, fetch separately from paginated data.

```python
# Backend: Add /stats endpoint
@router.get("/stats")
async def get_targets_stats():
    rows = await execute_query("SELECT status, COUNT(*) as count FROM targets GROUP BY status")
    return {"total": sum(...), "pending": ..., "completed": ...}
```

```typescript
// Frontend: Fetch global stats separately
const { data: stats } = useSWR('/targets/stats', fetcher);
const { data: targetData } = useTargets({ page: 1, page_size: 20 });
```

**Why**: Pagination is for UI display; statistics require aggregation across ALL records.
