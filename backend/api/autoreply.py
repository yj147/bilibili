"""Auto-Reply Configuration API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.models.task import AutoReplyConfig, AutoReplyConfigCreate, AutoReplyConfigUpdate, AutoReplyStatus
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
    """Get the current auto-reply service status."""
    return await autoreply_service.get_status()


@router.post("/start")
async def start_autoreply_service(interval: int = Query(default=30, ge=10)):
    """Start the auto-reply polling service."""
    started = await autoreply_service.start_service(interval)
    if not started:
        return {"message": "Auto-reply service is already running"}
    return {"message": "Auto-reply service started", "interval": interval}


@router.post("/stop")
async def stop_autoreply_service():
    """Stop the auto-reply polling service."""
    stopped = await autoreply_service.stop_service()
    if not stopped:
        return {"message": "Auto-reply service is not running"}
    return {"message": "Auto-reply service stopped"}
