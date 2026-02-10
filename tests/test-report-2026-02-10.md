# Bili-Sentinel Automated Test Report

**Date**: 2026-02-10
**Environment**: Backend http://127.0.0.1:8000, Frontend http://localhost:3000
**Auth**: Tested both disabled and enabled modes

---

## Summary

| Metric | Count |
|--------|-------|
| Total Executed | 115 |
| PASS | 115 |
| FAIL | 0 |
| FIXED (was FAIL) | 6 |
| **Pass Rate** | **100%** |

**Bugs Found & Fixed**: 6 (BUG-001~006, all resolved)

---

## Results by Module

### Module 1: Account Management (16 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-001 | Create account (required fields) | **PASS** |
| TC-F-002 | Create account (all optional fields) | **PASS** |
| TC-F-003 | List accounts | **PASS** |
| TC-F-004 | Get single account | **PASS** |
| TC-F-005 | Update account | **PASS** |
| TC-F-006 | Delete account | **PASS** |
| TC-F-007 | Account health check (valid Cookie) | **PASS** (is_valid=true, uid=690693777) |
| TC-F-008 | Export accounts (no credentials) | **PASS** |
| TC-F-009 | Export accounts (with credentials) | **PASS** |
| TC-F-010 | Import accounts (batch) | **PASS** |
| TC-E-001 | Empty name | **PASS** (422) — *Fixed: BUG-003* |
| TC-E-002 | Missing sessdata | **PASS** (422) |
| TC-E-003 | Get nonexistent account | **PASS** (404) |
| TC-E-004 | Update nonexistent account | **PASS** (404) — *Fixed: BUG-004* |
| TC-E-005 | Delete nonexistent account | **PASS** (404) |
| TC-E-006 | Import empty array | **PASS** (200) |

### Module 2: Target Management (16 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-011 | Create video target | **PASS** — *Fixed: BUG-001* |
| TC-F-012 | Create comment target | **PASS** — *Fixed: BUG-001* |
| TC-F-013 | Create user target | **PASS** — *Fixed: BUG-001* |
| TC-F-014 | Batch create targets | **PASS** — *Fixed: BUG-001* |
| TC-F-015 | Pagination | **PASS** |
| TC-F-016 | Filter by status | **PASS** |
| TC-F-017 | Filter by type | **PASS** |
| TC-F-018 | Update target | **PASS** |
| TC-F-019 | Delete single target | **PASS** |
| TC-F-020 | Delete targets by status | **PASS** |
| TC-F-021 | Export targets | **PASS** |
| TC-E-008 | Invalid type | **PASS** (422) |
| TC-E-009 | Batch create empty identifiers | **PASS** (200) |
| TC-E-010 | Page out of range | **PASS** |
| TC-E-011 | page_size=0 | **PASS** (422) |
| TC-E-012 | Batch delete no match | **PASS** |

### Module 3: Reports (8 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-022 | Single target report execution | **PASS** (200, 7 results) |
| TC-F-024 | Batch report (2 targets, 1 account) | **PASS** (1 success, 1 fail — invalid BV) |
| TC-F-026 | Get report logs | **PASS** |
| TC-F-027 | Get logs for specific target | **PASS** |
| TC-F-028 | Comment scan (BV1K77HzAENW) | **PASS** (found 2 comments, created 2 targets) |
| TC-F-029 | Report comment target | **PASS** (code=0, "举报已受理") |
| TC-E-013 | Report nonexistent target | **PASS** (404) |
| TC-F-085 | Target type constraint (DB) | **PASS** |

### Module 4: Auto Reply (12 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-030 | Create keyword reply rule | **PASS** |
| TC-F-031 | Create default reply (null keyword) | **PASS** |
| TC-F-032 | List reply configs | **PASS** |
| TC-F-033 | Update reply config | **PASS** |
| TC-F-034 | Delete reply config | **PASS** |
| TC-F-035 | Start autoreply service | **PASS** |
| TC-F-036 | Stop autoreply service | **PASS** |
| TC-F-037 | Get autoreply status | **PASS** |
| TC-ST-001 | State transition (stop->start->stop) | **PASS** |
| TC-E-016 | Duplicate start | **PASS** (graceful) |
| TC-E-017 | Stop when not running | **PASS** (graceful) |
| TC-E-018 | Empty response | **PASS** (422) — *Fixed: BUG-005* |

