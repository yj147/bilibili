# Bili-Sentinel 自动化测试报告（Round 2）

日期：2026-02-18  
执行基线：`tests/prd-test-cases-v2.md`  
执行清单：`tests/automation-checklist-2026-02-18.md`

## 1) 执行结论

| 指标 | 结果 |
|---|---|
| 总执行项（含 Code-Verified） | 20 |
| PASS | 20 |
| FAIL | 0 |
| 修复后复测通过 | 2 |
| 风险策略 | 严格低风险（未触发真实高频举报/多账号并发实测） |

结论：本轮“测试 → 发现问题 → 修复/调整 → 复测”闭环完成，未复现阻塞性错误。

## 2) 本轮闭环记录（Fail → Fix → Retest）

### 问题 A：`agent-browser` 无法启动浏览器
- 现象：启动时报 `chromium_headless_shell-1200` 不存在。
- 根因：本机 Playwright 缓存版本为 `1208`，`agent-browser` 期待 `1200` 路径。
- 处理：创建兼容软链 `chromium_headless_shell-1200 -> chromium_headless_shell-1208`。
- 复测：`agent-browser open/get/errors/console` 正常，后续 3 轮页面巡检全部通过。

### 问题 B：配置更新用例首次失败（测试输入问题）
- 现象：`C13` 首次用 `max_delay=5` 返回 400。
- 根因：代码约束 `max_delay` 合法区间是 `10-60`，输入 5 越界。
- 证据：`backend/services/config_service.py:27`~`backend/services/config_service.py:30`。
- 处理：改用合法值 `max_delay=20`，并在同一用例中验证回滚。
- 复测：更新/验证/回滚全部成功。

## 3) 自动化覆盖结果（低风险主链路）

- API & 代理：
  - `GET /api/accounts/`（前端代理）通过
  - `GET /api/targets/stats` 通过
  - 目标创建/查询/删除闭环通过（未执行举报）
  - 边界校验通过：非法 `reason_id`（422）、`min_delay` 越界（400）
  - 自动回复规则 CRUD（不启停服务）通过
  - 调度任务创建→toggle→删除通过
- WebSocket：
  - `/ws/logs` 收到 `connected`、`pong`、`heartbeat`
- 前端页面巡检（agent-browser）：
  - `/` `/accounts` `/targets` `/autoreply` `/scheduler` `/config`
  - 单页检查 + 3 轮循环巡检：无页面错误、无 console error

## 4) 回归验证

- 后端：`pytest backend/tests/ -q` -> `52 passed`（10.37s）
- 前端：`npm run lint` -> 通过

## 5) 多账号池场景（Code-Verified 归档）

按风险约束未做真实多账号并发压测，采用代码与测试证据归档：

- 多账号打散、公平尝试、提前成功退出：
  - `backend/services/report_service.py:227`~`backend/services/report_service.py:272`
  - `backend/services/report_service.py:323`~`backend/services/report_service.py:363`
- 并发信号量（批量）：
  - `backend/services/report_service.py:313`
- 冷却与 12019 重试路径：
  - `backend/services/report_service.py:239`~`backend/services/report_service.py:265`
  - `backend/services/report_service.py:349`~`backend/services/report_service.py:356`
- claim CAS / 并发抢占保护的测试证据：
  - `backend/tests/test_scheduler_regressions.py:282`~`backend/tests/test_scheduler_regressions.py:288`
  - `backend/tests/test_scheduler_regressions.py:331`~`backend/tests/test_scheduler_regressions.py:362`

## 6) 风险与后续建议

- 当前未做真实多账号池压测（符合本轮“活性账号保护”要求）。
- 若后续具备隔离测试账号池，建议补充：
  1. 多账号池公平性统计（分布验证）
  2. 长时 12019 退避策略稳定性（小时级）
  3. 调度+举报混合负载下数据库锁竞争观察
