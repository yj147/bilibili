# Bili-Sentinel 剩余架构修复 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 完成剩余 10 项架构问题的修复，使项目达到生产可用水平

**Architecture:** 按依赖顺序分 5 个阶段执行。Phase 1 处理后端基础（Service层、WebSocket认证、配置化），Phase 2 处理后端配套API，Phase 3 处理前端状态管理和WebSocket集成，Phase 4 处理基础设施（测试、Docker），Phase 5 处理低优先级收尾。

**Tech Stack:** Python/FastAPI/aiosqlite, Next.js 16/React 19/TypeScript, SWR, Docker, pytest

---

## 依赖关系图

```
Phase 1 (后端基础)
├── Task 1: Service 层填充
├── Task 2: WebSocket 认证
├── Task 3: 超时/延迟配置化
└── Task 4: 全局状态 → 单 worker 约束文档化

Phase 2 (后端配套)
├── Task 5: Config API (依赖 Task 1)
└── Task 6: 系统信息 API

Phase 3 (前端升级)
├── Task 7: SWR 状态管理 (依赖 Task 5, 6)
├── Task 8: WebSocket 日志集成 (依赖 Task 2)
└── Task 9: 硬编码文案替换 (依赖 Task 6)

Phase 4 (基础设施)
├── Task 10: pytest 测试框架
├── Task 11: Dockerfile + docker-compose
└── Task 12: start.sh 修复
```

---

## Phase 1: 后端基础

### Task 1: Service 层填充

**问题:** `backend/services/` 只有 `__init__.py`，API 路由直接操作数据库 + 调用 core，违反三层架构

**方案:** 将 API 路由中的业务逻辑提取到 Service 层，API 层只负责请求解析和响应构造

**Files:**
- Create: `backend/services/account_service.py`
- Create: `backend/services/config_service.py`
- Modify: `backend/api/accounts.py` — 调用 service 替代直接 SQL
- Modify: `backend/api/autoreply.py` — 提取配置 CRUD 到 service

**Step 1: 创建 account_service.py**

```python
"""Account business logic."""
from backend.database import execute_query, execute_insert
from backend.logger import logger

ALLOWED_UPDATE_FIELDS = {"name", "sessdata", "bili_jct", "buvid3", "group_tag", "is_active"}


async def list_accounts():
    return await execute_query("SELECT * FROM accounts ORDER BY created_at DESC")


async def get_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def create_account(name: str, sessdata: str, bili_jct: str, buvid3: str = "", group_tag: str = "default"):
    account_id = await execute_insert(
        "INSERT INTO accounts (name, sessdata, bili_jct, buvid3, group_tag) VALUES (?, ?, ?, ?, ?)",
        (name, sessdata, bili_jct, buvid3, group_tag)
    )
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0]


async def update_account(account_id: int, fields: dict):
    updates = []
    params = []
    for field, value in fields.items():
        if value is not None and field in ALLOWED_UPDATE_FIELDS:
            updates.append(f"{field} = ?")
            params.append(value)
    if not updates:
        return None
    params.append(account_id)
    await execute_query(f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?", tuple(params))
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    return rows[0] if rows else None


async def delete_account(account_id: int):
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return False
    await execute_query("DELETE FROM accounts WHERE id = ?", (account_id,))
    return True


async def get_active_accounts():
    return await execute_query("SELECT * FROM accounts WHERE is_active = 1")


async def check_account_validity(account_id: int):
    import httpx
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return None
    account = rows[0]
    cookies = {"SESSDATA": account["sessdata"], "bili_jct": account["bili_jct"], "buvid3": account["buvid3"] or ""}
    async with httpx.AsyncClient(cookies=cookies) as client:
        resp = await client.get(
            "https://api.bilibili.com/x/web-interface/nav",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
        )
        data = resp.json()
    is_valid = data.get("code") == 0
    uid = data.get("data", {}).get("mid") if is_valid else None
    status = "valid" if is_valid else "invalid"
    await execute_query(
        "UPDATE accounts SET status = ?, uid = ?, last_check_at = datetime('now') WHERE id = ?",
        (status, uid, account_id)
    )
    return {"id": account_id, "name": account["name"], "status": status, "is_valid": is_valid, "uid": uid}
```