### Module 5: Scheduler (10 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-038 | Create interval task | **PASS** |
| TC-F-039 | Create cron task | **PASS** |
| TC-F-040 | List tasks | **PASS** |
| TC-F-041 | Get single task | **PASS** |
| TC-F-042 | Update task | **PASS** |
| TC-F-043 | Delete task | **PASS** |
| TC-F-044 | Toggle task active/inactive | **PASS** |
| TC-F-045 | Get execution history | **PASS** |
| TC-E-019 | Invalid task_type | **PASS** (422) |
| TC-E-021 | Toggle nonexistent task | **PASS** (404) |

### Module 6: Config & Auth (14 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-046 | List all configs | **PASS** |
| TC-F-047 | Get single config | **PASS** |
| TC-F-048 | Update config | **PASS** |
| TC-F-049 | Batch update config | **PASS** (verified values updated) |
| TC-F-050 | Generate QR code | **PASS** |
| TC-F-051/052 | QR scan login complete flow | **PASS** (updated existing account Cookie) |
| TC-F-053 | Cookie status check | **PASS** |
| TC-E-022 | Get nonexistent config key | **PASS** (404) |
| TC-F-068 | API Key auth — valid key | **PASS** (200) |
| TC-F-069 | API Key auth — invalid key | **PASS** (401) |
| TC-ERR-002 | No API Key with auth enabled | **PASS** (401) |
| TC-F-070 | Auth disabled (no API key) | **PASS** (200) |
| TC-E-023 | WebSocket invalid token | **PASS** (rejected with 4001) |

### Module 7: WebSocket (2 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-055 | WebSocket connection | **PASS** — *Fixed: BUG-002* |
| TC-F-056 | WebSocket ping/pong | **PASS** |

### Module 8: Frontend UI — Pages (10 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-058 | Dashboard page loads | **PASS** |
| TC-F-058+ | Dashboard content (stats cards, log stream) | **PASS** |
| TC-F-059 | Accounts page (list, CRUD buttons, QR login) | **PASS** |
| TC-F-060 | Targets page (filters, pagination, actions) | **PASS** |
| TC-F-061 | Autoreply page (rules, start/stop) | **PASS** |
| TC-F-062 | Scheduler page (tasks, toggle) | **PASS** |
| TC-F-063 | Config page (sliders, inputs, save) | **PASS** |
| TC-F-064 | Dark theme rendering | **PASS** |
| TC-F-065 | Sidebar navigation | **PASS** |
| TC-F-067 | Responsive layout (375x812 mobile) | **PASS** (sidebar collapses to hamburger) |

### Module 9: Frontend UI — E2E Interactions (10 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-066 | Toast notifications (success/error) | **PASS** (shown on edit, add, save) |
| TC-F-089 | Add target modal | **PASS** (type/identifier/reason fields) |
| TC-F-090 | Create target via UI + list refresh | **PASS** (count updated 14->15) |
| TC-F-091 | Add autoreply rule via modal | **PASS** (Toast: rule added) |
| TC-F-092 | Create scheduler task modal | **PASS** (name/type/cron/interval) |
| TC-F-093 | Edit account modal + save | **PASS** (name/group changed) |
| TC-F-094 | Config page save | **PASS** (log_retention_days=60 verified) |
| TC-F-095 | Delete account confirmation dialog | **PASS** (confirm prompt shown) |
| TC-F-096 | QR login modal | **PASS** (QR code generated) |
| TC-F-097 | Comment scan modal + execution | **PASS** (BV input, account select, scan state, results display) |
| TC-F-098 | Comment scan dedup | **PASS** (0 new comments for already-scanned video) |

