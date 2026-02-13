import pytest

from backend.database import close_db, execute_insert, execute_query, init_db
from backend.services import account_service


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "new_value"),
    [
        ("sessdata", "sess-new"),
        ("bili_jct", "jct-new"),
        ("buvid3", "buvid3-new"),
        ("buvid4", "buvid4-new"),
    ],
)
async def test_update_account_resets_status_when_credentials_change(field, new_value):
    await init_db()
    last_check_at = "2026-01-01T00:00:00.000Z"
    account_id = await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, buvid3, buvid4, status, last_check_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("acc", "sess-old", "jct-old", "buvid3-old", "buvid4-old", "valid", last_check_at),
    )

    result = await account_service.update_account(account_id, {field: new_value})
    assert result is not None
    assert result["status"] == "unknown"
    assert result["last_check_at"] is None

    rows = await execute_query("SELECT status, last_check_at FROM accounts WHERE id = ?", (account_id,))
    assert rows[0]["status"] == "unknown"
    assert rows[0]["last_check_at"] is None
    await close_db()


@pytest.mark.asyncio
async def test_update_account_keeps_status_when_credentials_not_changed():
    await init_db()
    last_check_at = "2026-01-01T00:00:00.000Z"
    account_id = await execute_insert(
        """INSERT INTO accounts
           (name, sessdata, bili_jct, buvid3, buvid4, status, last_check_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        ("acc", "sess-old", "jct-old", "buvid3-old", "buvid4-old", "valid", last_check_at),
    )

    result = await account_service.update_account(account_id, {"name": "acc-new"})
    assert result is not None
    assert result["status"] == "valid"
    assert result["last_check_at"] == last_check_at

    same_value_result = await account_service.update_account(account_id, {"sessdata": "sess-old"})
    assert same_value_result is not None
    assert same_value_result["status"] == "valid"
    assert same_value_result["last_check_at"] == last_check_at
    await close_db()
