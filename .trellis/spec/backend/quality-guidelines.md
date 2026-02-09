# Quality Guidelines

> Code quality standards for Bili-Sentinel backend.

---

## Overview

- **Python**: 3.12+
- **Framework**: FastAPI + uvicorn
- **Async**: All I/O operations are async (`async def`, `await`)
- **Type Hints**: Use for function signatures; Pydantic handles runtime validation
- **Single Worker**: The app must run with `--workers 1` (SQLite + singleton connection)

---

## Required Patterns

### 1. Thin API Routes

Routes should only: validate input → call service → return response.

```python
# Good — thin route
@router.get("/{target_id}", response_model=Target)
async def get_target(target_id: int):
    result = await target_service.get_target(target_id)
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    return result
```

### 2. Service Layer for Business Logic

All business logic (queries, orchestration, validation) belongs in `services/`.

### 3. Pydantic Schemas with Request/Response Separation

In `models/`, separate request models from response models:

```python
# Request schemas
class TargetCreate(BaseModel):
    type: TargetType
    identifier: str

# Response schemas
class TargetResponse(BaseModel):
    id: int
    type: TargetType
    identifier: str
    status: TargetStatus
    created_at: datetime

    class Config:
        from_attributes = True
```

### 4. Context Manager for BilibiliClient

Always use `async with` to prevent connection leaks:

```python
# Good
async with BilibiliClient(auth, account_index=0) as client:
    result = await client.report_video(...)

# Bad — may leak connections
client = BilibiliClient(auth, account_index=0)
result = await client.report_video(...)
```

### 5. Field Whitelist for Dynamic Updates

Always define `ALLOWED_UPDATE_FIELDS` when building dynamic SQL:

```python
ALLOWED_UPDATE_FIELDS = {"reason_id", "reason_text", "status"}
```

### 6. Anti-Detection Delays

Use `asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))` between Bilibili API calls.

### 7. Centralize Constants in config.py

All shared constants (e.g., `USER_AGENTS`, `MIN_DELAY`, `MAX_DELAY`) must be defined in `backend/config.py` and imported from there. Never duplicate constant lists across files.

```python
# Good — import from config
from backend.config import USER_AGENTS

# Bad — duplicate definition
USER_AGENTS = ["Mozilla/5.0 ...", ...]  # Already defined in config.py!
```

---

## Forbidden Patterns

### 1. Don't Put Business Logic in API Routes

```python
# Forbidden — SQL in route
@router.get("/")
async def list_targets():
    rows = await execute_query("SELECT * FROM targets")  # Wrong layer!
    return rows
```

### 2. Don't Use String Interpolation in SQL

```python
# Forbidden — SQL injection
await execute_query(f"SELECT * FROM targets WHERE id = {user_input}")
```

### 3. Don't Import API from Services

```python
# Forbidden (except broadcast_log)
from backend.api.reports import router  # circular dependency risk
```

### 4. Don't Use Multiple Workers

SQLite + singleton connection = single worker only.

### 5. Don't Leak Bilibili Credentials in Logs

Never log `sessdata`, `bili_jct`, or full cookie strings.

---

## Code Style

| Item | Convention |
|------|----------|
| Docstrings | One-line at module/function level, triple-quoted |
| Module docstring | Required — `"""Module purpose."""` |
| Type hints | Use `Optional[]`, `list[]`, `dict[]`, `Literal[]` |
| Imports | stdlib → third-party → local, separated by blank lines |
| Line length | Soft limit ~100 chars |
| String formatting | f-strings for code, `%s` for logger calls |

### Logger String Formatting

```python
# Good — lazy formatting (logger evaluates only if needed)
logger.info("Target %s status: %s", target_id, status)

# Acceptable but less efficient
logger.info(f"Target {target_id} status: {status}")
```

---

## Testing

### Test Setup

- Tests use `conftest.py` with monkeypatched `DATABASE_PATH` pointing to in-memory DB
- Test files: `backend/tests/test_*.py`
- Run: `pytest backend/tests/`

