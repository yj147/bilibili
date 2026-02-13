# Backend Architecture Guide

> Detailed guide for AI agents working on the Bili-Sentinel backend.

---

## Architecture Pattern

**Strict 3-layer architecture with unidirectional dependencies**:

```
API Layer (api/) → Service Layer (services/) → Data Layer (database.py)
                                             ↘ Core Layer (core/)
```

---

## Key Files

| File | Purpose | Critical Notes |
|------|---------|----------------|
| `main.py` | App entry, lifespan, router registration | **MUST** use `--workers 1` |
| `database.py` | Singleton aiosqlite with asyncio.Lock | 3 core functions: `execute_query`, `execute_insert`, `execute_many` |
| `config.py` | Environment variables | All `SENTINEL_*` vars |
| `middleware.py` | Unified exception handlers | 3-layer: HTTP, validation, unhandled |
| `core/bilibili_client.py` | HTTP client with retry logic | Anti-detection fingerprinting |
| `core/bilibili_auth.py` | Cookie/credential management | WBI key refresh (1h TTL) |
| `core/wbi_sign.py` | WBI request signing | Standard 64-element shuffle |

---

## Database Layer (`database.py`)

### Singleton Pattern

```python
# Global singleton connection
_connection: Optional[aiosqlite.Connection] = None
_lock = asyncio.Lock()

async def get_connection():
    global _connection
    if _connection is None:
        async with _lock:
            if _connection is None:
                _connection = await aiosqlite.connect(...)
    return _connection
```

**Critical**: Single worker only (`--workers 1`), enforced in `main.py:45-48`.

### Core Functions

1. **`execute_query(sql, params) -> list[dict]`**
   - SELECT queries
   - Returns rows as dictionaries
   - TTL cache support

2. **`execute_insert(sql, params) -> int`**
   - INSERT/UPDATE/DELETE
   - Returns `lastrowid`
   - Auto-invalidates cache

3. **`execute_many(sql, params_list) -> int`**
   - Batch operations
   - Returns `rowcount`

4. **`execute_in_transaction(operations) -> bool`**
   - Multi-statement transactions
   - Auto-rollback on failure

### WAL Mode

```sql
PRAGMA journal_mode=WAL;  -- Better read concurrency
```

---

## Service Layer (`services/`)

### Patterns

**Field Whitelists** (prevent SQL injection):
```python
ALLOWED_UPDATE_FIELDS = {"name", "status", "priority"}
if field not in ALLOWED_UPDATE_FIELDS:
    raise ValueError(f"Invalid field: {field}")
```

**Status Validation**:
```python
VALID_STATUSES = {"pending", "processing", "completed", "failed"}
if status not in VALID_STATUSES:
    raise ValueError(f"Invalid status: {status}")
```

**Cache Invalidation**:
```python
from database import invalidate_cache
await execute_insert(...)
invalidate_cache("accounts")  # Manual invalidation
```

---

## API Layer (`api/`)

### Thin Router Pattern

```python
@router.post("/targets")
async def create_target(request: TargetCreate):
    # 1. Pydantic validation (automatic)
    # 2. Call service layer
    result = await target_service.create_target(request.dict())
    # 3. Return response
    return {"id": result}
```

**No business logic in routers** - delegate to services.

### Fire-and-Forget Pattern

```python
# reports.py:49-58
await target_service.update_target_status(target_id, "processing")
task = None
try:
    task = asyncio.create_task(_run_report_in_background(...))
except Exception as e:
    # CRITICAL: Rollback status on task creation failure
    await target_service.update_target_status(target_id, "pending")
    raise HTTPException(...)

return JSONResponse({"status": "accepted"}, status_code=202)
```

**Why**: Long operations (举报执行) return immediately, run in background.

---

## Core Layer (`core/`)

### BilibiliClient

**Anti-Detection Fingerprinting**:
```python
# bilibili_client.py:89-103
headers = {
    "User-Agent": random.choice(UA_LIST),
    "Accept-Encoding": random.choice(["gzip, deflate, br", "gzip, deflate"]),
    "Sec-Ch-Ua": random.choice([...]),  # Randomize browser fingerprint
}
```

**Retry Logic**:
```python
# bilibili_client.py:134-152
if code == -412:  # Rate limit
    await asyncio.sleep(2 ** attempt)  # Exponential backoff
    continue
elif code == -352:  # Risk control
    raise BilibiliError("Account flagged")  # Fail fast
elif code == -799:  # Human verification
    raise BilibiliError("Human verification required")  # Stop immediately
```

**Account Cooldown**:
```python
# report_service.py:23-25
_account_last_report: dict[int, float] = {}
ACCOUNT_COOLDOWN = 90  # seconds

def _can_use_account(account_id: int) -> bool:
    last_time = _account_last_report.get(account_id, 0)
    return time.time() - last_time >= ACCOUNT_COOLDOWN
```

### BilibiliAuth

**WBI Key Refresh**:
```python
# bilibili_auth.py:18-22
_wbi_img_key: Optional[str] = None
_wbi_sub_key: Optional[str] = None
_wbi_keys_fetched_at: Optional[float] = None
WBI_KEYS_TTL = 3600  # 1 hour

def wbi_keys_stale() -> bool:
    return time.time() - _wbi_keys_fetched_at > WBI_KEYS_TTL
```

