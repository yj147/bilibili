"""System Configuration Service"""
import json
import math
from backend.database import execute_query, get_all_configs_cached, invalidate_cache, execute_in_transaction
from backend.logger import logger


def _validate_config(key: str, value):
    """Validate a config key-value pair. Raises ValueError if invalid."""
    if key == "log_retention_days":
        days = int(value)
        if days < 1:
            raise ValueError("log_retention_days must be >= 1")
    elif key == "account_cooldown":
        if isinstance(value, bool):
            raise ValueError("account_cooldown cannot be a boolean")
        try:
            v = float(value)
        except (ValueError, OverflowError) as e:
            raise ValueError(f"account_cooldown must be a valid number: {e}")
        if not math.isfinite(v) or v < 1:
            raise ValueError("account_cooldown must be a finite number >= 1")
    elif key == "min_delay":
        v = float(value)
        if not (1 <= v <= 10):
            raise ValueError("min_delay must be between 1 and 10")
    elif key == "max_delay":
        v = float(value)
        if not (10 <= v <= 60):
            raise ValueError("max_delay must be between 10 and 60")
    elif key in ("autoreply_poll_interval_seconds", "autoreply_poll_min_interval_seconds"):
        v = int(value)
        if v < 1:
            raise ValueError(f"{key} must be >= 1")
    elif key in ("autoreply_account_batch_size", "autoreply_session_batch_size"):
        v = int(value)
        if v < 0:
            raise ValueError(f"{key} must be >= 0")


async def _invalidate_config_related_caches():
    """Invalidate config caches across services on a best-effort basis."""
    try:
        await invalidate_cache("all_configs")
        from backend.services.report_service import invalidate_delay_config_cache
        invalidate_delay_config_cache()
    except Exception:
        logger.exception("Failed to invalidate config-related caches")


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
    try:
        _validate_config(key, value)
    except (TypeError, ValueError, OverflowError) as e:
        raise ValueError(str(e))
    serialized = json.dumps(value)
    await execute_query(
        "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (key, serialized),
    )
    await _invalidate_config_related_caches()


async def set_configs_batch_atomic(configs: dict):
    """Atomically update multiple configs in a transaction."""
    # Validate all configs first
    for key, value in configs.items():
        try:
            _validate_config(key, value)
        except (TypeError, ValueError) as e:
            raise ValueError(f"Validation failed for '{key}': {str(e)}")

    # Write all in transaction
    async def _write_all(conn):
        for key, value in configs.items():
            serialized = json.dumps(value)
            await conn.execute(
                "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
                (key, serialized)
            )

    await execute_in_transaction(_write_all)
    await _invalidate_config_related_caches()


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
