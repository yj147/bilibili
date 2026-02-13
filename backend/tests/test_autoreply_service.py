import asyncio
from contextlib import suppress

import pytest

import backend.core.bilibili_client as bilibili_client_module
import backend.services.autoreply_service as autoreply_service
from backend.database import close_db, execute_insert, execute_query, init_db
from backend.services.config_service import set_config


@pytest.mark.asyncio
async def test_upsert_default_reply_keeps_single_null_keyword_row_under_concurrency():
    await init_db()
    try:
        await asyncio.gather(
            *[
                autoreply_service.upsert_default_reply(f"default reply {i}")
                for i in range(20)
            ]
        )

        rows = await execute_query(
            "SELECT id, response FROM autoreply_config WHERE keyword IS NULL ORDER BY id ASC"
        )
        assert len(rows) == 1
        assert rows[0]["response"].startswith("default reply ")
    finally:
        await close_db()


@pytest.mark.asyncio
async def test_match_reply_rule_keeps_creation_order_for_same_priority_rules():
    await init_db()
    try:
        first_id = await execute_insert(
            "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
            ("alpha", "reply alpha", 100, 1),
        )
        second_id = await execute_insert(
            "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
            ("beta", "reply beta", 100, 1),
        )
        await execute_insert(
            "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
            (None, "default reply", 0, 1),
        )

        for _ in range(3):
            configs = await execute_query(autoreply_service.ACTIVE_AUTOREPLY_CONFIGS_QUERY)
            same_priority_rule_ids = [
                row["id"] for row in configs if row["priority"] == 100 and row["keyword"] is not None
            ]
            assert same_priority_rule_ids == [first_id, second_id]
            assert autoreply_service._match_reply_rule("alpha beta", configs) == "reply alpha"
    finally:
        await close_db()


@pytest.mark.asyncio
async def test_send_failure_always_updates_dedup_state(monkeypatch):
    """State is always updated even on send failure to avoid retry loops on persistent errors."""
    await init_db()
    account_id = await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc", "sess", "jct", 12345, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "default reply", 0, 1),
    )

    send_calls = {"count": 0}
    msg_ts = 1700000000

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
                            "talker_id": 67890,
                            "last_msg": {"timestamp": msg_ts, "content": "hello", "sender_uid": 67890},
                        }
                    ]
                },
            }

        async def send_private_message(self, talker_id, content):
            send_calls["count"] += 1
            return {"code": -1, "message": "send failed"}

    sleep_state = {"calls": 0}
    original_sleep = asyncio.sleep

    async def fake_sleep(_seconds):
        sleep_state["calls"] += 1
        if sleep_state["calls"] >= 2:
            autoreply_service._autoreply_running = False
        await original_sleep(0)

    monkeypatch.setattr(bilibili_client_module, "BilibiliClient", MockBilibiliClient)
    monkeypatch.setattr(autoreply_service.asyncio, "sleep", fake_sleep)

    autoreply_service._autoreply_running = False
    autoreply_service._autoreply_task = None

    try:
        started = await autoreply_service.start_service(interval=10)
        assert started is True
        assert autoreply_service._autoreply_task is not None
        await autoreply_service._autoreply_task

        # Only 1 send: second cycle skips because state was already updated on first failure
        assert send_calls["count"] == 1

        state_rows = await execute_query(
            "SELECT last_msg_ts FROM autoreply_state WHERE account_id = ?",
            (account_id,),
        )
        assert len(state_rows) == 1
        assert state_rows[0]["last_msg_ts"] == msg_ts

        status = await autoreply_service.get_status()
        assert status["last_poll_at"] is not None
        assert status["last_poll_at"].endswith("Z")

        log_rows = await execute_query(
            "SELECT executed_at FROM report_logs WHERE account_id = ? AND action = 'autoreply'",
            (account_id,),
        )
        assert len(log_rows) == 1
        assert all(row["executed_at"].endswith("Z") for row in log_rows)
    finally:
        autoreply_service._autoreply_running = False
        task = autoreply_service._autoreply_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        autoreply_service._autoreply_task = None
        await close_db()


