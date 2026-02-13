import asyncio
import json
from contextlib import suppress

import pytest

import backend.core.bilibili_client as bilibili_client_module
import backend.services.autoreply_service as autoreply_service
import backend.services.scheduler_service as scheduler_service
from backend.database import close_db, execute_insert, execute_query, init_db
from backend.services.autoreply_polling import (
    STANDALONE_AUTOREPLY_ACCOUNTS_QUERY,
    run_autoreply_poll_cycle,
)


async def _reset_autoreply_runtime_state() -> None:
    autoreply_service._autoreply_running = False
    task = autoreply_service._autoreply_task
    if task and not task.done():
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
    autoreply_service._autoreply_task = None
    autoreply_service._last_poll_at = None


@pytest.mark.asyncio
async def test_service_start_stop_lifecycle(monkeypatch):
    await init_db()
    await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc-start-stop", "sess", "jct", 10001, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "默认回复", 0, 1),
    )

    poll_called = asyncio.Event()
    original_sleep = asyncio.sleep

    async def fake_poll_cycle(*, account_query, on_reply_sent=None, account_batch_size=0, session_batch_size=0):
        assert account_query == STANDALONE_AUTOREPLY_ACCOUNTS_QUERY
        poll_called.set()

    async def fake_sleep(_seconds):
        await original_sleep(0)

    monkeypatch.setattr(autoreply_service, "run_autoreply_poll_cycle", fake_poll_cycle)
    monkeypatch.setattr(autoreply_service.asyncio, "sleep", fake_sleep)

    await _reset_autoreply_runtime_state()

    try:
        started = await autoreply_service.start_service(interval=1)
        assert started is True

        await asyncio.wait_for(poll_called.wait(), timeout=1.0)

        status = await autoreply_service.get_status()
        assert status["is_running"] is True
        assert status["active_accounts"] == 1
        assert status["last_poll_at"] is not None
        assert status["last_poll_at"].endswith("Z")

        stopped = await autoreply_service.stop_service()
        assert stopped is True
        assert autoreply_service.is_running() is False
        assert autoreply_service._autoreply_task is None

        stopped_again = await autoreply_service.stop_service()
        assert stopped_again is False
    finally:
        await _reset_autoreply_runtime_state()
        await close_db()


@pytest.mark.asyncio
async def test_poll_cycle_matches_keyword_and_default_rules(monkeypatch):
    await init_db()
    account_id = await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc-rules", "sess", "jct", 20001, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        ("合作", "商务合作请发邮箱", 10, 1),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "感谢来信", 0, 1),
    )

    sent_messages = []

    class MockBilibiliClient:
        def __init__(self, auth, account_index=0):
            self.auth = auth
            self.account_index = account_index

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_recent_sessions(self):
            return {
                "code": 0,
                "data": {
                    "session_list": [
                        {
                            "talker_id": 30001,
                            "last_msg": {"timestamp": 1700000001, "content": "想要合作"},
                        },
                        {
                            "talker_id": 30002,
                            "last_msg": {"timestamp": 1700000002, "content": "你好"},
                        },
                    ]
                },
            }

        async def send_private_message(self, talker_id, content):
            sent_messages.append((talker_id, content))
            return {"code": 0, "message": "ok"}

    monkeypatch.setattr(bilibili_client_module, "BilibiliClient", MockBilibiliClient)

    try:
        await run_autoreply_poll_cycle(account_query=STANDALONE_AUTOREPLY_ACCOUNTS_QUERY)

        assert sent_messages == [
            (30001, "商务合作请发邮箱"),
            (30002, "感谢来信"),
        ]

        state_rows = await execute_query(
            "SELECT talker_id, last_msg_ts FROM autoreply_state WHERE account_id = ? ORDER BY talker_id ASC",
            (account_id,),
        )
        assert state_rows == [
            {"talker_id": 30001, "last_msg_ts": 1700000001},
            {"talker_id": 30002, "last_msg_ts": 1700000002},
        ]
    finally:
        await close_db()


@pytest.mark.asyncio
async def test_poll_cycle_sends_reply_and_persists_log_once_for_same_message(monkeypatch):
    await init_db()
    account_id = await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc-send", "sess", "jct", 40001, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "默认兜底回复", 0, 1),
    )

    send_calls = []

    class MockBilibiliClient:
        def __init__(self, auth, account_index=0):
            self.auth = auth
            self.account_index = account_index

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_recent_sessions(self):
            return {
                "code": 0,
                "data": {
                    "session_list": [
                        {
                            "talker_id": 50001,
                            "last_msg": {"timestamp": 1700001000, "content": "hi"},
                        }
                    ]
                },
            }

        async def send_private_message(self, talker_id, content):
            send_calls.append((talker_id, content))
            return {"code": 0, "message": "ok"}

    monkeypatch.setattr(bilibili_client_module, "BilibiliClient", MockBilibiliClient)

    try:
        await run_autoreply_poll_cycle(account_query=STANDALONE_AUTOREPLY_ACCOUNTS_QUERY)
        await run_autoreply_poll_cycle(account_query=STANDALONE_AUTOREPLY_ACCOUNTS_QUERY)

        assert send_calls == [(50001, "默认兜底回复")]

        log_rows = await execute_query(
            "SELECT success, request_data, response_data FROM report_logs WHERE account_id = ? AND action = 'autoreply'",
            (account_id,),
        )
        assert len(log_rows) == 1
        assert bool(log_rows[0]["success"]) is True

        request_payload = json.loads(log_rows[0]["request_data"])
        assert request_payload["talker_id"] == 50001
        assert request_payload["reply"] == "默认兜底回复"

        response_payload = json.loads(log_rows[0]["response_data"])
        assert response_payload["code"] == 0

        state_rows = await execute_query(
            "SELECT last_msg_ts FROM autoreply_state WHERE account_id = ? AND talker_id = ?",
            (account_id, 50001),
        )
        assert state_rows == [{"last_msg_ts": 1700001000}]
    finally:
        await close_db()


@pytest.mark.asyncio
async def test_start_service_rejects_when_active_scheduler_task_exists():
    await init_db()
    await execute_insert(
        """INSERT INTO scheduled_tasks
           (name, task_type, interval_seconds, is_active)
           VALUES (?, ?, ?, ?)""",
        ("autoreply-job", "autoreply_poll", 30, 1),
    )

    await _reset_autoreply_runtime_state()

    try:
        assert await scheduler_service.has_active_autoreply_poll_task() is True

        started = await autoreply_service.start_service(interval=10)
        assert started is False
        assert autoreply_service.is_running() is False
        assert autoreply_service._autoreply_task is None
    finally:
        await _reset_autoreply_runtime_state()
        await close_db()
