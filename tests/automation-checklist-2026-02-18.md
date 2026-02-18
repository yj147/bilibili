# 自动化测试执行清单（低风险优先）

日期：2026-02-18  
基线：`tests/prd-test-cases-v2.md`  
约束：避免触发真实高频举报与多账号并发风控场景

| ID | 对应用例 | 执行方式 | 状态 | 备注 |
|---|---|---|---|---|
| C01 | 环境启动校验（前后端） | shell + curl | [x] PASS | `127.0.0.1:3000` 与 `127.0.0.1:8000` 均可访问 |
| C02 | TC-F-035 前端代理 GET 转发 | curl | [x] PASS | `GET /api/accounts/` 通过前端代理返回 200 |
| C03 | 仪表盘加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C04 | 账号页加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C05 | 目标页加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C06 | 自动回复页加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C07 | 调度页加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C08 | 配置页加载与无错误闪现 | agent-browser | [x] PASS | URL/Title 正常，`errors` 空 |
| C09 | TC-F-013 目标统计接口 | curl | [x] PASS | `GET /api/targets/stats` 返回 200 |
| C10 | TC-F-009/012 创建+查询 video 目标 | curl | [x] PASS | 创建/查询/删除闭环通过；不执行真实举报 |
| C11 | TC-E-004 非法 comment reason_id | curl | [x] PASS | 返回 422（含 reason_id 非法提示） |
| C12 | TC-E-011 配置 min_delay 越界 | curl | [x] PASS | 返回 400（区间校验生效） |
| C13 | TC-F-028/029 配置更新与回滚 | curl | [x] PASS | 依据代码约束 `max_delay` 使用 20，更新与回滚均成功 |
| C14 | TC-F-019/020 自动回复规则 CRUD（不启停服务） | curl | [x] PASS | 新增/查询/删除 + default upsert 通过 |
| C15 | TC-F-023/025 调度任务创建-切换-删除 | curl | [x] PASS | 测试任务创建后双 toggle 与删除成功 |
| C16 | TC-F-033/034 WebSocket 连接与 ping/pong | python 脚本 | [x] PASS | 收到 `connected` / `pong` / `heartbeat` |
| C17 | 页面巡检循环（3 轮）无新增错误 | agent-browser | [x] PASS | 3 轮巡检均无 `page error`/`console error` |
| C18 | 后端回归测试 | pytest | [x] PASS | `52 passed` |
| C19 | 前端静态检查 | npm | [x] PASS | `eslint` 通过 |
| C20 | 多账号池场景 | Code-Verified | [x] PASS | 以代码/测试证据归档：`report_service` 并发+冷却+重试+提前退出路径已覆盖，真实多账号压测按风险策略跳过 |

## 失败闭环规则
- 任一失败项：记录复现步骤 -> 根因定位 -> 最小修复 -> 原用例复测 -> 相关回归复测。
- 连续 3 次修复无效：触发 `$break-loop`，并在修复后执行 `$update-spec` 记录经验。
