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

## Security Patterns

### Authentication Fail-Closed Design

**Problem**: Fail-open authentication allows unauthorized access when configuration is missing.

**Solution**: Raise errors when required security configuration is absent.

```python
# Good — fail-closed
_API_KEY = os.getenv("SENTINEL_API_KEY", "")

async def verify_api_key(request: Request):
    if not _API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfiguration: SENTINEL_API_KEY not set")
    # ... verify logic
```

**Why**: Missing API keys should halt the server, not silently allow all requests.

### WebSocket Authentication via Subprotocol

**Problem**: Passing API keys in WebSocket URLs leaks credentials in logs and browser history.

**Solution**: Use `Sec-WebSocket-Protocol` header for authentication tokens.

```python
# Backend
if api_key:
    for header_name, header_value in websocket.headers.items():
        if header_name.lower() == "sec-websocket-protocol":
            if header_value.startswith("token."):
                token = header_value[6:]
                subprotocol = header_value
            break
    if not token:
        await websocket.close(code=1008, reason="API key required")
        return
    if not hmac.compare_digest(token, api_key):
        await websocket.close(code=4001, reason="Unauthorized")
        return
await websocket.accept(subprotocol=subprotocol)
```

```typescript
// Frontend
const ws = apiKey
    ? new WebSocket(url, [`token.${apiKey}`])
    : new WebSocket(url);
```

**Why**: Prevents credential leakage in server logs, browser DevTools, and proxy logs.

### Fire-and-Forget Error Handling

**Problem**: Background tasks created with `asyncio.create_task()` can fail silently, leaving entities stuck in "processing" state.

**Solution**: Use defense-in-depth with both wrapper exception handling AND `done_callback`.

```python
# Good — wrapper exception handling
async def _run_report_in_background(target_id: int, account_ids: list[int] | None):
    try:
        await report_service.execute_report_for_target(target_id, account_ids)
    except Exception as e:
        logger.error("Background report execution failed for target %s: %s", target_id, e)
        await target_service.update_target_status(target_id, "failed")
        await execute_insert(
            "INSERT INTO report_logs (target_id, action, success, error_message) VALUES (?, ?, ?, ?)",
            (target_id, "background_task_crash", False, str(e))
        )

# Good — done_callback for defense-in-depth
task = asyncio.create_task(_run_report_in_background(target_id, account_ids))

def handle_task_exception(t):
    try:
        t.result()
    except Exception as e:
        logger.error("Background report task failed for target %s: %s", target_id, e)

task.add_done_callback(handle_task_exception)
```

**Why**:
- Wrapper exception handling catches most failures
- `done_callback` provides safety net for catastrophic failures before wrapper executes
- Consistent pattern across all background tasks (single and batch execution)

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

### 8. Account Filtering: Context-Dependent Status Filtering

**For B站 API Operations (reporting, scanning)**: Always filter by `status = 'valid'` in addition to `is_active = 1`. Accounts with `status = 'expiring'` have invalid credentials and will fail with -352.

```python
# Good — filter by both is_active and status for API calls
await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status = 'valid'")

# Bad — includes expired/invalid accounts
await execute_query("SELECT * FROM accounts WHERE is_active = 1")
```

**For Health Checks (cookie validation)**: Must include BOTH `status = 'valid'` AND `status = 'expiring'` accounts. Health checks are the mechanism that allows 'expiring' accounts to recover to 'valid' status.

```python
# Good — health check includes expiring accounts
await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status IN ('valid', 'expiring')")

# Bad — creates permanent loop where expiring accounts never recover
await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status = 'valid'")
```

> **Critical Gotcha**: If health checks exclude 'expiring' accounts, those accounts can NEVER recover to 'valid' status, creating a permanent degradation loop. This was discovered in Session 11 when all 'expiring' accounts remained stuck indefinitely.

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

### 12. Memory Management for Long-Running Services

For services that maintain in-memory state (cooldowns, caches, tracking dicts), implement periodic cleanup to prevent memory leaks.

```python
# Good — periodic cleanup
_account_last_report: dict[int, float] = {}

def _cleanup_stale_cooldowns():
    """Remove cooldown entries older than 1 hour."""
    current_time = time.monotonic()
    stale_threshold = 3600
    stale_keys = [
        account_id for account_id, last_ts in _account_last_report.items()
        if current_time - last_ts > stale_threshold
    ]
    for key in stale_keys:
        del _account_last_report[key]

# Call cleanup periodically in hot paths
_cleanup_stale_cooldowns()
```

> **Why**: Long-running services (auto-reply, report execution) can accumulate stale entries in tracking dictionaries. Without cleanup, memory usage grows unbounded over time.

### 10. Fire-and-Forget for Long-Running API Calls

When an API endpoint triggers a long-running operation (e.g., batch reports), use `asyncio.create_task()` to run it in the background and return HTTP 202 immediately.

