"""Scheduler API Routes"""
from fastapi import APIRouter, HTTPException, Query
from typing import List

from backend.models.task import ScheduledTask, ScheduledTaskCreate, ScheduledTaskUpdate
from backend.services import scheduler_service

router = APIRouter()

# Re-export for main.py lifespan
start_scheduler = scheduler_service.start_scheduler
stop_scheduler = scheduler_service.stop_scheduler


@router.get("/tasks", response_model=List[ScheduledTask])
async def list_scheduled_tasks():
    return await scheduler_service.list_tasks()


@router.post("/tasks", response_model=ScheduledTask)
async def create_scheduled_task(task: ScheduledTaskCreate):
    return await scheduler_service.create_task(
        task.name, task.task_type, task.cron_expression,
        task.interval_seconds, task.config_json,
    )


@router.get("/tasks/{task_id}", response_model=ScheduledTask)
async def get_scheduled_task(task_id: int):
    result = await scheduler_service.get_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.put("/tasks/{task_id}", response_model=ScheduledTask)
async def update_scheduled_task(task_id: int, task: ScheduledTaskUpdate):
    result = await scheduler_service.update_task(task_id, task.model_dump(exclude_unset=True))
    if result == "no_valid_fields":
        raise HTTPException(status_code=400, detail="No valid fields to update")
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.delete("/tasks/{task_id}")
async def delete_scheduled_task(task_id: int):
    if not await scheduler_service.delete_task(task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted", "id": task_id}


@router.post("/tasks/{task_id}/toggle")
async def toggle_scheduled_task(task_id: int):
    result = await scheduler_service.toggle_task(task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": f"Task {'enabled' if result['is_active'] else 'disabled'}", **result}


@router.get("/history")
async def get_scheduler_history(limit: int = Query(default=50, ge=1, le=1000)):
    return await scheduler_service.get_history(limit)
