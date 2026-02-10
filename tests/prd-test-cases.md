# Bili-Sentinel PRD 测试用例文档

## Overview
- **Feature**: Bili-Sentinel 全功能测试
- **Requirements Source**: `docs/PRD.md`
- **Test Coverage**: 6 大核心模块 + 非功能需求 + 成功指标
- **Last Updated**: 2026-02-10
- **Total Test Cases**: 96

---

## 模块一：账号管理 (Account Management)

### 1. Functional Tests

#### TC-F-001: 创建账号 — 必填字段
- **Requirement**: PRD 3.1 — 多账号凭证存储 (P0)
- **Priority**: High
- **Preconditions**:
  - 后端服务正常运行
  - 数据库已初始化
- **Test Steps**:
  1. POST `/api/accounts/` 请求体包含 `name`, `sessdata`, `bili_jct`
  2. 检查响应状态码
  3. 检查响应体中是否包含 `id`, `created_at`, `status` 等字段
- **Expected Results**:
  - 状态码 200
  - 返回完整 Account 对象
  - `group_tag` 默认为 `"default"`
  - `is_active` 默认为 `true`
  - `status` 默认为 `"unknown"`
- **Postconditions**: 数据库中新增一条 accounts 记录

#### TC-F-002: 创建账号 — 带可选字段
- **Requirement**: PRD 3.1 — 多账号凭证存储 (P0)
- **Priority**: Medium
- **Preconditions**: 同 TC-F-001
- **Test Steps**:
  1. POST `/api/accounts/` 请求体包含所有字段（name, sessdata, bili_jct, buvid3, buvid4, dedeuserid_ckmd5, refresh_token, group_tag="举报组"）
  2. 检查返回的 Account 对象
- **Expected Results**:
  - 所有可选字段正确保存
  - `group_tag` 为 `"举报组"`
- **Postconditions**: 账号记录含完整字段

#### TC-F-003: 获取账号列表
- **Requirement**: PRD 3.1 — 多账号凭证存储 (P0)
- **Priority**: High
- **Preconditions**: 数据库中已有 3 个账号
- **Test Steps**:
  1. GET `/api/accounts/`
  2. 检查返回列表长度和内容
- **Expected Results**:
  - 状态码 200
  - 返回包含 3 个 Account 对象的列表
- **Postconditions**: 无变更

#### TC-F-004: 获取单个账号
- **Requirement**: PRD 3.1
- **Priority**: Medium
- **Preconditions**: 已创建 ID=1 的账号
- **Test Steps**:
  1. GET `/api/accounts/1`
- **Expected Results**:
  - 状态码 200，返回对应 Account

#### TC-F-005: 更新账号
- **Requirement**: PRD 3.1
- **Priority**: High
- **Preconditions**: 已创建一个账号
- **Test Steps**:
  1. PUT `/api/accounts/{id}` 更新 `name`, `group_tag`, `is_active`
  2. GET `/api/accounts/{id}` 验证更新
- **Expected Results**:
  - 状态码 200
  - 字段已更新
  - 未更新的字段保持不变

#### TC-F-006: 删除账号
- **Requirement**: PRD 3.1
- **Priority**: High
- **Preconditions**: 已创建一个账号
- **Test Steps**:
  1. DELETE `/api/accounts/{id}`
  2. GET `/api/accounts/{id}` 确认其已被删除
- **Expected Results**:
  - DELETE 返回 `{"message": ..., "id": ...}`
  - 再次 GET 返回 404

#### TC-F-007: 账号健康检查
- **Requirement**: PRD 3.1 — 账号健康检查 (P0)
- **Priority**: High
- **Preconditions**: 已创建含有效 Cookie 的账号
- **Test Steps**:
  1. POST `/api/accounts/{id}/check`
  2. 检查返回的 AccountStatus
- **Expected Results**:
  - 返回 `is_valid`, `status`, `uid` 字段
  - `last_check_at` 被更新

#### TC-F-008: 账号导出 — 不含凭证
- **Requirement**: PRD 3.1 — 账号导入/导出 (P1)
- **Priority**: Medium
- **Preconditions**: 数据库中已有账号
- **Test Steps**:
  1. GET `/api/accounts/export?include_credentials=false`
- **Expected Results**:
  - 返回 JSON 数组
  - 不包含 `sessdata`, `bili_jct` 等敏感字段

#### TC-F-009: 账号导出 — 含凭证
- **Requirement**: PRD 3.1 — 账号导入/导出 (P1)
- **Priority**: Medium
- **Preconditions**: 数据库中已有账号
- **Test Steps**:
  1. GET `/api/accounts/export?include_credentials=true`
- **Expected Results**:
  - 返回 JSON 数组
  - 包含 `sessdata`, `bili_jct` 等凭证字段

#### TC-F-010: 账号批量导入
- **Requirement**: PRD 3.1 — 账号导入/导出 (P1)
- **Priority**: Medium
- **Preconditions**: 准备一个包含 5 个账号的 JSON 数组
- **Test Steps**:
  1. POST `/api/accounts/import` 传入 JSON 数组
  2. GET `/api/accounts/` 确认数量增加
- **Expected Results**:
  - 返回 `{"message": ..., "count": 5}`
  - 列表增加 5 条记录

### 2. Edge Case Tests

#### TC-E-001: 创建账号 — 空 name
- **Requirement**: PRD 3.1
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/accounts/` 传入 `name: ""`
- **Expected Results**:
  - 返回 422 验证错误

#### TC-E-002: 创建账号 — 缺少必填字段 sessdata
- **Requirement**: PRD 3.1
- **Priority**: High
- **Test Steps**:
  1. POST `/api/accounts/` 不包含 `sessdata`
- **Expected Results**:
  - 返回 422 验证错误

#### TC-E-003: 获取不存在的账号
- **Requirement**: PRD 3.1
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/accounts/99999`
- **Expected Results**:
  - 返回 404

