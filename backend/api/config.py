"""System Configuration API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.config_service import get_config, set_config, get_all_configs

router = APIRouter()

class ConfigValue(BaseModel):
    value: str | int | float | bool

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
    try:
        await set_config(key, body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"key": key, "value": body.value}

@router.post("/batch")
async def update_configs_batch(configs: dict):
    for key, value in configs.items():
        try:
            await set_config(key, value)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
    return {"message": f"Updated {len(configs)} configs"}