```python
# Good — fire-and-forget with error handling
async def execute(target_id: int):
    await target_service.update_target_status(target_id, "processing")
    try:
        asyncio.create_task(_run_report(target_id))
    except Exception as e:
        logger.error("Failed to create background task: %s", e)
        await target_service.update_target_status(target_id, "pending")
        raise HTTPException(status_code=500, detail="Failed to queue execution")
    return {"status": "accepted"}

# Bad — blocks until complete (may timeout)
async def execute(target_id: int):
    results = await report_service.execute_report_for_target(target_id)  # Blocks!
    return results
```

> **Gotcha**: Always wrap `asyncio.create_task()` in try-except. If task creation fails after status update, the status becomes inconsistent (marked "processing" but no task running). Rollback the status on failure.

### 11. Comment Report Reason Validation

B站 comment report API only supports `reason_id` values 1-9. Values 10+ (e.g., 11 = 涉政敏感) return error code 12012. Always validate before sending.

```python
# In models/target.py - Pydantic validation
VALID_COMMENT_REASONS = {1, 2, 3, 4, 5, 7, 8, 9}

class TargetCreate(TargetBase):
    @field_validator('reason_id')
    @classmethod
    def validate_comment_reason(cls, v, info):
        if info.data.get('type') == 'comment' and v is not None:
            if v not in VALID_COMMENT_REASONS:
                raise ValueError(f'Invalid reason_id for comment: {v}')
        return v

# In report_service.py - Runtime fallback
comment_reason = target.get("reason_id") or 4
if comment_reason not in (1, 2, 3, 4, 5, 7, 8, 9):
    comment_reason = 4  # fallback
```

> **Best Practice**: Validate at both input (Pydantic) and runtime (service layer) for defense in depth.

### 13. Sentinel Values for Ambiguous None Returns

When a service function can return `None` for multiple reasons (no valid fields vs. record not found), use a sentinel string value to distinguish cases at the API layer.

```python
# Good — service returns sentinel value
async def update_config(config_id: int, fields: dict):
    updates = []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
    if not updates:
        return "no_valid_fields"  # Sentinel value
    # ... perform update ...
    rows = await execute_query("SELECT * FROM table WHERE id = ?", (config_id,))
    return rows[0] if rows else None  # None = not found

# Good — API distinguishes cases
result = await service.update_config(config_id, fields)
if result == "no_valid_fields":
    raise HTTPException(status_code=400, detail="No valid fields to update")
if result is None:
    raise HTTPException(status_code=404, detail="Config not found")
return result

# Bad — ambiguous None
async def update_config(config_id: int, fields: dict):
    if not updates:
        return None  # Ambiguous: no fields or not found?
    # ...
    return rows[0] if rows else None
```

**Why**: Prevents API layer from guessing which error occurred. Clear distinction between client errors (400) and not found (404).

### 14. Credential Filtering in API Responses

Always filter sensitive fields from API responses, even for authenticated endpoints. Define a module-level set of sensitive field names and use dictionary comprehension to exclude them.

```python
# Good — filter sensitive fields
_SENSITIVE_FIELDS = {"sessdata", "bili_jct", "refresh_token", "dedeuserid_ckmd5"}

async def qr_login_save(qrcode_key: str, account_name: str):
    # ... login logic ...
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    safe_account = {k: v for k, v in rows[0].items() if k not in _SENSITIVE_FIELDS}
    return {"status_code": 0, "message": "登录成功", "account": safe_account}

# Bad — returns full account with credentials
async def qr_login_save(qrcode_key: str, account_name: str):
    # ... login logic ...
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return {"status_code": 0, "message": "登录成功", "account": rows[0]}
```

**Why**: Defense in depth. Even if the endpoint is authenticated, credentials should never be exposed in responses. Prevents accidental logging, caching, or client-side storage of sensitive data.

**Pattern**: Use Pydantic response models (e.g., `AccountPublic`) for type safety, but also filter at service layer for operations that bypass Pydantic serialization.

### 15. Input Validation with Query Constraints

For query parameters that control resource usage (limit, page_size, etc.), always use FastAPI's `Query` validator with explicit bounds.

```python
# Good — bounded limit with validation
@router.get("/history")
async def get_history(limit: int = Query(default=50, ge=1, le=1000)):
    return await service.get_history(limit)

# Bad — unbounded limit
@router.get("/history")
async def get_history(limit: int = 50):
    return await service.get_history(limit)  # Could be 999999999
```

**Why**: Prevents resource exhaustion attacks. Limits memory usage and database load. Provides clear API contract with validation errors (HTTP 422) for out-of-range values.

**Convention**: Use `ge=1, le=1000` for most list endpoints. Adjust upper bound based on expected use cases.

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