#### TC-E-004: 更新不存在的账号
- **Requirement**: PRD 3.1
- **Priority**: Medium
- **Test Steps**:
  1. PUT `/api/accounts/99999` body: `{"name": "test"}`
- **Expected Results**:
  - 返回 404

#### TC-E-005: 删除不存在的账号
- **Requirement**: PRD 3.1
- **Priority**: Low
- **Test Steps**:
  1. DELETE `/api/accounts/99999`
- **Expected Results**:
  - 返回 404

#### TC-E-006: 导入空数组
- **Requirement**: PRD 3.1
- **Priority**: Low
- **Test Steps**:
  1. POST `/api/accounts/import` body: `[]`
- **Expected Results**:
  - 返回 `{"count": 0}` 或合理的空导入提示

#### TC-E-007: 导入格式错误的数据
- **Requirement**: PRD 3.1
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/accounts/import` body: `[{"invalid": "data"}]`
- **Expected Results**:
  - 返回 422 验证错误

### 3. Error Handling Tests

#### TC-ERR-001: 健康检查 — Cookie 已失效
- **Requirement**: PRD 3.1 — 账号健康检查 (P0)
- **Priority**: High
- **Preconditions**: 账号 Cookie 已过期
- **Test Steps**:
  1. POST `/api/accounts/{id}/check`
- **Expected Results**:
  - 返回 `is_valid: false`
  - `status` 标记为失效状态（如 `"expired"` / `"invalid"`）

#### TC-ERR-002: 无 API Key 访问受保护端点
- **Requirement**: 非功能需求
- **Priority**: High
- **Preconditions**: `SENTINEL_API_KEY` 已设置
- **Test Steps**:
  1. GET `/api/accounts/` 不带 `X-API-Key` header
- **Expected Results**:
  - 返回 401 或 403

---

## 模块二：目标列表管理 (Target Management)

### 1. Functional Tests

#### TC-F-011: 创建单个目标 — video 类型
- **Requirement**: PRD 3.2 — 黑名单数据库 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/targets/` body: `{"type": "video", "identifier": "BV1xx411x7xx"}`
- **Expected Results**:
  - 状态码 200
  - 返回 Target 对象，`status` 为 `"pending"`
  - `retry_count` 为 0

#### TC-F-012: 创建单个目标 — comment 类型
- **Requirement**: PRD 3.2
- **Priority**: High
- **Test Steps**:
  1. POST `/api/targets/` body: `{"type": "comment", "identifier": "123456789", "aid": 100}`
- **Expected Results**:
  - Target 创建成功，type 为 comment

#### TC-F-013: 创建单个目标 — user 类型
- **Requirement**: PRD 3.2
- **Priority**: High
- **Test Steps**:
  1. POST `/api/targets/` body: `{"type": "user", "identifier": "12345678"}`
- **Expected Results**:
  - Target 创建成功，type 为 user

#### TC-F-014: 批量创建目标
- **Requirement**: PRD 3.2 — 批量导入 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/targets/batch` body: `{"type": "video", "identifiers": ["BV1aaa", "BV2bbb", "BV3ccc"]}`
- **Expected Results**:
  - 返回 `{"count": 3}`
  - 数据库新增 3 条 pending 记录

#### TC-F-015: 获取目标列表 — 分页
- **Requirement**: PRD 3.2 — 目标状态追踪 (P0)
- **Priority**: High
- **Preconditions**: 数据库中已有 25 个目标
- **Test Steps**:
  1. GET `/api/targets/?page=1&page_size=10`
  2. GET `/api/targets/?page=2&page_size=10`
  3. GET `/api/targets/?page=3&page_size=10`
- **Expected Results**:
  - 第一页 10 条，第二页 10 条，第三页 5 条
  - `total` = 25
  - `page` 和 `page_size` 正确

#### TC-F-016: 获取目标列表 — 按状态过滤
- **Requirement**: PRD 3.2 — 目标状态追踪 (P0)
- **Priority**: High
- **Preconditions**: 数据库中有不同状态的目标
- **Test Steps**:
  1. GET `/api/targets/?status=pending`
  2. GET `/api/targets/?status=completed`
- **Expected Results**:
  - 仅返回对应状态的目标

#### TC-F-017: 获取目标列表 — 按类型过滤
- **Requirement**: PRD 3.2
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/targets/?type=video`
- **Expected Results**:
  - 仅返回 video 类型

#### TC-F-018: 更新目标
- **Requirement**: PRD 3.2
- **Priority**: Medium
- **Test Steps**:
  1. PUT `/api/targets/{id}` body: `{"status": "completed", "reason_text": "垃圾广告"}`
- **Expected Results**:
  - 字段已更新
  - `updated_at` 被设置

#### TC-F-019: 删除单个目标
- **Requirement**: PRD 3.2
- **Priority**: Medium
- **Test Steps**:
  1. DELETE `/api/targets/{id}`
- **Expected Results**:
  - 返回成功消息
  - GET 该 ID 返回 404

#### TC-F-020: 批量删除目标 — 按状态
- **Requirement**: PRD 3.2
- **Priority**: Medium
- **Test Steps**:
  1. DELETE `/api/targets/?status=completed`
- **Expected Results**:
  - 返回 `{"count": N}` 其中 N 为所有 completed 目标数
  - pending 目标不受影响

#### TC-F-021: 导出目标
- **Requirement**: PRD 3.2 — 批量导出 (P1)
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/targets/export`
  2. GET `/api/targets/export?status=pending`
- **Expected Results**:
  - 返回 JSON 数组
  - 带状态过滤时仅返回对应状态

### 2. Edge Case Tests

#### TC-E-008: 创建目标 — 无效 type
- **Requirement**: PRD 3.2
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/targets/` body: `{"type": "dynamic", "identifier": "xxx"}`
- **Expected Results**:
  - 返回 422（type 仅限 video/comment/user）

