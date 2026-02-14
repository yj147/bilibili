#!/usr/bin/env python3
"""Repair invalid scheduled task trigger data."""
import asyncio

from backend.database import init_db, close_db
from backend.services.scheduler_service import repair_invalid_task_triggers


async def main() -> None:
    await init_db()
    try:
        repaired = await repair_invalid_task_triggers()
        print(f"Repaired {repaired} scheduled task rows.")
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
