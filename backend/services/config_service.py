"""System Configuration Service"""
import json
from backend.database import execute_query, get_all_configs_cached, invalidate_cache


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
    # Validate known config keys
    if key == "log_retention_days":
        try:
            days = int(value)
            if days < 1:
                raise ValueError("log_retention_days must be >= 1")
        except (TypeError, ValueError) as e:
            raise ValueError(str(e))
    if key in ("min_delay", "max_delay"):
        try:
            v = float(value)
            if v < 0:
                raise ValueError(f"{key} must be >= 0")
        except (TypeError, ValueError) as e:
            raise ValueError(str(e))
    if key in ("autoreply_poll_interval_seconds", "autoreply_poll_min_interval_seconds"):
        try:
            v = int(value)
            if v < 1:
                raise ValueError(f"{key} must be >= 1")
        except (TypeError, ValueError) as e:
            raise ValueError(str(e))
    if key in ("autoreply_account_batch_size", "autoreply_session_batch_size"):
        try:
            v = int(value)
            if v < 0:
                raise ValueError(f"{key} must be >= 0")
        except (TypeError, ValueError) as e:
            raise ValueError(str(e))
    serialized = json.dumps(value) if not isinstance(value, str) else value
    await execute_query(
        "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, serialized),
    )
    await invalidate_cache("all_configs")


async def get_all_configs():
    """Get all config key-value pairs."""
    rows = await get_all_configs_cached()
    result = {}
    for row in rows:
        raw = row["value"]
        try:
            result[row["key"]] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            result[row["key"]] = raw
    return result