#### TC-E-009: 批量创建 — identifiers 为空列表
- **Requirement**: PRD 3.2
- **Priority**: Low
- **Test Steps**:
  1. POST `/api/targets/batch` body: `{"type": "video", "identifiers": []}`
- **Expected Results**:
  - 返回 `{"count": 0}` 或 422

#### TC-E-010: 分页 — page 超出范围
- **Requirement**: PRD 3.2
- **Priority**: Low
- **Test Steps**:
  1. GET `/api/targets/?page=999&page_size=10`
- **Expected Results**:
  - 返回 `items: []`, `total` 为实际总数

#### TC-E-011: 分页 — page_size 为 0 或负数
- **Requirement**: PRD 3.2
- **Priority**: Low
- **Test Steps**:
  1. GET `/api/targets/?page=1&page_size=0`
  2. GET `/api/targets/?page=1&page_size=-1`
- **Expected Results**:
  - 返回 422 或使用默认 page_size

#### TC-E-012: 批量删除 — 无匹配状态
- **Requirement**: PRD 3.2
- **Priority**: Low
- **Test Steps**:
  1. DELETE `/api/targets/?status=processing` （无 processing 目标）
- **Expected Results**:
  - 返回 `{"count": 0}`

---

## 模块三：内容审核/举报 (Reporting)

### 1. Functional Tests

#### TC-F-022: 单目标举报执行
- **Requirement**: PRD 3.3 — 视频举报/评论举报/用户空间举报 (P0)
- **Priority**: High
- **Preconditions**:
  - 至少 1 个 active 账号
  - 至少 1 个 pending 目标
- **Test Steps**:
  1. POST `/api/reports/execute` body: `{"target_id": 1}`
- **Expected Results**:
  - 返回 `List[ReportResult]`
  - 每个结果包含 `target_id`, `account_id`, `success`, `message`
  - 日志已写入 report_logs 表

#### TC-F-023: 单目标举报 — 指定账号
- **Requirement**: PRD 3.3 — 多账号轮询执行 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/reports/execute` body: `{"target_id": 1, "account_ids": [1, 2]}`
- **Expected Results**:
  - 仅使用指定的 2 个账号
  - 返回 2 条 ReportResult

#### TC-F-024: 批量举报执行
- **Requirement**: PRD 3.3 — 多账号轮询执行 (P0)
- **Priority**: High
- **Preconditions**: 有多个 pending 目标和多个 active 账号
- **Test Steps**:
  1. POST `/api/reports/execute/batch` body: `{"target_ids": [1, 2, 3]}`
- **Expected Results**:
  - 返回 BatchReportResult
  - `total_targets`, `successful`, `failed` 数据正确

#### TC-F-025: 批量举报 — 自动选择所有 pending
- **Requirement**: PRD 3.3
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/reports/execute/batch` body: `{}` (不指定 target_ids)
- **Expected Results**:
  - 自动处理所有 pending 目标

#### TC-F-026: 获取举报日志
- **Requirement**: PRD 3.6 — 详细日志记录 (P1)
- **Priority**: Medium
- **Preconditions**: 已执行过举报
- **Test Steps**:
  1. GET `/api/reports/logs?limit=50`
- **Expected Results**:
  - 返回 ReportLog 列表
  - 每条含 `target_id`, `account_name`, `success`, `executed_at`

#### TC-F-027: 获取特定目标的举报日志
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/reports/logs/1`
- **Expected Results**:
  - 仅返回 target_id=1 的日志

#### TC-F-028: 评论区扫描
- **Requirement**: PRD 3.3 — 评论区扫描 (P1)
- **Priority**: High
- **Preconditions**: 有 1 个有效账号
- **Test Steps**:
  1. POST `/api/reports/scan-comments` body: `{"bvid": "BV1xx411x7xx", "account_id": 1, "max_pages": 2, "auto_report": false}`
- **Expected Results**:
  - 返回 CommentScanResult
  - `comments_found` > 0
  - `targets_created` > 0
  - `reports_executed` = 0 (未开启自动举报)

#### TC-F-029: 评论区扫描 — 自动举报
- **Requirement**: PRD 3.3
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/reports/scan-comments` body: `{"bvid": "BV1xx", "account_id": 1, "auto_report": true}`
- **Expected Results**:
  - `reports_executed` > 0
  - 举报日志已写入

### 2. Edge Case Tests

#### TC-E-013: 举报不存在的目标
- **Requirement**: PRD 3.3
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/reports/execute` body: `{"target_id": 99999}`
- **Expected Results**:
  - 返回 404

#### TC-E-014: 举报 — 无 active 账号
- **Requirement**: PRD 3.3
- **Priority**: High
- **Preconditions**: 所有账号均 `is_active: false`
- **Test Steps**:
  1. POST `/api/reports/execute` body: `{"target_id": 1}`
- **Expected Results**:
  - 返回错误提示「无可用账号」或类似信息

#### TC-E-015: 评论扫描 — 无效 BV 号
- **Requirement**: PRD 3.3
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/reports/scan-comments` body: `{"bvid": "INVALID", "account_id": 1}`
- **Expected Results**:
  - 返回错误（Bilibili API 返回失败）

### 3. Error Handling Tests

#### TC-ERR-003: 举报 — Bilibili 返回 -412 (频率限制)
- **Requirement**: PRD 4 — 低检测风险
- **Priority**: High
- **Test Steps**:
  1. 模拟 Bilibili API 返回 -412
- **Expected Results**:
  - 日志记录错误码
  - `success: false` 并含有对应 error_message
  - 目标状态更新为 `"failed"` 或增加 `retry_count`

#### TC-ERR-004: 举报 — Bilibili 返回 -101 (未登录)
- **Requirement**: PRD 4
- **Priority**: High
- **Test Steps**:
  1. 模拟 Bilibili API 返回 -101
