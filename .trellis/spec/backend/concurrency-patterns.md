# Concurrency Patterns

> Async concurrency patterns and safety guidelines for Bili-Sentinel backend.

---

## Overview

Bili-Sentinel uses Python's `asyncio` for concurrent I/O operations. This document covers patterns for safe concurrent access to shared resources, preventing race conditions, and managing background tasks.

---

## Core Principles

1. **Protect shared state with asyncio.Lock**
2. **Use atomic database operations for claim patterns**
3. **Validate state before operations (prevent TOCTOU)**
4. **Always handle background task failures**
5. **Clean up long-lived in-memory state**

---

## Pattern: asyncio.Lock for Shared Resource Protection

When multiple async tasks may concurrently access or modify shared resources (dicts, caches, counters), protect with `asyncio.Lock`:

```python
# Good — Lock protects shared dict
_account_last_report: dict[int, float] = {}
_cooldown_lock = asyncio.Lock()

async def check_cooldown(account_id: int) -> float:
    config = await get_config()
    async with _cooldown_lock:
        last_ts = _account_last_report.get(account_id, 0)
        elapsed = time.monotonic() - last_ts
        if elapsed < config['cooldown']:
            wait = config['cooldown'] - elapsed
            _account_last_report[account_id] = time.monotonic() + wait
            return wait
        _account_last_report[account_id] = time.monotonic()
        return 0

# Bad — Race condition on dict access
async def check_cooldown(account_id: int) -> float:
    last_ts = _account_last_report.get(account_id, 0)  # Read
    # Another task could modify here!
    _account_last_report[account_id] = time.monotonic()  # Write
```

**Why**: Without the lock, concurrent tasks can interleave reads and writes, causing lost updates or inconsistent state.

**When to use**:
- Shared dictionaries (cooldowns, caches, tracking state)
- Counters or flags accessed by multiple tasks
- Any mutable state modified by concurrent coroutines

---

## Pattern: Atomic Database Claim

For fire-and-forget operations where multiple workers may try to process the same entity, use atomic database claims:

```python
# Good — Atomic claim via transaction
async def _claim_target_for_processing(target_id: int) -> bool:
    """Atomically claim a pending target for processing."""
    async def _operation(conn):
        cursor = await conn.execute(
            "UPDATE targets SET status = 'processing', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') "
            "WHERE id = ? AND status != 'processing'",
            (target_id,),
        )
        return cursor.rowcount > 0
    return await execute_in_transaction(_operation)

# Usage in batch processing
async def process_target(target: dict):
    claimed = await _claim_target_for_processing(target["id"])
    if not claimed:
        logger.info("Skipping target #%d (already processing)", target["id"])
        return
    # ... process target ...

# Bad — Check-then-set race condition
async def process_target(target: dict):
    current = await get_target(target["id"])
    if current["status"] == "processing":  # Check
        return
    await update_target_status(target["id"], "processing")  # Set
    # Race: another task could have claimed between check and set!
```

**Why**: The `WHERE status != 'processing'` clause ensures only one task can successfully claim the entity. The transaction guarantees atomicity.

**When to use**:
- Batch processing with concurrent workers
- Fire-and-forget background tasks
- Any scenario where multiple processes might try to work on the same entity

---

## Pattern: Trigger Pre-Validation (Prevent TOCTOU)

When updating configuration that will be used to register external resources (APScheduler jobs, etc.), validate BEFORE the database update:

```python
# Good — Validate before DB update
async def update_task(task_id: int, data: dict):
    current_row = await get_task(task_id)
    if not current_row:
        raise ValueError("Task not found")

    # Build validation row
    validation_row = dict(current_row)
    validation_row.update(data)

    # Pre-validate trigger configuration
    if validation_row.get("is_active"):
        try:
            if validation_row.get("cron_expression"):
                from apscheduler.triggers.cron import CronTrigger
                CronTrigger.from_crontab(validation_row["cron_expression"])
            elif validation_row.get("interval_seconds"):
                from apscheduler.triggers.interval import IntervalTrigger
                IntervalTrigger(seconds=validation_row["interval_seconds"])
            else:
                raise ValueError("Either cron_expression or interval_seconds required")
        except Exception as e:
            raise ValueError(f"Invalid trigger configuration: {e}")

    # Now safe to update DB
    await execute_query("UPDATE tasks SET ... WHERE id = ?", (..., task_id))

    # Register job with validated config
    if validation_row.get("is_active"):
        _register_job(validation_row)

# Bad — TOCTOU vulnerability
async def update_task(task_id: int, data: dict):
    await execute_query("UPDATE tasks SET ... WHERE id = ?", (..., task_id))

    # Fetch updated row
    updated_row = await get_task(task_id)

    # Try to register job — may fail if config invalid!
    if updated_row.get("is_active"):
        try:
            _register_job(updated_row)  # Fails here!
        except Exception as e:
            # Task is now in DB with invalid config but inactive
            logger.error("Failed to register job: %s", e)
```

