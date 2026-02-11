"""
Bili-Sentinel Database Module
Singleton connection with asyncio.Lock for concurrency safety.
"""
import asyncio
import aiosqlite
from pathlib import Path
from backend.config import DATABASE_PATH
from backend.logger import logger

_connection: aiosqlite.Connection | None = None
_lock = asyncio.Lock()
_db_initialized = False


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


async def close_db():
    """Close the database connection."""
    global _connection
    if _connection is not None:
        await _connection.close()
        _connection = None
        logger.info("Database connection closed")