- **Expected Results**:
  - 日志记录 Cookie 失效
  - 账号 status 更新为 expired/invalid

---

## 模块四：自动互动/私信回复 (Auto Reply)

### 1. Functional Tests

#### TC-F-030: 创建关键词回复规则
- **Requirement**: PRD 3.4 — 关键词匹配回复 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/autoreply/config` body: `{"keyword": "合作", "response": "请联系邮箱 xxx@xx.com", "priority": 10}`
- **Expected Results**:
  - 返回 AutoReplyConfig 对象
  - `is_active` 默认为 true

#### TC-F-031: 创建默认回复规则（keyword=null）
- **Requirement**: PRD 3.4 — 默认回复模板 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/autoreply/config` body: `{"response": "感谢您的消息，我会尽快回复！"}`
- **Expected Results**:
  - `keyword` 为 null
  - 作为未匹配时的兜底回复

#### TC-F-032: 获取所有回复规则
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/autoreply/config`
- **Expected Results**:
  - 返回列表，含所有规则

#### TC-F-033: 更新回复规则
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. PUT `/api/autoreply/config/{id}` body: `{"response": "新回复内容", "is_active": false}`
- **Expected Results**:
  - 字段已更新

#### TC-F-034: 删除回复规则
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. DELETE `/api/autoreply/config/{id}`
- **Expected Results**:
  - 返回成功
  - 再次 GET 已不包含该规则

#### TC-F-035: 启动自动回复服务
- **Requirement**: PRD 3.4 — 私信轮询 (P0)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/autoreply/start?interval=30`
  2. GET `/api/autoreply/status`
- **Expected Results**:
  - start 返回 `{"interval": 30}`
  - status 返回 `is_running: true`

#### TC-F-036: 停止自动回复服务
- **Requirement**: PRD 3.4
- **Priority**: High
- **Preconditions**: 自动回复服务已启动
- **Test Steps**:
  1. POST `/api/autoreply/stop`
  2. GET `/api/autoreply/status`
- **Expected Results**:
  - stop 返回成功
  - status 返回 `is_running: false`

#### TC-F-037: 获取自动回复状态
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/autoreply/status`
- **Expected Results**:
  - 返回 `is_running`, `active_accounts`, `last_poll_at`

### 2. Edge Case Tests

#### TC-E-016: 重复启动自动回复
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Preconditions**: 服务已启动
- **Test Steps**:
  1. POST `/api/autoreply/start`
- **Expected Results**:
  - 返回提示已在运行或安全幂等处理

#### TC-E-017: 停止未运行的自动回复
- **Requirement**: PRD 3.4
- **Priority**: Low
- **Test Steps**:
  1. POST `/api/autoreply/stop`（服务未启动）
- **Expected Results**:
  - 返回提示未在运行或安全幂等处理

#### TC-E-018: 创建回复规则 — response 为空
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/autoreply/config` body: `{"response": ""}`
- **Expected Results**:
  - 返回 422 验证错误

### 3. State Transition Tests

#### TC-ST-001: 自动回复服务状态切换
- **Requirement**: PRD 3.4
- **Priority**: High
- **Test Steps**:
  1. GET `/api/autoreply/status` → `is_running: false`
  2. POST `/api/autoreply/start` → 成功
  3. GET `/api/autoreply/status` → `is_running: true`
  4. POST `/api/autoreply/stop` → 成功
  5. GET `/api/autoreply/status` → `is_running: false`
- **Expected Results**:
  - 状态忠实反映服务当前状态
  - 多次切换稳定无异常

---

## 模块五：定时任务调度 (Scheduler)

### 1. Functional Tests

#### TC-F-038: 创建定时任务 — 基于 interval
- **Requirement**: PRD 3.5 — 周期性举报任务 (P1)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/scheduler/tasks` body: `{"name": "每5分钟举报", "task_type": "report_batch", "interval_seconds": 300}`
- **Expected Results**:
  - 返回 ScheduledTask，`is_active: true`

#### TC-F-039: 创建定时任务 — 基于 cron
- **Requirement**: PRD 3.5 — Cron 表达式支持 (P2)
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/scheduler/tasks` body: `{"name": "每天8点检查", "task_type": "cookie_health_check", "cron_expression": "0 8 * * *"}`
- **Expected Results**:
  - 返回 ScheduledTask，`cron_expression` 正确保存

#### TC-F-040: 获取任务列表
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/scheduler/tasks`
- **Expected Results**:
  - 返回所有定时任务列表

#### TC-F-041: 获取单个任务
- **Requirement**: PRD 3.5
- **Priority**: Low
- **Test Steps**:
  1. GET `/api/scheduler/tasks/{id}`
- **Expected Results**:
  - 返回对应 ScheduledTask

#### TC-F-042: 更新定时任务
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. PUT `/api/scheduler/tasks/{id}` body: `{"interval_seconds": 600}`
- **Expected Results**:
  - interval_seconds 已更新为 600

#### TC-F-043: 删除定时任务
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. DELETE `/api/scheduler/tasks/{id}`
- **Expected Results**:
  - 返回成功

#### TC-F-044: 暂停/恢复任务（toggle）
- **Requirement**: PRD 3.5 — 任务暂停/恢复 (P1)
- **Priority**: High
- **Test Steps**:
  1. POST `/api/scheduler/tasks/{id}/toggle`（当前 active=true）
  2. GET `/api/scheduler/tasks/{id}` 确认 `is_active: false`
  3. POST `/api/scheduler/tasks/{id}/toggle`
  4. 确认 `is_active: true`
- **Expected Results**:
  - 每次 toggle 翻转 `is_active`

#### TC-F-045: 获取执行历史
- **Requirement**: PRD 3.5 — 执行历史 (P1)
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/scheduler/history?limit=50`
- **Expected Results**:
  - 返回历史记录列表（可能为空）

