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
# Good — periodic cleanup with safe iteration
_account_last_report: dict[int, float] = {}

def _cleanup_stale_cooldowns():
    """Remove cooldown entries older than 1 hour."""
    current_time = time.monotonic()
    stale_threshold = 3600
    stale_keys = [
        account_id for account_id, last_ts in list(_account_last_report.items())
        if current_time - last_ts > stale_threshold
    ]
    for key in stale_keys:
        del _account_last_report[key]

# Call cleanup periodically in hot paths
_cleanup_stale_cooldowns()
```

> **Gotcha: Dict Iteration Safety**: Always use `list()` when iterating a dict that may be modified concurrently (e.g., `list(_account_last_report.items())`). Without `list()`, asyncio task switches during iteration can cause `RuntimeError: dictionary changed size during iteration`.

> **Why**: Long-running services (auto-reply, report execution) can accumulate stale entries in tracking dictionaries. Without cleanup, memory usage grows unbounded over time.

### 16. asyncio.Lock for Shared Resource Protection

When multiple async tasks may concurrently access or modify a shared resource (e.g., WBI key refresh, config reload), protect with `asyncio.Lock` and use double-check pattern:

```python
# Good — Lock + double-check to prevent redundant work
_wbi_refresh_lock = asyncio.Lock()

async def refresh_wbi_keys(self) -> bool:
    async with _wbi_refresh_lock:
        # Double-check: another coroutine may have refreshed while we waited
        if not self.wbi_keys_stale():
            return True
        # ... actual refresh logic
```

**Why**: Without the lock, multiple concurrent requests discovering stale WBI keys will all trigger redundant refresh calls to Bilibili's API, wasting requests and risking rate limits. The double-check avoids unnecessary work after acquiring the lock.

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

### Gotcha: Cookie Refresh is Multi-Step (RSA-OAEP Flow)

Cookie refresh requires 5 steps with specific crypto and header requirements:

1. **Check cookie status**: `GET /x/passport-login/web/cookie/info` — returns `refresh: true` if expired
2. **Generate CorrespondPath**: RSA-OAEP encrypt `refresh_{millisecond_timestamp}` with B站 fixed public key (SHA-256), hex-encode result
3. **Fetch refresh_csrf**: `GET https://www.bilibili.com/correspond/1/{correspondPath}` — extract `<div id="1-name">` content
4. **Refresh cookies**: `POST /x/passport-login/web/cookie/refresh` with `csrf`, `refresh_csrf`, `refresh_token`
5. **Confirm refresh**: `POST /x/passport-login/web/confirm/refresh` with new `csrf` + old `refresh_token`
6. Update DB with new `sessdata`, `bili_jct`, `refresh_token`

Each step can fail independently. The service must handle partial failures gracefully.

> **Critical: RSA Public Key Must Match bilibili-api-python**
>
> The RSA public key used for CorrespondPath encryption MUST be identical to the one in `bilibili-api-python` library. A single-character difference causes HTTP 404 on the correspond endpoint. Always verify against the reference implementation.

> **Critical: Correspond Endpoint Requirements**
>
> The correspond endpoint (`/correspond/1/{path}`) requires:
> - **buvid3 cookie**: Without it, returns 404. Use `account.get("buvid3") or str(uuid.uuid4())` as fallback.
> - **Accept-Encoding: gzip, deflate**: httpx defaults to `br` (brotli) which B站 returns but Python can't decode without `brotli` package. Explicitly set `gzip, deflate`.
> - **Millisecond timestamp**: `round(time.time() * 1000)`. Seconds timestamp → 404, milliseconds → 200.

```python
# Correct CorrespondPath generation
def _generate_correspond_path() -> str:
    ts = round(time.time() * 1000)  # MUST be milliseconds
    key = RSA.import_key(_BILIBILI_RSA_PUBLIC_KEY)
    cipher = PKCS1_OAEP.new(key, SHA256)
    encrypted = cipher.encrypt(f"refresh_{ts}".encode())
    return binascii.b2a_hex(encrypted).decode()

# Correct correspond request
correspond_cookies = {
    "SESSDATA": account["sessdata"],
    "bili_jct": account["bili_jct"],
    "buvid3": account.get("buvid3") or str(uuid.uuid4()),
}
async with httpx.AsyncClient(
    cookies=correspond_cookies,
    headers={**headers, "Accept-Encoding": "gzip, deflate"},
    timeout=10.0,
) as cp_client:
    resp = await cp_client.get(f"https://www.bilibili.com/correspond/1/{path}")
```

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

---

## Auto-Reply Service Patterns

### Pattern: Always Update Dedup State (Even on Failure)