**Step 2: 重构 api/accounts.py 调用 service**

将每个路由函数体替换为对 `account_service` 的调用，路由层只做：
- 参数解析（已由 Pydantic 处理）
- 调用 service
- 处理 404 等 HTTP 语义
- 返回响应

**Step 3: 创建 config_service.py（为 Task 5 做准备）**

```python
"""System configuration service."""
import json
from backend.database import execute_query, execute_insert
from backend.config import MIN_DELAY, MAX_DELAY

# In-memory config cache (single worker)
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
        await execute_query("UPDATE system_config SET value = ? WHERE key = ?", (str_value, key))
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
```

**Step 4: 添加 system_config 表到 schema.sql**

```sql
CREATE TABLE IF NOT EXISTS system_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Default config values
INSERT OR IGNORE INTO system_config (key, value) VALUES ('min_delay', '2.0');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('max_delay', '10.0');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('ua_rotation', 'true');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('auto_clean_logs', 'true');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('log_retention_days', '30');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('webhook_url', '');
INSERT OR IGNORE INTO system_config (key, value) VALUES ('notify_level', 'error');
```

**Step 5: Commit**

```bash
git add backend/services/ backend/api/accounts.py backend/db/schema.sql
git commit -m "refactor: 填充 Service 层 + system_config 表"
```

---

### Task 2: WebSocket 认证

**问题:** `/ws/logs` 任何人连上就能收到所有日志，无认证

**Files:**
- Modify: `backend/api/websocket.py`

**Step 1: 添加 token query param 验证**

在 `websocket_logs` 函数开头添加：

```python
import os

@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    api_key = os.getenv("SENTINEL_API_KEY", "")
    if api_key:
        token = websocket.query_params.get("token", "")
        if token != api_key:
            await websocket.close(code=4001, reason="Unauthorized")
            return
    
    await websocket.accept()
    # ... rest of existing code
```

**Step 2: 修复裸 except**

将 `except:` 改为 `except Exception:`

**Step 3: Commit**

```bash
git add backend/api/websocket.py
git commit -m "fix: WebSocket 认证 + 异常处理修复"
```

---

### Task 3: 超时/延迟配置化

**问题:** 超时硬编码 10.0s，延迟 2-10s 硬编码

**Files:**
- Modify: `backend/config.py` — 从环境变量读取
- Modify: `backend/core/bilibili_client.py` — 使用 config

**Step 1: 扩展 config.py**

```python
# Timeouts
HTTP_TIMEOUT = float(os.getenv("SENTINEL_HTTP_TIMEOUT", "10.0"))
MAX_RETRIES = int(os.getenv("SENTINEL_MAX_RETRIES", "3"))
```

**Step 2: bilibili_client.py 引用 config**

```python
from backend.config import MIN_DELAY, MAX_DELAY, HTTP_TIMEOUT, MAX_RETRIES

# __init__ 中:
self._client = httpx.AsyncClient(cookies=self.cookies, headers=self.headers, timeout=HTTP_TIMEOUT)

# _request 中:
async def _request(self, method, url, params=None, data=None, sign=False, retries=None):
    if retries is None:
        retries = MAX_RETRIES
```

**Step 3: Commit**

```bash
git commit -am "feat: 超时/延迟/重试次数配置化"
```

---

### Task 4: 全局状态 — 单 Worker 约束文档化

**问题:** autoreply 和 scheduler 用模块级全局变量，多 worker 会失效

**方案:** 不做架构改造（过度工程化），在 start.sh 和文档中明确约束 `--workers 1`

