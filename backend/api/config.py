"""System Configuration API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any
from backend.services.config_service import get_config, set_config, get_all_configs

router = APIRouter()

class ConfigValue(BaseModel):
    value: Any

@router.get("/")
async def list_configs():
    return await get_all_configs()

@router.get("/{key}")
async def get_config_value(key: str):
    value = await get_config(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
    return {"key": key, "value": value}

@router.put("/{key}")
async def update_config_value(key: str, body: ConfigValue):
    await set_config(key, body.value)
    return {"key": key, "value": body.value}

@router.post("/batch")
async def update_configs_batch(configs: dict):
    for key, value in configs.items():
        await set_config(key, value)
    return {"message": f"Updated {len(configs)} configs"}