### 2. Edge Case Tests

#### TC-E-019: 创建任务 — 无效 task_type
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/scheduler/tasks` body: `{"name": "test", "task_type": "invalid_type"}`
- **Expected Results**:
  - 返回 422（仅限 report_batch / autoreply_poll / cookie_health_check / log_cleanup）

#### TC-E-020: 创建任务 — 既无 cron 也无 interval
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/scheduler/tasks` body: `{"name": "test", "task_type": "report_batch"}`
- **Expected Results**:
  - 允许创建（使用默认行为）或返回 422

#### TC-E-021: Toggle 不存在的任务
- **Requirement**: PRD 3.5
- **Priority**: Low
- **Test Steps**:
  1. POST `/api/scheduler/tasks/99999/toggle`
- **Expected Results**:
  - 返回 404

---

## 模块六：控制中心 Web UI (Dashboard & Config)

### 1. Functional Tests — Configuration API

#### TC-F-046: 获取所有系统配置
- **Requirement**: PRD 3.6 — 配置面板 (P0)
- **Priority**: High
- **Test Steps**:
  1. GET `/api/config/`
- **Expected Results**:
  - 返回包含默认配置的列表
  - 包含 `min_delay`, `max_delay`, `ua_rotation`, `auto_clean_logs`, `log_retention_days` 等

#### TC-F-047: 获取单个配置
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/config/min_delay`
- **Expected Results**:
  - 返回 `{"key": "min_delay", "value": "2.0"}`

#### TC-F-048: 更新单个配置
- **Requirement**: PRD 3.6
- **Priority**: High
- **Test Steps**:
  1. PUT `/api/config/min_delay` body: `{"value": "5.0"}`
  2. GET `/api/config/min_delay` 验证
- **Expected Results**:
  - 值已更新为 `"5.0"`

#### TC-F-049: 批量更新配置
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. POST `/api/config/batch` body: `{"min_delay": "3.0", "max_delay": "8.0"}`
- **Expected Results**:
  - 两个配置同时更新成功

### 2. Functional Tests — Auth/QR Login

#### TC-F-050: 生成 QR 登录二维码
- **Requirement**: PRD 3.1（QR 扫码登录）
- **Priority**: High
- **Test Steps**:
  1. GET `/api/auth/qr/generate`
- **Expected Results**:
  - 返回 `{"url": "...", "qrcode_key": "..."}`
  - `url` 为有效的 Bilibili 扫码 URL

#### TC-F-051: 轮询 QR 扫码状态
- **Requirement**: PRD 3.1
- **Priority**: High
- **Test Steps**:
  1. GET `/api/auth/qr/generate` 获取 qrcode_key
  2. POST `/api/auth/qr/poll` body: `{"qrcode_key": "xxx"}`
- **Expected Results**:
  - 返回当前扫码状态（等待扫码 / 扫码未确认 / 已确认 / 已过期）

#### TC-F-052: QR 登录 — 完整流程
- **Requirement**: PRD 3.1
- **Priority**: High
- **Test Steps**:
  1. GET `/api/auth/qr/generate`
  2. 用户扫码确认
  3. POST `/api/auth/qr/login` body: `{"qrcode_key": "xxx", "account_name": "新账号"}`
- **Expected Results**:
  - 返回新创建的 Account 对象
  - 数据库中新增一条记录，含 Cookie 信息

#### TC-F-053: Cookie 状态检查
- **Requirement**: PRD 3.1 — Cookie 维护
- **Priority**: Medium
- **Test Steps**:
  1. GET `/api/auth/{account_id}/cookie-status`
- **Expected Results**:
  - 返回 `needs_refresh` 布尔值和 `reason`

#### TC-F-054: Cookie 刷新
- **Requirement**: PRD 3.1 — Cookie 维护
- **Priority**: Medium
- **Preconditions**: 账号有 `refresh_token`
- **Test Steps**:
  1. POST `/api/auth/{account_id}/refresh`
- **Expected Results**:
  - 返回 `{"success": true/false, "message": "..."}`

### 3. Functional Tests — WebSocket

#### TC-F-055: WebSocket 连接建立
- **Requirement**: PRD 3.6 — 实时日志流 (P0)
- **Priority**: High
- **Test Steps**:
  1. 连接 `ws://localhost:8000/ws/logs`
- **Expected Results**:
  - 收到 `{"type": "connected", "message": "..."}`

#### TC-F-056: WebSocket 心跳
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. 连接 WebSocket
  2. 发送 `"ping"`
- **Expected Results**:
  - 收到 `{"type": "pong"}`

#### TC-F-057: WebSocket 接收日志
- **Requirement**: PRD 3.6
- **Priority**: High
- **Preconditions**: WebSocket 已连接
- **Test Steps**:
  1. 通过 API 触发举报等操作
  2. 观察 WebSocket 消息
- **Expected Results**:
  - 收到 `{"type": "...", "message": "...", "timestamp": ...}` 格式日志

### 4. Edge Case Tests — Config

#### TC-E-022: 获取不存在的配置 key
- **Requirement**: PRD 3.6
- **Priority**: Low
- **Test Steps**:
  1. GET `/api/config/nonexistent_key`
- **Expected Results**:
  - 返回 404

#### TC-E-023: WebSocket — 带无效 token 连接
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Preconditions**: `SENTINEL_API_KEY` 已设置
- **Test Steps**:
  1. 连接 `ws://localhost:8000/ws/logs?token=wrong_token`
- **Expected Results**:
  - 连接被拒绝或收到错误消息

---

## 模块七：前端 UI 测试

### 1. Functional Tests — Pages

#### TC-F-058: 仪表盘页面加载
- **Requirement**: PRD 3.6 — 仪表盘概览 (P0)
- **Priority**: High
- **Test Steps**:
  1. 访问 `/`（Dashboard）
  2. 检查页面是否包含账号数、任务数、执行统计