**Background Refresh** (`main.py:60-67`):
```python
async def refresh_wbi_keys_periodically():
    while True:
        await asyncio.sleep(3600)  # Every hour
        await auth.refresh_wbi_keys()
```

---

## Error Handling

### Middleware (`middleware.py`)

**3-Layer Exception Handlers**:

1. **`StarletteHTTPException`** - HTTP exceptions with `bilibili_code`
2. **`RequestValidationError`** - Pydantic validation errors
3. **`Exception`** - Unhandled exceptions (500)

**Unified Response Format**:
```json
{
  "error": true,
  "code": 12012,
  "detail": "评论举报原因ID无效"
}
```

### Bilibili Error Codes

| Code | Meaning | Handling |
|------|---------|----------|
| -412 | Rate limit | Exponential backoff (2^attempt seconds) |
| -352 | Risk control | Fail fast, mark account flagged |
| -101 | Not logged in | Mark account invalid |
| -799 | Human verification | Stop immediately |
| 12012 | Invalid comment reason | Fallback to reason_id=4 |

---

## Critical Patterns

### 1. Fire-and-Forget with Rollback

```python
# CORRECT
await update_status(id, "processing")
try:
    task = asyncio.create_task(long_operation())
except Exception:
    await update_status(id, "pending")  # Rollback
    raise
```

```python
# WRONG - Status stuck at "processing" if task creation fails
await update_status(id, "processing")
task = asyncio.create_task(long_operation())  # May raise
```

### 2. Circuit Breaker

```python
# report_service.py:143-147
MAX_RETRY_COUNT = 3
if target.get("retry_count", 0) >= MAX_RETRY_COUNT:
    await target_service.update_target_status(target_id, "failed")
    return None, f"Target exceeded max retry count"
```

### 3. Comment Reason Validation

**Pydantic Validator** (`models/target.py:27-37`):
```python
VALID_COMMENT_REASONS = {1, 2, 3, 4, 5, 7, 8, 9}  # NOT 6, 10+

@field_validator('reason_id')
def validate_comment_reason(cls, v, info):
    if info.data.get('type') == 'comment' and v not in VALID_COMMENT_REASONS:
        raise ValueError(f"Invalid comment reason_id: {v}")
```

**Runtime Fallback** (`report_service.py:63-65`):
```python
if target_type == "comment" and reason_id not in VALID_COMMENT_REASONS:
    reason_id = 4  # Default: 赌博诈骗
```

### 4. Startup Recovery

```python
# main.py:53-57
async def lifespan(app: FastAPI):
    # Reset stuck "processing" targets to "pending"
    await execute_query(
        "UPDATE targets SET status = 'pending' WHERE status = 'processing'"
    )
```

---

## Anti-Patterns Avoided

✅ **No N+1 queries** - Use JOIN and batch queries
✅ **No hardcoded secrets** - Environment variables + `.gitignore`
✅ **No global state leaks** - WBI cache is module-level with TTL
✅ **No blocking I/O** - Full async/await

---

## Potential Improvements

⚠️ `_account_last_report` dict fails in multi-worker (but single-worker enforced)
⚠️ Cache invalidation is manual - consider decorator automation
⚠️ `execute_many` has no transaction protection

---

## Testing Requirements

- **Unit tests**: All service functions
- **Integration tests**: All API routes
- **E2E tests**: Report flow, auth, auto-reply
- **No real credentials**: Use mock data

---

## Performance Optimization

### Database Indexes

```sql
-- schema.sql:102-114
CREATE INDEX idx_targets_status_type ON targets(status, type);
CREATE INDEX idx_targets_type_aid_status ON targets(type, aid, status);
CREATE INDEX idx_targets_aid ON targets(aid) WHERE aid IS NOT NULL;
CREATE INDEX idx_report_logs_executed_at ON report_logs(executed_at DESC);
```

### Caching

```python
# L1: Active accounts (60s TTL)
get_active_accounts_cached()

# L2: System config (300s TTL)
get_all_configs_cached()
```

### Human-like Delays

```python
# bilibili_client.py:14-19
def _human_delay(min_s, max_s):
    mu = math.log((min_s + max_s) / 2)
    sigma = 0.5
    delay = random.lognormvariate(mu, sigma)
    return max(min_s, min(delay, max_s))
```

**Why**: Log-normal distribution simulates real user behavior, avoids detection.

---

## Security Practices

1. **API Key Auth**: HMAC constant-time comparison (`hmac.compare_digest`)
2. **SQL Injection**: Parameterized queries + field whitelists
3. **Cookie Escaping**: `urllib.parse.quote()` for special chars
4. **CSRF Protection**: All POST requests carry `csrf` field (`bili_jct`)
5. **Sensitive Fields**: Export can exclude `sessdata`/`bili_jct`

---

## Development Workflow

### Before Coding

1. Read `.trellis/spec/backend/index.md`
2. Read relevant topic docs (database, error handling, logging)

### During Development

1. Follow guidelines strictly
2. Run `pytest backend/tests/` frequently
3. Check `uvicorn` logs for errors

### After Development

1. Run full test suite: `pytest backend/tests/ -v`
2. Manual API testing (Postman/curl)
3. Check logs for warnings

---

## Resources

- **Guidelines**: `.trellis/spec/backend/`
- **Database Schema**: `db/schema.sql`
- **Error Codes**: `core/bilibili_errors.py`
- **Reason Mappings**: `core/bilibili_reasons.py`
