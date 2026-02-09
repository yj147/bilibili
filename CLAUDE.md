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
npm install
npm run dev      # Development server
npm run build    # Production build
npm run lint     # ESLint
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
- **`models/`** — Dataclass-style models for DB rows.
- **`schemas/`** — Pydantic models for request/response validation.
- **`services/`** — Business logic (account_service, target_service, report_service, scheduler_service, autoreply_service, auth_service, config_service).

API routes are mounted at `/api/<resource>` (e.g., `/api/accounts`, `/api/targets`). WebSocket endpoint at `/ws/logs` for real-time log streaming.

**Critical constraint**: Single worker only (`--workers 1`) because SQLite uses a singleton connection with asyncio.Lock.

### Frontend (Next.js 16 / React 19 / TypeScript)

- **`src/app/api/[...path]/route.ts`** — Catch-all API proxy forwarding all `/api/*` requests to `http://127.0.0.1:8000` (the backend). Frontend never calls Bilibili directly.
- **`src/lib/api.ts`** — Typed API client with `X-API-Key` auth header. Exports `api` object with namespaced methods (accounts, targets, reports, autoreply, auth, scheduler, config).
- **`src/lib/swr.ts`** — SWR hooks per resource (useAccounts, useTargets, useReportLogs, etc.).
- **`src/lib/types.ts`** — TypeScript interfaces manually synced with backend `schemas/`. Must be kept in sync.
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
| Frontend ↔ Backend | Manual sync: `lib/types.ts` mirrors `backend/schemas/` |
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