- **Expected Results**:
  - 页面正常渲染
  - 显示统计数据卡片
  - 实时日志区域正常展示

#### TC-F-059: 账号管理页面
- **Requirement**: PRD 3.1
- **Priority**: High
- **Test Steps**:
  1. 访问 `/accounts`
  2. 检查账号列表展示
  3. 测试新增账号表单
  4. 测试编辑/删除操作
- **Expected Results**:
  - 列表正确显示所有账号
  - CRUD 操作正常
  - 支持 QR 扫码登录入口

#### TC-F-060: 目标管理页面
- **Requirement**: PRD 3.2
- **Priority**: High
- **Test Steps**:
  1. 访问 `/targets`
  2. 检查目标列表、分页、过滤
  3. 测试新增/编辑/删除
- **Expected Results**:
  - 分页正常，过滤正常
  - CRUD 操作正常

#### TC-F-061: 自动回复页面
- **Requirement**: PRD 3.4
- **Priority**: Medium
- **Test Steps**:
  1. 访问 `/autoreply`
  2. 检查规则列表
  3. 测试启动/停止服务
  4. 测试规则 CRUD
- **Expected Results**:
  - 服务状态正确显示
  - 规则管理正常

#### TC-F-062: 定时任务页面
- **Requirement**: PRD 3.5
- **Priority**: Medium
- **Test Steps**:
  1. 访问 `/scheduler`
  2. 检查任务列表
  3. 测试创建/toggle/删除
- **Expected Results**:
  - 任务列表正确
  - toggle 功能正常

#### TC-F-063: 系统配置页面
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. 访问 `/config`
  2. 修改配置值并保存
- **Expected Results**:
  - 配置读取和保存正常

### 2. UI/UX Tests

#### TC-F-064: 深色主题渲染
- **Requirement**: PRD 4 — 视觉风格
- **Priority**: Medium
- **Test Steps**:
  1. 打开任意页面
  2. 检查背景、文字、卡片颜色
- **Expected Results**:
  - 深色主题一致
  - 玻璃拟态效果正常

#### TC-F-065: 侧边栏导航
- **Requirement**: PRD 3.6
- **Priority**: High
- **Test Steps**:
  1. 点击侧边栏各导航项
  2. 检查页面切换
- **Expected Results**:
  - 各页面正确跳转
  - 当前页面高亮

#### TC-F-066: Toast 提示
- **Requirement**: PRD 3.6
- **Priority**: Medium
- **Test Steps**:
  1. 执行成功操作（如创建账号）
  2. 执行失败操作（如无效输入）
- **Expected Results**:
  - 成功时显示绿色 Toast
  - 失败时显示红色 Toast
  - Toast 自动消失

#### TC-F-067: 响应式布局
- **Requirement**: PRD 4 — 响应式设计
- **Priority**: Medium
- **Test Steps**:
  1. 在 1920px 宽度下查看
  2. 在 1024px 宽度下查看
  3. 在 768px 宽度下查看
- **Expected Results**:
  - 布局适配各尺寸
  - 侧边栏在小屏幕可折叠或变为 hamburger menu

---

## 模块八：非功能需求测试

### 1. Security Tests

#### TC-F-068: API Key 认证 — 有效 Key
- **Requirement**: 非功能需求 — 安全
- **Priority**: High
- **Preconditions**: `SENTINEL_API_KEY=test123`
- **Test Steps**:
  1. GET `/api/accounts/` with header `X-API-Key: test123`
- **Expected Results**:
  - 状态码 200

#### TC-F-069: API Key 认证 — 无效 Key
- **Requirement**: 非功能需求 — 安全
- **Priority**: High
- **Test Steps**:
  1. GET `/api/accounts/` with header `X-API-Key: wrongkey`
- **Expected Results**:
  - 状态码 401 或 403

#### TC-F-070: API Key 认证 — 未设置 Key（auth disabled）
- **Requirement**: 非功能需求
- **Priority**: Medium
- **Preconditions**: `SENTINEL_API_KEY` 未设置
- **Test Steps**:
  1. GET `/api/accounts/` 不带 X-API-Key
- **Expected Results**:
  - 状态码 200（auth 已禁用）

### 2. Anti-Detection Tests

#### TC-F-071: 随机延迟机制
- **Requirement**: PRD 4 — 低检测风险（随机延迟 2-10 秒）
- **Priority**: High
- **Test Steps**:
  1. 配置 `min_delay=2.0`, `max_delay=10.0`
  2. 批量举报 10 个目标
  3. 检查日志中每次请求的间隔
- **Expected Results**:
  - 每次请求间隔在 [2, 10] 秒范围内
  - 间隔随机分布

#### TC-F-072: User-Agent 轮换
- **Requirement**: PRD 4 — 低检测风险（UA 轮换）
- **Priority**: Medium
- **Test Steps**:
  1. 确认 `ua_rotation: true`
  2. 执行多次 API 调用
  3. 检查 HTTP 请求头中的 User-Agent
- **Expected Results**:
  - 不同请求使用不同 UA

#### TC-F-073: WBI 签名
- **Requirement**: PRD 4 — WBI 签名
- **Priority**: High
- **Test Steps**:
  1. 检查需要 WBI 签名的 API 调用
  2. 验证签名参数 (wts, w_rid) 存在
- **Expected Results**:
  - 所有需要签名的请求中含 wts 和 w_rid

### 3. Performance Tests

#### TC-F-074: 并发账号健康检查
- **Requirement**: PRD 4 — 高性能（异步）
- **Priority**: Medium
- **Preconditions**: 有 10+ 个账号
- **Test Steps**:
  1. 并发对所有账号执行健康检查
- **Expected Results**:
  - 所有检查完成无报错
  - 异步执行，非串行

#### TC-F-075: 数据库并发安全
- **Requirement**: 架构约束 — 单 Worker + asyncio.Lock
- **Priority**: High
- **Test Steps**:
  1. 并发发送 50 个 API 请求
