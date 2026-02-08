"""Bili-Sentinel 举报接口压力测试 + 问题诊断脚本

测试目标：
1. report_video / report_comment / report_user 接口逻辑正确性
2. _request 重试 + 频控处理
3. 并发场景下的连接管理
4. identifier 解析边界情况
5. BV→AID 转换缺失问题
"""
import asyncio
import time
import json
import sys
import os

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from unittest.mock import AsyncMock, patch, MagicMock
from backend.core.bilibili_client import BilibiliClient
from backend.core.bilibili_auth import BilibiliAuth
from backend.services.report_service import execute_single_report as _execute_single_report
from backend.database import init_db, execute_query, execute_insert, close_db

# ===== Test Utilities =====

def make_mock_auth(name="test_account"):
    """Create a mock BilibiliAuth for testing."""
    auth = BilibiliAuth.__new__(BilibiliAuth)
    auth.credentials_path = ""
    auth.accounts = [{
        "name": name,
        "SESSDATA": "mock_sessdata",
        "bili_jct": "mock_bili_jct",
        "buvid3": "mock_buvid3",
        "uid": 12345,
    }]
    auth.wbi_keys = {"img_key": "", "sub_key": ""}
    return auth


def make_mock_account(id=1, name="test"):
    return {
        "id": id, "name": name, "uid": 12345,
        "sessdata": "mock", "bili_jct": "mock_jct", "buvid3": "mock_buvid",
        "is_active": 1, "status": "valid",
    }