**Files:**
- Modify: `docs/backend_architecture.md` — 添加部署约束说明
- Modify: `backend/config.py` — 添加 WORKERS 配置

**Step 1: config.py 添加 WORKERS**

```python
WORKERS = int(os.getenv("SENTINEL_WORKERS", "1"))
```

**Step 2: main.py 启动时加警告**

在 lifespan startup 中：
```python
if os.cpu_count() and os.cpu_count() > 1:
    logger.warning("Bili-Sentinel 必须以单 worker 模式运行 (--workers 1)，否则调度器和自动回复状态会不一致")
```

**Step 3: Commit**

```bash
git commit -am "docs: 单 worker 约束 + WORKERS 配置"
```

---

## Phase 2: 后端配套 API

### Task 5: Config CRUD API

**问题:** Config 页面纯静态，没有后端 API

**Files:**
- Create: `backend/api/config.py`
- Modify: `backend/main.py` — 注册新路由
- Modify: `backend/models/__init__.py` — 添加 ConfigModel

**Step 1: 创建 api/config.py**

```python
"""System Configuration API Routes"""
from fastapi import APIRouter
from backend.services.config_service import get_config, set_config, get_all_configs

router = APIRouter()

@router.get("/")
async def list_configs():
    return await get_all_configs()

@router.get("/{key}")
async def get_config_value(key: str):
    value = await get_config(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Config '{key}' not found")
    return {"key": key, "value": value}

@router.put("/{key}")
async def update_config_value(key: str, body: dict):
    await set_config(key, body.get("value"))
    return {"key": key, "value": body.get("value")}

@router.post("/batch")
async def update_configs_batch(configs: dict):
    for key, value in configs.items():
        await set_config(key, value)
    return {"message": f"Updated {len(configs)} configs"}
```

**Step 2: 注册路由到 main.py**

```python
from backend.api import config
app.include_router(config.router, prefix="/api/config", tags=["Config"])
```

**Step 3: Commit**

```bash
git commit -am "feat: Config CRUD API"
```

---

### Task 6: 系统信息 API

**Files:**
- Modify: `backend/main.py` — 添加 /api/system/info 路由

**Step 1: 添加系统信息端点**

```python
@app.get("/api/system/info")
async def system_info():
    import platform
    account_count = await execute_query("SELECT COUNT(*) as c FROM accounts")
    target_count = await execute_query("SELECT COUNT(*) as c FROM targets")
    return {
        "version": "1.0.0",
        "python": platform.python_version(),
        "platform": platform.system(),
        "accounts": account_count[0]["c"],
        "targets": target_count[0]["c"],
    }
```

**Step 2: Commit**

```bash
git commit -am "feat: 系统信息 API"
```

---

## Phase 3: 前端升级

### Task 7: SWR 状态管理

**问题:** 每个页面独立 useState + useEffect 拉数据，无缓存共享

**Files:**
- Modify: `frontend/package.json` — 添加 swr
- Create: `frontend/src/lib/swr.ts` — SWR 配置
- Modify: `frontend/src/app/page.tsx` — 用 useSWR 替代 useEffect
- Modify: `frontend/src/app/accounts/page.tsx`
- Modify: `frontend/src/app/targets/page.tsx`
- Modify: `frontend/src/app/autoreply/page.tsx`
- Modify: `frontend/src/app/scheduler/page.tsx`

**Step 1: 安装 SWR**

```bash
cd frontend && npm install swr
```

**Step 2: 创建 SWR 配置**

