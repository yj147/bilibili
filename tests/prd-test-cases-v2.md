# Test Cases: Bili-Sentinel PRD v2（重构后代码对齐版）

## Overview
- **Feature**: Bili-Sentinel 全模块回归测试（重构后）
- **Requirements Source**: `docs/PRD.md`
- **Reference Docs**: `tests/prd-test-cases.md`, `tests/test-report-2026-02-10.md`
- **Code Alignment Baseline**: `backend/api/*`, `backend/models/*`, `backend/services/*`, `frontend/src/app/*`
- **Last Updated**: 2026-02-18
- **Scope**: 手工 QA 可执行用例 + 可自动化拆分提示

## Risk-First Test Policy（必须遵守）
- 优先保障账号稳定性，避免触发平台风控。
- 真实环境只使用测试账号，不对生产账号做高频压测。
- 涉及举报频率/轮询/并发的高风险场景优先使用 mock、代码验证与单账号替代验证。
- 多账号池真实并发执行在当前阶段标记为 `Code-Verified`（见文末“受限场景”）。

## Environment & Preconditions
- 后端：FastAPI（单 worker）
- 前端：Next.js + API Proxy
- 数据库：SQLite（独立测试库）
- 默认鉴权：根据 `SENTINEL_API_KEY` 进行开关测试
- 风控相关配置：`min_delay` / `max_delay` / `account_cooldown`

---

## Requirement IDs
- `REQ-ACC-*`: 账号管理
- `REQ-TGT-*`: 目标管理
- `REQ-RPT-*`: 举报执行
- `REQ-AR-*`: 自动回复
- `REQ-SCH-*`: 调度任务
- `REQ-CFG-*`: 系统配置
- `REQ-AUTH-*`: 登录与 Cookie
- `REQ-WS-*`: WebSocket 日志
- `REQ-NFR-*`: 非功能（稳定性/低风险）

---

## 1. Functional Tests

### TC-F-001: 创建账号（最小必填）
- **Requirement**: REQ-ACC-001
- **Priority**: High
- **Preconditions**: 系统启动，数据库可写
- **Test Steps**:
  1. `POST /api/accounts/`，仅传 `name,sessdata,bili_jct`
- **Expected Results**:
  - 返回 200 且符合 `AccountPublic`
  - `group_tag` 默认为 `default`
  - 不返回敏感字段

### TC-F-002: 获取账号列表（分页）
- **Requirement**: REQ-ACC-002
- **Priority**: High
- **Test Steps**:
  1. `GET /api/accounts/?page=1&page_size=50`
- **Expected Results**:
  - 返回分页结构
  - `items,total,page,page_size` 正确

### TC-F-003: 账号导出（不含凭证）
- **Requirement**: REQ-ACC-003
- **Priority**: High
- **Test Steps**:
  1. `GET /api/accounts/export?include_credentials=false`
- **Expected Results**:
  - 不包含 `sessdata/bili_jct`

### TC-F-004: 账号导出（含凭证审计）
- **Requirement**: REQ-ACC-004
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/accounts/export?include_credentials=true`
- **Expected Results**:
  - 包含凭证字段
  - 记录审计日志（warning）

### TC-F-005: 批量导入账号
- **Requirement**: REQ-ACC-005
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/import` 传合法数组
- **Expected Results**:
  - 导入成功且数量正确

### TC-F-006: 单账号健康检查
- **Requirement**: REQ-ACC-006
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/{id}/check`
- **Expected Results**:
  - 返回 `AccountStatus`

### TC-F-007: 全量健康检查排队（异步）
- **Requirement**: REQ-ACC-007
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/check-all`
- **Expected Results**:
  - 返回 202
  - 消息为 queued

