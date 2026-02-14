# Backend Development Guidelines

> Best practices for backend development in Bili-Sentinel.

---

## Overview

Bili-Sentinel backend is a **FastAPI** application with **aiosqlite** (SQLite), organized in a layered architecture: API routes → Services → Database, with a `core/` layer for Bilibili API integration.

**Key constraints**:
- Single worker only (`--workers 1`) due to SQLite singleton connection
- All I/O is async
- Python 3.12+

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | Module organization, layer rules, import direction | Done |
| [Database Guidelines](./database-guidelines.md) | Raw SQL patterns, parameterized queries, schema conventions | Done |
| [Error Handling](./error-handling.md) | Middleware, (result, error) tuples, retry logic | Done |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, required/forbidden patterns, testing | Done |
| [Logging Guidelines](./logging-guidelines.md) | Logger usage, levels, WebSocket broadcasting | Done |
| [Concurrency Patterns](./concurrency-patterns.md) | asyncio.Lock, atomic claims, TOCTOU prevention, background tasks | Done |

---

## Quick Reference

### Architecture Layers

```
api/ (thin routers) -> services/ (business logic) -> database.py (raw SQL)
                                                   -> core/ (Bilibili API)
```

### Key Files

| File | Purpose |
|------|--------|
| `main.py` | App entry, lifespan, router registration |
| `database.py` | Singleton aiosqlite with asyncio.Lock |
| `config.py` | Environment variables and constants |
| `middleware.py` | Unified exception handlers |
| `auth.py` | API key authentication (X-API-Key header) |
| `db/schema.sql` | SQLite DDL (idempotent) |

### Common Commands

```bash
# Run backend
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1

# Run tests
pytest backend/tests/
```
