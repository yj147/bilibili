"""Account Management API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from backend.models.account import Account, AccountCreate, AccountUpdate, AccountStatus, AccountPublic, AccountImport
from backend.services import account_service

router = APIRouter()


@router.get("/export")
async def export_accounts(include_credentials: bool = Query(False)):
    """Export all accounts as JSON."""
    return await account_service.export_accounts(include_credentials)


@router.post("/import")
async def import_accounts(accounts: List[AccountImport]):
    """Batch import accounts from JSON array."""
    if len(accounts) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 accounts per import")
    return await account_service.import_accounts([a.model_dump() for a in accounts])

@router.get("/", response_model=List[AccountPublic])
async def list_accounts():
    return await account_service.list_accounts()

@router.post("/", response_model=AccountPublic)
async def create_account(account: AccountCreate):
    return await account_service.create_account(
        account.name, account.sessdata, account.bili_jct,
        account.buvid3 or "", account.buvid4 or "", account.dedeuserid_ckmd5 or "", account.group_tag or "default")


@router.post("/check-all")
async def check_all_accounts():
    accounts = await account_service.list_accounts()
    results = []
    for acc in accounts:
        result = await account_service.check_account_health(acc["id"])
        if result:
            results.append(result)
    return {"checked": len(results), "results": results}

@router.get("/{account_id}", response_model=AccountPublic)
async def get_account(account_id: int):
    result = await account_service.get_account(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result

@router.put("/{account_id}", response_model=AccountPublic)
async def update_account(account_id: int, account: AccountUpdate):
    existing = await account_service.get_account(account_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Account not found")
    result = await account_service.update_account(account_id, account.model_dump(exclude_unset=True))
    if result == "no_valid_fields":
        raise HTTPException(status_code=400, detail="No valid fields to update")
    if result is None:
        raise HTTPException(status_code=404, detail="Account not found after update")
    return result

@router.delete("/{account_id}")
async def delete_account(account_id: int):
    if not await account_service.delete_account(account_id):
        raise HTTPException(status_code=404, detail="Account not found")
    return {"message": "Account deleted", "id": account_id}

@router.post("/{account_id}/check", response_model=AccountStatus)
async def check_account_validity(account_id: int):
    result = await account_service.check_account_validity(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result
