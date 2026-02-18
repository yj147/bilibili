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

**Automated Sync (Recommended)**:
1. Update Pydantic schema in `backend/models/`
2. Run `python3 scripts/sync-types.py` to auto-generate TypeScript types
3. TypeScript compiler validates the generated types

**Manual Sync (Legacy)**:
1. Update Pydantic schema in `backend/models/`
2. Manually mirror change in `frontend/src/lib/types.ts`
3. TypeScript compiler flags mismatches

> **Best Practice**: Use `scripts/sync-types.py` to automatically generate TypeScript interfaces from Pydantic models. This eliminates manual sync errors and ensures perfect type alignment between frontend and backend.

---

## Real Code Examples

1. **Literal unions mirror backend constraints**

```typescript
// frontend/src/lib/types.ts
export type TargetStatus = "pending" | "processing" | "completed" | "failed";
export type TargetType = "video" | "comment" | "user";
```

2. **Nullable vs optional fields**

```typescript
// Generated from backend Pydantic models
export interface AccountPublic {
  uid: number | null;
  buvid3: string | null;
  last_check_at: string | null;
}

export interface AccountUpdate {
  name?: string | null;
  is_active?: boolean | null;
}
```

3. **Paged response contract matches backend**

```typescript
export interface TargetListResponse {
  items: Target[];
  total: number;
  page: number;
  page_size: number;
}
```

These map to backend models in `backend/models/target.py` and are synced by `scripts/sync-types.py`.

---

## Common Mistakes

1. **Using `any`** — use proper typed interfaces instead
2. **Forgetting null checks** — use `account.uid ?? '---'` not `account.uid.toString()`
3. **Assuming dates are Date objects** — backend returns ISO strings, use `new Date(str)`
