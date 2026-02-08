"""Report execution business logic."""
import json
import asyncio
import random

from backend.database import execute_query, execute_insert
from backend.config import MIN_DELAY, MAX_DELAY
from backend.logger import logger


async def execute_single_report(target: dict, account: dict) -> dict:
    """Execute a single report using one account. Returns a result dict."""
    from backend.core.bilibili_client import BilibiliClient
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.api.websocket import broadcast_log

    try:
        auth = BilibiliAuth.from_db_account(account)

        async with BilibiliClient(auth, account_index=0) as client:
            if target["type"] == "video":
                aid = target.get("aid") or 0
                # BV号时自动获取aid
                if not aid and target.get("identifier", "").startswith("BV"):
                    info = await client.get_video_info(target["identifier"])
                    if info.get("code") == 0:
                        aid = info["data"]["aid"]
                result = await client.report_video(
                    aid=aid,
                    reason=target.get("reason_id") or 1,
                    content=target.get("reason_text") or "",
                )
            elif target["type"] == "comment":
                identifier = target["identifier"]
                if ":" in identifier:
                    oid = int(identifier.split(":")[0])
                    rpid = int(identifier.split(":")[-1])
                else:
                    oid = target.get("aid") or 0
                    rpid = int(identifier)
                result = await client.report_comment(
                    oid=oid, rpid=rpid,
                    reason=target.get("reason_id") or 1,
                    content=target.get("reason_text") or "",
                )
            elif target["type"] == "user":
                result = await client.report_user(
                    mid=int(target["identifier"]),
                    reason=target.get("reason_text") or "违规内容",
                    reason_id=target.get("reason_id") or 1,
                )
            else:
                result = {"code": -1, "message": "Unknown target type"}

            success = result.get("code") == 0

            await execute_insert(
                """INSERT INTO report_logs (target_id, account_id, action, request_data, response_data, success, error_message)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    target["id"], account["id"],
                    f"report_{target['type']}",
                    json.dumps({"identifier": target["identifier"], "reason_id": target.get("reason_id")}),
                    json.dumps(result),
                    success,
                    None if success else result.get("message", "Unknown error"),
                ),
            )

            await broadcast_log(
                "report",
                f"[{account['name']}] report_{target['type']} {target['identifier']} -> {'OK' if success else 'FAIL'}",
                {"target_id": target["id"], "account_id": account["id"], "success": success},
            )

            return {
                "target_id": target["id"],
                "account_id": account["id"],
                "account_name": account["name"],
                "success": success,
                "message": result.get("message", "OK" if success else "Failed"),
                "response": result,
            }

    except Exception as e:
        await execute_insert(
            """INSERT INTO report_logs (target_id, account_id, action, success, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (target["id"], account["id"], f"report_{target['type']}", False, str(e)),
        )
        from backend.api.websocket import broadcast_log
        await broadcast_log(
            "report",
            f"[{account['name']}] report_{target['type']} {target['identifier']} -> ERROR: {str(e)}",
            {"target_id": target["id"], "account_id": account["id"], "success": False},
        )
        return {
            "target_id": target["id"],
            "account_id": account["id"],
            "account_name": account["name"],
            "success": False,
            "message": str(e),
        }


async def execute_report_for_target(target_id: int, account_ids: list[int] | None = None):
    """Execute reports for a single target using specified or all active accounts."""
    from backend.services import target_service, account_service

    target = await target_service.get_target(target_id)
    if not target:
        return None, "Target not found"

    if account_ids:
        placeholders = ",".join("?" * len(account_ids))
        accounts = await execute_query(
            f"SELECT * FROM accounts WHERE id IN ({placeholders}) AND is_active = 1",
            tuple(account_ids),
        )
    else:
        accounts = await account_service.get_active_accounts()

    if not accounts:
        return None, "No active accounts available"

    await target_service.update_target_status(target_id, "processing")

    results = []
    for account in accounts:
        result = await execute_single_report(target, account)
        results.append(result)
        await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

    any_success = any(r["success"] for r in results)
    final_status = "completed" if any_success else "failed"
    await target_service.increment_retry_and_set_status(target_id, final_status)

    return results, None


async def execute_batch_reports(target_ids: list[int] | None, account_ids: list[int] | None):
    """Execute reports for multiple targets."""
    from backend.services import target_service, account_service

    if target_ids:
        placeholders = ",".join("?" * len(target_ids))
        targets = await execute_query(
            f"SELECT * FROM targets WHERE id IN ({placeholders})", tuple(target_ids)
        )
    else:
        targets = await target_service.get_pending_targets()

    if not targets:
        return None, "No targets to process"

    if account_ids:
        placeholders = ",".join("?" * len(account_ids))
        accounts = await execute_query(
            f"SELECT * FROM accounts WHERE id IN ({placeholders}) AND is_active = 1",
            tuple(account_ids),
        )
    else:
        accounts = await account_service.get_active_accounts()

    if not accounts:
        return None, "No active accounts available"

    all_results = []
    for target in targets:
        await target_service.update_target_status(target["id"], "processing")
        for account in accounts:
            result = await execute_single_report(target, account)
            all_results.append(result)
            await asyncio.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        any_success = any(r["success"] and r["target_id"] == target["id"] for r in all_results)
        await target_service.update_target_status(
            target["id"], "completed" if any_success else "failed"
        )

    successful = sum(1 for r in all_results if r["success"])
    return {
        "total_targets": len(targets),
        "total_accounts": len(accounts),
        "successful": successful,
        "failed": len(all_results) - successful,
        "results": all_results,
    }, None


async def get_report_logs(limit: int = 100):
    return await execute_query(
        """SELECT l.*, a.name as account_name
           FROM report_logs l
           LEFT JOIN accounts a ON l.account_id = a.id
           ORDER BY l.executed_at DESC LIMIT ?""",
        (limit,),
    )


async def get_target_logs(target_id: int):
    return await execute_query(
        """SELECT l.*, a.name as account_name
           FROM report_logs l
           LEFT JOIN accounts a ON l.account_id = a.id
           WHERE l.target_id = ?
           ORDER BY l.executed_at DESC""",
        (target_id,),
    )
