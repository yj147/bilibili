# Directory Structure

> How backend code is organized in the Bili-Sentinel project.

---

## Overview

The backend is a **FastAPI** application using **aiosqlite** for persistence. Code is organized into clear layers: API routes → Services → Database, with a separate `core/` layer for external Bilibili API integration.

---

## Directory Layout

```
backend/
├── main.py                 # FastAPI app entry point, lifespan, router registration
├── config.py               # Environment variables and constants (paths, delays, UA list)
├── database.py             # Singleton aiosqlite connection with asyncio.Lock
├── logger.py               # Centralized logging (stdlib logging, stdout handler)
├── auth.py                 # API key authentication dependency (X-API-Key header)
├── middleware.py            # Unified exception handlers (HTTP, validation, catch-all)
│
├── api/                    # FastAPI routers (thin controllers)
│   ├── __init__.py
│   ├── accounts.py         # /api/accounts — CRUD + cookie check
│   ├── targets.py          # /api/targets — CRUD + batch + status filter
│   ├── reports.py          # /api/reports — execute single/batch, logs
│   ├── autoreply.py        # /api/autoreply — config CRUD + start/stop service
│   ├── scheduler.py        # /api/scheduler — task CRUD + toggle + history
│   ├── config.py           # /api/config — system key-value config
│   └── websocket.py        # /ws/logs — real-time log broadcasting
│
├── services/               # Business logic layer
│   ├── __init__.py
│   ├── account_service.py  # Account CRUD + cookie validation
│   ├── target_service.py   # Target CRUD + status transitions
│   ├── report_service.py   # Report execution orchestration
│   ├── autoreply_service.py # Auto-reply polling loop + CRUD
│   ├── scheduler_service.py # APScheduler integration + task management
│   └── config_service.py   # System config get/set (key-value store)
│
├── models/                 # Pydantic models (LEGACY — being replaced by schemas/)
│   ├── __init__.py
│   ├── account.py
│   ├── target.py
│   ├── report.py
│   └── task.py
│
├── schemas/                # Pydantic request/response schemas (CANONICAL)
│   ├── __init__.py
│   ├── account.py          # AccountCreate, AccountUpdate, AccountResponse
│   ├── target.py           # TargetCreate, TargetUpdate, TargetResponse, TargetListResponse
│   ├── report.py           # ReportExecuteRequest, ReportLogResponse, etc.
│   ├── config.py           # ConfigValue
│   └── task.py             # ScheduledTask + AutoReply schemas
│
├── core/                   # External API integration (Bilibili-specific)
│   ├── __init__.py
│   ├── bilibili_client.py  # HTTP client with anti-detection, retry, rate-limit handling
│   ├── bilibili_auth.py    # Cookie/credential management per account
│   └── wbi_sign.py         # WBI signature algorithm for Bilibili API
│
├── db/                     # Database schema
│   ├── __init__.py
│   └── schema.sql          # SQLite DDL (CREATE TABLE IF NOT EXISTS)
│
└── tests/                  # Test suite
    ├── __init__.py
    ├── conftest.py          # Shared fixtures (in-memory DB, monkeypatched paths)
    ├── test_health.py
    └── test_report_stress.py
```

---

## Module Organization

### Layer Rules

1. **`api/`** — Thin routers. Parse request, call service, return response. No business logic.
2. **`services/`** — All business logic. Calls `database.py` functions directly. May call `core/` for external APIs.
3. **`schemas/`** — Pydantic models for request validation and response serialization. Separated into Request and Response sections.
4. **`core/`** — Bilibili API client and auth. Used only by services.
5. **`database.py`** — Raw SQL execution. No ORM. Functions: `execute_query`, `execute_insert`, `execute_many`.

### Import Direction

```
api/ → services/ → database.py
                 → core/
```

- `api/` imports from `services/` and `schemas/` (or `models/` for legacy code)
- `services/` imports from `database`, `core/`, and `logger`
- `core/` imports from `config` only
- **Exception**: `services/` may import `api.websocket.broadcast_log` for real-time updates

### models/ vs schemas/ (Migration in Progress)

- `models/` is the **legacy** location for Pydantic models
- `schemas/` is the **new canonical** location with proper Request/Response separation
- API routes currently import from `models/` — migrate to `schemas/` over time
- **New code should always use `schemas/`**

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|---------|
| Files | `snake_case.py` | `report_service.py` |
| API routers | Plural noun matching resource | `accounts.py`, `targets.py` |
| Service modules | `{resource}_service.py` | `target_service.py` |
| Schema modules | `{resource}.py` in `schemas/` | `schemas/target.py` |
| Core modules | `bilibili_{purpose}.py` | `bilibili_client.py` |

---

## Adding a New Feature

1. Create schema in `schemas/{resource}.py` with Request and Response classes
2. Create service in `services/{resource}_service.py` with business logic
3. Create router in `api/{resource}.py` — keep thin
4. Register router in `main.py` with `app.include_router()`
5. Add DB table in `db/schema.sql` if needed

---

## Anti-Patterns to Avoid

1. **Direct DB calls from `api/` layer**

```python
# Bad (in api/*.py)
from backend.database import execute_query
rows = await execute_query("SELECT * FROM accounts")
```

```python
# Good
from backend.services.account_service import list_accounts
rows = await list_accounts()
```

2. **Putting new request/response models in `models/`**
- `models/` is legacy compatibility only.
- New contracts go to `schemas/` with explicit Request/Response separation.

3. **Importing `api/` modules from services**
- Forbidden except `api.websocket.broadcast_log` integration.
- Keep dependency direction one-way: `api -> services -> database/core`.
