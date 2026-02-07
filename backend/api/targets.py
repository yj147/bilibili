"""
Target Management API Routes
"""
from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional

from backend.models.target import Target, TargetCreate, TargetUpdate, TargetBatchCreate, TargetListResponse
from backend.database import execute_query, execute_insert, execute_many

router = APIRouter()


@router.get("/", response_model=TargetListResponse)
async def list_targets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None
):
    """Get targets with pagination and filters."""
    where_clauses = []
    params = []
    
    if status:
        where_clauses.append("status = ?")
        params.append(status)
    if type:
        where_clauses.append("type = ?")
        params.append(type)
    
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
    
    # Get total count
    count_rows = await execute_query(f"SELECT COUNT(*) as total FROM targets {where_sql}", tuple(params))
    total = count_rows[0]["total"]
    
    # Get paginated results
    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await execute_query(
        f"SELECT * FROM targets {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params)
    )
    
    return TargetListResponse(items=rows, total=total, page=page, page_size=page_size)


@router.post("/", response_model=Target)
async def create_target(target: TargetCreate):
    """Add a single target."""
    target_id = await execute_insert(
        """INSERT INTO targets (type, identifier, aid, reason_id, reason_text) 
           VALUES (?, ?, ?, ?, ?)""",
        (target.type, target.identifier, target.aid, target.reason_id, target.reason_text)
    )
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    return rows[0]


@router.post("/batch")
async def create_targets_batch(batch: TargetBatchCreate):
    """Add multiple targets at once."""
    params_list = [
        (batch.type, identifier, None, batch.reason_id, batch.reason_text)
        for identifier in batch.identifiers
    ]
    
    await execute_many(
        "INSERT INTO targets (type, identifier, aid, reason_id, reason_text) VALUES (?, ?, ?, ?, ?)",
        params_list
    )
    
    return {"message": f"Created {len(batch.identifiers)} targets", "count": len(batch.identifiers)}


@router.get("/{target_id}", response_model=Target)
async def get_target(target_id: int):
    """Get a single target by ID."""
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Target not found")
    return rows[0]


@router.put("/{target_id}", response_model=Target)
async def update_target(target_id: int, target: TargetUpdate):
    """Update a target."""
    updates = []
    params = []
    for field, value in target.model_dump(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = ?")
            params.append(value)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = datetime('now')")
    params.append(target_id)
    
    await execute_query(f"UPDATE targets SET {', '.join(updates)} WHERE id = ?", tuple(params))
    
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Target not found")
    return rows[0]


@router.delete("/{target_id}")
async def delete_target(target_id: int):
    """Delete a target."""
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="Target not found")
    
    await execute_query("DELETE FROM targets WHERE id = ?", (target_id,))
    return {"message": "Target deleted", "id": target_id}


@router.delete("/")
async def delete_targets_by_status(status: str = Query(...)):
    """Delete all targets with a specific status."""
    result = await execute_query("DELETE FROM targets WHERE status = ? RETURNING id", (status,))
    return {"message": f"Deleted {len(result)} targets", "count": len(result)}
