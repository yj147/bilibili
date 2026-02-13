"""Scheduler business logic."""
import json
import asyncio
import random

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from backend.database import execute_query, execute_insert
from backend.config import MIN_DELAY, MAX_DELAY
from backend.logger import logger

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler():
    """Start the APScheduler and load active tasks from DB."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE is_active = 1")
    for row in rows:
        _register_job(row)
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
    """Stop the APScheduler."""
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")


# ── Job functions ─────────────────────────────────────────────────────────

async def _run_report_batch(task_id: int):
    """Job function: execute pending reports using all active accounts.
    Delegates to report_service.execute_batch_reports which handles cooldown,
    12019 retry, valid-account filtering, and early exit on success."""
    from backend.services.report_service import execute_batch_reports
    from backend.api.websocket import broadcast_log

    await broadcast_log("scheduler", f"Task #{task_id}: starting batch reports")
    result, error = await execute_batch_reports(target_ids=None, account_ids=None)
    if error:
        await broadcast_log("scheduler", f"Task #{task_id}: {error}")
    else:
        await broadcast_log("scheduler", f"Task #{task_id} completed: {result['successful']}/{result['total_targets']} successful")

    await execute_query(
        "UPDATE scheduled_tasks SET last_run_at = datetime('now') WHERE id = ?", (task_id,)
    )


async def _run_autoreply_poll(task_id: int):
    """Job function: poll private messages and auto-reply."""
    from backend.services.autoreply_service import _autoreply_running
    if _autoreply_running:
        logger.warning(
            "Standalone autoreply service is running. "
            "Skipping scheduler autoreply_poll (task #%d) to avoid double-replies.",
            task_id,
        )
        return

    from backend.core.bilibili_client import BilibiliClient
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.api.websocket import broadcast_log

    accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status IN ('valid', 'expiring')")
    configs = await execute_query(
        "SELECT * FROM autoreply_config WHERE is_active = 1 ORDER BY priority DESC"
    )
    default_reply = next(
        (c["response"] for c in configs if c["keyword"] is None), "您好，稍后回复。"
    )
    keyword_map = {c["keyword"]: c["response"] for c in configs if c["keyword"]}

    for account in accounts:
        try:
            auth = BilibiliAuth.from_db_account(account)
            async with BilibiliClient(auth, account_index=0) as client:
                sessions = await client.get_recent_sessions()
                if sessions.get("code") == 0:
                    for session in sessions.get("data", {}).get("session_list", []) or []:
                        talker_id = session.get("talker_id")
                        if str(talker_id) == str(account.get("uid", 0)):
                            continue
                        last_msg = session.get("last_msg", {})
                        msg_ts = last_msg.get("timestamp", 0)
                        state_rows = await execute_query(
                            "SELECT last_msg_ts FROM autoreply_state WHERE account_id = ? AND talker_id = ?",
                            (account["id"], talker_id),
                        )
                        last_replied_ts = state_rows[0]["last_msg_ts"] if state_rows else 0
                        if msg_ts <= last_replied_ts:
                            continue
                        msg_content = str(last_msg.get("content", ""))
                        reply_text = default_reply
                        for kw, resp in keyword_map.items():
                            if kw in msg_content:
                                reply_text = resp
                                break
                        await client.send_private_message(talker_id, reply_text)
                        # Log to report_logs for unified activity tracking
                        await execute_insert(
                            """INSERT INTO report_logs (target_id, account_id, action, request_data, response_data, success, error_message)
                               VALUES (?, ?, ?, ?, ?, ?, ?)""",
                            (
                                None, account["id"], "autoreply",
                                json.dumps({"talker_id": talker_id, "reply": reply_text}),
                                None, True, None,
                            ),
                        )
                        await execute_query(
                            "INSERT INTO autoreply_state (account_id, talker_id, last_msg_ts) VALUES (?, ?, ?) "
                            "ON CONFLICT(account_id, talker_id) DO UPDATE SET last_msg_ts = excluded.last_msg_ts",
                            (account["id"], talker_id, msg_ts),
                        )
                        await broadcast_log("autoreply", f"[{account['name']}] Replied to {talker_id}")
        except Exception as e:
            logger.error("[Scheduler AutoReply][%s] Error: %s", account.get("name", "?"), e)
    await execute_query(
        "UPDATE scheduled_tasks SET last_run_at = datetime('now') WHERE id = ?", (task_id,)
    )




async def _run_cookie_health_check(task_id: int):
    """Job function: check all active accounts' cookie health and auto-refresh if needed."""
    from backend.services.auth_service import check_cookie_refresh_needed, refresh_account_cookies
    from backend.api.websocket import broadcast_log

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
                else:
                    await broadcast_log("auth", f"[{account['name']}] No refresh_token. QR re-login required.")
                    await execute_query(
                        "UPDATE accounts SET status = 'expiring' WHERE id = ?",
                        (account["id"],),
                    )
        except Exception as e:
            logger.error("[Cookie Health][%s] Error: %s", account.get("name", "?"), e)
    await execute_query(
        "UPDATE scheduled_tasks SET last_run_at = datetime('now') WHERE id = ?", (task_id,)
    )


