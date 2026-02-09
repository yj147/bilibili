# Journal - Bambi (Part 1)

> AI development session journal
> Started: 2026-02-08

---


## Session 1: WBI自动刷新 + 风控码处理 + buvid4 + 代码质量优化

**Date**: 2026-02-08
**Task**: WBI自动刷新 + 风控码处理 + buvid4 + 代码质量优化

### Summary

(Add summary)

### Main Changes

## Changes (uncommitted)

| Category | Change | Files |
|----------|--------|-------|
| **WBI Keys** | Module-level cache with 1h TTL, auto-refresh on stale, startup refresh | `bilibili_auth.py`, `bilibili_client.py`, `main.py` |
| **Error Codes** | -352 risk control (5min wait), -101 not-logged-in (no retry), exponential backoff | `bilibili_client.py` |
| **buvid4** | Full-stack support: schema → service → API → model → core | `schema.sql`, `account_service.py`, `accounts.py`, `account.py`, `bilibili_auth.py` |
| **Code Quality** | USER_AGENTS consolidated to config.py, print→logger, unused import removed | `config.py`, `bilibili_client.py`, `bilibili_auth.py` |
| **Tests** | Added @pytest.mark.asyncio to all stress tests, 13/13 passing | `test_report_stress.py` |
| **Specs** | Updated error-handling.md, database-guidelines.md, quality-guidelines.md | `.trellis/spec/backend/` |
| **DB Migration** | ALTER TABLE accounts ADD COLUMN buvid4 TEXT (executed on live DB) | `schema.sql` |

**Key Learnings Captured in Specs**:
- Bilibili API error code table with retry strategies
- Schema migration pattern for existing SQLite databases
- Constants must be centralized in config.py

### Git Commits

| Hash | Message |
|------|---------|
| `uncommitted` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

## Session 2: 归档 bootstrap-guidelines 任务

**Date**: 2026-02-08
**Task**: 归档 bootstrap-guidelines 任务

### Summary

审查了所有 backend/frontend spec 文件，确认规范文档已完整填写（含真实代码示例和反模式）。更新 task.json 子任务状态为 completed，归档任务到 archive/2026-02/。

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `9077e8a` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

## Session 3: 归档 bootstrap-guidelines 任务

**Date**: 2026-02-08
**Task**: 归档 bootstrap-guidelines 任务

### Summary

审查了所有 backend/frontend spec 文件，确认规范文档已完整填写。更新 task.json 子任务状态为 completed，归档任务到 archive/2026-02/。

### Main Changes



### Git Commits

| Hash | Message |
|------|---------|
| `9077e8a` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete

## Session 4: QR扫码登录前端集成 + Cookie可视化维护

**Date**: 2026-02-09
**Task**: QR扫码登录前端集成 + Cookie可视化维护

### Summary

(Add summary)

### Main Changes

## 工作内容

| 模块 | 变更 |
|------|------|
| QRLoginModal 组件 | 新建，状态机（loading/waiting/scanned/success/expired/error），qrcode.react 渲染，2s 轮询 |
| Toast 组件 | 新建，4 种类型（warning/success/info/error），framer-motion 动画，auto-dismiss |
| accounts 页面 | 重写：扫码登录按钮、Cookie 状态列、刷新按钮、Toast 提醒、空状态 CTA |
| SWR useAccounts | 加 30s refreshInterval 自动轮询 |
| auth_service.py | 新增 _fetch_buvid() 获取 buvid3/buvid4，覆盖新建+更新两条路径 |
| auth_service.py | UA 改从 config.py 引用，logger 加 [Auth] 前缀 |
| types.ts | 新增 QRGenerateResponse, QRPollResponse, CookieStatusResponse, CookieRefreshResponse |

## Spec 更新

- `frontend/hook-guidelines.md` — React 19 effect rules、useAccounts 30s、auth hooks
- `frontend/component-guidelines.md` — Toast 模式（useRef 去重）、QR modal 状态机
- `frontend/quality-guidelines.md` — cn() vs 模板字符串、Toast dedup
- `backend/quality-guidelines.md` — buvid gotcha、cookie refresh 多步骤、auth_service 架构决策
- `guides/cross-layer-thinking-guide.md` — QR 登录跨层 case study

## 关键发现

- React 19 禁止 useEffect 内同步 setState，需拆分 async fetch 和 button handler
- buvid3/buvid4 不在 QR 登录返回中，须单独调 `/x/frontend/finger/spi`
- 缺少 buvid 会导致 -352 风控或 -412 限流

## 质量检查

- Lint: 0 新增错误（9 预存）
- TypeScript: 0 新增错误（2 预存）
- 无 console.log / print / any

### Git Commits

| Hash | Message |
|------|---------|
| `4a289bd` | (see git log) |

### Testing

- [OK] (Add test results)

### Status

[OK] **Completed**

### Next Steps

- None - task complete
