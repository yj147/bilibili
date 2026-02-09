# Type Safety

> TypeScript type patterns in Bili-Sentinel frontend.

---

## Overview

- **TypeScript**: 5.9+
- **Types location**: `lib/types.ts` — all shared interfaces
- **Source of truth**: Backend Pydantic schemas, manually mirrored in `types.ts`

---

## Type Conventions

| Pattern | Convention |
|---------|----------|
| Entity types | PascalCase matching backend model |
| Create requests | `{Entity}Create` |
| Update requests | `Partial<{Entity}Create>` |
| List responses | `{Entity}ListResponse` with `items`, `total`, `page`, `page_size` |
| Nullable fields | `fieldName: Type \| null` |
| Optional fields | `fieldName?: Type` |
| Dates from backend | `string` (ISO format) |
| JSON fields | `Record<string, unknown> \| null` |

---

## Keeping Types in Sync

When backend schema changes:
1. Update Pydantic schema in `backend/models/`
2. Mirror change in `frontend/src/lib/types.ts`
3. TypeScript compiler flags mismatches

> **Warning**: Types are manually synced. No auto-generation. Always verify both sides.

---

## Common Mistakes

1. **Using `any`** — use proper typed interfaces instead
2. **Forgetting null checks** — use `account.uid ?? '---'` not `account.uid.toString()`
3. **Assuming dates are Date objects** — backend returns ISO strings, use `new Date(str)`
