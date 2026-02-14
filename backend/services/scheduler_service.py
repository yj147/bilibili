"""Scheduler business logic."""
import json
import asyncio
import random
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.models.task import ScheduledTaskBase, ScheduledTaskCreate
from backend.database import execute_query, execute_insert, invalidate_cache
from backend.config import MIN_DELAY, MAX_DELAY
from backend.logger import logger

_scheduler: AsyncIOScheduler | None = None
MIN_TASK_INTERVAL_SECONDS = 10
DEFAULT_TASK_INTERVAL_SECONDS = 300


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 60
            }
        )
    return _scheduler


async def start_scheduler():
    """Start the APScheduler and load active tasks from DB."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")

    repaired = await repair_invalid_task_triggers()
    if repaired:
        logger.warning("Repaired %d invalid scheduled task trigger rows during startup", repaired)

    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE is_active = 1")
    for row in rows:
        try:
            _register_job(row)
        except Exception as e:
            logger.error("Failed to register task #%d (%s): %s", row.get("id"), row.get("task_type"), e)
            await _deactivate_task_after_job_failure(row.get("id"), e)
    logger.info("Loaded %d scheduled tasks", len(rows))

    # Built-in: cookie health check every 6 hours
    existing = await execute_query(
        "SELECT id FROM scheduled_tasks WHERE task_type = 'cookie_health_check' LIMIT 1"
    )
    if not existing:
        await create_task(
            name="Cookie Health Check",
            task_type="cookie_health_check",
            interval_seconds=21600,
        )
        logger.info("Created built-in cookie health check task (every 6h)")

    # Built-in: log cleanup every 24 hours
    existing_cleanup = await execute_query(
        "SELECT id FROM scheduled_tasks WHERE task_type = 'log_cleanup' LIMIT 1"
    )
    if not existing_cleanup:
        await create_task(
            name="Log Cleanup",
            task_type="log_cleanup",
            interval_seconds=86400,
        )
        logger.info("Created built-in log cleanup task (every 24h)")


def stop_scheduler():
    """Stop the APScheduler and wait for running jobs."""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped (waited for running jobs)")


async def has_active_autoreply_poll_task() -> bool:
    """Check whether any active autoreply_poll task exists in DB."""
    rows = await execute_query(
        "SELECT 1 FROM scheduled_tasks WHERE task_type = ? AND is_active = 1 LIMIT 1",
        ("autoreply_poll",),
    )
    return bool(rows)


# ── Job functions ─────────────────────────────────────────────────────────

async def _run_report_batch(task_id: int):
    """Job function: execute pending reports using all active accounts.
    Delegates to report_service.execute_batch_reports which handles cooldown,
    12019 retry, valid-account filtering, and early exit on success."""
    from backend.services.report_service import execute_batch_reports
    from backend.api.websocket import broadcast_log

    try:
        await broadcast_log("scheduler", f"Task #{task_id}: starting batch reports")
        result, error = await execute_batch_reports(target_ids=None, account_ids=None)
        if error:
            await broadcast_log("scheduler", f"Task #{task_id}: {error}")
        else:
            await broadcast_log("scheduler", f"Task #{task_id} completed: {result['successful']}/{result['total_targets']} successful")
    except Exception as e:
        logger.error("Task #%d (_run_report_batch) failed: %s", task_id, e)
        await broadcast_log("scheduler", f"Task #{task_id} error: Internal error occurred")
    finally:
        await execute_query(
            "UPDATE scheduled_tasks SET last_run_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?", (task_id,)
        )


async def _run_autoreply_poll(task_id: int):
    """Job function: poll private messages and auto-reply."""
    from backend.api.websocket import broadcast_log
    from backend.services.autoreply_polling import (
        SCHEDULER_AUTOREPLY_ACCOUNTS_QUERY,
        run_autoreply_poll_cycle,
    )
    from backend.services.autoreply_service import is_running

    try:
        if is_running():
            logger.warning(
                "Standalone autoreply service is running. "
                "Skipping scheduler autoreply_poll (task #%d) to avoid double-replies.",
                task_id,
            )
            return

        async def on_reply_sent(account: dict, talker_id: int | str, _reply_text: str, _send_result: dict):
            await broadcast_log("autoreply", f"[{account['name']}] Replied to {talker_id}")

        await run_autoreply_poll_cycle(
            account_query=SCHEDULER_AUTOREPLY_ACCOUNTS_QUERY,
            on_reply_sent=on_reply_sent,
        )
    except Exception as e:
        logger.error("Task #%d (_run_autoreply_poll) failed: %s", task_id, e)
        await broadcast_log("autoreply", f"Task #{task_id} error: Internal error occurred")
    finally:
        await execute_query(
            "UPDATE scheduled_tasks SET last_run_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?", (task_id,)
        )




async def _run_cookie_health_check(task_id: int):
    """Job function: check all active accounts' cookie health and auto-refresh if needed."""
    from backend.services.auth_service import check_cookie_refresh_needed, refresh_account_cookies
    from backend.api.websocket import broadcast_log

    try:
        accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status IN ('valid', 'expiring')")
        for account in accounts:
            try:
                status = await check_cookie_refresh_needed(account["id"])
                if status.get("needs_refresh"):
                    reason = status.get("reason", "unknown")
                    await broadcast_log("auth", f"[{account['name']}] Cookie refresh needed ({reason})")
                    if account.get("refresh_token"):
                        result = await refresh_account_cookies(account["id"])
                        if result.get("success"):
                            await broadcast_log("auth", f"[{account['name']}] Cookie refreshed successfully")
                        else:
                            await broadcast_log("auth", f"[{account['name']}] Cookie refresh failed: {result.get('message')}")
                            await execute_query(
                                "UPDATE accounts SET status = 'expiring' WHERE id = ?",
                                (account["id"],),
                            )
                            await invalidate_cache("active_accounts")
                    else:
                        await broadcast_log("auth", f"[{account['name']}] No refresh_token. QR re-login required.")
                        await execute_query(
                            "UPDATE accounts SET status = 'expiring' WHERE id = ?",
                            (account["id"],),
                        )
                        await invalidate_cache("active_accounts")
            except Exception as e:
                logger.error("[Cookie Health][%s] Error: %s", account.get("name", "?"), e)
                await broadcast_log("auth", f"[{account.get('name', '?')}] Cookie health check error: Internal error occurred")
    except Exception as e:
        logger.error("[Task #%d] Cookie health check failed: %s", task_id, e)
        await broadcast_log("scheduler", f"Task #{task_id} error: Internal error occurred")
    finally:
        await execute_query(
            "UPDATE scheduled_tasks SET last_run_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?", (task_id,)
        )


