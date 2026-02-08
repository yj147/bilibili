"""Target Management API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.models.target import Target, TargetCreate, TargetUpdate, TargetBatchCreate, TargetListResponse
from backend.services import target_service

router = APIRouter()


@router.get("/", response_model=TargetListResponse)
async def list_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
):
    """Get targets with pagination and filters."""
    result = await target_service.list_targets(page, page_size, status, type)
    return result


@router.post("/", response_model=Target)
async def create_target(target: TargetCreate):
    """Add a single target."""
    return await target_service.create_target(
        target.type, target.identifier, target.aid, target.reason_id, target.reason_text
    )


@router.post("/batch")
async def create_targets_batch(batch: TargetBatchCreate):
    """Add multiple targets at once."""
    count = await target_service.create_targets_batch(
        batch.type, batch.identifiers, batch.reason_id, batch.reason_text
    )
    return {"message": f"Created {count} targets", "count": count}


@router.get("/{target_id}", response_model=Target)
async def get_target(target_id: int):
    """Get a single target by ID."""
    result = await target_service.get_target(target_id)
    if not result:
        raise HTTPException(status_code=404, detail="Target not found")
    return result


@router.put("/{target_id}", response_model=Target)
async def update_target(target_id: int, target: TargetUpdate):
    """Update a target."""
    result = await target_service.update_target(target_id, target.model_dump(exclude_unset=True))
    if result is None:
        raise HTTPException(status_code=400, detail="No fields to update or target not found")
    return result


@router.delete("/{target_id}")
async def delete_target(target_id: int):
    """Delete a target."""
    if not await target_service.delete_target(target_id):
        raise HTTPException(status_code=404, detail="Target not found")
    return {"message": "Target deleted", "id": target_id}


@router.delete("/")
async def delete_targets_by_status(status: str = Query(...)):
    """Delete all targets with a specific status."""
    count = await target_service.delete_targets_by_status(status)
    return {"message": f"Deleted {count} targets", "count": count}