@pytest.mark.asyncio
async def test_start_service_rejects_active_autoreply_poll_task():
    await init_db()
    await execute_insert(
        """INSERT INTO scheduled_tasks
           (name, task_type, interval_seconds, is_active)
           VALUES (?, ?, ?, ?)""",
        ("每日巡检", "autoreply_poll", 30, 1),
    )

    autoreply_service._autoreply_running = False
    autoreply_service._autoreply_task = None

    try:
        started = await autoreply_service.start_service(interval=10)
        assert started is False
        assert autoreply_service._autoreply_running is False
        assert autoreply_service._autoreply_task is None
    finally:
        autoreply_service._autoreply_running = False
        task = autoreply_service._autoreply_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        autoreply_service._autoreply_task = None
        await close_db()


@pytest.mark.asyncio
async def test_start_service_respects_configured_batch_sizes(monkeypatch):
    await init_db()
    await set_config("autoreply_account_batch_size", 1)
    await set_config("autoreply_session_batch_size", 1)

    await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc-1", "sess-1", "jct-1", 10001, 1, "valid"),
    )
    await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc-2", "sess-2", "jct-2", 20002, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "default reply", 0, 1),
    )

    sent_to = []

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
                        {"talker_id": 30001, "last_msg": {"timestamp": 1700000001, "content": "hello 1", "sender_uid": 30001}},
                        {"talker_id": 30002, "last_msg": {"timestamp": 1700000002, "content": "hello 2", "sender_uid": 30002}},
                    ]
                },
            }

        async def send_private_message(self, talker_id, _content):
            sent_to.append(talker_id)
            return {"code": 0}

    original_sleep = asyncio.sleep

    async def fake_sleep(_seconds):
        autoreply_service._autoreply_running = False
        await original_sleep(0)

    monkeypatch.setattr(bilibili_client_module, "BilibiliClient", MockBilibiliClient)
    monkeypatch.setattr(autoreply_service.asyncio, "sleep", fake_sleep)

    autoreply_service._autoreply_running = False
    autoreply_service._autoreply_task = None

    try:
        started = await autoreply_service.start_service(interval=10)
        assert started is True
        assert autoreply_service._autoreply_task is not None
        await autoreply_service._autoreply_task

        assert sent_to == [30001]
    finally:
        autoreply_service._autoreply_running = False
        task = autoreply_service._autoreply_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        autoreply_service._autoreply_task = None
        await close_db()


@pytest.mark.asyncio
async def test_runtime_interval_config_update_applies_without_restart(monkeypatch):
    await init_db()
    await set_config("autoreply_poll_interval_seconds", 11)
    await set_config("autoreply_poll_min_interval_seconds", 1)

    await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, uid, is_active, status)
           VALUES (?, ?, ?, ?, ?, ?)""",
        ("acc", "sess", "jct", 12345, 1, "valid"),
    )
    await execute_insert(
        "INSERT INTO autoreply_config (keyword, response, priority, is_active) VALUES (?, ?, ?, ?)",
        (None, "default reply", 0, 1),
    )

    sleep_calls = []
    original_sleep = asyncio.sleep

    class MockBilibiliClient:
        def __init__(self, auth, account_index=0):
            self.auth = auth
            self.account_index = account_index

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get_recent_sessions(self):
            return {"code": 0, "data": {"session_list": []}}

        async def send_private_message(self, talker_id, content):
            return {"code": 0}

    async def fake_sleep(seconds):
        sleep_calls.append(seconds)
        if len(sleep_calls) == 1:
            await set_config("autoreply_poll_interval_seconds", 17)
        if len(sleep_calls) >= 2:
            autoreply_service._autoreply_running = False
        await original_sleep(0)

    monkeypatch.setattr(bilibili_client_module, "BilibiliClient", MockBilibiliClient)
    monkeypatch.setattr(autoreply_service.asyncio, "sleep", fake_sleep)

    autoreply_service._autoreply_running = False
    autoreply_service._autoreply_task = None

    try:
        started = await autoreply_service.start_service(interval=30)
        assert started is True
        assert autoreply_service._autoreply_task is not None
        await autoreply_service._autoreply_task

        assert sleep_calls[:2] == [11, 17]
    finally:
        autoreply_service._autoreply_running = False
        task = autoreply_service._autoreply_task
        if task and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        autoreply_service._autoreply_task = None
        await close_db()
