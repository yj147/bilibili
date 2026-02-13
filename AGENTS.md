<!-- TRELLIS:START -->
# Trellis Instructions

These instructions are for AI assistants working in this project.

Use the `/trellis:start` command when starting a new session to:
- Initialize your developer identity
- Understand current project context
- Read relevant guidelines

Use `@/.trellis/` to learn:
- Development workflow (`workflow.md`)
- Project structure guidelines (`spec/`)
- Developer workspace (`workspace/`)

Keep this managed block so 'trellis update' can refresh the instructions.

<!-- TRELLIS:END -->

---

# Bili-Sentinel Agent Guide

> Comprehensive guide for AI agents working on the Bili-Sentinel codebase.

---

## Project Overview

**Bili-Sentinel** is a Bilibili automation/management tool with:
- **Backend**: FastAPI (Python 3.12+) with SQLite
- **Frontend**: Next.js 16 / React 19 / TypeScript
- **Purpose**: Manage Bilibili accounts, targets (videos/comments/users) for reporting, auto-reply, and scheduled tasks

---

## Quick Start for Agents

### 1. Read This First

```bash
# Project instructions
cat CLAUDE.md

# Backend architecture
cat backend/AGENTS.md

# Frontend architecture
cat frontend/AGENTS.md

# Development guidelines
cat .trellis/spec/backend/index.md
cat .trellis/spec/frontend/index.md
```

### 2. Common Commands

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1
pytest backend/tests/

# Frontend
cd frontend
bun install
bun run dev
bun run lint
```

### 3. Critical Constraints

- **Single worker only** (`--workers 1`) - SQLite singleton connection
- **WBI keys refresh** every 1 hour (background task)
- **Account cooldown** 90s between reports per account
- **Comment report reasons** only support `reason_id` 1-9

---

## Architecture Overview

### Data Flow

```
Next.js Page → SWR hook (lib/swr.ts) → fetch with auth (lib/api.ts)
  → Next.js API proxy (app/api/[...path]/route.ts)
    → FastAPI router (backend/api/) → Service (backend/services/)
      → SQLite (backend/database.py) / Bilibili API (backend/core/)
```

### Backend Layers

```
api/ (thin routers) → services/ (business logic) → database.py (raw SQL)
                                                  → core/ (Bilibili API)
```

### Frontend Structure

**Pages** (all client-side rendered):
- `/` - Dashboard (overview, charts, logs)
- `/accounts` - Account management, QR login
- `/targets` - Report targets (videos/comments/users)
- `/autoreply` - Auto-reply configuration
- `/scheduler` - Scheduled tasks
- `/config` - System configuration

---

## Type Boundaries

| Boundary | Convention |
|----------|------------|
| Frontend ↔ Backend | Manual sync: `lib/types.ts` mirrors `backend/schemas/` |
| Dates | Python datetime → JSON ISO string → TS string |
| JSON columns | SQLite TEXT → Python dict → TS `Record<string, unknown>` |
| Booleans | SQLite INTEGER (0/1) → Python bool → JSON true/false |
| Pagination | `{ items, total, page, page_size }` contract |

---

## Common Gotchas

### 1. SQLite Singleton Connection
- **MUST** use `--workers 1` (enforced in lifespan)
- All DB operations use `asyncio.Lock` for concurrency safety

### 2. WBI Signature Refresh
- Keys expire after 1 hour
- Auto-refresh runs in background task

### 3. Account Cooldown
- 90s cooldown between reports per account
- Tracked in `_account_last_report` dict

### 4. Comment Report Reason Validation
- B站 API only supports `reason_id` values 1-9
- Values 10+ return error code 12012

### 5. Fire-and-Forget Status Management
- Long operations use `asyncio.create_task()` with HTTP 202
- **MUST** wrap in try-except to rollback status on failure

### 6. Circuit Breaker for Retries
- `MAX_RETRY_COUNT = 3` prevents infinite loops
- Targets exceeding max retries marked as "failed"

---

## Error Handling

| Code | Meaning | Action |
|------|---------|--------|
| -412 | Rate limit | Exponential backoff |
| -352 | Risk control | Fail fast, account flagged |
| -101 | Not logged in | Mark account invalid |
| -799 | Human verification | Stop immediately |

---

## Next Steps

1. **Backend work**: Read `backend/AGENTS.md`
2. **Frontend work**: Read `frontend/AGENTS.md`
3. **Cross-layer work**: Read `.trellis/spec/guides/cross-layer-thinking-guide.md`

---

## Resources

- **Backend Guidelines**: `.trellis/spec/backend/index.md`
- **Frontend Guidelines**: `.trellis/spec/frontend/index.md`
- **Workflow**: `.trellis/workflow.md`
- **Project Instructions**: `CLAUDE.md`
