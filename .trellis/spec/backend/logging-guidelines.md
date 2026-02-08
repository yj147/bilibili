# Logging Guidelines

> How logging is done in Bili-Sentinel.

---

## Overview

- **Library**: Python stdlib `logging`
- **Output**: `stdout` (for container/Docker compatibility)
- **Format**: `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
- **Date format**: `%Y-%m-%d %H:%M:%S`
- **Default level**: `DEBUG`
- **Logger name**: `"sentinel"`

---

## Setup

A singleton logger is created in `backend/logger.py`:

```python
from backend.logger import logger

logger.info("Something happened")
```

Do not create new loggers. Always import the shared `logger` instance.

---

## Log Levels

| Level | When to Use | Example |
|-------|------------|--------|
| `DEBUG` | Detailed diagnostic info, stack traces | `logger.debug(traceback.format_exc())` |
| `INFO` | Normal operations, state changes | `logger.info("Database initialized")` |
| `WARNING` | Non-critical issues, config concerns | `logger.warning("必须以单 worker 模式运行")` |
| `ERROR` | Failures that need attention | `logger.error("Auto-reply error: %s", e)` |

---

## Logging Patterns

### Service-Level Logging

Use brackets to identify the subsystem:

```python
logger.info("[AutoReply][%s] Replying to %s: %s", account["name"], talker_id, reply_text)
logger.error("[AutoReply][%s] Error: %s", account["name"], acc_err)
logger.error("[Scheduler AutoReply][%s] Error: %s", account.get("name", "?"), e)
```

### Middleware Error Logging

```python
logger.error("Unhandled exception on %s %s: %s", request.method, request.url.path, exc)
logger.debug(traceback.format_exc())  # Full trace at DEBUG level
```

### Lifecycle Events

```python
logger.info("Bili-Sentinel starting up...")
logger.info("Database initialized")
logger.info("Scheduler started")
logger.info("Bili-Sentinel shutting down...")
```

---

## String Formatting

Use `%s` style (lazy evaluation) for logger calls:

```python
# Good — lazy formatting
logger.info("Target %s status: %s", target_id, status)
logger.error("Error processing %s: %s", target_id, error)

# Acceptable but less optimal
logger.info(f"Target {target_id} status: {status}")
```

---

## Real-Time Log Broadcasting (WebSocket)

In addition to file logging, important events are broadcast to connected WebSocket clients via `broadcast_log()`:

```python
from backend.api.websocket import broadcast_log

await broadcast_log(
    "report",  # log type
    f"[{account['name']}] report_{target['type']} {target['identifier']} -> OK",  # message
    {"target_id": target["id"], "account_id": account["id"], "success": True},  # data
)
```

This is used for the frontend real-time log display.

---

## What NOT to Log

| Forbidden | Reason |
|-----------|--------|
| `sessdata` cookie values | Credential leakage |
| `bili_jct` tokens | CSRF token leakage |
| Full HTTP response bodies from Bilibili | Too verbose, may contain PII |
| User passwords or API keys | Security |

### Safe to Log

- Account names (not credentials)
- Target identifiers (BV numbers, rpids, UIDs)
- Operation results (success/fail)
- Error messages and types
- Request counts and timing
