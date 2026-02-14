"""Account Management API Routes"""
import asyncio
from fastapi import APIRouter, HTTPException, Query, Response
from typing import List
from backend.models.account import Account, AccountCreate, AccountUpdate, AccountStatus, AccountPublic, AccountImport, AccountCredentials
from backend.services import account_service
from backend.logger import logger

router = APIRouter()


@router.get("/export")
async def export_accounts(include_credentials: bool = Query(False)):
    """Export all accounts as JSON."""
    if include_credentials:
        logger.warning("AUDIT: Credential export requested (include_credentials=True)")
    return await account_service.export_accounts(include_credentials)


@router.post("/import")
async def import_accounts(accounts: List[AccountImport]):
    """Batch import accounts from JSON array."""
    if len(accounts) > 500:
        raise HTTPException(status_code=400, detail="Maximum 500 accounts per import")
    return await account_service.import_accounts([a.model_dump() for a in accounts])

@router.get("/")
async def list_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    return await account_service.list_accounts(page, page_size)

@router.post("/", response_model=AccountPublic)
async def create_account(account: AccountCreate):
    return await account_service.create_account(
        account.name, account.sessdata, account.bili_jct,
        account.buvid3 or "", account.buvid4 or "", account.dedeuserid_ckmd5 or "", account.group_tag or "default")


_check_all_running = False
_check_all_lock = asyncio.Lock()

async def _check_all_in_background():
    global _check_all_running
    try:
        accounts = await account_service.list_accounts_internal()
        sem = asyncio.Semaphore(3)
        async def check_one(acc):
            async with sem:
                return await account_service.check_account_health(acc["id"])
        tasks = [check_one(acc) for acc in accounts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        valid = [r for r in results if isinstance(r, dict)]
        logger.info("check-all complete: %d/%d accounts checked", len(valid), len(accounts))
    except Exception as e:
        logger.error("check-all background task failed: %s", e)
    finally:
        _check_all_running = False

@router.post("/check-all", status_code=202)
async def check_all_accounts():
    async with _check_all_lock:
        global _check_all_running
        if _check_all_running:
            raise HTTPException(status_code=409, detail="Health check already in progress")
        try:
            _check_all_running = True
            asyncio.create_task(_check_all_in_background())
            return {"status": "accepted", "message": "Account health check queued"}
        except Exception as e:
            _check_all_running = False
            logger.error("Failed to create check-all background task: %s", e)
            raise HTTPException(status_code=500, detail="Failed to start health check")

@router.post("/{account_id}/credentials", response_model=AccountCredentials)
async def get_account_credentials(account_id: int, response: Response):
    logger.warning("AUDIT: Credential read requested for account_id=%d", account_id)
    result = await account_service.get_account_credentials(account_id)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    response.headers["Cache-Control"] = "no-store"
    return {
        "id": result["id"],
        "name": result["name"],
        "sessdata": result["sessdata"],
        "bili_jct": result["bili_jct"],
        "buvid3": result.get("buvid3", ""),
        "buvid4": result.get("buvid4", ""),
    }

@router.get("/{account_id}", response_model=AccountPublic)
async def get_account(account_id: int):
    result = await account_service.get_account_public(account_id)
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
