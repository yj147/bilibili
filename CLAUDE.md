# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Bili-Sentinel is a Bilibili automation/management tool with a FastAPI backend and Next.js frontend. It manages Bilibili accounts, targets (videos/comments/users) for reporting, auto-reply, and scheduled tasks.

## Commands

### Backend
```bash
# Install dependencies (uses venv at .venv/)
pip install -r backend/requirements.txt

# Run backend (MUST use --workers 1 due to SQLite singleton connection)
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1

# Run backend with auto-reload
python -m backend.main

# Run tests
pytest backend/tests/

# Run a single test
pytest backend/tests/test_health.py -v
```

### Frontend
```bash
cd frontend
bun install
bun run dev      # Development server
bun run build    # Production build
bun run lint     # ESLint
```

## Architecture

### Backend (Python 3.12+ / FastAPI)

Layered architecture with strict import direction:

```
api/ (thin routers) → services/ (business logic) → database.py (raw SQL)
                                                  → core/ (Bilibili API client)
```

- **`main.py`** — App entry, lifespan (init DB, refresh WBI keys, start scheduler), router registration. All routes require `X-API-Key` header when `SENTINEL_API_KEY` env is set.
- **`database.py`** — Singleton `aiosqlite` connection with `asyncio.Lock`. Three functions: `execute_query`, `execute_insert`, `execute_many`. All return `list[dict]` or `int`.
- **`config.py`** — Environment variables (`SENTINEL_*`), anti-detection delays, UA list. Data stored at `data/sentinel.db`.
- **`middleware.py`** — Unified exception handlers (HTTP, validation, unhandled).
- **`auth.py`** — API key verification via `X-API-Key` header.
- **`core/bilibili_client.py`** — HTTP client wrapping `httpx.AsyncClient` with retry logic, WBI signing, and Bilibili error code handling (-412 rate limit, -352 risk control, -101 not logged in).
- **`core/bilibili_auth.py`** — Cookie/credential management, WBI key refresh, QR login flow.
- **`core/wbi_sign.py`** — WBI request signing algorithm.
- **`db/schema.sql`** — Idempotent SQLite DDL (CREATE IF NOT EXISTS). Tables: `accounts`, `targets`, `report_logs`, `autoreply_config`, `scheduled_tasks`, `system_config`, `autoreply_state`.
- **`models/`** — Dataclass-style models for DB rows and Pydantic models for request/response validation.
- **`services/`** — Business logic (account_service, target_service, report_service, scheduler_service, autoreply_service, auth_service, config_service).

API routes are mounted at `/api/<resource>` (e.g., `/api/accounts`, `/api/targets`). WebSocket endpoint at `/ws/logs` for real-time log streaming.

**Critical constraint**: Single worker only (`--workers 1`) because SQLite uses a singleton connection with asyncio.Lock.

### Frontend (Next.js 16 / React 19 / TypeScript)

- **`src/app/api/[...path]/route.ts`** — Catch-all API proxy forwarding all `/api/*` requests to `http://127.0.0.1:8000` (the backend). Frontend never calls Bilibili directly.
- **`src/lib/api.ts`** — Typed API client with `X-API-Key` auth header. Exports `api` object with namespaced methods (accounts, targets, reports, autoreply, auth, scheduler, config).
- **`src/lib/swr.ts`** — SWR hooks per resource (useAccounts, useTargets, useReportLogs, useTargetStats, etc.).
- **`src/lib/types.ts`** — TypeScript interfaces manually synced with backend `models/`. Must be kept in sync.
- **`src/lib/websocket.ts`** — `useLogStream` hook for real-time WebSocket log streaming.
- **`src/components/`** — Shared components (Sidebar, BentoCard, StatItem, ErrorBoundary, QRLoginModal, Toast) plus `ui/` directory with shadcn/ui primitives.
- **`src/app/`** — Page routes: dashboard (`page.tsx`), accounts, targets, autoreply, scheduler, config.

Styling: Tailwind CSS 4, dark theme, cyberpunk aesthetic with glassmorphism effects. Uses Framer Motion for animations.

### Data Flow