- **Expected Results**:
  - 无数据库锁错误
  - 所有请求正常返回

---

## 模块九：成功指标验证

#### TC-F-076: 批量举报成功率 >= 90%
- **Requirement**: PRD 6 — 成功指标
- **Priority**: High
- **Test Steps**:
  1. 准备 100 个有效目标 + 5 个有效账号
  2. 执行批量举报
  3. 统计 success 比率
- **Expected Results**:
  - 成功率 >= 90%

#### TC-F-077: 私信回复延迟 < 60 秒
- **Requirement**: PRD 6
- **Priority**: Medium
- **Test Steps**:
  1. 启动自动回复（interval=30s）
  2. 发送私信
  3. 记录从发送到回复的时间
- **Expected Results**:
  - 回复延迟 < 60 秒

#### TC-F-078: 24 小时连续运行无 Cookie 失效
- **Requirement**: PRD 6 — 账号存活率
- **Priority**: Medium
- **Test Steps**:
  1. 使用有效 Cookie 启动系统
  2. 开启定时健康检查
  3. 运行 24 小时
- **Expected Results**:
  - Cookie 维持有效
  - Cookie 刷新机制正常工作

#### TC-F-079: 系统可用性 99%
- **Requirement**: PRD 6
- **Priority**: Low
- **Test Steps**:
  1. 每分钟 ping 一次 health endpoint
  2. 连续运行 24 小时
- **Expected Results**:
  - 成功率 >= 99%

---

## 模块十：API 代理层测试 (Next.js Proxy)

#### TC-F-080: API 代理转发 — GET
- **Requirement**: 架构 — Next.js API Proxy
- **Priority**: High
- **Test Steps**:
  1. 前端 GET `/api/accounts/`
  2. 检查是否正确转发到 `http://127.0.0.1:8000/api/accounts/`
- **Expected Results**:
  - 返回与后端一致的响应
  - 正确传递 X-API-Key header

#### TC-F-081: API 代理转发 — POST with body
- **Requirement**: 架构
- **Priority**: High
- **Test Steps**:
  1. 前端 POST `/api/accounts/` with JSON body
- **Expected Results**:
  - 请求体正确转发
  - 响应正确返回

#### TC-F-082: API 代理 — 后端不可达
- **Requirement**: 架构
- **Priority**: Medium
- **Test Steps**:
  1. 停止后端服务
  2. 前端发起 API 请求
- **Expected Results**:
  - 返回合理的错误响应（如 502/500），非页面崩溃

---

## 模块十一：数据完整性测试

#### TC-F-083: report_logs 级联删除
- **Requirement**: DB Schema — ON DELETE CASCADE
- **Priority**: Medium
- **Test Steps**:
  1. 创建目标 → 执行举报产生日志
  2. DELETE 该目标
  3. 检查 report_logs 是否被级联删除
- **Expected Results**:
  - 相关 report_logs 记录已被删除

#### TC-F-084: report_logs 账号删除处理
- **Requirement**: DB Schema — ON DELETE SET NULL
- **Priority**: Medium
- **Test Steps**:
  1. 用账号 A 执行举报
  2. 删除账号 A
  3. 检查相关 report_logs
- **Expected Results**:
  - report_logs 仍存在
  - `account_id` 被设为 NULL

#### TC-F-085: targets type 约束
- **Requirement**: DB Schema — CHECK 约束
- **Priority**: Medium
- **Test Steps**:
  1. 直接 SQL 插入 type='invalid'
- **Expected Results**:
  - 数据库拒绝插入（CHECK 约束违反）

#### TC-F-086: targets status 约束
- **Requirement**: DB Schema — CHECK 约束
- **Priority**: Medium
- **Test Steps**:
  1. 直接 SQL 更新 status='unknown'
- **Expected Results**:
  - 数据库拒绝更新

#### TC-F-087: autoreply_state 去重
- **Requirement**: DB Schema — UNIQUE(account_id, talker_id)
- **Priority**: Medium
- **Test Steps**:
  1. 插入 (account_id=1, talker_id=100)
  2. 再次插入 (account_id=1, talker_id=100)
- **Expected Results**:
  - 第二次插入应 UPDATE（UPSERT）或报唯一约束冲突

#### TC-F-088: system_config key 唯一性
- **Requirement**: DB Schema — UNIQUE(key)
- **Priority**: Low
- **Test Steps**:
  1. INSERT INTO system_config (key, value) VALUES ('min_delay', '999')
- **Expected Results**:
  - 被 UNIQUE 约束拒绝或 INSERT OR IGNORE 忽略

---

## 模块十二：SWR Hooks & 前端状态测试

#### TC-F-089: SWR 数据获取 — useAccounts
- **Requirement**: 前端 Hook 模式
- **Priority**: Medium
- **Test Steps**:
  1. 渲染使用 useAccounts 的组件
  2. 检查 loading → data 状态转换
- **Expected Results**:
  - 初始 loading 状态
  - 数据加载完成后展示列表
  - 错误情况展示错误提示

#### TC-F-090: SWR 数据获取 — useTargets with 分页
- **Requirement**: 前端 Hook 模式
- **Priority**: Medium
- **Test Steps**:
  1. 渲染 Targets 页面
  2. 切换页码
  3. 切换过滤条件
- **Expected Results**:
  - 数据正确刷新
  - 分页、过滤参数正确传递

#### TC-F-091: SWR 数据变更 — mutate 刷新
- **Requirement**: 前端 Hook 模式
- **Priority**: Medium
- **Test Steps**:
  1. 创建一个新账号
  2. 检查列表是否自动刷新
- **Expected Results**:
  - 列表自动更新，显示新增记录

