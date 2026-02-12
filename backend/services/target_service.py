"""Target business logic."""
from typing import Optional
from backend.database import execute_query, execute_insert, execute_many

# Whitelist of fields allowed in dynamic UPDATE statements
ALLOWED_UPDATE_FIELDS = {"reason_id", "reason_content_id", "reason_text", "status"}

VALID_STATUSES = {"pending", "processing", "completed", "failed"}


async def list_targets(
    page: int = 1,
    page_size: int = 20,
    status: Optional[str] = None,
    target_type: Optional[str] = None,
):
    """Get targets with pagination and filters."""
    where_clauses = []
    params = []

    if status:
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        where_clauses.append("status = ?")
        params.append(status)
    if target_type:
        where_clauses.append("type = ?")
        params.append(target_type)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    count_rows = await execute_query(
        f"SELECT COUNT(*) as total FROM targets {where_sql}", tuple(params)
    )
    total = count_rows[0]["total"]

    offset = (page - 1) * page_size
    params.extend([page_size, offset])
    rows = await execute_query(
        f"SELECT * FROM targets {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
        tuple(params),
    )

    return {"items": rows, "total": total, "page": page, "page_size": page_size}


async def get_target(target_id: int):
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    return rows[0] if rows else None


async def create_target(target_type: str, identifier: str, aid=None, reason_id=None, reason_content_id=None, reason_text=None, display_text=None):
    target_id = await execute_insert(
        "INSERT INTO targets (type, identifier, aid, reason_id, reason_content_id, reason_text, display_text) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (target_type, identifier, aid, reason_id, reason_content_id, reason_text, display_text),
    )
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    return rows[0]


async def create_targets_batch(target_type: str, identifiers: list[str], reason_id=None, reason_content_id=None, reason_text=None):
    params_list = [
        (target_type, identifier, None, reason_id, reason_content_id, reason_text)
        for identifier in identifiers
    ]
    await execute_many(
        "INSERT INTO targets (type, identifier, aid, reason_id, reason_content_id, reason_text) VALUES (?, ?, ?, ?, ?, ?)",
        params_list,
    )
    return len(identifiers)


async def update_target(target_id: int, fields: dict):
    updates = []
    params = []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)

    if not updates:
        return "no_valid_fields"

    updates.append("updated_at = datetime('now')")
    params.append(target_id)
    await execute_query(
        f"UPDATE targets SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )

    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    return rows[0] if rows else None


async def delete_target(target_id: int) -> bool:
    rows = await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
    if not rows:
        return False
    await execute_query("DELETE FROM targets WHERE id = ?", (target_id,))
    return True


async def delete_targets_by_status(status: str) -> int:
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid target status: {status}. Must be one of {VALID_STATUSES}")
    count_rows = await execute_query(
        "SELECT COUNT(*) as count FROM targets WHERE status = ?", (status,)
    )
    count = count_rows[0]["count"] if count_rows else 0
    await execute_query("DELETE FROM targets WHERE status = ?", (status,))
    return count


async def update_target_status(target_id: int, status: str):
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid target status: {status}. Must be one of {VALID_STATUSES}")
    await execute_query(
        "UPDATE targets SET status = ?, updated_at = datetime('now') WHERE id = ?",
        (status, target_id),
    )


async def increment_retry_and_set_status(target_id: int, status: str):
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid target status: {status}. Must be one of {VALID_STATUSES}")
    await execute_query(
        "UPDATE targets SET status = ?, updated_at = datetime('now'), retry_count = retry_count + 1 WHERE id = ?",
        (status, target_id),
    )


async def get_pending_targets():
    return await execute_query("SELECT * FROM targets WHERE status = 'pending'")


async def export_targets(status: Optional[str] = None):
    """Export all targets, optionally filtered by status."""
    if status:
        return await execute_query("SELECT * FROM targets WHERE status = ? ORDER BY created_at DESC", (status,))
    return await execute_query("SELECT * FROM targets ORDER BY created_at DESC")
