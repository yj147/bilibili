"""
Report Execution API Routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import List
import json
import asyncio
import random

from backend.models.report import ReportExecuteRequest, ReportBatchExecuteRequest, ReportLog, ReportResult, BatchReportResult
from backend.database import execute_query, execute_insert
from backend.config import MIN_DELAY, MAX_DELAY
from backend.api.websocket import broadcast_log

router = APIRouter()


async def _execute_single_report(target: dict, account: dict) -> ReportResult:
    """Execute a single report using one account."""
    from backend.core.bilibili_client import BilibiliClient
    from backend.core.bilibili_auth import BilibiliAuth
    
    try:
        # Create temporary auth object
        auth = BilibiliAuth.__new__(BilibiliAuth)
        auth.accounts = [{
            "name": account["name"],
            "SESSDATA": account["sessdata"],
            "bili_jct": account["bili_jct"],
            "buvid3": account.get("buvid3", "")
        }]
        auth.wbi_keys = {"img_key": "", "sub_key": ""}
        
        client = BilibiliClient(auth, account_index=0)
        
        # Execute based on target type
        if target["type"] == "video":
            result = await client.report_video(
                aid=target.get("aid") or 0,
                reason=target.get("reason_id") or 1,
                content=target.get("reason_text") or ""
            )
        elif target["type"] == "comment":
            result = await client.report_comment(
                oid=int(target["identifier"].split(":")[0]) if ":" in target["identifier"] else 0,
                rpid=int(target["identifier"].split(":")[-1]) if ":" in target["identifier"] else int(target["identifier"]),
                reason=target.get("reason_id") or 1,
                content=target.get("reason_text") or ""
            )
        elif target["type"] == "user":
            result = await client.report_user(
                mid=int(target["identifier"]),
                reason=target.get("reason_text") or "违规内容",
                reason_id=target.get("reason_id") or 1
            )
        else:
            result = {"code": -1, "message": "Unknown target type"}
        
        success = result.get("code") == 0
        
        # Log to database
        await execute_insert(
            """INSERT INTO report_logs (target_id, account_id, action, request_data, response_data, success, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                target["id"],
                account["id"],
                f"report_{target['type']}",
                json.dumps({"identifier": target["identifier"], "reason_id": target.get("reason_id")}),
                json.dumps(result),
                success,
                None if success else result.get("message", "Unknown error")
            )
        )
        
        # Broadcast log via WebSocket
        await broadcast_log(
            "report",
            f"[{account['name']}] report_{target['type']} {target['identifier']} -> {'OK' if success else 'FAIL'}",
            {"target_id": target["id"], "account_id": account["id"], "success": success}
        )
        
        return ReportResult(
            target_id=target["id"],
            account_id=account["id"],
            account_name=account["name"],
            success=success,
            message=result.get("message", "OK" if success else "Failed"),
            response=result
        )
        
    except Exception as e:
        await execute_insert(
            """INSERT INTO report_logs (target_id, account_id, action, success, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (target["id"], account["id"], f"report_{target['type']}", False, str(e))
        )
        await broadcast_log(
            "report",
            f"[{account['name']}] report_{target['type']} {target['identifier']} -> ERROR: {str(e)}",
            {"target_id": target["id"], "account_id": account["id"], "success": False}
        )
        return ReportResult(
            target_id=target["id"],
            account_id=account["id"],
            account_name=account["name"],
            success=False,
            message=str(e)
        )


@router.post("/execute", response_model=List[ReportResult])
async def execute_report(request: ReportExecuteRequest):
    """Execute a report for a single target using multiple accounts."""
    # Get target
    targets = await execute_query("SELECT * FROM targets WHERE id = ?", (request.target_id,))
    if not targets:
        raise HTTPException(status_code=404, detail="Target not found")
    target = targets[0]
    
    # Get accounts
    if request.account_ids:
        accounts = await execute_query(
            f"SELECT * FROM accounts WHERE id IN ({','.join('?' * len(request.account_ids))}) AND is_active = 1",
            tuple(request.account_ids)
        )
    else:
        accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1")
    
    if not accounts:
        raise HTTPException(status_code=400, detail="No active accounts available")
    
    # Update target status
    await execute_query("UPDATE targets SET status = 'processing', updated_at = datetime('now') WHERE id = ?", (target["id"],))
    
    results = []
    for account in accounts:
        result = await _execute_single_report(target, account)
        results.append(result)
        # Random delay between accounts
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
    
    # Update target status based on results
    any_success = any(r.success for r in results)
    final_status = "completed" if any_success else "failed"
    await execute_query(
        "UPDATE targets SET status = ?, updated_at = datetime('now'), retry_count = retry_count + 1 WHERE id = ?",
        (final_status, target["id"])
    )
    
    return results


@router.post("/execute/batch", response_model=BatchReportResult)
async def execute_batch_reports(request: ReportBatchExecuteRequest, background_tasks: BackgroundTasks):
    """Execute reports for multiple targets."""
    # Get targets
    if request.target_ids:
        targets = await execute_query(
            f"SELECT * FROM targets WHERE id IN ({','.join('?' * len(request.target_ids))})",
            tuple(request.target_ids)
        )
    else:
        targets = await execute_query("SELECT * FROM targets WHERE status = 'pending'")
    
    if not targets:
        raise HTTPException(status_code=400, detail="No targets to process")
    
    # Get accounts
    if request.account_ids:
        accounts = await execute_query(
            f"SELECT * FROM accounts WHERE id IN ({','.join('?' * len(request.account_ids))}) AND is_active = 1",
            tuple(request.account_ids)
        )
    else:
        accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1")
    
    if not accounts:
        raise HTTPException(status_code=400, detail="No active accounts available")
    
    all_results = []
    for target in targets:
        await execute_query("UPDATE targets SET status = 'processing' WHERE id = ?", (target["id"],))
        for account in accounts:
            result = await _execute_single_report(target, account)
            all_results.append(result)
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))
        
        any_success = any(r.success and r.target_id == target["id"] for r in all_results)
        await execute_query(
            "UPDATE targets SET status = ?, updated_at = datetime('now') WHERE id = ?",
            ("completed" if any_success else "failed", target["id"])
        )
    
    successful = sum(1 for r in all_results if r.success)
    return BatchReportResult(
        total_targets=len(targets),
        total_accounts=len(accounts),
        successful=successful,
        failed=len(all_results) - successful,
        results=all_results
    )


@router.get("/logs", response_model=List[ReportLog])
async def get_report_logs(limit: int = 100):
    """Get recent report logs."""
    rows = await execute_query(
        """SELECT l.*, a.name as account_name 
           FROM report_logs l 
           LEFT JOIN accounts a ON l.account_id = a.id 
           ORDER BY l.executed_at DESC LIMIT ?""",
        (limit,)
    )
    return rows


@router.get("/logs/{target_id}", response_model=List[ReportLog])
async def get_target_logs(target_id: int):
    """Get logs for a specific target."""
    rows = await execute_query(
        """SELECT l.*, a.name as account_name 
           FROM report_logs l 
           LEFT JOIN accounts a ON l.account_id = a.id 
           WHERE l.target_id = ? 
           ORDER BY l.executed_at DESC""",
        (target_id,)
    )
    return rows