**Why**: Validating after the DB update creates a TOCTOU (Time-of-Check-Time-of-Use) race condition. If validation fails, the DB is left in an inconsistent state (invalid config stored but job not registered).

**When to use**:
- Configuration updates that trigger external resource registration
- Any update where validation failure should prevent the DB write
- Operations where rollback is expensive or impossible

---

## Pattern: Background Task Error Handling

Always wrap background tasks with error handling and status rollback:

```python
# Good — Wrapper with error handling
async def _run_report_in_background(target_id: int):
    try:
        await report_service.execute_report_for_target(target_id)
    except Exception as e:
        logger.error("Background report failed for target %s: %s", target_id, e)
        await target_service.update_target_status(target_id, "failed")
        await execute_insert(
            "INSERT INTO report_logs (target_id, success, error_message) VALUES (?, ?, ?)",
            (target_id, False, str(e))
        )

# API endpoint
async def execute_report(target_id: int):
    await target_service.update_target_status(target_id, "processing")
    try:
        asyncio.create_task(_run_report_in_background(target_id))
    except Exception as e:
        logger.error("Failed to create background task: %s", e)
        await target_service.update_target_status(target_id, "pending")
        raise HTTPException(status_code=500, detail="Failed to queue execution")
    return {"status": "accepted"}

# Bad — No error handling
async def execute_report(target_id: int):
    await target_service.update_target_status(target_id, "processing")
    asyncio.create_task(report_service.execute_report_for_target(target_id))
    # If task creation fails, status stuck at "processing"!
    # If task execution fails, no status update!
    return {"status": "accepted"}
```

**Why**: Background tasks can fail silently. Without error handling, entities get stuck in "processing" state forever.

**When to use**:
- All fire-and-forget background tasks
- Long-running operations triggered by API endpoints
- Any `asyncio.create_task()` call

---

## Pattern: Async Function Lock Protection

When converting sync functions to async, ensure lock protection is preserved:

```python
# Good — Async function with lock
async def _cleanup_stale_cooldowns():
    """Remove cooldown entries older than 1 hour."""
    current_time = time.monotonic()
    stale_threshold = 3600
    async with _cooldown_lock:
        stale_keys = [
            account_id for account_id, last_ts in list(_account_last_report.items())
            if current_time - last_ts > stale_threshold
        ]
        for key in stale_keys:
            del _account_last_report[key]

# Bad — Forgot to add lock when converting to async
async def _cleanup_stale_cooldowns():
    current_time = time.monotonic()
    stale_threshold = 3600
    # Missing lock! Race condition with other tasks accessing _account_last_report
    stale_keys = [...]
    for key in stale_keys:
        del _account_last_report[key]
```

**Why**: Converting a function to async doesn't automatically make it thread-safe. Shared state still needs lock protection.

**When to use**:
- When converting sync functions to async
- When adding async operations to functions that access shared state

---

## Pattern: Lock Optimization (Minimize Critical Section)

Minimize time spent holding locks by moving independent operations outside the critical section:

```python
# Good — Minimal lock scope
async def check_and_wait_cooldown(account_id: int):
    config = await get_config()  # Outside lock

    async with _cooldown_lock:
        last_ts = _account_last_report.get(account_id, 0)
        elapsed = time.monotonic() - last_ts
        if elapsed < config['cooldown']:
            wait = config['cooldown'] - elapsed
            _account_last_report[account_id] = time.monotonic() + wait
        else:
            wait = 0
            _account_last_report[account_id] = time.monotonic()

    if wait > 0:
        await asyncio.sleep(wait)  # Outside lock!

# Bad — Lock held during sleep
async def check_and_wait_cooldown(account_id: int):
    config = await get_config()

    async with _cooldown_lock:
        last_ts = _account_last_report.get(account_id, 0)
        elapsed = time.monotonic() - last_ts
        if elapsed < config['cooldown']:
            wait = config['cooldown'] - elapsed
            await asyncio.sleep(wait)  # Blocks other tasks!
            _account_last_report[account_id] = time.monotonic()
```

**Why**: Holding a lock during `asyncio.sleep()` blocks all other tasks waiting for the lock, reducing concurrency.

