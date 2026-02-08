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
