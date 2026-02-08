"""Auto-reply business logic."""
import asyncio

from backend.database import execute_query, execute_insert
from backend.logger import logger

# Whitelist of fields allowed in dynamic UPDATE
ALLOWED_UPDATE_FIELDS = {"keyword", "response", "priority", "is_active"}

# Global service state
_autoreply_running = False
_autoreply_task = None


# ── CRUD ──────────────────────────────────────────────────────────────────

async def list_configs():
    return await execute_query(
        "SELECT * FROM autoreply_config ORDER BY priority DESC, id ASC"
    )


async def create_config(keyword, response, priority=0):
    config_id = await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority) VALUES (?, ?, ?)",
        (keyword, response, priority),
    )
    rows = await execute_query("SELECT * FROM autoreply_config WHERE id = ?", (config_id,))
    return rows[0]


async def update_config(config_id: int, fields: dict):
    updates = []
    params = []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return None
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
    }


async def start_service(interval: int = 30):
    global _autoreply_running, _autoreply_task

    if _autoreply_running:
        return False  # already running

    _autoreply_running = True

    async def poll_loop():
        from backend.core.bilibili_client import BilibiliClient
        from backend.core.bilibili_auth import BilibiliAuth

        while _autoreply_running:
            try:
                accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1")
                configs = await execute_query(
                    "SELECT * FROM autoreply_config WHERE is_active = 1 ORDER BY priority DESC"
                )

                default_reply = next(
                    (c["response"] for c in configs if c["keyword"] is None),
                    "您好，稍后回复。",
                )
                keyword_map = {c["keyword"]: c["response"] for c in configs if c["keyword"]}

                for account in accounts:
                    auth = BilibiliAuth.from_db_account(account)
                    async with BilibiliClient(auth, account_index=0) as client:
                        try:
                            sessions = await client.get_recent_sessions()
                            if sessions.get("code") == 0:
                                for session in sessions.get("data", {}).get("session_list", []) or []:
                                    last_msg = session.get("last_msg", {})
                                    msg_ts = last_msg.get("timestamp", 0)

                                    talker_id = session.get("talker_id")
                                    own_uid = account.get("uid", 0)
                                    if str(talker_id) == str(own_uid):
                                        continue

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

                                    logger.info("[AutoReply][%s] Replying to %s: %s", account["name"], talker_id, reply_text)
                                    await client.send_private_message(talker_id, reply_text)

                                    await execute_query(
                                        "INSERT INTO autoreply_state (account_id, talker_id, last_msg_ts) VALUES (?, ?, ?) "
                                        "ON CONFLICT(account_id, talker_id) DO UPDATE SET last_msg_ts = excluded.last_msg_ts",
                                        (account["id"], talker_id, msg_ts),
                                    )
                        except Exception as acc_err:
                            logger.error("[AutoReply][%s] Error: %s", account["name"], acc_err)

            except Exception as e:
                logger.error("Auto-reply error: %s", e)

            await asyncio.sleep(interval)

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