async def _run_log_cleanup(task_id: int):
    """Job function: delete old report_logs based on system config."""
    from backend.services.config_service import get_config
    from backend.api.websocket import broadcast_log

    try:
        auto_clean = await get_config("auto_clean_logs")
        if auto_clean not in (True, "true", "1"):
            logger.info("[Log Cleanup] auto_clean_logs is disabled, skipping")
            return

        retention_days = await get_config("log_retention_days")
        try:
            retention_days = int(retention_days)
        except (TypeError, ValueError):
            retention_days = 30

        count_rows = await execute_query(
            "SELECT COUNT(*) as count FROM report_logs WHERE executed_at < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        count = count_rows[0]["count"] if count_rows else 0

        if count > 0:
            await execute_query(
                "DELETE FROM report_logs WHERE executed_at < datetime('now', ?)",
                (f"-{retention_days} days",),
            )
            logger.info("[Log Cleanup] Deleted %d logs older than %d days", count, retention_days)
            await broadcast_log("system", f"Log cleanup: deleted {count} logs older than {retention_days} days")
    except Exception as e:
        logger.error("[Task #%d] Log cleanup failed: %s", task_id, e)
        await broadcast_log("scheduler", f"Task #{task_id} error: Internal error occurred")
    finally:
        await execute_query(
            "UPDATE scheduled_tasks SET last_run_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?", (task_id,)
        )

_JOB_FUNCTIONS = {"report_batch": _run_report_batch, "autoreply_poll": _run_autoreply_poll, "cookie_health_check": _run_cookie_health_check, "log_cleanup": _run_log_cleanup}


# ── Job registration ──────────────────────────────────────────────────────

def _register_job(task_row: dict):
    """Register a DB task row as an APScheduler job."""
    scheduler = get_scheduler()
    job_id = f"task_{task_row['id']}"
    func = _JOB_FUNCTIONS.get(task_row["task_type"])
    if not func:
        logger.warning("Unknown task_type '%s' for task #%d, skipping job registration", task_row["task_type"], task_row["id"])
        return
    try:
        if task_row.get("cron_expression"):
            trigger = CronTrigger.from_crontab(task_row["cron_expression"])
        elif task_row.get("interval_seconds"):
            trigger = IntervalTrigger(seconds=task_row["interval_seconds"])
        else:
            return
    except Exception as e:
        logger.error("Invalid trigger config for task #%d: %s", task_row["id"], e)
        return
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    scheduler.add_job(
        func, trigger=trigger, id=job_id, args=[task_row["id"]],
        replace_existing=True, name=task_row.get("name", job_id),
    )
    logger.info("Registered job: %s (%s)", job_id, task_row["task_type"])


def _unregister_job(task_id: int):
    """Remove an APScheduler job by task ID."""
    scheduler = get_scheduler()
    job_id = f"task_{task_id}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)


async def _deactivate_task_after_job_failure(task_id: int, error: Exception) -> None:
    """Keep task config but disable it when APScheduler registration fails."""
    await execute_query("UPDATE scheduled_tasks SET is_active = 0 WHERE id = ?", (task_id,))
    _unregister_job(task_id)
    logger.error("Failed to register job for task #%d, set inactive: %s", task_id, error)


# ── CRUD ──────────────────────────────────────────────────────────────────

def _normalize_trigger_values(
    cron_expression: Optional[str],
    interval_seconds: Optional[int]
) -> tuple[Optional[str], Optional[int], bool]:
    original_cron = cron_expression
    original_interval = interval_seconds
    changed = False

    cron_value = cron_expression
    if isinstance(cron_value, str):
        cron_value = cron_value.strip() or None

    interval_value = interval_seconds
    if interval_value is not None:
        try:
            interval_value = int(interval_value)
        except (TypeError, ValueError):
            interval_value = None

    cron_valid = False
    if cron_value is not None:
        try:
            CronTrigger.from_crontab(cron_value)
            cron_valid = True
        except Exception:
            cron_value = None

    if interval_value is not None and interval_value < MIN_TASK_INTERVAL_SECONDS:
        interval_value = MIN_TASK_INTERVAL_SECONDS

    if cron_valid:
        interval_value = None
    elif interval_value is None:
        # Mark as inactive instead of forcing default interval
        changed = True
        return cron_value, interval_value, changed

    changed = cron_value != original_cron or interval_value != original_interval
    return cron_value, interval_value, changed


def _parse_row_config(config_json):
    if not config_json:
        return None
    if isinstance(config_json, dict):
        return config_json
    try:
        return json.loads(config_json)
    except (TypeError, json.JSONDecodeError):
        return None


async def repair_invalid_task_triggers() -> int:
    rows = await execute_query("SELECT id, cron_expression, interval_seconds, is_active FROM scheduled_tasks ORDER BY id ASC")
    repaired = 0
    for row in rows:
        cron_expression, interval_seconds, changed = _normalize_trigger_values(
            row.get("cron_expression"),
            row.get("interval_seconds"),
        )
        if not changed:
            continue
        # If no valid trigger, disable task instead of forcing default
        if cron_expression is None and interval_seconds is None:
            await execute_query(
                "UPDATE scheduled_tasks SET is_active = 0 WHERE id = ?",
                (row["id"],)
            )
            logger.warning("Disabled task #%d (no valid trigger)", row["id"])
        else:
            await execute_query(
                "UPDATE scheduled_tasks SET cron_expression = ?, interval_seconds = ? WHERE id = ?",
                (cron_expression, interval_seconds, row["id"]),
            )
            logger.warning("Repaired invalid trigger config for task #%d", row["id"])
        repaired += 1
    return repaired


def _parse_config_json(row: dict) -> dict:
    if row.get("config_json"):
        try:
            row["config_json"] = json.loads(row["config_json"])
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning("Failed to parse config_json for task #%s: %s", row.get("id"), e)
            row["config_json"] = None
    return row


async def list_tasks():
    rows = await execute_query("SELECT * FROM scheduled_tasks ORDER BY id ASC")
    return [_parse_config_json(r) for r in rows]


async def create_task(name, task_type, cron_expression=None, interval_seconds=None, config_json=None):
    validated = ScheduledTaskCreate(
        name=name,
        task_type=task_type,
        cron_expression=cron_expression,
        interval_seconds=interval_seconds,
        config_json=config_json,
    )
    config_str = json.dumps(validated.config_json) if validated.config_json is not None else None
    task_id = await execute_insert(
        "INSERT INTO scheduled_tasks (name, task_type, cron_expression, interval_seconds, config_json) VALUES (?, ?, ?, ?, ?)",
        (
            validated.name,
            validated.task_type,
            validated.cron_expression,
            validated.interval_seconds,
            config_str,
        ),
    )
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    row = _parse_config_json(rows[0])
    if row.get("is_active", True):
        try:
            _register_job(row)
        except Exception as e:
            await _deactivate_task_after_job_failure(task_id, e)
            raise
    return row


async def get_task(task_id: int):
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return None
    return _parse_config_json(rows[0])


ALLOWED_TASK_UPDATE_FIELDS = {"name", "task_type", "cron_expression", "interval_seconds", "is_active", "config_json"}


async def update_task(task_id: int, fields: dict):
    current = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not current:
        return None

    updates, params = [], []
    data = dict(fields)
    current_row = current[0]

    # Reject NULL for required fields
    if "name" in data and data["name"] is None:
        raise ValueError("name cannot be null")
    if "task_type" in data and data["task_type"] is None:
        raise ValueError("task_type cannot be null")

    # Mode switch support: updating one trigger clears the other.
    if "cron_expression" in data and "interval_seconds" not in data and data["cron_expression"] is not None:
        data["interval_seconds"] = None
    if "interval_seconds" in data and "cron_expression" not in data and data["interval_seconds"] is not None:
        data["cron_expression"] = None

    if "cron_expression" in data or "interval_seconds" in data:
        candidate = ScheduledTaskBase(
            name=data.get("name", current_row.get("name")),
            task_type=data.get("task_type", current_row.get("task_type")),
            cron_expression=data.get("cron_expression", current_row.get("cron_expression")),
            interval_seconds=data.get("interval_seconds", current_row.get("interval_seconds")),
            config_json=data.get("config_json", _parse_row_config(current_row.get("config_json"))),
        )
        if "cron_expression" in data:
            data["cron_expression"] = candidate.cron_expression
        if "interval_seconds" in data:
            data["interval_seconds"] = candidate.interval_seconds

    if "config_json" in data:
        data["config_json"] = json.dumps(data["config_json"]) if data["config_json"] is not None else None

    for field in ALLOWED_TASK_UPDATE_FIELDS:
        if field in data:
            updates.append(f"{field} = ?")
            params.append(data[field])
    if not updates:
        return "no_valid_fields"
    params.append(task_id)
    # H-2 fix: Validate trigger before DB update to ensure atomicity
    # Build the updated row for validation
    validation_row = dict(current_row)
    validation_row.update(data)
    if validation_row.get("is_active"):
        try:
            # Pre-validate trigger configuration
            if validation_row.get("cron_expression"):
                from apscheduler.triggers.cron import CronTrigger
                CronTrigger.from_crontab(validation_row["cron_expression"])
            elif validation_row.get("interval_seconds"):
                from apscheduler.triggers.interval import IntervalTrigger
                IntervalTrigger(seconds=validation_row["interval_seconds"])
            else:
                raise ValueError("Either cron_expression or interval_seconds must be set")
        except Exception as e:
            raise ValueError(f"Invalid trigger configuration: {e}")
    
    await execute_query(
        f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return None
    row = _parse_config_json(rows[0])
    if row.get("is_active"):
        try:
            _register_job(row)
        except Exception as e:
            await _deactivate_task_after_job_failure(task_id, e)
            raise
    else:
        _unregister_job(task_id)
    return row


async def delete_task(task_id: int) -> bool:
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return False
    _unregister_job(task_id)
    await execute_query("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
    return True


async def toggle_task(task_id: int):
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return None
    new_status = not rows[0]["is_active"]
    await execute_query(
        "UPDATE scheduled_tasks SET is_active = ? WHERE id = ?", (new_status, task_id)
    )
    if new_status:
        updated = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
        try:
            _register_job(updated[0])
        except Exception as e:
            await _deactivate_task_after_job_failure(task_id, e)
            raise
    else:
        _unregister_job(task_id)
    return {"is_active": new_status}


async def get_history(limit: int = 50):
    return await execute_query(
        """SELECT l.*, a.name as account_name
           FROM report_logs l
           LEFT JOIN accounts a ON l.account_id = a.id
           ORDER BY l.executed_at DESC LIMIT ?""",
        (limit,),
    )
