"""Account business logic."""
from backend.database import execute_query, execute_insert, get_active_accounts_cached, invalidate_cache
from backend.logger import logger

ALLOWED_UPDATE_FIELDS = {"name", "sessdata", "bili_jct", "buvid3", "buvid4", "dedeuserid_ckmd5", "refresh_token", "group_tag", "is_active"}
STATUS_RESET_FIELDS = {"sessdata", "bili_jct"}
_PUBLIC_COLUMNS = "id, name, uid, buvid3, buvid4, group_tag, is_active, last_check_at, status, created_at"


async def list_accounts(page: int = 1, page_size: int = 50):
    """List accounts with pagination, excluding credentials."""
    offset = (page - 1) * page_size
    items = await execute_query(
        f"SELECT {_PUBLIC_COLUMNS} FROM accounts ORDER BY created_at DESC LIMIT ? OFFSET ?",
        (page_size, offset)
    )
    count_result = await execute_query("SELECT COUNT(*) as total FROM accounts")
    total = count_result[0]["total"] if count_result else 0
    return {"items": items, "total": total, "page": page, "page_size": page_size}


async def get_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def get_account_public(account_id: int):
    """Get account by ID, excluding credentials."""
    rows = await execute_query(f"SELECT {_PUBLIC_COLUMNS} FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def list_accounts_internal():
    """List all account IDs and names for internal operations."""
    return await execute_query("SELECT id, name FROM accounts ORDER BY created_at DESC")


async def create_account(name, sessdata, bili_jct, buvid3="", buvid4="", dedeuserid_ckmd5="", group_tag="default"):
    account_id = await execute_insert(
        "INSERT INTO accounts (name, sessdata, bili_jct, buvid3, buvid4, dedeuserid_ckmd5, group_tag) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (name, sessdata, bili_jct, buvid3, buvid4, dedeuserid_ckmd5, group_tag)
    )
    await invalidate_cache("active_accounts")
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0]


async def update_account(account_id: int, fields: dict):
    existing_rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not existing_rows:
        return None
    existing = existing_rows[0]

    updates, params = [], []
    should_reset_status = False
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
            if (field in STATUS_RESET_FIELDS or field.startswith("buvid")) and existing.get(field) != value:
                should_reset_status = True
    if not updates:
        return "no_valid_fields"
    if should_reset_status:
        updates.append("status = ?")
        params.append("unknown")
        updates.append("last_check_at = NULL")
    params.append(account_id)
    await execute_query(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", tuple(params))
    await invalidate_cache("active_accounts")
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def delete_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return False
    await execute_query("DELETE FROM accounts WHERE id = ?", (account_id,))
    await invalidate_cache("active_accounts")
    return True


async def get_active_accounts():
    return await get_active_accounts_cached()


async def export_accounts(include_credentials: bool = False):
    """Export all accounts. Optionally include sensitive credential fields."""
    rows = await execute_query("SELECT * FROM accounts ORDER BY created_at DESC")
    if not include_credentials:
        sensitive = {"sessdata", "bili_jct", "refresh_token", "dedeuserid_ckmd5"}
        rows = [{k: v for k, v in row.items() if k not in sensitive} for row in rows]
    return rows


async def import_accounts(accounts_data: list[dict]) -> dict:
    """Batch import accounts from JSON array. Returns count of created/skipped."""
    created = 0
    skipped = 0
    for acc in accounts_data:
        name = acc.get("name")
        sessdata = acc.get("sessdata")
        bili_jct = acc.get("bili_jct")
        if not name or not sessdata or not bili_jct:
            skipped += 1
            continue
        try:
            await create_account(
                name=name,
                sessdata=sessdata,
                bili_jct=bili_jct,
                buvid3=acc.get("buvid3", ""),
                buvid4=acc.get("buvid4", ""),
                dedeuserid_ckmd5=acc.get("dedeuserid_ckmd5", ""),
                group_tag=acc.get("group_tag", "default"),
            )
            created += 1
        except Exception as e:
            logger.warning("Import account '%s' failed: %s", name, e)
            skipped += 1
    return {"created": created, "skipped": skipped, "total": len(accounts_data)}


async def check_account_validity(account_id: int):
    import httpx
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return None
    account = rows[0]
    cookies = {
        "SESSDATA": account["sessdata"],
        "bili_jct": account["bili_jct"],
        "buvid3": account["buvid3"] or "",
    }
    if account.get("buvid4"):
        cookies["buvid4"] = account["buvid4"]
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = await client.get("https://api.bilibili.com/x/web-interface/nav",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"})
        data = resp.json()
    is_valid = data.get("code") == 0
    uid = data.get("data", {}).get("mid") if is_valid else None
    status = "valid" if is_valid else "invalid"
    await execute_query("UPDATE accounts SET status = ?, uid = ?, last_check_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
        (status, uid, account_id))
    await invalidate_cache("active_accounts")
    return {"id": account_id, "name": account["name"], "status": status, "is_valid": is_valid, "uid": uid}


async def check_account_health(account_id: int):
    return await check_account_validity(account_id)
