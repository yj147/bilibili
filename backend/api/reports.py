"""Report Execution API Routes"""
from fastapi import APIRouter, HTTPException
from typing import List

from backend.models.report import (
    ReportExecuteRequest, ReportBatchExecuteRequest,
    ReportLog, ReportResult, BatchReportResult,
    CommentScanRequest, CommentScanResult,
)
from backend.services import report_service

router = APIRouter()


@router.post("/execute", response_model=List[ReportResult])
async def execute_report(request: ReportExecuteRequest):
    """Execute a report for a single target using multiple accounts."""
    results, error = await report_service.execute_report_for_target(
        request.target_id, request.account_ids
    )
    if error:
        status = 404 if "not found" in error.lower() else 400
        raise HTTPException(status_code=status, detail=error)
    return results


@router.post("/execute/batch", response_model=BatchReportResult)
async def execute_batch_reports(request: ReportBatchExecuteRequest):
    """Execute reports for multiple targets."""
    result, error = await report_service.execute_batch_reports(
        request.target_ids, request.account_ids
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


@router.get("/logs", response_model=List[ReportLog])
async def get_report_logs(limit: int = 100):
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
