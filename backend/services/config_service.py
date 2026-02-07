"""System Configuration Service"""
import json
from backend.database import execute_query, execute_insert


async def get_config(key: str):
    """Get a config value by key."""
    rows = await execute_query(
        "SELECT value FROM system_config WHERE key = ?", (key,)
    )
    if not rows:
        return None
    raw = rows[0]["value"]
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw


async def set_config(key: str, value):
    """Set a config value (upsert)."""
    serialized = json.dumps(value) if not isinstance(value, str) else value
    await execute_query(
        "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, serialized),
    )


async def get_all_configs():
    """Get all config key-value pairs."""
    rows = await execute_query("SELECT key, value FROM system_config ORDER BY key")
    result = {}
    for row in rows:
        raw = row["value"]
        try:
            result[row["key"]] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = raw
    return result