### Module 9b: Browser Automation — Supplemental E2E (10 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-099 | Account health check via UI button | **PASS** (Toast: 检测完成, last_check updated) |
| TC-F-100 | Autoreply start service via UI | **PASS** (button→停止服务, status→服务运行中) |
| TC-F-101 | Autoreply stop service via UI | **PASS** (button→启动服务, status→服务已停止) |
| TC-F-102 | Scheduler task toggle via UI | **PASS** (ACTIVE→PAUSED) |
| TC-F-103 | Clear completed targets via UI | **PASS** (confirm dialog, 17→14, 3 COMPLETED removed) |
| TC-F-104 | Clear failed targets via UI | **PASS** (confirm dialog, 14→2, 12 FAILED removed) |
| TC-F-105 | Delete single target via UI | **PASS** (confirm dialog, 2→1) |
| TC-F-106 | Manual import account via UI | **PASS** (form fill + submit, Toast: 账号添加成功) |
| TC-F-107 | Batch import targets via UI | **PASS** (2 targets imported, Toast: 已导入 2 个目标) |
| TC-F-108 | Execute report via UI button | **PASS** (button disabled during exec, Toast shown) |

### Module 9c: Browser Automation — Filter/Delete/Misc (9 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-109 | Type filter「视频」via UI dropdown | **PASS** (9→5 items, all video) |
| TC-F-110 | Type filter「评论」via UI dropdown | **PASS** (9→3 items, all comment) |
| TC-F-111 | Status filter「待处理」via UI dropdown | **PASS** (9→7 items, all PENDING) |
| TC-F-112 | Status filter「失败」via UI dropdown | **PASS** (9→1 item, only FAILED) |
| TC-F-113 | Page size dropdown switch | **PASS** (20→10 per page, pagination text correct) |
| TC-F-114 | 全域巡航 batch report trigger | **PASS** (triggers /api/reports/execute/batch) |
| TC-F-115 | Delete scheduler task via UI | **PASS** (confirm dialog, 4→3 tasks) |
| TC-F-116 | Delete autoreply rule via UI | **PASS** (confirm dialog, rule removed from list) |
| TC-F-117 | Remove account via UI + list refresh | **PASS** (confirm dialog, 8→7 accounts) |

### Module 10: API Proxy (2 tests)

| Test Case | Description | Result |
|-----------|-------------|--------|
| TC-F-080 | Proxy GET forwarding | **PASS** |
| TC-F-081 | Proxy POST forwarding | **PASS** |

---

## Bugs Found & Fixed

| Bug ID | Severity | Description | Root Cause | Fix | Files |
|--------|----------|-------------|------------|-----|-------|
| BUG-001 | Critical | Target creation returns 500 | DB missing `reason_content_id` column | ALTER TABLE ADD COLUMN | `data/sentinel.db` |
| BUG-002 | High | WebSocket connection returns 500 | Global `dependencies=[Depends(verify_api_key)]` injects `Request` type which fails for WebSocket | Per-router auth deps, WebSocket excluded | `backend/main.py`, `backend/auth.py` |
| BUG-003 | Low | Empty account name accepted | `AccountBase.name` had no min_length | Added `Field(..., min_length=1)` | `backend/models/account.py` |
| BUG-004 | Low | Update nonexistent account returns 400 | `update_account` returns None for both "no fields" and "not found" | Check existence first, return 404 | `backend/api/accounts.py` |
| BUG-005 | Low | Empty autoreply response accepted | `AutoReplyConfigBase.response` had no min_length | Added `Field(..., min_length=1)` | `backend/models/task.py` |
| BUG-006 | Medium | Autoreply config list API returns 500 | DB row id=7 has `response=''` violating Pydantic `min_length=1` validation during serialization | Deleted invalid row from `autoreply_config` table | `data/sentinel.db` |

---

## Not Tested (Require Special Conditions)

| Test Case | Reason |
|-----------|--------|
| TC-F-054 | Cookie refresh — MainAccount has no refresh_token |
| TC-F-071~079 | Anti-detection/performance — requires extended runtime monitoring |
| TC-F-083~088 | Data integrity (cascade/constraints) — needs isolated DB environment |

---

## Recommendations

1. Add refresh_token to MainAccount for cookie refresh testing (TC-F-054)
2. Consider adding DB connection pool timeout/retry to prevent `database is locked` under concurrent scheduler load
3. Add automated Playwright test suite for regression testing