```typescript
// src/lib/swr.ts
import useSWR from 'swr';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || '/api';

const fetcher = (path: string) => fetch(`${API_BASE}${path}`).then(r => {
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
});

export function useAccounts() {
  return useSWR('/accounts/', fetcher);
}

export function useTargets(params = {}) {
  const query = new URLSearchParams(params).toString();
  return useSWR(`/targets/?${query}`, fetcher);
}

export function useReportLogs(limit = 50) {
  return useSWR(`/reports/logs?limit=${limit}`, fetcher);
}

export function useAutoReplyConfigs() {
  return useSWR('/autoreply/config', fetcher);
}

export function useAutoReplyStatus() {
  return useSWR('/autoreply/status', fetcher, { refreshInterval: 5000 });
}

export function useSchedulerTasks() {
  return useSWR('/scheduler/tasks', fetcher);
}

export function useSchedulerHistory(limit = 20) {
  return useSWR(`/scheduler/history?limit=${limit}`, fetcher);
}

export function useSystemInfo() {
  return useSWR('/system/info', fetcher, { refreshInterval: 30000 });
}

export function useConfigs() {
  return useSWR('/config/', fetcher);
}
```

**Step 3: 重构 Dashboard 用 useSWR**

替换 `useState` + `useEffect` + `setInterval` 模式为：
```typescript
const { data: accounts, mutate: mutateAccounts } = useAccounts();
const { data: targets } = useTargets();
const { data: logs } = useReportLogs(15);
```

删除 `fetchData` 函数和 10 秒轮询。

**Step 4: 同样重构其他 4 个页面**

**Step 5: Commit**

```bash
git commit -am "feat: SWR 状态管理替代 useEffect 轮询"
```

---

### Task 8: WebSocket 日志集成

**问题:** 后端有 /ws/logs，前端不用

**Files:**
- Create: `frontend/src/lib/websocket.ts` — WS hook
- Modify: `frontend/src/app/page.tsx` — Dashboard 实时日志

**Step 1: 创建 WebSocket hook**

```typescript
// src/lib/websocket.ts
import { useEffect, useRef, useState, useCallback } from 'react';

export interface LogEntry {
  type: string;
  message: string;
  data: Record<string, any>;
  timestamp: number;
}

export function useLogStream(maxLogs = 100) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/logs`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => {
      setConnected(false);
      // Auto-reconnect after 3s
      setTimeout(() => wsRef.current?.close(), 3000);
    };
    ws.onmessage = (event) => {
      try {
        const entry = JSON.parse(event.data) as LogEntry;
        if (entry.type === 'heartbeat' || entry.type === 'pong') return;
        setLogs(prev => [entry, ...prev].slice(0, maxLogs));
      } catch {}
    };

    return () => ws.close();
  }, [maxLogs]);

  return { logs, connected };
}
```

**Step 2: Dashboard 集成实时日志**

在 Dashboard 的日志区域用 `useLogStream()` 替代 API 轮询的 logs。

**Step 3: Commit**

```bash
git commit -am "feat: WebSocket 实时日志集成"
```

---

### Task 9: 硬编码文案替换

**Files:**
- Modify: `frontend/src/components/Sidebar.tsx` — 用户信息从 API 获取
- Modify: `frontend/src/app/config/page.tsx` — 版本号从 API 获取

**Step 1: Config 页面接入真实数据**

- 用 `useConfigs()` 和 `useSystemInfo()` 替代硬编码值
- 保存按钮调用 `api.config.updateBatch()`
- 版本号从 `/api/system/info` 获取

**Step 2: Sidebar 用户信息**

暂时从 localStorage 或固定配置读取（不做用户系统，但至少不硬编码 "ENI Enchanted"）

**Step 3: Commit**

```bash
git commit -am "fix: 替换硬编码文案为动态数据"
```

---

## Phase 4: 基础设施

### Task 10: pytest 测试框架

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_accounts_api.py`
- Create: `backend/tests/test_database.py`
- Create: `backend/tests/test_config_service.py`
- Modify: `backend/requirements.txt` — 添加 pytest, pytest-asyncio, httpx[test]

**Step 1: requirements.txt 添加测试依赖**

```
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx[test]>=0.26.0
```

**Step 2: conftest.py — 测试数据库 fixture**