### What to Test

- Service functions (unit tests)
- API routes via FastAPI `TestClient`
- Edge cases: empty inputs, missing records, duplicate entries

---

## Pre-Commit Checklist

- [ ] No SQL injection (all queries parameterized)
- [ ] No credential leaks in logs or responses
- [ ] BilibiliClient used with `async with`
- [ ] Dynamic UPDATE uses field whitelist
- [ ] Anti-detection delays between Bilibili API calls
- [ ] New schemas in `models/` with request/response separation
- [ ] Constants defined once in `config.py`, not duplicated
- [ ] Schema changes: existing DBs need `ALTER TABLE` migration
- [ ] All `print()` in non-test code replaced with `logger`

---

## Bilibili Auth Gotchas

### Gotcha: buvid3/buvid4 Must Be Fetched After QR Login

QR login only returns `SESSDATA`, `bili_jct`, `DedeUserID`, `refresh_token`. The `buvid3`/`buvid4` cookies must be fetched separately via:

```
GET https://api.bilibili.com/x/frontend/finger/spi
```

Response:
```json
{"code": 0, "data": {"b_3": "buvid3_value", "b_4": "buvid4_value"}}
```

**Implementation**: Call `_fetch_buvid(sessdata, bili_jct)` in `auth_service.py` after QR login success, for both new and existing accounts.

**Why**: Without buvid, many Bilibili API calls return -352 (risk control) or -412 (rate limit).

### Gotcha: Cookie Refresh is Multi-Step

Cookie refresh is not a single API call. The full flow:
1. Generate `correspondPath` via `/x/web-interface/nav`
2. Call `/passport/login/refresh` with `refresh_token` + `correspondPath`
3. Confirm new token via `/passport/login/refresh/confirm`
4. Revoke old refresh token
5. Update all 6 cookie fields in DB

Each step can fail independently. The service must handle partial failures gracefully.

---

## Architectural Decisions

### auth_service Uses Raw httpx (Not BilibiliClient)

`auth_service.py` deliberately uses `httpx.AsyncClient` directly instead of `BilibiliClient` because:
- Passport endpoints (`passport.bilibili.com`) don't require WBI signing
- `BilibiliClient` requires an account index, but auth operations happen before/without an account
- The SPI endpoint for buvid fetching also doesn't need WBI

This is an intentional exception to the "use BilibiliClient for Bilibili API" pattern.

---

## Gotcha: FastAPI Route Ordering with Static + Dynamic Paths

When a router has both static paths (`/export`) and dynamic paths (`/{id}`), the **static routes must be defined BEFORE the dynamic routes**. Otherwise FastAPI matches `/export` as `id="export"` and returns a 422 validation error.

```python
# Good — static before dynamic
@router.get("/export")
async def export_accounts(): ...

@router.get("/{account_id}")
async def get_account(account_id: int): ...

# Bad — dynamic catches static
@router.get("/{account_id}")
async def get_account(account_id: int): ...

@router.get("/export")  # Never reached!
async def export_accounts(): ...
```

---

## Gotcha: Duplicate Background Service Prevention

When the same business logic (e.g., auto-reply polling) can run as both a standalone `asyncio.Task` and an APScheduler job, add mutual exclusion guards to prevent double execution:

```python
# In standalone service start
from backend.services.scheduler_service import get_scheduler
scheduler = get_scheduler()
if scheduler.running:
    for job in scheduler.get_jobs():
        if 'autoreply' in job.name.lower():
            return False  # Scheduler already handling this

# In scheduler job
from backend.services.autoreply_service import _autoreply_running
if _autoreply_running:
    return  # Standalone service already running
```

---

## Logger Level Configuration

Logger level is configurable via `SENTINEL_LOG_LEVEL` environment variable (default: `INFO`).

```bash
# Set to DEBUG for development
SENTINEL_LOG_LEVEL=DEBUG python -m backend.main
```

Valid values: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