### TC-F-008: 读取单账号凭证
- **Requirement**: REQ-ACC-008
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/{id}/credentials`
- **Expected Results**:
  - 返回 `AccountCredentials`
  - 响应头 `Cache-Control: no-store`

### TC-F-009: 创建目标（video）
- **Requirement**: REQ-TGT-001
- **Priority**: High
- **Test Steps**:
  1. `POST /api/targets/` with `type=video, identifier=BV...`
- **Expected Results**:
  - 返回 200，状态默认 `pending`

### TC-F-010: 创建目标（comment，合法 reason_id）
- **Requirement**: REQ-TGT-002
- **Priority**: High
- **Test Steps**:
  1. `POST /api/targets/` with `type=comment, reason_id=4`
- **Expected Results**:
  - 创建成功
  - `reason_id` 被保留

### TC-F-011: 批量创建目标
- **Requirement**: REQ-TGT-003
- **Priority**: High
- **Test Steps**:
  1. `POST /api/targets/batch`
- **Expected Results**:
  - 返回 `{message,count}`

### TC-F-012: 获取目标列表（分页+过滤）
- **Requirement**: REQ-TGT-004
- **Priority**: High
- **Test Steps**:
  1. `GET /api/targets/?page=1&page_size=20&status=pending&type=video`
- **Expected Results**:
  - 过滤与分页同时生效

### TC-F-013: 目标统计接口
- **Requirement**: REQ-TGT-005
- **Priority**: High
- **Test Steps**:
  1. `GET /api/targets/stats`
- **Expected Results**:
  - 返回全局统计，不受分页影响

### TC-F-014: 按状态批量删除目标
- **Requirement**: REQ-TGT-006
- **Priority**: Medium
- **Test Steps**:
  1. `DELETE /api/targets/by-status/failed`
- **Expected Results**:
  - 返回删除数量

### TC-F-015: 单目标举报执行入队
- **Requirement**: REQ-RPT-001
- **Priority**: High
- **Test Steps**:
  1. 目标为 pending
  2. `POST /api/reports/execute`
- **Expected Results**:
  - 返回 202
  - 目标原子转为 processing

### TC-F-016: 批量举报执行入队
- **Requirement**: REQ-RPT-002
- **Priority**: High
- **Test Steps**:
  1. `POST /api/reports/execute/batch`
- **Expected Results**:
  - 返回 202 accepted

### TC-F-017: 举报日志查询
- **Requirement**: REQ-RPT-003
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/reports/logs?limit=100`
  2. `GET /api/reports/logs/{target_id}`
- **Expected Results**:
  - 返回 `ReportLog[]`

### TC-F-018: 评论扫描（只建目标）
- **Requirement**: REQ-RPT-004
- **Priority**: High
- **Test Steps**:
  1. `POST /api/reports/scan-comments` with `auto_report=false`
- **Expected Results**:
  - 返回扫描数量与创建数量

### TC-F-019: 自动回复规则创建
- **Requirement**: REQ-AR-001
- **Priority**: High
- **Test Steps**:
  1. `POST /api/autoreply/config`
- **Expected Results**:
  - 返回 `AutoReplyConfig`

### TC-F-020: 默认回复 upsert
- **Requirement**: REQ-AR-002
- **Priority**: High
- **Test Steps**:
  1. `PUT /api/autoreply/config/default`
- **Expected Results**:
  - 创建或更新默认规则成功

### TC-F-021: 启用自动回复（standalone）
- **Requirement**: REQ-AR-003
- **Priority**: High
- **Test Steps**:
  1. `POST /api/autoreply/enable`
- **Expected Results**:
  - 返回 enabled message

### TC-F-022: 停用自动回复（standalone）
- **Requirement**: REQ-AR-004
- **Priority**: High
- **Test Steps**:
  1. `POST /api/autoreply/disable`
- **Expected Results**:
  - 返回 disabled message

### TC-F-023: 创建调度任务（interval）
- **Requirement**: REQ-SCH-001
- **Priority**: High
- **Test Steps**:
  1. `POST /api/scheduler/tasks` with `interval_seconds`
- **Expected Results**:
  - 返回 `ScheduledTask`

### TC-F-024: 创建调度任务（cron）
- **Requirement**: REQ-SCH-002
- **Priority**: Medium
- **Test Steps**:
  1. `POST /api/scheduler/tasks` with `cron_expression`
- **Expected Results**:
  - 创建成功

### TC-F-025: 调度任务启停切换
- **Requirement**: REQ-SCH-003
- **Priority**: High
- **Test Steps**:
  1. `POST /api/scheduler/tasks/{id}/toggle`
- **Expected Results**:
  - `is_active` 正确翻转

### TC-F-026: 调度历史查询
- **Requirement**: REQ-SCH-004
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/scheduler/history?limit=50`
- **Expected Results**:
  - 返回历史列表

### TC-F-027: 获取全部配置
- **Requirement**: REQ-CFG-001
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/config/`
- **Expected Results**:
  - 返回 key-value 集合

