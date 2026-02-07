"""Account business logic."""
from backend.database import execute_query, execute_insert
from backend.logger import logger

ALLOWED_UPDATE_FIELDS = {"name", "sessdata", "bili_jct", "buvid3", "group_tag", "is_active"}


async def list_accounts():
    return await execute_query("SELECT * FROM accounts ORDER BY created_at DESC")


async def get_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def create_account(name, sessdata, bili_jct, buvid3="", group_tag="default"):
    account_id = await execute_insert(
        "INSERT INTO accounts (name, sessdata, bili_jct, buvid3, group_tag) VALUES (?, ?, ?, ?, ?)",
        (name, sessdata, bili_jct, buvid3, group_tag)
    )
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0]


async def update_account(account_id: int, fields: dict):
    updates, params = [], []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return None
    params.append(account_id)
    await execute_query(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", tuple(params))
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def delete_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return False
    await execute_query("DELETE FROM accounts WHERE id = ?", (account_id,))
    return True


async def get_active_accounts():
    return await execute_query("SELECT * FROM accounts WHERE is_active = 1")


async def check_account_validity(account_id: int):
    import httpx
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return None
    account = rows[0]
    cookies = {"SESSDATA": account["sessdata"], "bili_jct": account["bili_jct"], "buvid3": account["buvid3"] or ""}
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"})
        data = resp.json()
    is_valid = data.get("code") == 0
    uid = data.get("data", {}).get("mid") if is_valid else None
    status = "valid" if is_valid else "invalid"
    await execute_query("UPDATE accounts SET status = ?, uid = ?, last_check_at = datetime('now') WHERE id = ?",
        (status, uid, account_id))
    return {"id": account_id, "name": account["name"], "status": status, "is_valid": is_valid, "uid": uid}
