# Database Guidelines

> Database patterns and conventions for Bili-Sentinel.

---

## Overview

- **Database**: SQLite via `aiosqlite`
- **ORM**: None — raw SQL with parameterized queries
- **Connection**: Singleton with `asyncio.Lock` for concurrency safety
- **Schema**: `backend/db/schema.sql` with `CREATE TABLE IF NOT EXISTS` (idempotent)
- **WAL mode**: Enabled at connection time for better concurrency

---

## Performance Optimization

### Composite Indexes for High-Frequency Queries

**Problem**: Queries filtering by multiple columns or sorting large result sets are slow without proper indexes.

**Solution**: Create composite indexes matching query patterns.

```sql
-- High-frequency query patterns
CREATE INDEX IF NOT EXISTS idx_targets_status_type ON targets(status, type);
CREATE INDEX IF NOT EXISTS idx_report_logs_executed_at ON report_logs(executed_at DESC);
CREATE INDEX IF NOT EXISTS idx_targets_aid ON targets(aid) WHERE aid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_targets_type_aid_status ON targets(type, aid, status);
```

**Why**: Composite indexes provide 10-100x performance improvement for filtered queries. Index column order matters: put equality filters first, then range/sort columns.

**Index Design Rules**:
- Match WHERE clause column order
- Include sort columns (DESC/ASC) at the end
- Use partial indexes (WHERE clause) for sparse columns
- Avoid over-indexing (each index adds write overhead)

---

## Connection Pattern

All database access goes through three functions in `backend/database.py`:

```python
# Read operations (SELECT)
rows = await execute_query("SELECT * FROM targets WHERE status = ?", (status,))
# Returns: list[dict]

# Insert operations (INSERT)
last_id = await execute_insert("INSERT INTO targets (...) VALUES (...)", params)
# Returns: int (lastrowid)

# Batch operations (INSERT/UPDATE many)
await execute_many("INSERT INTO targets (...) VALUES (...)", params_list)
# Returns: None
```

**Important**: All three functions acquire `_lock` internally. Never hold additional locks.

---

## Query Patterns

### Parameterized Queries (REQUIRED)

```python
# Good — parameterized
await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))

# Bad — string interpolation (SQL injection risk)
await execute_query(f"SELECT * FROM targets WHERE id = {target_id}")
```

### Dynamic WHERE Clauses

Build WHERE clauses dynamically for optional filters:

```python
where_clauses = []
params = []
if status:
    where_clauses.append("status = ?")
    params.append(status)
where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
rows = await execute_query(f"SELECT * FROM targets {where_sql}", tuple(params))
```

### Dynamic UPDATE with Whitelist

Use a field whitelist to prevent arbitrary column updates:

```python
ALLOWED_UPDATE_FIELDS = {"reason_id", "reason_text", "status"}

async def update_target(target_id: int, fields: dict):
    updates, params = [], []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return None
    updates.append("updated_at = datetime('now')")
    params.append(target_id)
    await execute_query(
        f"UPDATE targets SET {', '.join(updates)} WHERE id = ?", tuple(params)
    )
```

### Upsert Pattern (ON CONFLICT)

```python
await execute_query(
    "INSERT INTO system_config (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP) "
    "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
    (key, serialized),
)
```

### Pagination

```python
# Always count first, then fetch page
count_rows = await execute_query(f"SELECT COUNT(*) as total FROM targets {where_sql}", params)
total = count_rows[0]["total"]

offset = (page - 1) * page_size
rows = await execute_query(
    f"SELECT * FROM targets {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
    (*params, page_size, offset),
)
```

---

## Schema Conventions

### Table Structure

| Convention | Example |
|-----------|--------|
| Table names | Plural, `snake_case` | `accounts`, `report_logs` |
| Primary key | `id INTEGER PRIMARY KEY AUTOINCREMENT` |
| Timestamps | `created_at DATETIME DEFAULT CURRENT_TIMESTAMP` |
| Update tracking | `updated_at DATETIME` (set manually) |
| Booleans | `INTEGER` with `DEFAULT 1` or `DEFAULT 0` |
| JSON storage | `TEXT` column, parsed in Python |
| Enums | `TEXT` with `CHECK` constraint |

### Existing Tables