```python
import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.database import init_db, close_db
from backend.config import DATABASE_PATH
import os

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
async def setup_test_db(tmp_path):
    os.environ["SENTINEL_DB_PATH"] = str(tmp_path / "test.db")
    await init_db()
    yield
    await close_db()

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

**Step 3: 写基础 API 测试**

```python
# test_accounts_api.py
import pytest

@pytest.mark.asyncio
async def test_list_accounts_empty(client):
    resp = await client.get("/api/accounts/")
    assert resp.status_code == 200
    assert resp.json() == []

@pytest.mark.asyncio
async def test_create_account(client):
    resp = await client.post("/api/accounts/", json={
        "name": "test", "sessdata": "abc", "bili_jct": "def"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "test"
    assert data["id"] == 1

@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"
```

**Step 4: 运行验证**

```bash
cd /tmp/bilibili && python -m pytest backend/tests/ -v
```

**Step 5: Commit**

```bash
git commit -am "test: pytest 框架 + 基础 API 测试"
```

---

### Task 11: Docker 部署

**Files:**
- Create: `Dockerfile`
- Create: `docker-compose.yml`
- Create: `.dockerignore`

**Step 1: Dockerfile (多阶段构建)**

```dockerfile
# --- Frontend build ---
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Backend ---
FROM python:3.12-slim
WORKDIR /app

COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY --from=frontend-build /app/frontend/.next ./frontend/.next
COPY --from=frontend-build /app/frontend/public ./frontend/public
COPY --from=frontend-build /app/frontend/package*.json ./frontend/
COPY --from=frontend-build /app/frontend/node_modules ./frontend/node_modules

EXPOSE 8000 3000

CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 1 & cd frontend && npx next start -p 3000 & wait"]
```

**Step 2: docker-compose.yml**

```yaml
version: '3.8'
services:
  sentinel:
    build: .
    ports:
      - "8000:8000"
      - "3000:3000"
    volumes:
      - ./data:/app/data
    environment:
      - SENTINEL_API_KEY=${SENTINEL_API_KEY:-}
      - SENTINEL_DEBUG=false
    restart: unless-stopped
```

**Step 3: .dockerignore**

```
.git
node_modules
__pycache__
*.pyc
data/
.trellis/
venv/
```

**Step 4: Commit**

```bash
git commit -am "infra: Dockerfile + docker-compose"
```

---

### Task 12: start.sh 修复

**问题:** 硬编码 `/home/jikns/Projects/bilibili`

**Files:**
- Modify: `start.sh`

**Step 1: 使用相对路径**

```bash
#!/bin/bash
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_ROOT"

echo "Starting Bili-Sentinel..."

python -m backend.main > /tmp/sentinel-backend.log 2>&1 &
BACKEND_PID=$!

cd frontend && npx next dev > /tmp/sentinel-frontend.log 2>&1 &
FRONTEND_PID=$!

echo "Backend: http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:3000 (PID: $FRONTEND_PID)"

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo 'Stopped'; exit" INT TERM
wait
```

**Step 2: Commit**

```bash
git commit -am "fix: start.sh 使用相对路径"
```

---

## 执行顺序总结

| 阶段 | 任务 | 预估复杂度 |
|------|------|------------|
| Phase 1 | Task 1: Service 层 | 高 |
| Phase 1 | Task 2: WS 认证 | 低 |
| Phase 1 | Task 3: 配置化 | 低 |
| Phase 1 | Task 4: 单 Worker 约束 | 低 |
| Phase 2 | Task 5: Config API | 中 |
| Phase 2 | Task 6: 系统信息 API | 低 |
| Phase 3 | Task 7: SWR | 高 |
| Phase 3 | Task 8: WS 集成 | 中 |
| Phase 3 | Task 9: 文案替换 | 低 |
| Phase 4 | Task 10: pytest | 中 |
| Phase 4 | Task 11: Docker | 中 |
| Phase 4 | Task 12: start.sh | 低 |