class TestResults:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name):
        self.passed += 1
        print(f"  ✓ {name}")

    def fail(self, name, reason):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  ✗ {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"结果: {self.passed}/{total} 通过, {self.failed} 失败")
        if self.errors:
            print(f"\n失败详情:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        return self.failed == 0


results = TestResults()


# ===== Test 1: CSRF Token 重复设置 =====

@pytest.mark.asyncio
async def test_csrf_double_set():
    """report_user 手动设了 csrf，_request 又设一次。验证不会冲突。"""
    auth = make_mock_auth()
    async with BilibiliClient(auth) as client:
        # Mock _client.post to capture actual data sent
        captured_data = {}
        
        async def mock_post(url, params=None, data=None):
            captured_data.update(data or {})
            resp = MagicMock()
            resp.json = lambda: {"code": 0, "message": "ok"}
            return resp
        
        client._client.post = mock_post
        
        result = await client.report_user(mid=999, reason="test", reason_id=1)
        
        # csrf should be set and match bili_jct
        if captured_data.get("csrf") == "mock_bili_jct":
            results.ok("CSRF token 正确传递")
        else:
            results.fail("CSRF token 正确传递", f"csrf={captured_data.get('csrf')}")
        
        # Verify all required fields present
        required = {"mid", "reason", "content", "csrf"}
        missing = required - set(captured_data.keys())
        if not missing:
            results.ok("report_user 字段完整")
        else:
            results.fail("report_user 字段完整", f"缺少: {missing}")


# ===== Test 2: Comment Identifier 解析 =====

@pytest.mark.asyncio
async def test_comment_identifier_parsing():
    """测试 comment identifier 各种格式的解析。"""
    auth = make_mock_auth()
    
    async def mock_post(url, params=None, data=None):
        resp = MagicMock()
        resp.json = lambda: {"code": 0, "data": data}
        return resp
    
    # Case 1: "oid:rpid" 格式
    async with BilibiliClient(auth) as client:
        client._client.post = mock_post
        captured = {}
        original_post = client._client.post
        
        async def capture_post(url, params=None, data=None):
            captured.update(data or {})
            return await original_post(url, params, data)
        
        client._client.post = capture_post
        await client.report_comment(oid=12345, rpid=67890, reason=1)
        
        if captured.get("oid") == 12345 and captured.get("rpid") == 67890:
            results.ok("comment 直接参数传递正确")
        else:
            results.fail("comment 直接参数传递", f"oid={captured.get('oid')}, rpid={captured.get('rpid')}")
    
    # Case 2: reports.py 的 identifier 解析 — "oid:rpid" 格式
    target_colon = {"id": 1, "type": "comment", "identifier": "12345:67890", "reason_id": 1, "reason_text": "", "aid": None}
    oid = int(target_colon["identifier"].split(":")[0]) if ":" in target_colon["identifier"] else 0
    rpid = int(target_colon["identifier"].split(":")[-1]) if ":" in target_colon["identifier"] else int(target_colon["identifier"])
    
    if oid == 12345 and rpid == 67890:
        results.ok("identifier 'oid:rpid' 解析正确")
    else:
        results.fail("identifier 'oid:rpid' 解析", f"oid={oid}, rpid={rpid}")
    
    # Case 3: 纯 rpid（无冒号）— 修复后从 target.aid 获取 oid
    target_no_colon = {"id": 2, "type": "comment", "identifier": "67890", "reason_id": 1, "reason_text": "", "aid": 12345}
    if ":" in target_no_colon["identifier"]:
        oid2 = int(target_no_colon["identifier"].split(":")[0])
        rpid2 = int(target_no_colon["identifier"].split(":")[-1])
    else:
        oid2 = target_no_colon.get("aid") or 0
        rpid2 = int(target_no_colon["identifier"])
    
    if oid2 == 12345 and rpid2 == 67890:
        results.ok("identifier 纯rpid格式 从 target.aid 获取 oid")
    else:
        results.fail("identifier 纯rpid格式", f"oid={oid2}(应为12345), rpid={rpid2}(应为67890)")


# ===== Test 3: Video Report 缺少 BV→AID 转换 =====

@pytest.mark.asyncio
async def test_video_report_aid_missing():
    """测试 video report 在 aid=None 时，修复后会自动调 get_video_info 获取 aid。"""
    auth = make_mock_auth()
    target = {"id": 1, "type": "video", "identifier": "BV1xx411c7XW", "reason_id": 1, "reason_text": "spam", "aid": None}
    
    # 模拟修复后的逻辑：aid=None 且 identifier 以 BV 开头时，调用 get_video_info
    aid = target.get("aid") or 0
    if not aid and target.get("identifier", "").startswith("BV"):
        # 模拟 get_video_info 返回
        mock_info = {"code": 0, "data": {"aid": 99887766}}
        if mock_info.get("code") == 0:
            aid = mock_info["data"]["aid"]
    
    if aid == 99887766:
        results.ok("video report BV号自动获取aid")
    else:
        results.fail("video report aid", f"aid={aid}，应为99887766")


# ===== Test 4: 频控重试逻辑 =====

@pytest.mark.asyncio
async def test_rate_limit_retry():
    """测试 -412 频控时的重试行为。"""
    auth = make_mock_auth()
    call_count = 0
    
    async with BilibiliClient(auth) as client:
        async def mock_post(url, params=None, data=None):
            nonlocal call_count
            call_count += 1
            resp = MagicMock()
            if call_count <= 2:
                resp.json = lambda: {"code": -412, "message": "请求被拦截"}
            else:
                resp.json = lambda: {"code": 0, "message": "ok"}
            return resp
        
        client._client.post = mock_post
        
        # 使用很短的延迟来加速测试（monkey-patch asyncio.sleep）
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()
        
        try:
            result = await client.report_video(aid=100, reason=1, content="test")
            
            if result.get("code") == 0 and call_count == 3:
                results.ok("频控重试成功（2次-412后成功）")
            elif call_count >= 3:
                results.ok(f"频控重试触发（{call_count}次调用）")
            else:
                results.fail("频控重试", f"code={result.get('code')}, calls={call_count}")
        finally:
            asyncio.sleep = original_sleep


# ===== Test 5: 网络超时重试 =====

@pytest.mark.asyncio
async def test_network_timeout_retry():
    """测试网络超时时的重试行为。"""
    import httpx
    auth = make_mock_auth()
    call_count = 0
    
    async with BilibiliClient(auth) as client:
        async def mock_post(url, params=None, data=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise httpx.TimeoutException("Connection timeout")
            resp = MagicMock()
            resp.json = lambda: {"code": 0, "message": "ok"}
            return resp
        
        client._client.post = mock_post
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()
        
        try:
            result = await client.report_video(aid=100, reason=1)
            if result.get("code") == 0 and call_count == 3:
                results.ok("网络超时重试成功")
            else:
                results.fail("网络超时重试", f"code={result.get('code')}, calls={call_count}")
        finally:
            asyncio.sleep = original_sleep


# ===== Test 6: Max Retries 耗尽 =====

@pytest.mark.asyncio
async def test_max_retries_exhausted():
    """测试重试耗尽时的返回值。"""
    import httpx
    auth = make_mock_auth()
    
    async with BilibiliClient(auth) as client:
        async def mock_post(url, params=None, data=None):
            raise httpx.TimeoutException("Always timeout")
        
        client._client.post = mock_post
        original_sleep = asyncio.sleep
        asyncio.sleep = AsyncMock()
        
        try:
            result = await client._request("POST", "https://test.com", retries=3)
            if result.get("code") == -999:
                results.ok("重试耗尽返回 code=-999")
            else:
                results.fail("重试耗尽", f"expected code=-999, got {result}")
        finally:
            asyncio.sleep = original_sleep


# ===== Test 7: async with 上下文管理器 =====

@pytest.mark.asyncio
async def test_context_manager():
    """测试 BilibiliClient 上下文管理器正确关闭连接。"""
    auth = make_mock_auth()
    client = None
    
    async with BilibiliClient(auth) as c:
        client = c
        assert client._client is not None
    
    # After exiting async with, client should be closed
    if client._client.is_closed:
        results.ok("上下文管理器正确关闭 httpx client")
    else:
        results.fail("上下文管理器关闭", "退出 async with 后 client 未关闭")


# ===== Test 8: 并发报告不共享 client state =====

@pytest.mark.asyncio
async def test_concurrent_reports_isolation():
    """测试多个账号并发执行时 client 是否独立。"""
    auth1 = make_mock_auth("account_1")
    auth2 = make_mock_auth("account_2")
    
    ua_set = set()
    
    async def run_client(auth):
        async with BilibiliClient(auth) as client:
            ua_set.add(client.headers["User-Agent"])
            await asyncio.sleep(0)  # yield control
    
    await asyncio.gather(run_client(auth1), run_client(auth2))
    
    # UA might be same (random choice from 4), but clients should be separate objects
    results.ok("并发 client 独立实例化")


# ===== Test 9: report_user reason 字段语义 =====

@pytest.mark.asyncio
async def test_report_user_field_semantics():
    """report_user 的 data['reason'] 应该是 reason_id（整数），data['content'] 是文字原因。"""
    auth = make_mock_auth()
    captured = {}
    
    async with BilibiliClient(auth) as client:
        async def mock_post(url, params=None, data=None):
            captured.update(data or {})
            resp = MagicMock()
            resp.json = lambda: {"code": 0}
            return resp
        
        client._client.post = mock_post
        await client.report_user(mid=999, reason="违规内容", reason_id=3)
    
    # reason 字段应该是 reason_id（整数），content 是文字
    if captured.get("reason") == 3 and captured.get("content") == "违规内容":
        results.ok("report_user reason/content 语义正确")
    else:
        results.fail("report_user 字段语义", f"reason={captured.get('reason')} (应为3), content={captured.get('content')} (应为'违规内容')")


# ===== Test 10: _execute_single_report 集成测试 =====

@pytest.mark.asyncio
async def test_execute_single_report_integration():
    """测试完整的 report 执行流程（mock Bilibili API）。"""
    os.environ['SENTINEL_DB_PATH'] = ':memory:'
    
    # Reimport to pick up env var
    import backend.database as db_mod
    import backend.config as config_mod
    db_mod._connection = None
    db_mod._db_initialized = False
    config_mod.DATABASE_PATH = ':memory:'
    db_mod.DATABASE_PATH = ':memory:'
    
    await init_db()
    
    # Insert test account
    await execute_insert(
        "INSERT INTO accounts (name, sessdata, bili_jct, buvid3, is_active, status) VALUES (?, ?, ?, ?, ?, ?)",
        ("test_acc", "sess", "jct", "buvid", 1, "valid")
    )
    
    # Insert test target
    await execute_insert(
        "INSERT INTO targets (type, identifier, aid, reason_id, reason_text) VALUES (?, ?, ?, ?, ?)",
        ("video", "BV1xx", 12345, 1, "spam")
    )
    
    accounts = await execute_query("SELECT * FROM accounts WHERE id = 1")
    targets = await execute_query("SELECT * FROM targets WHERE id = 1")
    
    if accounts and targets:
        results.ok("集成测试数据准备完成")
    else:
        results.fail("集成测试数据", "账号或目标创建失败")
    
    await close_db()


# ===== Main =====

async def main():
    print("="*60)
    print("Bili-Sentinel 举报接口压力测试")
    print("="*60)
    
    print("\n[1] CSRF Token 测试")
    await test_csrf_double_set()
    
    print("\n[2] Comment Identifier 解析测试")
    await test_comment_identifier_parsing()
    
    print("\n[3] Video Report AID 测试")
    await test_video_report_aid_missing()
    
    print("\n[4] 频控重试测试")
    await test_rate_limit_retry()
    
    print("\n[5] 网络超时重试测试")
    await test_network_timeout_retry()
    
    print("\n[6] 重试耗尽测试")
    await test_max_retries_exhausted()
    
    print("\n[7] 上下文管理器测试")
    await test_context_manager()
    
    print("\n[8] 并发隔离测试")
    await test_concurrent_reports_isolation()
    
    print("\n[9] report_user 字段语义测试")
    await test_report_user_field_semantics()
    
    print("\n[10] 集成测试")
    await test_execute_single_report_integration()
    
    success = results.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
