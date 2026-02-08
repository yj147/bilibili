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

In `schemas/`, separate request models from response models:

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
- [ ] New schemas in `schemas/` (not `models/`)
- [ ] Constants defined once in `config.py`, not duplicated
- [ ] Schema changes: existing DBs need `ALTER TABLE` migration
- [ ] All `print()` in non-test code replaced with `logger`