**Performance impact**: In the bad example, if 10 tasks need cooldown checks and each waits 90 seconds, total time is 900 seconds (sequential). In the good example, all 10 tasks can wait concurrently, total time is ~90 seconds.

---

## Pattern: Task Registration Failure Handling

When registering external resources (APScheduler jobs) during startup, handle failures gracefully:

```python
# Good — Handle registration failures
async def start_scheduler():
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE is_active = 1")
    for row in rows:
        try:
            _register_job(row)
        except Exception as e:
            logger.error("Failed to register task #%d (%s): %s",
                        row.get("id"), row.get("task_type"), e)
            await _deactivate_task_after_job_failure(row.get("id"), e)

async def _deactivate_task_after_job_failure(task_id: int, error: Exception):
    """Deactivate task and log failure when job registration fails."""
    await execute_query(
        "UPDATE scheduled_tasks SET is_active = 0 WHERE id = ?",
        (task_id,)
    )
    await execute_insert(
        "INSERT INTO report_logs (action, success, error_message) VALUES (?, ?, ?)",
        (f"task_{task_id}_registration_failed", False, str(error))
    )

# Bad — Crash on first failure
async def start_scheduler():
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE is_active = 1")
    for row in rows:
        _register_job(row)  # Crashes if any task has invalid config!
```

**Why**: One invalid task shouldn't prevent other valid tasks from starting. Graceful degradation is better than total failure.

---

## Common Mistakes

### Mistake 1: Forgetting await on Async Functions

```python
# Bad — Missing await
_cleanup_stale_cooldowns()  # Returns coroutine, doesn't execute!

# Good
await _cleanup_stale_cooldowns()
```

### Mistake 2: Lock Contention from Redundant Acquisitions

```python
# Bad — Acquires lock twice in loop
for account in accounts:
    async with _cooldown_lock:
        last_ts = _account_last_report.get(account["id"], 0)
        # ... calculate wait ...

    if wait > 0:
        await asyncio.sleep(wait)

    async with _cooldown_lock:  # Second acquisition!
        _account_last_report[account["id"]] = time.monotonic()

# Good — Single lock acquisition
for account in accounts:
    async with _cooldown_lock:
        last_ts = _account_last_report.get(account["id"], 0)
        # ... calculate wait ...
        if wait > 0:
            _account_last_report[account["id"]] = time.monotonic() + wait
        else:
            _account_last_report[account["id"]] = time.monotonic()

    if wait > 0:
        await asyncio.sleep(wait)
```

### Mistake 3: Status Verification After Claim

```python
# Bad — Verify status after it's already set
async def execute_report(target_id: int):
    await update_target_status(target_id, "processing")

    target = await get_target(target_id)
    if target["status"] != "processing":  # Always true!
        return None, "Wrong status"

# Good — Verify before claim, or use atomic claim
async def execute_report(target_id: int):
    target = await get_target(target_id)
    if target["status"] == "processing":
        return None, "Already processing"

    await update_target_status(target_id, "processing")
```

---

## Testing Concurrency

### Test Pattern: Concurrent Task Execution

```python
@pytest.mark.asyncio
async def test_concurrent_cooldown_checks():
    """Test that concurrent cooldown checks don't race."""
    account_id = 1

    # Launch 10 concurrent cooldown checks
    tasks = [check_cooldown(account_id) for _ in range(10)]
    results = await asyncio.gather(*tasks)

    # All should see consistent state
    assert all(r >= 0 for r in results)
```

### Test Pattern: Claim Atomicity

```python
@pytest.mark.asyncio
async def test_claim_target_only_once():
    """Test that only one task can claim a target."""
    target_id = 1

    # Launch 5 concurrent claim attempts
    tasks = [_claim_target_for_processing(target_id) for _ in range(5)]
    results = await asyncio.gather(*tasks)

    # Exactly one should succeed
    assert sum(results) == 1
```

---

## Checklist: Concurrency Safety Review

Before merging concurrent code:

- [ ] All shared state protected by `asyncio.Lock`
- [ ] Lock scope minimized (no I/O inside locks)
- [ ] Atomic database operations for claims
- [ ] Pre-validation before state-changing operations
- [ ] Background task error handling with status rollback
- [ ] All async functions properly awaited
- [ ] No TOCTOU vulnerabilities
- [ ] Concurrent access tested

---

## Related Documents

- [Error Handling](./error-handling.md) - Background task error patterns
- [Quality Guidelines](./quality-guidelines.md) - Memory management for long-running services
- [Database Guidelines](./database-guidelines.md) - Transaction patterns
