"""Shared auto-reply polling business logic."""

import asyncio
from collections.abc import Awaitable, Callable
import json

from backend.database import execute_insert, execute_query
from backend.logger import logger

ACTIVE_AUTOREPLY_CONFIGS_QUERY = (
    "SELECT * FROM autoreply_config "
    "WHERE is_active = 1 "
    "ORDER BY priority DESC, id ASC"
)
STANDALONE_AUTOREPLY_ACCOUNTS_QUERY = "SELECT * FROM accounts WHERE is_active = 1 AND status IN ('valid', 'expiring')"
SCHEDULER_AUTOREPLY_ACCOUNTS_QUERY = (
    "SELECT * FROM accounts WHERE is_active = 1 AND status IN ('valid', 'expiring')"
)
FALLBACK_AUTOREPLY_TEXT = "您好，稍后回复。"
AUTOREPLY_SEND_DELAY = 3.0  # seconds between replies to avoid B站 rate limiting


ReplySentCallback = Callable[[dict, int | str, str, dict], Awaitable[None]]


def match_reply_rule(msg_content: str, configs: list[dict]) -> str:
    """Match first keyword rule in configured order; fallback to default reply."""
    default_reply = FALLBACK_AUTOREPLY_TEXT
    has_default_reply = False

    for config in configs:
        keyword = config["keyword"]
        if keyword is None:
            if not has_default_reply:
                default_reply = config["response"]
                has_default_reply = True
            continue
        if keyword and keyword in msg_content:
            return config["response"]

    return default_reply


def _apply_batch_limit(items: list, limit: int) -> list:
    if limit <= 0:
        return items
    return items[:limit]


async def run_autoreply_poll_cycle(
    account_query: str,
    on_reply_sent: ReplySentCallback | None = None,
    account_batch_size: int = 0,
    session_batch_size: int = 0,
) -> None:
    """Run one auto-reply polling cycle for the given account query."""
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.core.bilibili_client import BilibiliClient

    accounts = await execute_query(account_query)
    configs = await execute_query(ACTIVE_AUTOREPLY_CONFIGS_QUERY)

    for account in _apply_batch_limit(accounts, account_batch_size):
        try:
            own_uid = account.get("uid")
            if not own_uid:
                logger.warning("[AutoReply][%s] Account has no UID, skipping", account.get("name", "?"))
                continue

            auth = BilibiliAuth.from_db_account(account)
            async with BilibiliClient(auth, account_index=0) as client:
                sessions = await client.get_recent_sessions()
                if sessions.get("code") != 0:
                    continue

                session_list = sessions.get("data", {}).get("session_list", []) or []
                for session in _apply_batch_limit(session_list, session_batch_size):
                    last_msg = session.get("last_msg", {})
                    msg_ts = last_msg.get("timestamp", 0)

                    talker_id = session.get("talker_id")
                    if str(talker_id) == str(own_uid):
                        continue

                    # Skip if last message was sent by ourselves (avoid reply loop)
                    sender_uid = last_msg.get("sender_uid", 0)
                    if str(sender_uid) == str(own_uid):
                        continue

                    state_rows = await execute_query(
                        "SELECT last_msg_ts FROM autoreply_state WHERE account_id = ? AND talker_id = ?",
                        (account["id"], talker_id),
                    )
                    last_replied_ts = state_rows[0]["last_msg_ts"] if state_rows else 0
                    if msg_ts <= last_replied_ts:
                        continue

                    msg_content = str(last_msg.get("content", ""))
                    reply_text = match_reply_rule(msg_content, configs)

                    logger.info("[AutoReply][%s] Replying to %s: %s", account["name"], talker_id, reply_text)
                    send_result = await client.send_private_message(talker_id, reply_text)
                    send_success = send_result.get("code") == 0

                    await execute_insert(
                        """INSERT INTO report_logs (
                               target_id, account_id, action, request_data, response_data, success, error_message, executed_at
                           )
                           VALUES (?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%dT%H:%M:%fZ','now'))""",
                        (
                            None,
                            account["id"],
                            "autoreply",
                            json.dumps({"talker_id": talker_id, "reply": reply_text}),
                            json.dumps(send_result),
                            send_success,
                            None if send_success else send_result.get("message", "Unknown error"),
                        ),
                    )

                    # Always update autoreply_state to avoid retry loops on persistent failures
                    await execute_query(
                        "INSERT INTO autoreply_state (account_id, talker_id, last_msg_ts) VALUES (?, ?, ?) "
                        "ON CONFLICT(account_id, talker_id) DO UPDATE SET last_msg_ts = excluded.last_msg_ts",
                        (account["id"], talker_id, msg_ts),
                    )

                    if not send_success:
                        send_code = send_result.get("code")
                        # Rate limited by B站 — stop processing this account entirely
                        if send_code == 21046:
                            logger.warning("[AutoReply][%s] Rate limited (21046), skipping remaining sessions", account["name"])
                            break
                        continue

                    if on_reply_sent:
                        await on_reply_sent(account, talker_id, reply_text, send_result)

                    # Delay between replies to avoid B站 rate limiting
                    await asyncio.sleep(AUTOREPLY_SEND_DELAY)
        except Exception as acc_err:
            logger.error("[AutoReply][%s] Error: %s", account.get("name", "?"), acc_err)
