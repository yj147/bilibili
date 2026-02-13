"""Auto-reply business logic."""
import asyncio
from datetime import datetime, timezone

from backend.config import (
    AUTOREPLY_ACCOUNT_BATCH_SIZE,
    AUTOREPLY_POLL_INTERVAL_SECONDS,
    AUTOREPLY_POLL_MIN_INTERVAL_SECONDS,
    AUTOREPLY_SESSION_BATCH_SIZE,
)
from backend.database import execute_in_transaction, execute_query, execute_insert
from backend.logger import logger
from backend.services.autoreply_polling import (
    ACTIVE_AUTOREPLY_CONFIGS_QUERY,
    STANDALONE_AUTOREPLY_ACCOUNTS_QUERY,
    match_reply_rule,
    run_autoreply_poll_cycle,
)

# Whitelist of fields allowed in dynamic UPDATE
ALLOWED_UPDATE_FIELDS = {"keyword", "response", "priority", "is_active"}

# Global service state for standalone mode.
_autoreply_running = False
_autoreply_task = None
_last_poll_at = None

# Backward-compatible alias for existing imports/tests.
_match_reply_rule = match_reply_rule

AUTOREPLY_POLL_INTERVAL_KEY = "autoreply_poll_interval_seconds"
AUTOREPLY_POLL_MIN_INTERVAL_KEY = "autoreply_poll_min_interval_seconds"
AUTOREPLY_ACCOUNT_BATCH_SIZE_KEY = "autoreply_account_batch_size"
AUTOREPLY_SESSION_BATCH_SIZE_KEY = "autoreply_session_batch_size"


