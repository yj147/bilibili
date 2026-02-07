"""
Bili-Sentinel FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, close_db
from backend.logger import logger
from backend.middleware import register_exception_handlers
from backend.auth import verify_api_key
from backend.api import accounts, targets, reports, autoreply, scheduler, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("Bili-Sentinel starting up...")
    import os as _os
    if (_os.cpu_count() or 1) > 1:
        logger.warning("Bili-Sentinel 必须以单 worker 模式运行 (--workers 1)")
    await init_db()
    logger.info("Database initialized")
    from backend.api.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()
    logger.info("Scheduler started")
    yield
    # Shutdown
    stop_scheduler()
    await close_db()
    logger.info("Bili-Sentinel shutting down...")


app = FastAPI(
    title="Bili-Sentinel",
    description="Bilibili 自动化管理工具 API",
    version="1.0.0",
    lifespan=lifespan,
    dependencies=[Depends(verify_api_key)],
)

# Unified error handling
register_exception_handlers(app)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(targets.router, prefix="/api/targets", tags=["Targets"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(autoreply.router, prefix="/api/autoreply", tags=["Auto-Reply"])
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"])
app.include_router(websocket.router, tags=["WebSocket"])


@app.get("/")
async def root():
    return {"message": "Bili-Sentinel API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT, DEBUG
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=DEBUG)