**Problem**: If dedup state is only updated on successful sends, a persistent failure (e.g., invalid message format) causes infinite retry loops — the same message triggers a reply attempt every poll cycle.

**Solution**: Update `autoreply_state.last_msg_ts` immediately after the send attempt, regardless of success/failure.

```python
# Good — always update state
send_result = await client.send_private_message(talker_id, reply_text)
send_success = send_result.get("code") == 0

# Log the attempt
await execute_insert("INSERT INTO report_logs ...", (...))

# Always update state to prevent retry loops
await execute_query(
    "INSERT INTO autoreply_state ... ON CONFLICT ... DO UPDATE SET last_msg_ts = excluded.last_msg_ts",
    (account["id"], talker_id, msg_ts),
)

# Bad — only update on success (causes infinite retries)
if send_success:
    await execute_query("INSERT INTO autoreply_state ...", (...))
```

### Pattern: Rate Limit Circuit Breaker (21046)

**Problem**: When B站 returns code 21046 (24-hour send rate limit), continuing to process remaining sessions wastes time and accumulates errors.

**Solution**: Break out of the session loop immediately on 21046.

```python
if not send_success:
    if send_result.get("code") == 21046:
        logger.warning("[AutoReply][%s] Rate limited (21046), skipping remaining sessions", account["name"])
        break  # Skip ALL remaining sessions for this account
    continue  # Other errors: skip this session only
```

### Pattern: Inter-Reply Delay

**Problem**: Sending private messages too fast triggers B站 rate limiting.

**Solution**: Add a configurable delay between successful sends. Default: 3 seconds.

```python
AUTOREPLY_SEND_DELAY = 3.0  # seconds

# After successful send
if send_success:
    await asyncio.sleep(AUTOREPLY_SEND_DELAY)
```

### Pattern: Self-Message Filtering

**Problem**: Auto-reply can create infinite loops by replying to its own messages.

**Solution**: Check both `talker_id` and `sender_uid` against own UID.

```python
# Skip conversations where we are the other party
if str(talker_id) == str(own_uid):
    continue

# Skip if last message was sent by us (even in conversations with others)
sender_uid = last_msg.get("sender_uid", 0)
if str(sender_uid) == str(own_uid):
    continue
```

### Gotcha: B站 Private Message API Endpoints

- **Session list**: `api.vc.bilibili.com/session_svr/v1/session_svr/get_sessions` (NOT `svr_sync`)
- **Send message**: `api.vc.bilibili.com/web_im/v1/web_im/send_msg` (no session_svr equivalent)

The `svr_sync` endpoint was deprecated. Always use `session_svr/get_sessions`.

---

## Testing Gotchas

### Gotcha: Mock Data Must Cover All Production Code Checks

**Problem**: When production code adds a new field check (e.g., `sender_uid`), existing mocks that omit this field still pass because `.get("sender_uid", 0)` returns the default. The test "passes" but doesn't exercise the filtering logic.

**Solution**: Always add the field to mocks when production code checks it.

```python
# Good — mock covers sender_uid check
"last_msg": {"timestamp": msg_ts, "content": "hello", "sender_uid": 67890}

# Bad — defaults to 0, never matches own_uid, test passes but doesn't test the filter
"last_msg": {"timestamp": msg_ts, "content": "hello"}
```

### Gotcha: Test Assertions Must Match Current Behavior

When production behavior changes (e.g., "state only updated on success" → "state always updated"), tests must be updated to assert the NEW behavior. Stale test assertions give false confidence.

```python
# After behavior change: state always updated even on failure
assert len(state_rows) == 1                  # State WAS written
assert state_rows[0]["last_msg_ts"] == msg_ts  # With correct timestamp

# Old (wrong) assertion:
# assert state_rows == []  # State was NOT written — matches old behavior only
```

### Gotcha: WebSocket Tests Must Send token Subprotocol When API Key Is Enabled

**Problem**: If backend runs with `SENTINEL_API_KEY`, a WebSocket test that connects without `token.<api_key>` subprotocol may connect-close or never receive expected messages (`pong`/`heartbeat`).

**Solution**: Build connect kwargs from auth config and pass `subprotocols` when API key is set.

```python
ws_connect_kwargs = {"open_timeout": 10, "close_timeout": 5}
if API_KEY:
    ws_connect_kwargs["subprotocols"] = [f"token.{API_KEY}"]

async with websockets.connect("ws://127.0.0.1:8000/ws/logs", **ws_connect_kwargs) as ws:
    ...
```

**Why**: Keeps test behavior aligned with runtime auth contract and prevents false negatives in auth-enabled environments.
