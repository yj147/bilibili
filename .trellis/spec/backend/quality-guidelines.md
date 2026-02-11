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

### 8. Account Filtering: Always Use `status='valid'`

When querying accounts for any operation that calls B站 API (reporting, scanning, etc.), always filter by `status = 'valid'` in addition to `is_active = 1`. Accounts with `status = 'expiring'` have invalid credentials and will fail with -352.

```python
# Good — filter by both is_active and status
await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status = 'valid'")

# Bad — includes expired/invalid accounts
await execute_query("SELECT * FROM accounts WHERE is_active = 1")
```

> **Gotcha**: This applies everywhere accounts are queried for B站 API calls — `account_service.get_active_accounts()`, direct SQL in `report_service`, and `scheduler_service`. Missing this in any one place causes fake accounts to be used.

### 9. Scheduler Must Delegate to Service Layer

Scheduler job functions must delegate to existing service functions instead of reimplementing business logic. This ensures all improvements (cooldown, retry, filtering) are applied consistently.

```python
# Good — delegate to service
async def _run_report_batch(task_id):
    result, error = await execute_batch_reports(target_ids=None, account_ids=None)

# Bad — duplicate logic in scheduler
async def _run_report_batch(task_id):
    targets = await execute_query("SELECT * FROM targets WHERE status = 'pending'")
    for target in targets:
        for account in accounts:
            await execute_single_report(target, account)  # Missing cooldown, retry, etc.
```

### 10. Fire-and-Forget for Long-Running API Calls

When an API endpoint triggers a long-running operation (e.g., batch reports), use `asyncio.create_task()` to run it in the background and return HTTP 202 immediately.

```python
# Good — fire-and-forget
async def execute(target_id: int):
    await target_service.update_target_status(target_id, "processing")
    asyncio.create_task(_run_report(target_id))  # Background
    return {"status": "accepted"}

# Bad — blocks until complete (may timeout)
async def execute(target_id: int):
    results = await report_service.execute_report_for_target(target_id)  # Blocks!
    return results
```

### 11. Comment Report Reason Validation

B站 comment report API only supports `reason_id` values 1-9. Values 10+ (e.g., 11 = 涉政敏感) return error code 12012. Always validate before sending.

```python
# In report_service.py
VALID_COMMENT_REASONS = (1, 2, 3, 4, 5, 7, 8, 9)
comment_reason = target.get("reason_id") or 4
if comment_reason not in VALID_COMMENT_REASONS:
    comment_reason = 4  # fallback
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

---

## Gotcha: Global App Dependencies Break WebSocket Routes

Never use `app = FastAPI(dependencies=[Depends(verify_api_key)])` when the app has WebSocket routes. The `Security(APIKeyHeader(...))` dependency injects a `str` parameter, but WebSocket handshakes don't go through the same HTTP header pipeline, causing a 500 error.

**Solution**: Apply auth dependencies per-router instead of globally:

```python
# Good — per-router auth, WebSocket excluded
_auth_deps = [Depends(verify_api_key)]
app.include_router(accounts.router, prefix="/api/accounts", dependencies=_auth_deps)
app.include_router(websocket.router, tags=["WebSocket"])  # No auth deps

# Bad — global dependency breaks WebSocket
app = FastAPI(dependencies=[Depends(verify_api_key)])
```

Also ensure `verify_api_key` reads headers directly via `request.headers.get()` instead of using `Security(APIKeyHeader(...))`, which adds an incompatible parameter type for WebSocket scope.
