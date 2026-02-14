"""Auto-Reply Configuration API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.config import AUTOREPLY_POLL_INTERVAL_SECONDS
from backend.models.task import (
    AutoReplyConfig,
    AutoReplyConfigCreate,
    AutoReplyConfigUpdate,
    AutoReplyDefaultUpsert,
    AutoReplyStatus,
)
from backend.services import autoreply_service

router = APIRouter()


@router.get("/config", response_model=List[AutoReplyConfig])
async def list_autoreply_configs():
    """Get all auto-reply configurations."""
    return await autoreply_service.list_configs()


@router.post("/config", response_model=AutoReplyConfig)
async def create_autoreply_config(config: AutoReplyConfigCreate):
    """Add a new auto-reply configuration."""
    return await autoreply_service.create_config(config.keyword, config.response, config.priority)


@router.put("/config/default", response_model=AutoReplyConfig)
async def upsert_default_reply(config: AutoReplyDefaultUpsert):
    """Create or update default auto-reply atomically."""
    return await autoreply_service.upsert_default_reply(config.response)


@router.put("/config/{config_id}", response_model=AutoReplyConfig)
async def update_autoreply_config(config_id: int, config: AutoReplyConfigUpdate):
    """Update an auto-reply configuration."""
    result = await autoreply_service.update_config(config_id, config.model_dump(exclude_unset=True))
    if result == "no_valid_fields":
        raise HTTPException(status_code=400, detail="No valid fields to update")
    if result is None:
        raise HTTPException(status_code=404, detail="Config not found")
    return result


@router.delete("/config/{config_id}")
async def delete_autoreply_config(config_id: int):
    """Delete an auto-reply configuration."""
    if not await autoreply_service.delete_config(config_id):
        raise HTTPException(status_code=404, detail="Config not found")
    return {"message": "Config deleted", "id": config_id}


@router.get("/status", response_model=AutoReplyStatus)
async def get_autoreply_status():
    """Get the standalone auto-reply switch status (not scheduler task status)."""
    return await autoreply_service.get_status()


@router.post("/enable")
async def enable_autoreply_service(
    interval: int = Query(default=AUTOREPLY_POLL_INTERVAL_SECONDS, ge=1)
):
    """Enable standalone auto-reply polling. This does not toggle scheduler tasks."""
    started = await autoreply_service.start_service(interval)
    if not started:
        return {"message": "Auto-reply feature is already enabled (standalone mode)"}
    return {
        "message": "Auto-reply feature enabled (standalone mode)",
        "interval": interval,
        "affects_scheduler_tasks": False,
    }


@router.post("/disable")
async def disable_autoreply_service():
    """Disable standalone auto-reply polling. This does not toggle scheduler tasks."""
    stopped = await autoreply_service.stop_service()
    if not stopped:
        return {"message": "Auto-reply feature is already disabled (standalone mode)"}
    return {
        "message": "Auto-reply feature disabled (standalone mode)",
        "affects_scheduler_tasks": False,
    }


@router.post("/start", deprecated=True)
async def start_autoreply_service(
    interval: int = Query(default=AUTOREPLY_POLL_INTERVAL_SECONDS, ge=1)
):
    """Deprecated: use /enable instead. Will be removed after 2026-06-01."""
    from backend.logger import logger
    logger.warning("Deprecated endpoint /autoreply/start called; use /enable instead")
    return await enable_autoreply_service(interval)


@router.post("/stop", deprecated=True)
async def stop_autoreply_service():
    """Deprecated: use /disable instead. Will be removed after 2026-06-01."""
    from backend.logger import logger
    logger.warning("Deprecated endpoint /autoreply/stop called; use /disable instead")
    return await disable_autoreply_service()
