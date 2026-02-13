"""
Bili-Sentinel Database Module
Singleton connection with asyncio.Lock for concurrency safety.
"""
import asyncio
import aiosqlite
import time
from pathlib import Path
from typing import Awaitable, Callable, TypeVar
from backend.config import DATABASE_PATH
from backend.logger import logger

_connection: aiosqlite.Connection | None = None
_lock = asyncio.Lock()
_db_initialized = False

# Simple TTL cache
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_lock = asyncio.Lock()
T = TypeVar("T")


async def _get_connection() -> aiosqlite.Connection:
    """Get or create the singleton database connection."""
    global _connection
    if _connection is None:
        _connection = await aiosqlite.connect(DATABASE_PATH)
        _connection.row_factory = aiosqlite.Row
        await _connection.execute("PRAGMA journal_mode=WAL")
    return _connection


async def init_db():
    """Initialize database with schema (runs once)."""
    global _db_initialized
    if _db_initialized:
        return

    schema_path = Path(__file__).parent / "db" / "schema.sql"

    async with _lock:
        if _db_initialized:
            return
        conn = await _get_connection()
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        await conn.executescript(schema)
        await conn.commit()

        # Migrations for existing databases
        migrations = [
            "ALTER TABLE targets ADD COLUMN display_text TEXT",
        ]
        for sql in migrations:
            try:
                await conn.execute(sql)
                await conn.commit()
            except Exception:
                pass  # Column already exists

        _db_initialized = True
        logger.info("Database initialized at %s", DATABASE_PATH)


async def execute_query(query: str, params: tuple = ()):
    """Execute a query and return results."""
    async with _lock:
        conn = await _get_connection()
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        await conn.commit()
        return [dict(row) for row in rows]


async def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute an insert and return the last row id."""
    async with _lock:
        conn = await _get_connection()
        cursor = await conn.execute(query, params)
        await conn.commit()
        return cursor.lastrowid


async def execute_many(query: str, params_list: list):
    """Execute a query with multiple parameter sets."""
    async with _lock:
        conn = await _get_connection()
        await conn.executemany(query, params_list)
        await conn.commit()


async def execute_in_transaction(
    operation: Callable[[aiosqlite.Connection], Awaitable[T]],
) -> T:
    """Execute multiple statements atomically in a single transaction."""
    async with _lock:
        conn = await _get_connection()
        await conn.execute("BEGIN IMMEDIATE")
        try:
            result = await operation(conn)
        except Exception:
            await conn.rollback()
            raise
        await conn.commit()
        return result


async def close_db():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Database connection closed")


async def _get_cached(key: str, ttl: int) -> list[dict] | None:
    """Get cached result if not expired."""
    async with _cache_lock:
        if key in _cache:
            expire_time, data = _cache[key]
            if time.time() < expire_time:
                return data
            del _cache[key]
    return None


async def _set_cache(key: str, data: list[dict], ttl: int):
    """Set cache with TTL."""
    async with _cache_lock:
        _cache[key] = (time.time() + ttl, data)


async def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern."""
    async with _cache_lock:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for k in keys_to_delete:
            del _cache[k]


async def get_active_accounts_cached():
    """Get active accounts with 60s cache."""
    cache_key = "active_accounts"
    cached = await _get_cached(cache_key, 60)
    if cached is not None:
        return cached

    result = await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status = 'valid'")
    await _set_cache(cache_key, result, 60)
    return result


async def get_all_configs_cached():
    """Get all configs with 300s cache."""
    cache_key = "all_configs"
    cached = await _get_cached(cache_key, 300)
    if cached is not None:
        return cached

    result = await execute_query("SELECT key, value FROM system_config ORDER BY key")
    await _set_cache(cache_key, result, 300)
    return result