| Table | Purpose |
|-------|--------|
| `accounts` | Bilibili credentials (sessdata, bili_jct, buvid3, buvid4) |
| `targets` | Report targets (video/comment/user) with status |
| `report_logs` | Execution audit trail |
| `autoreply_config` | Keyword-response rules |
| `autoreply_state` | Dedup tracking (account_id + talker_id → last_msg_ts) |
| `scheduled_tasks` | APScheduler task definitions |
| `system_config` | Key-value settings store |

### Adding New Tables

1. Add `CREATE TABLE IF NOT EXISTS` to `backend/db/schema.sql`
2. Add indexes for frequently queried columns
3. Use foreign keys with appropriate `ON DELETE` behavior
4. Test with `init_db()` — schema is idempotent

### Adding Columns to Existing Tables

`CREATE TABLE IF NOT EXISTS` is idempotent but does NOT add new columns to existing tables. For existing databases:

1. Update `backend/db/schema.sql` with the new column
2. Run `ALTER TABLE <table> ADD COLUMN <col> <type>;` on the live database
3. SQLite `ALTER TABLE ADD COLUMN` is safe — it never fails if the column already exists

```python
# Migration pattern (run once)
async with aiosqlite.connect("data/sentinel.db") as conn:
    cols = await conn.execute("PRAGMA table_info(accounts)")
    col_names = [r[1] for r in await cols.fetchall()]
    if "new_column" not in col_names:
        await conn.execute("ALTER TABLE accounts ADD COLUMN new_column TEXT")
        await conn.commit()
```

> **Gotcha**: `CREATE TABLE IF NOT EXISTS` silently succeeds even if columns differ from the existing table. Always check live databases after schema changes.

---

## Common Mistakes

### Mistake 1: Forgetting Tuple for Single Params

```python
# Bad — missing comma, not a tuple
await execute_query("SELECT * FROM targets WHERE id = ?", (target_id))

# Good — trailing comma makes it a tuple
await execute_query("SELECT * FROM targets WHERE id = ?", (target_id,))
```

### Mistake 2: Not Parsing JSON from TEXT Columns

SQLite stores JSON as TEXT. Parse it in Python:

```python
# config_json is stored as TEXT
row = rows[0]
try:
    row["config_json"] = json.loads(row["config_json"])
except (json.JSONDecodeError, TypeError):
    row["config_json"] = None
```

### Mistake 3: Using execute_query for Writes Without Commit

`execute_query` calls `conn.commit()` after every operation. This is intentional — no explicit commit needed.

### Mistake 4: Dynamic Column Names Without Whitelist

Never build column names from user input without a whitelist. Always use `ALLOWED_UPDATE_FIELDS`.

---

## Caching

For high-frequency read queries, implement TTL-based caching to reduce database load:

```python
# In database.py
_cache: dict[str, tuple[float, list[dict]]] = {}
_cache_lock = asyncio.Lock()

async def get_active_accounts_cached():
    """Get active accounts with 60s TTL cache."""
    cache_key = "active_accounts"
    async with _cache_lock:
        if cache_key in _cache:
            expire_time, data = _cache[cache_key]
            if time.time() < expire_time:
                return data

    result = await execute_query("SELECT * FROM accounts WHERE is_active = 1 AND status = 'valid'")

    async with _cache_lock:
        _cache[cache_key] = (time.time() + 60, result)
    return result

async def invalidate_cache(pattern: str):
    """Invalidate cache entries matching pattern."""
    async with _cache_lock:
        keys_to_delete = [k for k in _cache.keys() if pattern in k]
        for key in keys_to_delete:
            del _cache[key]
```

**Cache invalidation**: Always invalidate cache when data changes:

```python
# In account_service.py
async def update_account(account_id, fields):
    await execute_query("UPDATE accounts SET ...", params)
    await invalidate_cache("active_accounts")  # Clear cache
```

> **Best Practice**: Use short TTLs (60-300s) to balance performance and data freshness. Always invalidate on writes.

---

## Concurrency

- **Single worker required** (`--workers 1`). Enforced with warning in `main.py` lifespan.
- `asyncio.Lock` serializes all DB operations within the single process.
- WAL mode allows concurrent reads while writing.
- No connection pooling — singleton connection pattern.
