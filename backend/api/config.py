"""System Configuration API Routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any
from backend.services.config_service import get_config, set_config, get_all_configs

router = APIRouter()

class ConfigValue(BaseModel):
    value: str | int | float | bool

class ConfigBatchUpdate(BaseModel):
    configs: dict[str, str | int | float | bool] = Field(..., max_length=50)

class ConfigResponse(BaseModel):
    key: str
    value: Any

class ConfigBatchResponse(BaseModel):
    message: str
    updated_keys: list[str]

@router.get("/")
async def list_configs():
    return await get_all_configs()

@router.get("/{key}", response_model=ConfigResponse)
async def get_config_value(key: str):
    value = await get_config(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
    return {"key": key, "value": value}

@router.put("/{key}", response_model=ConfigResponse)
async def update_config_value(key: str, body: ConfigValue):
    try:
        await set_config(key, body.value)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"key": key, "value": body.value}

@router.post("/batch", response_model=ConfigBatchResponse)
async def update_configs_batch(body: ConfigBatchUpdate):
    updated_keys = []
    for key, value in body.configs.items():
        try:
            await set_config(key, value)
            updated_keys.append(key)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Failed on key '{key}': {str(e)}")
    return {"message": f"Updated {len(updated_keys)} configs", "updated_keys": updated_keys}
