# Error Handling

> How errors are handled in Bili-Sentinel.

---

## Overview

Error handling uses a **unified middleware** approach. All exceptions are caught and converted to a consistent JSON response format. Services return `(result, error_string)` tuples instead of raising exceptions.

---

## Error Response Format

All API errors return this JSON structure:

```json
{
  "error": true,
  "code": 404,
  "detail": "Target not found"
}
```

---

## Exception Handlers (middleware.py)

Three handlers registered in `register_exception_handlers(app)`:

| Handler | Catches | Status | Behavior |
|---------|---------|--------|----------|
| `http_exception_handler` | `StarletteHTTPException` | Varies | Returns `exc.detail` |
| `validation_exception_handler` | `RequestValidationError` | 422 | Formats Pydantic errors as `"loc: msg; loc: msg"` |
| `general_exception_handler` | `Exception` | 500 | Logs full traceback, returns generic message |

**Important**: The catch-all handler returns `"Internal server error"` to the client — never leaks stack traces.

---

## Service Error Pattern: (result, error) Tuples

Services that can fail return a tuple instead of raising:

```python
# In service
async def execute_report_for_target(target_id, account_ids=None):
    target = await target_service.get_target(target_id)
    if not target:
        return None, "Target not found"    # Error case
    # ... do work ...
    return results, None                   # Success case

# In API route
results, error = await report_service.execute_report_for_target(...)
if error:
    status = 404 if "not found" in error.lower() else 400
    raise HTTPException(status_code=status, detail=error)
return results
```

### When to Use This Pattern

- Operations that can fail for expected business reasons (not found, no accounts, etc.)
- Batch operations where partial results are possible

### When to Raise HTTPException Directly

- Simple not-found cases in CRUD routes
- Input validation beyond Pydantic (e.g., checking if fields to update are empty)

```python
# Direct raise in API route — simple cases
result = await target_service.get_target(target_id)
if not result:
    raise HTTPException(status_code=404, detail="Target not found")
return result
```

---

## External API Error Handling (core/bilibili_client.py)

The Bilibili client handles errors internally with retry logic:

### Bilibili Response Codes

| Code | Meaning | Action | Retry? |
|------|---------|--------|--------|
| 0 | Success | Process data | — |
| -412 | Too many requests | Exponential backoff: `5 * 2^attempt + jitter` | Yes |
| -352 | Risk control triggered | **Fail-fast** — return immediately, don't wait | **No** |
| -101 | Not logged in | Log error, mark account invalid | **No** |
| 862, 101 | Frequency limits | Exponential backoff | Yes |
| -999 | Internal: max retries | Returned when all retries exhausted | — |

#### Report-Specific Response Codes

| Code | Meaning | Action | Treat as Success? |
|------|---------|--------|-------------------|
| 0 | Report accepted | Toast: "已为您隐藏该评论" | Yes |
| 12008 | Already reported | Target already dealt with | **Yes** |
| 12012 | Invalid reason | Reason not supported for this target type | No |
| 12019 | Rate limited | Wait 90s + retry (up to 2 times) | No (retry) |
| 12022 | Already deleted | Content already removed by B站 | **Yes** |

> **Gotcha**: `-101` must NOT be retried — the account session is invalid. Retrying wastes time and may trigger further rate limits. Log the error and return immediately.

> **Gotcha**: `-352` should **fail-fast** (return immediately) instead of waiting 5+ minutes. The account is flagged by B站's risk control — waiting won't help. Mark the report as failed and move on.

> **Gotcha**: `12022` (already deleted) and `12008` (already reported) should be treated as **success** in report_service, not failures. The target is effectively dealt with.

> **Gotcha**: `12012` (举报理由异常) means the `reason_id` is invalid for this target type. **Comment reports only support reason_id 1-9** (not 10 or 11). Always validate reason_id before sending to B站.

### WBI Keys Auto-Refresh

WBI keys rotate periodically on Bilibili's side. The client auto-refreshes when:
- Keys are stale (older than `_WBI_TTL_SECONDS` = 1 hour)
- A signed request is about to be made (`sign=True`)

Module-level cache (`_wbi_cache`) is shared across all `BilibiliAuth` instances to avoid redundant refreshes.

### Network Errors

- **timeout, connect, read**: Retry with `(attempt + 1) * 2` seconds backoff
- **Max retries exceeded**: Returns `{"code": -999, "message": "Max retries reached: ..."}`

Callers check `result.get("code") == 0` for success.

---

## Error Handling in Background Tasks

### Auto-Reply Service

The polling loop catches per-account errors individually to avoid killing the entire loop:

```python
for account in accounts:
    try:
        # ... process account ...
    except Exception as acc_err:
        logger.error("[AutoReply][%s] Error: %s", account["name"], acc_err)
```

### Report Execution

Each individual report catches its own exceptions and logs them to `report_logs`:

```python
try:
    # ... execute report ...
except Exception as e:
    await execute_insert(
        "INSERT INTO report_logs (..., success, error_message) VALUES (..., ?, ?)",
        (..., False, str(e)),
    )
```

---

## Common Mistakes

### Mistake 1: Catching Too Broadly in Routes

```python
# Bad — hides bugs, duplicates middleware behavior
try:
    result = await some_service_call()
except Exception as e:
    return JSONResponse(status_code=500, content={"error": str(e)})

# Good — let the middleware handle unexpected errors
result = await some_service_call()
```

### Mistake 2: Inconsistent Error Status Codes

Follow this mapping:

| Situation | Status Code |
|-----------|------------|
| Resource not found | 404 |
| Invalid input / no valid data | 400 |
| Pydantic validation | 422 (automatic) |
| Auth failure | 401 |
| Unexpected error | 500 (middleware) |

---

## Gotcha: Adding Pydantic Validation to Existing Fields Breaks List Endpoints

When adding stricter validation (e.g., `Field(..., min_length=1)`) to a `response_model` field, existing DB rows that violate the new constraint will cause **500 errors on list endpoints**.

**Why**: `response_model` validation runs during serialization, not just on input. A list endpoint tries to serialize all rows, and one invalid row fails the entire response.

**Example**: Adding `min_length=1` to `AutoReplyConfig.response` caused `/api/autoreply/config` to return 500 because row id=7 had `response=''`.

**Prevention**:
1. Before adding stricter validation, query the DB for rows that would violate it
2. Clean up or migrate invalid data first
3. Consider adding the constraint only to `Create`/`Update` models, not the response model

```python
# Check before adding min_length=1 to response field
rows = await execute_query("SELECT id FROM autoreply_config WHERE response = '' OR response IS NULL")
if rows:
    # Fix data first, then add validation
    await execute_query("DELETE FROM autoreply_config WHERE response = ''")
```