def _utc_now_iso() -> str:
    """Return current UTC timestamp in explicit-Z ISO format."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


async def _resolve_poll_settings(startup_interval: int | None = None) -> dict[str, int]:
    """Load poll settings from system_config with sane fallbacks."""
    from backend.services.config_service import get_config

    interval_fallback = (
        startup_interval
        if startup_interval is not None
        else AUTOREPLY_POLL_INTERVAL_SECONDS
    )

    try:
        min_interval_raw = await get_config(AUTOREPLY_POLL_MIN_INTERVAL_KEY)
        min_interval = max(
            _coerce_int(min_interval_raw, AUTOREPLY_POLL_MIN_INTERVAL_SECONDS), 1
        )

        poll_interval_raw = await get_config(AUTOREPLY_POLL_INTERVAL_KEY)
        poll_interval = max(_coerce_int(poll_interval_raw, interval_fallback), min_interval)

        account_batch_raw = await get_config(AUTOREPLY_ACCOUNT_BATCH_SIZE_KEY)
        account_batch_size = max(
            _coerce_int(account_batch_raw, AUTOREPLY_ACCOUNT_BATCH_SIZE), 0
        )

        session_batch_raw = await get_config(AUTOREPLY_SESSION_BATCH_SIZE_KEY)
        session_batch_size = max(
            _coerce_int(session_batch_raw, AUTOREPLY_SESSION_BATCH_SIZE), 0
        )
    except Exception as config_err:
        logger.warning("Failed to load auto-reply poll settings: %s", config_err)
        min_interval = AUTOREPLY_POLL_MIN_INTERVAL_SECONDS
        poll_interval = max(interval_fallback, min_interval)
        account_batch_size = AUTOREPLY_ACCOUNT_BATCH_SIZE
        session_batch_size = AUTOREPLY_SESSION_BATCH_SIZE

    return {
        "poll_interval_seconds": poll_interval,
        "account_batch_size": account_batch_size,
        "session_batch_size": session_batch_size,
    }


# ── CRUD ──────────────────────────────────────────────────────────────────

async def list_configs():
    return await execute_query(
        "SELECT * FROM autoreply_config ORDER BY priority DESC, id ASC"
    )


async def create_config(keyword, response, priority=0):
    if keyword is None:
        return await upsert_default_reply(response=response, priority=priority)

    config_id = await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority) VALUES (?, ?, ?)",
        (keyword, response, priority),
    )
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    return rows[0]


async def upsert_default_reply(response: str, priority: int = -1):
    async def _operation(conn):
        cursor = await conn.execute(
            "SELECT id FROM autoreply_config WHERE keyword IS NULL ORDER BY id ASC"
        )
        existing = await cursor.fetchall()

        if existing:
            config_id = existing[0]["id"]
            await conn.execute(
                "UPDATE autoreply_config SET response = ?, priority = ?, is_active = 1 WHERE id = ?",
                (response, priority, config_id),
            )
            if len(existing) > 1:
                duplicate_ids = [row["id"] for row in existing[1:]]
                placeholders = ",".join("?" for _ in duplicate_ids)
                await conn.execute(
                    f"DELETE FROM autoreply_config WHERE id IN ({placeholders})",
                    tuple(duplicate_ids),
                )
        else:
            insert_cursor = await conn.execute(
                "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (NULL, ?, ?, 1)",
                (response, priority),
            )
            config_id = insert_cursor.lastrowid

        row_cursor = await conn.execute("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
        row = await row_cursor.fetchone()
        return dict(row)

    return await execute_in_transaction(_operation)


async def update_config(config_id: int, fields: dict):
    updates = []
    params = []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return "no_valid_fields"
    params.append(config_id)
    await execute_query(
        f"UPDATE autoreply_config SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    return rows[0] if rows else None


async def delete_config(config_id: int) -> bool:
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    if not rows:
        return False
    await execute_query("DELETE FROM autoreply_config WHERE id = ?", (config_id,))
    return True


# ── Status / Service Control ──────────────────────────────────────────────

async def get_status():
    accounts = await execute_query(
        "SELECT COUNT(*) as count FROM accounts WHERE is_active = 1"
    )
    return {
        "is_running": _autoreply_running,
        "active_accounts": accounts[0]["count"] if accounts else 0,
        "last_poll_at": _last_poll_at,
    }


def is_running() -> bool:
    """Whether standalone auto-reply loop is running."""
    return _autoreply_running


async def start_service(interval: int = AUTOREPLY_POLL_INTERVAL_SECONDS):
    global _autoreply_running, _autoreply_task

    if _autoreply_running:
        return False  # already running

    # Guard: reject standalone mode when active autoreply scheduler task exists
    try:
        from backend.services.scheduler_service import has_active_autoreply_poll_task
        if await has_active_autoreply_poll_task():
            logger.warning(
                "Found active scheduled task (task_type='autoreply_poll', is_active=1). "
                "Refusing to start standalone autoreply service to avoid double-replies."
            )
            return False
    except Exception:
        pass  # scheduler not initialized yet, safe to proceed

    if interval != AUTOREPLY_POLL_INTERVAL_SECONDS:
        try:
            from backend.services.config_service import set_config

            await set_config(AUTOREPLY_POLL_INTERVAL_KEY, int(interval))
        except Exception as config_err:
            logger.warning("Failed to persist auto-reply interval override: %s", config_err)

    _autoreply_running = True

    async def poll_loop():
        global _last_poll_at

        while _autoreply_running:
            settings = await _resolve_poll_settings(startup_interval=interval)
            poll_interval = settings["poll_interval_seconds"]
            account_batch_size = settings["account_batch_size"]
            session_batch_size = settings["session_batch_size"]

            try:
                _last_poll_at = _utc_now_iso()
                await run_autoreply_poll_cycle(
                    account_query=STANDALONE_AUTOREPLY_ACCOUNTS_QUERY,
                    account_batch_size=account_batch_size,
                    session_batch_size=session_batch_size,
                )
            except Exception as e:
                logger.error("Auto-reply error: %s", e)

            await asyncio.sleep(poll_interval)

    _autoreply_task = asyncio.create_task(poll_loop())
    return True


async def stop_service():
    global _autoreply_running, _autoreply_task

    if not _autoreply_running:
        return False

    _autoreply_running = False
    if _autoreply_task:
        _autoreply_task.cancel()
        _autoreply_task = None
    return True