### TC-F-028: 更新单个配置
- **Requirement**: REQ-CFG-002
- **Priority**: High
- **Test Steps**:
  1. `PUT /api/config/min_delay` body `{value: 3}`
- **Expected Results**:
  - 返回更新值

### TC-F-029: 批量更新配置（原子）
- **Requirement**: REQ-CFG-003
- **Priority**: High
- **Test Steps**:
  1. `POST /api/config/batch`
- **Expected Results**:
  - 所有配置一次性成功更新

### TC-F-030: 生成二维码登录
- **Requirement**: REQ-AUTH-001
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/auth/qr/generate`
- **Expected Results**:
  - 返回二维码信息与 key

### TC-F-031: 二维码轮询/登录流程
- **Requirement**: REQ-AUTH-002
- **Priority**: Medium
- **Test Steps**:
  1. `POST /api/auth/qr/poll`
  2. `POST /api/auth/qr/login`
- **Expected Results**:
  - 状态推进符合预期

### TC-F-032: Cookie 状态查询与刷新
- **Requirement**: REQ-AUTH-003
- **Priority**: High
- **Test Steps**:
  1. `GET /api/auth/{id}/cookie-status`
  2. `POST /api/auth/{id}/refresh`
- **Expected Results**:
  - 返回可读状态/刷新结果

### TC-F-033: WebSocket 日志连接（鉴权打开）
- **Requirement**: REQ-WS-001
- **Priority**: High
- **Test Steps**:
  1. 使用 `Sec-WebSocket-Protocol: token.<api_key>` 连接 `/ws/logs`
- **Expected Results**:
  - 连接成功
  - 收到 connected 消息

### TC-F-034: WebSocket 心跳与 pong
- **Requirement**: REQ-WS-002
- **Priority**: Medium
- **Test Steps**:
  1. 发送 `ping`
  2. 等待超时心跳
- **Expected Results**:
  - 收到 `pong`
  - 超时后收到 `heartbeat`

### TC-F-035: 前端代理转发（GET/POST）
- **Requirement**: REQ-NFR-001
- **Priority**: Medium
- **Test Steps**:
  1. 从前端 `/api/*` 调用账号与目标接口
- **Expected Results**:
  - 请求正确转发到后端

---

## 2. Edge Case Tests

### TC-E-001: 导入账号超过上限
- **Requirement**: REQ-ACC-005
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/import` 传 501 条
- **Expected Results**:
  - 400，`Maximum 500 accounts per import`

### TC-E-002: 账号分页 page_size 超上限
- **Requirement**: REQ-ACC-002
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/accounts/?page_size=201`
- **Expected Results**:
  - 422（Query 参数校验失败）

### TC-E-003: 目标分页上限
- **Requirement**: REQ-TGT-004
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/targets/?page_size=101`
- **Expected Results**:
  - 422

### TC-E-004: 评论目标非法 reason_id
- **Requirement**: REQ-TGT-002
- **Priority**: High
- **Test Steps**:
  1. `POST /api/targets/` with `type=comment, reason_id=11`
- **Expected Results**:
  - 422，提示必须在允许集合内

### TC-E-005: 评论标识符格式错误
- **Requirement**: REQ-TGT-002
- **Priority**: High
- **Test Steps**:
  1. `POST /api/targets/` with `identifier=abc:def:ghi`
- **Expected Results**:
  - 422

### TC-E-006: 更新目标无有效字段
- **Requirement**: REQ-TGT-007
- **Priority**: Medium
- **Test Steps**:
  1. `PUT /api/targets/{id}` body `{}`
- **Expected Results**:
  - 400，`No valid fields to update`

### TC-E-007: 调度任务同时设置 cron 与 interval
- **Requirement**: REQ-SCH-002
- **Priority**: High
- **Test Steps**:
  1. `POST /api/scheduler/tasks` 同时传 `cron_expression` 与 `interval_seconds`
- **Expected Results**:
  - 422，`Cannot set both...`

### TC-E-008: 调度任务两者都不设置
- **Requirement**: REQ-SCH-001
- **Priority**: High
- **Test Steps**:
  1. `POST /api/scheduler/tasks` 两者都缺失
- **Expected Results**:
  - 422，`Either cron_expression or interval_seconds must be set`

### TC-E-009: 无效 cron 表达式
- **Requirement**: REQ-SCH-002
- **Priority**: Medium
- **Test Steps**:
  1. `POST /api/scheduler/tasks` with invalid cron
- **Expected Results**:
  - 422，`Invalid cron expression`

### TC-E-010: 自动回复启用重复调用
- **Requirement**: REQ-AR-003
- **Priority**: Medium
- **Test Steps**:
  1. 连续调用两次 `/api/autoreply/enable`
- **Expected Results**:
  - 第二次返回 already enabled 信息

### TC-E-011: 配置 min_delay 越界
- **Requirement**: REQ-CFG-002
- **Priority**: High
- **Test Steps**:
  1. `PUT /api/config/min_delay` with `0.5`
- **Expected Results**:
  - 400，`min_delay must be between 1 and 10`

### TC-E-012: account_cooldown 传布尔值
- **Requirement**: REQ-CFG-002
- **Priority**: High
- **Test Steps**:
  1. `PUT /api/config/account_cooldown` with `true`
- **Expected Results**:
  - 400，`account_cooldown cannot be a boolean`

---

## 3. Error Handling Tests

### TC-ERR-001: 举报目标不存在
- **Requirement**: REQ-RPT-001
- **Priority**: High
- **Test Steps**:
  1. `POST /api/reports/execute` with missing target
- **Expected Results**:
  - 404，`Target not found`

### TC-ERR-002: 举报目标重复抢占
- **Requirement**: REQ-RPT-001
- **Priority**: High
- **Test Steps**:
  1. 并发提交同一 target 的 execute 请求
- **Expected Results**:
  - 一个 202，一个 409

### TC-ERR-003: 扫描评论传无效 BV
- **Requirement**: REQ-RPT-004
- **Priority**: High
- **Test Steps**:
  1. `POST /api/reports/scan-comments` with bad bvid
- **Expected Results**:
  - 400，detail 为扫描错误

### TC-ERR-004: 读取不存在账号凭证
- **Requirement**: REQ-ACC-008
- **Priority**: High
- **Test Steps**:
  1. `POST /api/accounts/{id}/credentials` with missing id
- **Expected Results**:
  - 404

### TC-ERR-005: 调度任务不存在（get/update/delete/toggle）
- **Requirement**: REQ-SCH-005
- **Priority**: Medium
- **Test Steps**:
  1. 对不存在 task_id 调用上述接口
- **Expected Results**:
  - 404

### TC-ERR-006: 查询不存在配置 key
- **Requirement**: REQ-CFG-001
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/config/not_exist_key`
- **Expected Results**:
  - 404

### TC-ERR-007: 鉴权开启时未带 API Key
- **Requirement**: REQ-NFR-002
- **Priority**: High
- **Test Steps**:
  1. 设置 `SENTINEL_API_KEY`
  2. 不带 key 调用受保护接口
- **Expected Results**:
  - 401/403（按中间件定义）

### TC-ERR-008: WebSocket token 无效
- **Requirement**: REQ-WS-001
- **Priority**: High
- **Test Steps**:
  1. 鉴权开启时以错误 token 连接
- **Expected Results**:
  - 连接被关闭，code=1008

### TC-ERR-009: Cookie 状态查询账号不存在
- **Requirement**: REQ-AUTH-003
- **Priority**: Medium
- **Test Steps**:
  1. `GET /api/auth/{missing}/cookie-status`
- **Expected Results**:
  - 404

### TC-ERR-010: 全量健康检查重复触发
- **Requirement**: REQ-ACC-007
- **Priority**: High
- **Test Steps**:
  1. 首次触发 check-all 后未结束前再次触发
- **Expected Results**:
  - 409，`already in progress`

---

## 4. State Transition Tests

### TC-ST-001: 目标状态流（pending->processing->completed）
- **Requirement**: REQ-RPT-001
- **Priority**: High
- **Test Steps**:
  1. 创建 pending 目标
  2. execute 入队并模拟成功
- **Expected Results**:
  - 状态按流程迁移到 completed

### TC-ST-002: 目标失败流（pending->processing->failed）
- **Requirement**: REQ-RPT-001
- **Priority**: High
- **Test Steps**:
  1. execute 入队并模拟失败
- **Expected Results**:
  - 状态进入 failed，重试计数更新

### TC-ST-003: claim CAS 单次成功
- **Requirement**: REQ-RPT-005
- **Priority**: High
- **Test Steps**:
  1. 对同一 target 连续 claim 两次
- **Expected Results**:
  - 首次 true，第二次 false

### TC-ST-004: 自动回复开关状态
- **Requirement**: REQ-AR-003/004
- **Priority**: High
- **Test Steps**:
  1. disable -> enable -> disable
- **Expected Results**:
  - `status.is_running` 与动作一致

### TC-ST-005: 调度任务启用状态切换
- **Requirement**: REQ-SCH-003
- **Priority**: High
- **Test Steps**:
  1. 连续 toggle 两次
- **Expected Results**:
  - `is_active` true/false 往返

### TC-ST-006: 配置更新后缓存失效
- **Requirement**: REQ-CFG-004
- **Priority**: High
- **Test Steps**:
  1. 修改 `min_delay/max_delay/account_cooldown`
  2. 触发报告服务读取配置
- **Expected Results**:
  - 使用最新配置值（本地缓存失效成功）

### TC-ST-007: WebSocket 生命周期
- **Requirement**: REQ-WS-002
- **Priority**: Medium
- **Test Steps**:
  1. 建连
  2. 心跳
  3. 断连
- **Expected Results**:
  - `_clients` 注册与清理正确

### TC-ST-008: check-all 锁释放
- **Requirement**: REQ-ACC-007
- **Priority**: Medium
- **Test Steps**:
  1. check-all 完成后再次触发
- **Expected Results**:
  - 第二轮可正常触发（锁与 running 状态复位）

---

## 5. 风控与账号稳定专项（低风险优先）

### TC-RISK-001: account_cooldown 生效（单账号替代验证）
- **Requirement**: REQ-NFR-003
- **Priority**: High
- **Strategy**: 单账号 + mock 时间/响应
- **Expected**: 连续上报前有等待逻辑且不会超频

### TC-RISK-002: 频率限制 12019 退避
- **Requirement**: REQ-NFR-004
- **Priority**: High
- **Strategy**: mock `response.code=12019`
- **Expected**: 进入退避等待并按重试上限执行

### TC-RISK-003: 评论 reason 兜底
- **Requirement**: REQ-NFR-005
- **Priority**: High
- **Strategy**: 输入非法 reason_id
- **Expected**: 运行时回退到合法值（4）

### TC-RISK-004: 配置有限值校验
- **Requirement**: REQ-NFR-006
- **Priority**: High
- **Strategy**: 对 `min_delay/max_delay/account_cooldown` 做边界与非有限值测试
- **Expected**: 非法值被拒绝，避免错误配置导致风控风险

---

## 6. 受限场景与替代验证（多账号池）

当前环境无多个可用账号，以下场景标记为 `Code-Verified`：

1. 多账号轮询公平性（随机打散 + cooldown）
2. 批量举报并发信号量行为（Semaphore=5）
3. 多账号下的失败重试与提前成功退出
4. 多账号 cookie 健康检查并发行为

替代验证方式：
- 单账号功能实测 + monkeypatch/mock 多账号数据
- 单元/集成测试验证代码路径
- 审核 `report_service` / `scheduler_service` 的关键控制逻辑

---

## Test Coverage Matrix

| Requirement ID | Description | Test Cases | Coverage Status |
|---|---|---|---|
| REQ-ACC-001 | 账号创建 | TC-F-001 | ✓ Complete |
| REQ-ACC-002 | 账号分页查询 | TC-F-002, TC-E-002 | ✓ Complete |
| REQ-ACC-003 | 账号导出（无凭证） | TC-F-003 | ✓ Complete |
| REQ-ACC-004 | 账号导出（含凭证） | TC-F-004 | ✓ Complete |
| REQ-ACC-005 | 账号导入 | TC-F-005, TC-E-001 | ✓ Complete |
| REQ-ACC-006 | 单账号健康检查 | TC-F-006 | ✓ Complete |
| REQ-ACC-007 | check-all 异步与并发保护 | TC-F-007, TC-ERR-010, TC-ST-008 | ✓ Complete |
| REQ-ACC-008 | 凭证读取安全响应 | TC-F-008, TC-ERR-004 | ✓ Complete |
| REQ-TGT-001 | 创建视频目标 | TC-F-009 | ✓ Complete |
| REQ-TGT-002 | 创建评论目标及约束 | TC-F-010, TC-E-004, TC-E-005 | ✓ Complete |
| REQ-TGT-003 | 批量创建目标 | TC-F-011 | ✓ Complete |
| REQ-TGT-004 | 目标分页过滤 | TC-F-012, TC-E-003 | ✓ Complete |
| REQ-TGT-005 | 全局统计 | TC-F-013 | ✓ Complete |
| REQ-TGT-006 | 按状态批量删除 | TC-F-014 | ✓ Complete |
| REQ-TGT-007 | 更新目标字段校验 | TC-E-006 | ✓ Complete |
| REQ-RPT-001 | 单目标举报执行 | TC-F-015, TC-ERR-001, TC-ERR-002, TC-ST-001, TC-ST-002 | ✓ Complete |
| REQ-RPT-002 | 批量举报执行 | TC-F-016 | ✓ Complete |
| REQ-RPT-003 | 举报日志查询 | TC-F-017 | ✓ Complete |
| REQ-RPT-004 | 评论扫描 | TC-F-018, TC-ERR-003 | ✓ Complete |
| REQ-RPT-005 | claim 原子性 | TC-ST-003 | ✓ Complete |
| REQ-AR-001 | 规则创建 | TC-F-019 | ✓ Complete |
| REQ-AR-002 | 默认回复 upsert | TC-F-020 | ✓ Complete |
| REQ-AR-003 | 启用自动回复 | TC-F-021, TC-E-010, TC-ST-004 | ✓ Complete |
| REQ-AR-004 | 停用自动回复 | TC-F-022, TC-ST-004 | ✓ Complete |
| REQ-SCH-001 | interval 调度 | TC-F-023, TC-E-008 | ✓ Complete |
| REQ-SCH-002 | cron 调度 | TC-F-024, TC-E-007, TC-E-009 | ✓ Complete |
| REQ-SCH-003 | 调度切换 | TC-F-025, TC-ST-005 | ✓ Complete |
| REQ-SCH-004 | 调度历史 | TC-F-026 | ✓ Complete |
| REQ-SCH-005 | 调度不存在资源错误 | TC-ERR-005 | ✓ Complete |
| REQ-CFG-001 | 配置查询 | TC-F-027, TC-ERR-006 | ✓ Complete |
| REQ-CFG-002 | 单项配置更新与校验 | TC-F-028, TC-E-011, TC-E-012 | ✓ Complete |
| REQ-CFG-003 | 批量原子更新 | TC-F-029 | ✓ Complete |
| REQ-CFG-004 | 配置缓存失效链路 | TC-ST-006 | ✓ Complete |
| REQ-AUTH-001 | QR 生成 | TC-F-030 | ✓ Complete |
| REQ-AUTH-002 | QR 轮询/登录 | TC-F-031 | ✓ Complete |
| REQ-AUTH-003 | cookie 状态与刷新 | TC-F-032, TC-ERR-009 | ✓ Complete |
| REQ-WS-001 | WebSocket 鉴权连接 | TC-F-033, TC-ERR-008 | ✓ Complete |
| REQ-WS-002 | 心跳与生命周期 | TC-F-034, TC-ST-007 | ✓ Complete |
| REQ-NFR-001 | 前端代理可用性 | TC-F-035 | ✓ Complete |
| REQ-NFR-002 | API 鉴权安全 | TC-ERR-007 | ✓ Complete |
| REQ-NFR-003 | 账号冷却机制 | TC-RISK-001 | ✓ Complete |
| REQ-NFR-004 | 风控频率限制退避 | TC-RISK-002 | ✓ Complete |
| REQ-NFR-005 | 评论举报 reason 兜底 | TC-RISK-003 | ✓ Complete |
| REQ-NFR-006 | 低风险配置边界 | TC-RISK-004 | ✓ Complete |
| REQ-NFR-007 | 多账号池真实并发执行 | 受限场景 1-4 | ⚠ Partial (Code-Verified) |

---

## Notes
- 本文档以当前代码库接口与约束为准，替代历史测试用例作为新基线。
- 对于 `Code-Verified` 场景，待多账号测试条件具备后，补齐真实环境执行记录。
- 建议后续把 High 优先级用例优先拆成自动化回归（API + Playwright）。
