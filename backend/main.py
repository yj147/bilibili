"""
Bili-Sentinel FastAPI Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db, close_db
from backend.logger import logger
from backend.config import DEBUG
from backend.middleware import register_exception_handlers
from backend.auth import verify_api_key
from backend.api import accounts, targets, reports, autoreply, scheduler, websocket, config, auth


async def _background_wbi_refresh():
    """Background task to refresh WBI keys every hour."""
    import asyncio
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.database import execute_query

    while True:
        try:
            await asyncio.sleep(3600)  # 1 hour
            accounts = await execute_query("SELECT * FROM accounts WHERE is_active = 1 LIMIT 1")
            if accounts:
                auth = BilibiliAuth.from_db_account(accounts[0])
                if await auth.refresh_wbi_keys():
                    logger.info("Background WBI keys refresh succeeded")
                else:
                    logger.warning("Background WBI keys refresh failed")
            else:
                logger.debug("No active accounts for background WBI refresh")
        except asyncio.CancelledError:
            logger.info("Background WBI refresh task cancelled")
            raise
        except Exception as e:
            logger.error("Background WBI refresh error: %s", e)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    # Startup
    logger.info("Bili-Sentinel starting up...")
    import os as _os
    if not _os.getenv("SENTINEL_API_KEY", ""):
        logger.warning("⚠ SENTINEL_API_KEY not set! All API routes are UNAUTHENTICATED. Set this in production!")
    if (_os.cpu_count() or 1) > 1:
        logger.warning("Bili-Sentinel 必须以单 worker 模式运行 (--workers 1)")
    await init_db()
    logger.info("Database initialized")
    # Recover targets stuck in "processing" from previous crashes
    from backend.database import execute_query as _eq
    await _eq("UPDATE targets SET status = 'pending' WHERE status = 'processing'")
    _stuck = await _eq("SELECT changes() as c")
    if _stuck and _stuck[0]["c"] > 0:
        logger.info("Recovered %d stuck targets (processing -> pending)", _stuck[0]["c"])
    # Refresh WBI keys on startup using the first active account
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.database import execute_query
    startup_accounts = await execute_query(
        "SELECT * FROM accounts WHERE is_active = 1 LIMIT 1"
    )
    if startup_accounts:
        _auth = BilibiliAuth.from_db_account(startup_accounts[0])
        if await _auth.refresh_wbi_keys():
            logger.info("WBI keys refreshed on startup")
        else:
            logger.warning("WBI keys refresh failed on startup")
    else:
        logger.warning("No active accounts for WBI key refresh")

    # Start background WBI refresh task
    import asyncio
    _wbi_task = asyncio.create_task(_background_wbi_refresh())

    from backend.services.scheduler_service import start_scheduler, stop_scheduler
    await start_scheduler()
    logger.info("Scheduler started")
    yield
    # Shutdown
    _wbi_task.cancel()
    try:
        await _wbi_task
    except asyncio.CancelledError:
        pass
    stop_scheduler()
    await close_db()
    logger.info("Bili-Sentinel shutting down...")


app = FastAPI(
    title="Bili-Sentinel",
    description="Bilibili 自动化管理工具 API",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
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

# Include routers (auth on HTTP routers only, WebSocket handles its own auth)
_auth_deps = [Depends(verify_api_key)]
app.include_router(accounts.router, prefix="/api/accounts", tags=["Accounts"], dependencies=_auth_deps)
app.include_router(targets.router, prefix="/api/targets", tags=["Targets"], dependencies=_auth_deps)
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"], dependencies=_auth_deps)
app.include_router(autoreply.router, prefix="/api/autoreply", tags=["Auto-Reply"], dependencies=_auth_deps)
app.include_router(scheduler.router, prefix="/api/scheduler", tags=["Scheduler"], dependencies=_auth_deps)
app.include_router(websocket.router, tags=["WebSocket"])
app.include_router(config.router, prefix="/api/config", tags=["Config"], dependencies=_auth_deps)
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"], dependencies=_auth_deps)


@app.get("/")
async def root():
    return {"message": "Bili-Sentinel API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/system/info")
async def system_info():
    import platform
    from backend.database import execute_query
    account_count = await execute_query("SELECT COUNT(*) as c FROM accounts")
    target_count = await execute_query("SELECT COUNT(*) as c FROM targets")
    return {
        "version": "1.0.0",
        "python": platform.python_version(),
        "platform": platform.system(),
        "accounts": account_count[0]["c"],
        "targets": target_count[0]["c"],
    }


if __name__ == "__main__":
    import uvicorn
    from backend.config import HOST, PORT
    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=DEBUG)
