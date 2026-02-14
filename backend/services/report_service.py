"""Report execution business logic."""
import json
import asyncio
import random
import time

from backend.database import execute_query, execute_insert
from backend.config import MIN_DELAY, MAX_DELAY, ACCOUNT_COOLDOWN
from backend.core.bilibili_client import _human_delay
from backend.logger import logger

# Track last report time per account for cooldown
_account_last_report: dict[int, float] = {}
_cooldown_lock = asyncio.Lock()

def _cleanup_stale_cooldowns():
    """Remove cooldown entries older than 1 hour to prevent memory leak."""
    current_time = time.monotonic()
    stale_threshold = 3600  # 1 hour
    stale_keys = [
        account_id for account_id, last_ts in list(_account_last_report.items())
        if current_time - last_ts > stale_threshold
    ]
    for key in stale_keys:
        del _account_last_report[key]
    if stale_keys:
        logger.debug("Cleaned up %d stale cooldown entries", len(stale_keys))


async def execute_single_report(target: dict, account: dict) -> dict:
    """Execute a single report using one account. Returns a result dict."""
    from backend.core.bilibili_client import BilibiliClient
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.api.websocket import broadcast_log

    try:
        auth = BilibiliAuth.from_db_account(account)

        async with BilibiliClient(auth, account_index=0) as client:
            bvid = target.get("identifier", "") if target.get("identifier", "").startswith("BV") else ""

            if target["type"] == "video":
                aid = target.get("aid") or 0
                # BV号时自动获取aid
                if not aid and bvid:
                    info = await client.get_video_info(bvid)
                    if info.get("code") == 0:
                        aid = info["data"]["aid"]
                result = await client.report_video(
                    aid=aid,
                    reason=target.get("reason_id") or 1,
                    content=target.get("reason_text") or "",
                    bvid=bvid,
                )
            elif target["type"] == "comment":
                identifier = target["identifier"]
                if ":" in identifier:
                    oid = int(identifier.split(":")[0])
                    rpid = int(identifier.split(":")[-1])
                else:
                    oid = target.get("aid") or 0
                    rpid = int(identifier)
                # B站评论举报只支持 reason 1-9，其他值会返回 12012
                comment_reason = target.get("reason_id") or 4
                if comment_reason not in (1, 2, 3, 4, 5, 7, 8, 9):
                    comment_reason = 4  # fallback to 赌博诈骗
                result = await client.report_comment(
                    oid=oid, rpid=rpid,
                    reason=comment_reason,
                    content=target.get("reason_text") or "",
                    bvid=bvid,
                )
            elif target["type"] == "user":
                result = await client.report_user(
                    mid=int(target["identifier"]),
                    reason_v2=target.get("reason_id") or 4,
                    reason=target.get("reason_content_id") or 1,
                )
            else:
                result = {"code": -1, "message": "Unknown target type"}

            code = result.get("code")
            # 0=success, 12022=already deleted, 12008=already reported — target is dealt with
            success = code == 0 or code in (12022, 12008)

            log_id = await execute_insert(
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
                log_id=log_id,
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
        log_id = await execute_insert(
            """INSERT INTO report_logs (target_id, account_id, action, success, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (target["id"], account["id"], f"report_{target['type']}", False, str(e)),
        )
        from backend.api.websocket import broadcast_log
        await broadcast_log(
            "report",
            f"[{account['name']}] report_{target['type']} {target['identifier']} -> ERROR: {str(e)}",
            {"target_id": target["id"], "account_id": account["id"], "success": False},
            log_id=log_id,
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

    # Circuit breaker: stop retrying if retry_count exceeds threshold
    MAX_RETRY_COUNT = 3
    if target.get("retry_count", 0) >= MAX_RETRY_COUNT:
        logger.warning("Target %s exceeded max retry count (%d), marking as failed", target_id, MAX_RETRY_COUNT)
        await target_service.update_target_status(target_id, "failed")
        return None, f"Target exceeded max retry count ({MAX_RETRY_COUNT})"

    if account_ids:
        placeholders = ",".join("?" * len(account_ids))
        accounts = await execute_query(
            f"SELECT * FROM accounts WHERE id IN ({placeholders}) AND is_active = 1 AND status = 'valid'",
            tuple(account_ids),
        )
    else:
        accounts = await account_service.get_active_accounts()

    if not accounts:
        return None, "No active accounts available"

    # Status already set to "processing" by the API layer (fire-and-forget)

    # Shuffle accounts to avoid predictable ordering fingerprint
    accounts = list(accounts)
    random.shuffle(accounts)

    results = []
    for account in accounts:
        max_rate_retries = 2
        for attempt in range(1 + max_rate_retries):
            # Cleanup stale cooldown entries periodically
            _cleanup_stale_cooldowns()

            # Account cooldown: wait if reported too recently
            last_ts = _account_last_report.get(account["id"], 0)
            elapsed = time.monotonic() - last_ts
            if elapsed < ACCOUNT_COOLDOWN:
                wait = ACCOUNT_COOLDOWN - elapsed + random.uniform(0, 5)
                logger.info("[%s] Account cooldown, waiting %.1fs...", account["name"], wait)
                await asyncio.sleep(wait)

            result = await execute_single_report(target, account)
            _account_last_report[account["id"]] = time.monotonic()

            resp = result.get("response") or {}
            if resp.get("code") == 12019 and attempt < max_rate_retries:
                wait = 90 + random.uniform(0, 15)
                logger.info("[%s] Rate limited (12019), waiting %.0fs before retry %d...", account["name"], wait, attempt + 1)
                _account_last_report[account["id"]] = time.monotonic() + wait
                await asyncio.sleep(wait)
                continue
            break

        results.append(result)

        # Stop trying other accounts if this one succeeded
        if result.get("success"):
            break

        await asyncio.sleep(_human_delay(MIN_DELAY, MAX_DELAY))

    any_success = any(r["success"] for r in results)
    final_status = "completed" if any_success else "failed"
    await target_service.increment_retry_and_set_status(target_id, final_status)

    return results, None


async def execute_batch_reports(target_ids: list[int] | None, account_ids: list[int] | None):
    """Execute reports for multiple targets with concurrency control."""
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
            f"SELECT * FROM accounts WHERE id IN ({placeholders}) AND is_active = 1 AND status = 'valid'",
            tuple(account_ids),
        )
    else:
        accounts = await account_service.get_active_accounts()

    if not accounts:
        return None, "No active accounts available"

    semaphore = asyncio.Semaphore(5)

    async def process_target(target: dict) -> list[dict]:
        """Process a single target with all accounts until success."""
        async with semaphore:
            await target_service.update_target_status(target["id"], "processing")
            shuffled_accounts = list(accounts)
            random.shuffle(shuffled_accounts)

            results = []
            for account in shuffled_accounts:
                max_rate_retries = 2
                for attempt in range(1 + max_rate_retries):
                    last_ts = _account_last_report.get(account["id"], 0)
                    elapsed = time.monotonic() - last_ts
                    if elapsed < ACCOUNT_COOLDOWN:
                        wait = ACCOUNT_COOLDOWN - elapsed + random.uniform(0, 5)
                        logger.info("[%s] Account cooldown, waiting %.1fs...", account["name"], wait)
                        await asyncio.sleep(wait)

                    result = await execute_single_report(target, account)
                    _account_last_report[account["id"]] = time.monotonic()

                    resp = result.get("response") or {}
                    if resp.get("code") == 12019 and attempt < max_rate_retries:
                        wait = 90 + random.uniform(0, 15)
                        logger.info("[%s] Rate limited (12019), waiting %.0fs before retry %d...", account["name"], wait, attempt + 1)
                        _account_last_report[account["id"]] = time.monotonic() + wait
                        await asyncio.sleep(wait)
                        continue
                    break

                results.append(result)

                if result.get("success"):
                    break

                await asyncio.sleep(_human_delay(MIN_DELAY, MAX_DELAY))

            any_success = any(r["success"] for r in results)
            await target_service.update_target_status(
                target["id"], "completed" if any_success else "failed"
            )
            return results

    tasks = [process_target(target) for target in targets]
    all_results_nested = await asyncio.gather(*tasks)
    all_results = [r for results in all_results_nested for r in results]

    successful = sum(1 for r in all_results if r["success"])
    return {
        "total_targets": len(targets),
        "total_accounts": len(accounts),
        "successful": successful,
        "failed": len(all_results) - successful,
        "results": all_results,
    }, None


async def scan_and_report_comments(
    bvid: str,
    account_id: int,
    reason_id: int = 9,
    reason_text: str = "",
    max_pages: int = 5,
    auto_report: bool = False,
) -> dict:
    """Scan comments of a video, create targets, and optionally batch report them."""
    from backend.core.bilibili_client import BilibiliClient
    from backend.core.bilibili_auth import BilibiliAuth
    from backend.services import account_service, target_service
    from backend.api.websocket import broadcast_log

    account = await account_service.get_account(account_id)
    if not account:
        return {"error": "Account not found"}

    if not account.get("is_active") or account.get("status") != "valid":
        return {"error": "Account is not active or valid"}

    auth = BilibiliAuth.from_db_account(account)
    errors: list[str] = []
    comments_found = 0
    targets_created = 0
    targets_skipped = 0
    reports_executed = 0
    reports_successful = 0
    aid = 0

    async with BilibiliClient(auth, account_index=0) as client:
        # Step 1: Resolve BV -> aid
        info = await client.get_video_info(bvid)
        if info.get("code") != 0:
            msg = info.get("message", "Failed to get video info")
            return {"error": msg}
        aid = info["data"]["aid"]
        await broadcast_log("scan", f"Video {bvid} resolved to aid={aid}")

        # Step 2: Paginate through comments
        all_replies: list[dict] = []
        for page in range(1, max_pages + 1):
            resp = await client.get_comments(oid=aid, type_code=1, pn=page, ps=20)
            if resp.get("code") != 0:
                errors.append(f"Page {page}: {resp.get('message', 'error')}")
                break

            replies = (resp.get("data") or {}).get("replies") or []
            if not replies:
                break
            all_replies.extend(replies)
            await broadcast_log("scan", f"Page {page}: fetched {len(replies)} comments (total {len(all_replies)})")

            # Anti-detection delay between pages
            await asyncio.sleep(_human_delay(MIN_DELAY, MAX_DELAY))

        comments_found = len(all_replies)
        await broadcast_log("scan", f"Scan complete: {comments_found} comments found for {bvid}")

        # Step 3: Create targets for each comment
        for reply in all_replies:
            rpid = reply.get("rpid")
            if not rpid:
                continue
            try:
                # Check if target already exists
                existing = await execute_query(
                    "SELECT id FROM targets WHERE type = 'comment' AND identifier = ?",
                    (str(rpid),)
                )
                if existing:
                    targets_skipped += 1
                    continue

                comment_text = reply.get("content", {}).get("message", "")
                display = comment_text[:30] if comment_text else None
                await target_service.create_target(
                    target_type="comment",
                    identifier=str(rpid),
                    aid=aid,
                    reason_id=reason_id,
                    reason_text=reason_text,
                    display_text=display,
                )
                targets_created += 1
            except Exception as e:
                errors.append(f"Create target rpid={rpid}: {e}")

        await broadcast_log("scan", f"Created {targets_created} targets from {comments_found} comments (skipped {targets_skipped} duplicates)")

        # Step 4: Optionally auto-report
        if auto_report and targets_created > 0:
            # Fetch the newly created targets by querying recent pending comment targets for this aid
            pending = await execute_query(
                "SELECT * FROM targets WHERE type = 'comment' AND aid = ? AND status = 'pending' ORDER BY id DESC LIMIT ?",
                (aid, targets_created),
            )
            for target in pending:
                result = await execute_single_report(target, account)
                reports_executed += 1
                if result.get("success"):
                    reports_successful += 1
                await asyncio.sleep(_human_delay(MIN_DELAY, MAX_DELAY))

            await broadcast_log(
                "scan",
                f"Auto-report done: {reports_successful}/{reports_executed} successful",
            )

    return {
        "bvid": bvid,
        "aid": aid,
        "comments_found": comments_found,
        "targets_created": targets_created,
        "targets_skipped": targets_skipped,
        "reports_executed": reports_executed,
        "reports_successful": reports_successful,
        "errors": errors,
    }


async def get_report_logs(limit: int = 100):
    return await execute_query(
        """SELECT l.*, a.name as account_name
           FROM report_logs l
           LEFT JOIN accounts a ON l.account_id = a.id
           ORDER BY l.executed_at DESC LIMIT ?""",
        (limit,),
    )


async def get_target_logs(target_id: int, limit: int = 100):
    return await execute_query(
        """SELECT l.*, a.name as account_name
           FROM report_logs l
           LEFT JOIN accounts a ON l.account_id = a.id
           WHERE l.target_id = ?
           ORDER BY l.executed_at DESC LIMIT ?""",
        (target_id, limit),
    )