```
Next.js Page → SWR hook (lib/swr.ts) → fetch with auth (lib/api.ts)
  → Next.js API proxy (app/api/[...path]/route.ts)
    → FastAPI router (backend/api/) → Service (backend/services/)
      → SQLite (backend/database.py) / Bilibili API (backend/core/)
```

### Type Boundaries

| Boundary | Convention |
|----------|------------|
| Frontend ↔ Backend | Manual sync: `lib/types.ts` mirrors `backend/models/` |
| Dates | Python datetime → JSON ISO string → TS string |
| JSON columns | SQLite TEXT → Python dict → TS `Record<string, unknown>` |
| Booleans | SQLite INTEGER (0/1) → Python bool → JSON true/false |
| Pagination | `{ items, total, page, page_size }` contract |

### Environment Variables

- `SENTINEL_API_KEY` — API authentication key (empty = auth disabled)
- `SENTINEL_HOST` / `SENTINEL_PORT` — Server bind (default: 0.0.0.0:8000)
- `SENTINEL_DEBUG` — Enable reload (default: true)
- `SENTINEL_HTTP_TIMEOUT` — httpx timeout (default: 10.0s)
- `SENTINEL_MAX_RETRIES` — Request retry count (default: 3)
- `NEXT_PUBLIC_API_BASE` — Frontend API base URL (default: /api)
- `NEXT_PUBLIC_API_KEY` — Frontend API key for X-API-Key header

## Testing

### Running Tests
```bash
# Backend tests
pytest backend/tests/ -v

# Frontend tests (if available)
cd frontend && npm test
```

### Test Coverage Requirements
- All service functions must have unit tests
- API routes must have integration tests
- Critical paths (report flow, auth, auto-reply) require E2E tests
- Test data should not use real Bilibili credentials

## Common Gotchas

### SQLite Singleton Connection
- **MUST** use `--workers 1` (enforced in lifespan with warning)
- All DB operations use `asyncio.Lock` for concurrency safety
- WAL mode enabled for better read concurrency

### WBI Signature Refresh
- Keys expire after 1 hour (checked via `wbi_keys_stale()`)
- Auto-refresh runs in background task every hour
- Manual refresh: `await auth.refresh_wbi_keys()`

### Account Cooldown
- 90s cooldown between reports per account (`ACCOUNT_COOLDOWN`)
- Tracked in `_account_last_report` dict in `report_service.py`
- Cleanup runs periodically (`_cleanup_stale_cooldowns()`) to prevent memory leaks

### Type Synchronization
- Frontend types in `lib/types.ts` must match backend `models/`
- **Use `python scripts/sync-types.py` to auto-generate types**
- Never manually edit generated types (marked with auto-gen comment)

### Comment Report Reason Validation
- B站 comment report API only supports `reason_id` values 1-9
- Values 10+ (e.g., 11 = 涉政敏感) return error code 12012
- Pydantic validator in `models/target.py` enforces this at input time
- Runtime fallback in `report_service.py` defaults to 4 (赌博诈骗)

### Fire-and-Forget Status Management
- Long-running operations use `asyncio.create_task()` with HTTP 202 response
- **MUST** wrap task creation in try-except to rollback status on failure
- Example: If task creation fails after marking "processing", rollback to "pending"

### Circuit Breaker for Retries
- `MAX_RETRY_COUNT = 3` prevents infinite retry loops
- `retry_count` field tracked in `targets` table
- Targets exceeding max retries are marked as "failed"

## Error Handling

### Backend
- Use `HTTPException` for API errors with appropriate status codes
- Unified exception handlers in `middleware.py` (HTTP, validation, unhandled)
- Log errors with `logger.error()`, **never** `print()`
- Bilibili API error codes:
  - `-412`: Rate limit (exponential backoff)
  - `-352`: Risk control (fail fast, account flagged)
  - `-101`: Not logged in (mark account invalid)
  - `-799`: Human verification required (stop immediately)

### Frontend
- Use `ErrorBoundary` component for React errors
- Display user-friendly messages via `Toast` component
- Log errors to console in development only
- Handle API errors with proper status code checks
