"""System configuration service."""
import json
from backend.database import execute_query, execute_insert

_config_cache = {}

async def get_config(key: str, default=None):
    if key in _config_cache:
        return _config_cache[key]
    rows = await execute_query("SELECT value FROM system_config WHERE key = ?", (key,))
    if rows:
        val = rows[0]["value"]
        try:
            val = json.loads(val)
        except (json.JSONDecodeError, TypeError):
            pass
        _config_cache[key] = val
        return val
    return default

async def set_config(key: str, value):
    str_value = json.dumps(value) if not isinstance(value, str) else value
    existing = await execute_query("SELECT id FROM system_config WHERE key = ?", (key,))
    if existing:
        await execute_query("UPDATE system_config SET value = ?, updated_at = datetime('now') WHERE key = ?", (str_value, key))
    else:
        await execute_insert("INSERT INTO system_config (key, value) VALUES (?, ?)", (key, str_value))
    _config_cache[key] = value

async def get_all_configs():
    rows = await execute_query("SELECT key, value FROM system_config")
    result = {}
    for row in rows:
        try:
            result[row["key"]] = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = row["value"]
    return result
