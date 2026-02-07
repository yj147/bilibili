import pytest
import asyncio
from backend.database import init_db, execute_query, close_db


@pytest.mark.asyncio
async def test_init_db():
    await init_db()
    rows = await execute_query("SELECT name FROM sqlite_master WHERE type='table'")
    table_names = [r['name'] for r in rows]
    assert 'accounts' in table_names
    assert 'targets' in table_names
    assert 'report_logs' in table_names
    assert 'autoreply_config' in table_names
    assert 'scheduled_tasks' in table_names
    assert 'system_config' in table_names
    await close_db()


@pytest.mark.asyncio
async def test_execute_query_empty():
    await init_db()
    rows = await execute_query("SELECT * FROM accounts")
    assert rows == []
    await close_db()


@pytest.mark.asyncio
async def test_account_crud():
    from backend.database import execute_insert
    await init_db()
    # Create
    aid = await execute_insert(
        "INSERT INTO accounts (name, sessdata, bili_jct) VALUES (?, ?, ?)",
        ('test', 'sess123', 'jct456')
    )
    assert aid == 1
    # Read
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (aid,))
    assert len(rows) == 1
    assert rows[0]['name'] == 'test'
    # Delete
    await execute_query("DELETE FROM accounts WHERE id = ?", (aid,))
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (aid,))
    assert rows == []
    await close_db()
