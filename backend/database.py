"""
Bili-Sentinel Database Module
"""
import aiosqlite
from pathlib import Path
from backend.config import DATABASE_PATH

_db_initialized = False


async def get_db() -> aiosqlite.Connection:
    """Get a database connection."""
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    return db


async def init_db():
    """Initialize database with schema."""
    global _db_initialized
    if _db_initialized:
        return
    
    schema_path = Path(__file__).parent / "db" / "schema.sql"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        with open(schema_path, "r", encoding="utf-8") as f:
            schema = f.read()
        await db.executescript(schema)
        await db.commit()
    
    _db_initialized = True
    print(f"Database initialized at {DATABASE_PATH}")


async def execute_query(query: str, params: tuple = ()):
    """Execute a query and return results."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()
        await db.commit()
        return [dict(row) for row in rows]


async def execute_insert(query: str, params: tuple = ()) -> int:
    """Execute an insert and return the last row id."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.lastrowid


async def execute_many(query: str, params_list: list):
    """Execute a query with multiple parameter sets."""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.executemany(query, params_list)
        await db.commit()