async def _run_log_cleanup(task_id: int):
    """Job function: delete old report_logs based on system config."""
    from backend.services.config_service import get_config
    from backend.api.websocket import broadcast_log

    auto_clean = await get_config("auto_clean_logs")
    if auto_clean not in (True, "true", "1"):
        logger.info("[Log Cleanup] auto_clean_logs is disabled, skipping")
        await execute_query(
            "UPDATE scheduled_tasks SET last_run_at = datetime('now') WHERE id = ?", (task_id,)
        )
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

    await execute_query(
        "UPDATE scheduled_tasks SET last_run_at = datetime('now') WHERE id = ?", (task_id,)
    )

_JOB_FUNCTIONS = {"report_batch": _run_report_batch, "autoreply_poll": _run_autoreply_poll, "cookie_health_check": _run_cookie_health_check, "log_cleanup": _run_log_cleanup}


# ── Job registration ──────────────────────────────────────────────────────

def _register_job(task_row: dict):
    """Register a DB task row as an APScheduler job."""
    scheduler = get_scheduler()
    job_id = f"task_{task_row['id']}"
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
    func = _JOB_FUNCTIONS.get(task_row["task_type"])
    if not func:
        logger.warning("Unknown task_type '%s' for task #%d, skipping job registration", task_row["task_type"], task_row["id"])
        return
    if task_row.get("cron_expression"):
        trigger = CronTrigger.from_crontab(task_row["cron_expression"])
    elif task_row.get("interval_seconds"):
        trigger = IntervalTrigger(seconds=task_row["interval_seconds"])
    else:
        return
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


# ── CRUD ──────────────────────────────────────────────────────────────────

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
    config_str = json.dumps(config_json) if config_json else None
    task_id = await execute_insert(
        "INSERT INTO scheduled_tasks (name, task_type, cron_expression, interval_seconds, config_json) VALUES (?, ?, ?, ?, ?)",
        (name, task_type, cron_expression, interval_seconds, config_str),
    )
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    row = _parse_config_json(rows[0])
    if row.get("is_active", True):
        _register_job(row)
    return row


async def get_task(task_id: int):
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return None
    return _parse_config_json(rows[0])


ALLOWED_TASK_UPDATE_FIELDS = {"name", "task_type", "cron_expression", "interval_seconds", "is_active", "config_json"}


async def update_task(task_id: int, fields: dict):
    updates, params = [], []
    data = dict(fields)
    if "config_json" in data and data["config_json"] is not None:
        data["config_json"] = json.dumps(data["config_json"])
    for field, value in data.items():
        if value is not None and field in ALLOWED_TASK_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return "no_valid_fields"
    params.append(task_id)
    await execute_query(
        f"UPDATE scheduled_tasks SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )
    rows = await execute_query("SELECT * FROM scheduled_tasks WHERE id = ?", (task_id,))
    if not rows:
        return None
    row = _parse_config_json(rows[0])
    if row.get("is_active"):
        _register_job(row)
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
        _register_job(updated[0])
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