#### TC-F-092: WebSocket 日志流 — useLogStream
- **Requirement**: PRD 3.6 — 实时日志流 (P0)
- **Priority**: High
- **Test Steps**:
  1. 渲染 Dashboard
  2. 等待 WebSocket 连接
  3. 触发后端操作
- **Expected Results**:
  - 实时显示新日志
  - 断线重连正常

---

## 模块十三：编辑模态框 & 交互测试

#### TC-F-093: 编辑账号模态框
- **Requirement**: 前端 UI — 编辑功能
- **Priority**: Medium
- **Test Steps**:
  1. 点击账号列表中的编辑按钮
  2. 修改 name 和 group_tag
  3. 点击保存
- **Expected Results**:
  - 模态框正确展示当前数据
  - 保存后列表刷新
  - Toast 提示成功

#### TC-F-094: 编辑目标模态框
- **Requirement**: 前端 UI
- **Priority**: Medium
- **Test Steps**: 同 TC-F-093，适用于 Target
- **Expected Results**: 同 TC-F-093

#### TC-F-095: 删除确认交互
- **Requirement**: 前端 UX
- **Priority**: Medium
- **Test Steps**:
  1. 点击删除按钮
  2. 检查是否有确认弹窗/提示
  3. 确认删除
- **Expected Results**:
  - 删除前有二次确认
  - 确认后执行删除
  - 取消则不执行

#### TC-F-096: QR 登录模态框流程
- **Requirement**: 前端 UI — QR 登录
- **Priority**: High
- **Test Steps**:
  1. 打开 QR 登录模态框
  2. 检查二维码展示
  3. 检查轮询状态更新
  4. 扫码成功后检查账号创建
- **Expected Results**:
  - 二维码正常展示
  - 状态实时更新（等待→扫码→确认）
  - 成功后自动关闭模态框并刷新列表

---

## Test Coverage Matrix

| 需求 ID | 需求描述 | 测试用例 | 覆盖状态 |
|---------|---------|----------|----------|
| PRD 3.1-P0 | 多账号凭证存储 | TC-F-001~007, TC-E-001~005, TC-ERR-001~002 | ✓ Complete |
| PRD 3.1-P1 | 账号分组标签 | TC-F-002, TC-F-005 | ✓ Complete |
| PRD 3.1-P1 | 账号导入/导出 | TC-F-008~010, TC-E-006~007 | ✓ Complete |
| PRD 3.2-P0 | 黑名单数据库 | TC-F-011~013, TC-E-008 | ✓ Complete |
| PRD 3.2-P0 | 批量导入 | TC-F-014, TC-E-009 | ✓ Complete |
| PRD 3.2-P1 | 批量导出 | TC-F-021 | ✓ Complete |
| PRD 3.2-P0 | 目标状态追踪 | TC-F-015~017, TC-E-010~012 | ✓ Complete |
| PRD 3.3-P0 | 视频/评论/用户举报 | TC-F-022~025, TC-E-013~014, TC-ERR-003~004 | ✓ Complete |
| PRD 3.3-P1 | 评论区扫描 | TC-F-028~029, TC-E-015 | ✓ Complete |
| PRD 3.3-P0 | 多账号轮询执行 | TC-F-023~024 | ✓ Complete |
| PRD 3.4-P0 | 私信轮询 | TC-F-035~037, TC-ST-001 | ✓ Complete |
| PRD 3.4-P0 | 关键词匹配回复 | TC-F-030~034, TC-E-016~018 | ✓ Complete |
| PRD 3.4-P0 | 默认回复模板 | TC-F-031 | ✓ Complete |
| PRD 3.4-P1 | 回复日志 | TC-F-026~027 | ✓ Complete |
| PRD 3.5-P1 | 周期性举报任务 | TC-F-038, TC-F-044 | ✓ Complete |
| PRD 3.5-P2 | Cron 表达式支持 | TC-F-039 | ✓ Complete |
| PRD 3.5-P1 | 任务暂停/恢复 | TC-F-044 | ✓ Complete |
| PRD 3.5-P1 | 执行历史 | TC-F-045 | ✓ Complete |
| PRD 3.6-P0 | 仪表盘概览 | TC-F-058 | ✓ Complete |
| PRD 3.6-P0 | 实时日志流 | TC-F-055~057, TC-F-092 | ✓ Complete |
| PRD 3.6-P0 | 配置面板 | TC-F-046~049, TC-E-022 | ✓ Complete |
| PRD 4 | 低检测风险 | TC-F-071~073 | ✓ Complete |
| PRD 4 | 高性能/异步 | TC-F-074~075 | ✓ Complete |
| PRD 4 | 响应式设计 | TC-F-067 | ✓ Complete |
| PRD 4 | 深色模式/玻璃拟态 | TC-F-064 | ✓ Complete |
| PRD 6 | 举报成功率 >= 90% | TC-F-076 | ✓ Complete |
| PRD 6 | 回复延迟 < 60s | TC-F-077 | ✓ Complete |
| PRD 6 | 24h 无 Cookie 失效 | TC-F-078 | ✓ Complete |
| PRD 6 | 系统可用性 99% | TC-F-079 | ✓ Complete |

---

## Notes

1. **环境依赖**: 部分测试（TC-ERR-003/004, TC-F-071~073）需要模拟 Bilibili API 响应，建议使用 mock/intercept 工具
2. **QR 登录测试** (TC-F-050~052, TC-F-096): 需要实际扫码或模拟 Bilibili QR 状态接口
3. **长时间运行测试** (TC-F-078~079): 属于可靠性测试，建议单独调度
4. **前端 UI 测试** (TC-F-058~067, TC-F-089~096): 建议使用 Playwright 或 Cypress 进行 E2E 测试
5. **数据库约束测试** (TC-F-083~088): 可通过直接 SQL 或 pytest + aiosqlite 验证
6. **所有 API 测试默认需要** `X-API-Key` header (当 `SENTINEL_API_KEY` 已设置时)
