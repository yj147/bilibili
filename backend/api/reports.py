"""Report Execution API Routes"""
import asyncio
from fastapi import APIRouter, HTTPException
from typing import List

from backend.models.report import (
    ReportExecuteRequest, ReportBatchExecuteRequest,
    ReportLog, ReportResult, BatchReportResult,
    CommentScanRequest, CommentScanResult,
)
from backend.services import report_service
from backend.logger import logger

router = APIRouter()


async def _run_report_in_background(target_id: int, account_ids: list[int] | None):
    """Fire-and-forget wrapper for report execution."""
    try:
        await report_service.execute_report_for_target(target_id, account_ids)
    except Exception as e:
        logger.error("Background report execution failed for target %s: %s", target_id, e)
        from backend.services import target_service
        await target_service.increment_retry_and_set_status(target_id, "failed")


async def _run_batch_in_background(target_ids: list[int] | None, account_ids: list[int] | None):
    """Fire-and-forget wrapper for batch report execution."""
    try:
        await report_service.execute_batch_reports(target_ids, account_ids)
    except Exception as e:
        logger.error("Background batch execution failed: %s", e)


@router.post("/execute")
async def execute_report(request: ReportExecuteRequest):
    """Fire-and-forget: immediately returns, processes report in background."""
    from backend.services import target_service
    target = await target_service.get_target(request.target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    if target["status"] == "processing":
        raise HTTPException(status_code=409, detail="Target is already being processed")

    # Update status and create task atomically with error handling
    await target_service.update_target_status(request.target_id, "processing")
    try:
        asyncio.create_task(_run_report_in_background(request.target_id, request.account_ids))
    except Exception as e:
        # Rollback status if task creation fails
        logger.error("Failed to create background task for target %s: %s", request.target_id, e)
        await target_service.update_target_status(request.target_id, "pending")
        raise HTTPException(status_code=500, detail="Failed to queue report execution")

    return {"status": "accepted", "target_id": request.target_id, "message": "Report queued for execution"}


@router.post("/execute/batch")
async def execute_batch_reports(request: ReportBatchExecuteRequest):
    """Fire-and-forget: immediately returns, processes batch in background."""
    try:
        asyncio.create_task(_run_batch_in_background(request.target_ids, request.account_ids))
    except Exception as e:
        logger.error("Failed to create batch background task: %s", e)
        raise HTTPException(status_code=500, detail="Failed to queue batch execution")
    return {"status": "accepted", "message": "Batch execution queued"}


@router.get("/logs", response_model=List[ReportLog])
async def get_report_logs(limit: int = Query(default=100, ge=1, le=1000)):
    """Get recent report logs."""
    return await report_service.get_report_logs(limit)


@router.get("/logs/{target_id}", response_model=List[ReportLog])
async def get_target_logs(target_id: int):
    """Get logs for a specific target."""
    return await report_service.get_target_logs(target_id)


@router.post("/scan-comments", response_model=CommentScanResult)
async def scan_comments(request: CommentScanRequest):
    """Scan video comments, create targets, and optionally auto-report."""
    result = await report_service.scan_and_report_comments(
        bvid=request.bvid,
        account_id=request.account_id,
        reason_id=request.reason_id,
        reason_text=request.reason_text,
        max_pages=request.max_pages,
        auto_report=request.auto_report,
    )
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
