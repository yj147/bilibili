"""
Account Management API Routes
"""
from fastapi import APIRouter, HTTPException
from typing import List

from backend.models.account import Account, AccountCreate, AccountUpdate, AccountStatus
from backend.database import execute_query, execute_insert

router = APIRouter()


@router.get("/", response_model=List[Account])
async def list_accounts():
    """Get all accounts."""
    rows = await execute_query("SELECT * FROM accounts ORDER BY created_at DESC")
    return rows


@router.post("/", response_model=Account)
async def create_account(account: AccountCreate):
    """Add a new account."""
    account_id = await execute_insert(
        """INSERT INTO accounts (name, sessdata, bili_jct, buvid3, group_tag) 
           VALUES (?, ?, ?, ?, ?)""",
        (account.name, account.sessdata, account.bili_jct, account.buvid3, account.group_tag)
    )
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0]


@router.get("/{account_id}", response_model=Account)
async def get_account(account_id: int):
    """Get a single account by ID."""
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Account not found")
    return rows[0]


# Whitelist of fields allowed in dynamic UPDATE statements
ACCOUNT_ALLOWED_UPDATE_FIELDS = {"name", "sessdata", "bili_jct", "buvid3", "group_tag", "is_active"}


@router.put("/{account_id}", response_model=Account)
async def update_account(account_id: int, account: AccountUpdate):
    """Update an account."""
    updates = []
    params = []
    for field, value in account.model_dump(exclude_unset=True).items():
        if value is not None and field in ACCOUNT_ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    params.append(account_id)
    await execute_query(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", tuple(params))
    
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Account not found")
    return rows[0]


@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """Delete an account."""
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Account not found")
    
    await execute_query("DELETE FROM accounts WHERE id = ?", (account_id,))
    return {"message": "Account deleted", "id": account_id}


@router.post("/{account_id}/check", response_model=AccountStatus)
async def check_account_validity(account_id: int):
    """Check if an account's cookies are still valid."""
    from backend.core.bilibili_auth import BilibiliAuth
    import httpx
    
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Account not found")
    
    account = rows[0]
    cookies = {
        "SESSDATA": account["sessdata"],
        "bili_jct": account["bili_jct"],
        "buvid3": account["buvid3"] or ""
    }
    
    # Check by calling nav API
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = await client.get(
            "https://api.bilibili.com/x/web-interface/nav",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        )
        data = resp.json()
    
    is_valid = data.get("code") == 0
    uid = data.get("data", {}).get("mid") if is_valid else None
    status = "valid" if is_valid else "invalid"
    
    # Update account status in DB
    await execute_query(
        "UPDATE accounts SET status = ?, uid = ?, last_check_at = datetime('now') WHERE id = ?",
        (status, uid, account_id)
    )
    
    return AccountStatus(
        id=account_id,
        name=account["name"],
        status=status,
        is_valid=is_valid,
        uid=uid
    )
