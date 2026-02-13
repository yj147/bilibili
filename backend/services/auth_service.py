"""QR code login and cookie refresh service."""
import re
import httpx
from backend.database import execute_query, invalidate_cache
from backend.config import USER_AGENTS
from backend.logger import logger

_UA = USER_AGENTS[5]  # Chrome Linux — consistent with config.py
_SENSITIVE_FIELDS = {"sessdata", "bili_jct", "refresh_token", "dedeuserid_ckmd5"}


async def _fetch_buvid(sessdata: str, bili_jct: str) -> dict:
    """Fetch buvid3 and buvid4 cookies from bilibili after login."""
    cookies = {"SESSDATA": sessdata, "bili_jct": bili_jct}
    headers = {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}
    result = {"buvid3": "", "buvid4": ""}
    try:
        async with httpx.AsyncClient(cookies=cookies, headers=headers, timeout=10.0) as client:
            spi_resp = await client.get("https://api.bilibili.com/x/frontend/finger/spi")
            spi_data = spi_resp.json()
            if spi_data.get("code") == 0:
                b3 = spi_data.get("data", {}).get("b_3", "")
                b4 = spi_data.get("data", {}).get("b_4", "")
                if b3:
                    result["buvid3"] = b3
                if b4:
                    result["buvid4"] = b4
    except Exception as e:
        logger.warning("[Auth] Failed to fetch buvid cookies: %s", e)
    return result


async def qr_generate() -> dict:
    """Generate a QR code for login. Returns qrcode_key and url."""
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/generate",
            headers={"User-Agent": _UA},
        )
        data = resp.json()
    if data.get("code") != 0:
        return {"error": data.get("message", "QR generate failed")}
    return {
        "qrcode_key": data["data"]["qrcode_key"],
        "url": data["data"]["url"],
    }


async def qr_poll(qrcode_key: str) -> dict:
    """
    Poll QR code scan status.
    Returns:
      code 86101 = not scanned
      code 86090 = scanned, not confirmed
      code 86038 = expired
      code 0     = success (includes cookies)
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(
            "https://passport.bilibili.com/x/passport-login/web/qrcode/poll",
            params={"qrcode_key": qrcode_key},
            headers={"User-Agent": _UA},
        )
        data = resp.json()
        poll_code = data.get("data", {}).get("code", -1)

        result = {
            "status_code": poll_code,
            "message": data.get("data", {}).get("message", ""),
        }

        if poll_code == 0:
            cookies = dict(resp.cookies)
            result["cookies"] = {
                "sessdata": cookies.get("SESSDATA", ""),
                "bili_jct": cookies.get("bili_jct", ""),
                "DedeUserID": cookies.get("DedeUserID", ""),
                "DedeUserID__ckMd5": cookies.get("DedeUserID__ckMd5", ""),
            }
            result["refresh_token"] = data.get("data", {}).get("refresh_token", "")

        return result


async def qr_login_save(qrcode_key: str, account_name: str) -> dict:
    """Poll QR code and save account if login succeeds."""
    poll_result = await qr_poll(qrcode_key)
    if poll_result["status_code"] != 0:
        return poll_result

    cookies = poll_result["cookies"]
    sessdata = cookies.get("sessdata", "")
    bili_jct = cookies.get("bili_jct", "")
    uid_str = cookies.get("DedeUserID", "")
    ckmd5 = cookies.get("DedeUserID__ckMd5", "")
    refresh_token = poll_result.get("refresh_token", "")

    if not sessdata or not bili_jct:
        return {"status_code": -1, "message": "Login succeeded but cookies missing"}

    uid = int(uid_str) if uid_str else None

    # Check if account with this uid already exists
    if uid:
        existing = await execute_query(
            "SELECT id FROM accounts WHERE uid = ?", (uid,)
        )
        if existing:
            account_id = existing[0]["id"]
            await execute_query(
                """UPDATE accounts SET sessdata = ?, bili_jct = ?, dedeuserid_ckmd5 = ?,
                   refresh_token = ?, status = 'valid', last_check_at = strftime('%Y-%m-%dT%H:%M:%fZ','now'),
                   name = CASE WHEN name LIKE 'QR_%' THEN ? ELSE name END
                   WHERE id = ?""",
                (sessdata, bili_jct, ckmd5, refresh_token, account_name, account_id),
            )
            await invalidate_cache("active_accounts")
            # Fetch buvid cookies
            buvid = await _fetch_buvid(sessdata, bili_jct)
            if buvid["buvid3"] or buvid["buvid4"]:
                await execute_query(
                    "UPDATE accounts SET buvid3 = ?, buvid4 = ? WHERE id = ?",
                    (buvid["buvid3"], buvid["buvid4"], account_id),
                )
            logger.info("[Auth] QR login updated existing account %d (uid=%s)", account_id, uid)
            rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
            safe_account = {k: v for k, v in rows[0].items() if k not in _SENSITIVE_FIELDS}
            return {"status_code": 0, "message": "登录成功（已更新）", "account": safe_account}

    from backend.services.account_service import create_account
    account = await create_account(
        name=account_name,
        sessdata=sessdata,
        bili_jct=bili_jct,
        dedeuserid_ckmd5=ckmd5,
    )
    if uid:
        await execute_query(
            "UPDATE accounts SET uid = ?, refresh_token = ?, status = 'valid', last_check_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?",
            (uid, refresh_token, account["id"]),
        )
        await invalidate_cache("active_accounts")
    # Fetch buvid cookies
    buvid = await _fetch_buvid(sessdata, bili_jct)
    if buvid["buvid3"] or buvid["buvid4"]:
        await execute_query(
            "UPDATE accounts SET buvid3 = ?, buvid4 = ? WHERE id = ?",
            (buvid["buvid3"], buvid["buvid4"], account["id"]),
        )
    logger.info("[Auth] QR login created account %d (uid=%s)", account["id"], uid)
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account["id"],))
    safe_account = {k: v for k, v in rows[0].items() if k not in _SENSITIVE_FIELDS}
    return {"status_code": 0, "message": "登录成功（新账号）", "account": safe_account}


async def check_cookie_refresh_needed(account_id: int) -> dict:
    """Check if an account's cookies need refreshing."""
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return {"error": "Account not found"}
    account = rows[0]

    cookies = {"SESSDATA": account["sessdata"], "bili_jct": account["bili_jct"]}
    async with httpx.AsyncClient(cookies=cookies, timeout=10.0) as client:
        resp = await client.get(
            "https://passport.bilibili.com/x/passport-login/web/cookie/info",
            params={"csrf": account["bili_jct"]},
            headers={"User-Agent": _UA, "Referer": "https://www.bilibili.com/"},
        )
        data = resp.json()

    if data.get("code") != 0:
        return {"needs_refresh": True, "reason": "session_invalid", "message": data.get("message", "")}

    needs_refresh = data.get("data", {}).get("refresh", False)
    timestamp = data.get("data", {}).get("timestamp", 0)
    return {
        "needs_refresh": needs_refresh,
        "reason": "cookie_expiring" if needs_refresh else "ok",
        "timestamp": timestamp,
    }


async def refresh_account_cookies(account_id: int) -> dict:
    """
    Refresh an account's cookies using the stored refresh_token.
    Flow:
    1. Get timestamp from cookie/info
    2. Fetch correspondPath page to extract refresh_csrf
    3. POST cookie/refresh with refresh_csrf + refresh_token
    4. Confirm refresh to invalidate old token
    5. Update DB with new credentials
    """
    rows = await execute_query("SELECT * FROM accounts WHERE id = ?", (account_id,))
    if not rows:
        return {"success": False, "message": "Account not found"}
    account = rows[0]

    refresh_token = account.get("refresh_token", "")
    if not refresh_token:
        return {"success": False, "message": "No refresh_token stored. Re-login via QR code required."}

    cookies = {"SESSDATA": account["sessdata"], "bili_jct": account["bili_jct"]}
    headers = {"User-Agent": _UA, "Referer": "https://www.bilibili.com/"}

    try:
        async with httpx.AsyncClient(cookies=cookies, headers=headers, timeout=10.0) as client:
            # Step 1: Get cookie info
            info_resp = await client.get(
                "https://passport.bilibili.com/x/passport-login/web/cookie/info",
                params={"csrf": account["bili_jct"]},
            )
            info_data = info_resp.json()
            if info_data.get("code") != 0:
                return {"success": False, "message": f"Cookie info failed: {info_data.get('message')}"}

            if not info_data.get("data", {}).get("refresh"):
                return {"success": True, "message": "Cookies still valid, no refresh needed"}

            timestamp = info_data["data"]["timestamp"]

            # Step 2: Get refresh_csrf from correspond page
            correspond_resp = await client.get(
                f"https://www.bilibili.com/correspond/1/{timestamp}",
            )
            match = re.search(r'<div\s+id="1-name">([^<]+)</div>', correspond_resp.text)
            if not match:
                return {"success": False, "message": "Failed to extract refresh_csrf"}
            refresh_csrf = match.group(1)

            # Step 3: Refresh cookies
            refresh_resp = await client.post(
                "https://passport.bilibili.com/x/passport-login/web/cookie/refresh",
                data={
                    "csrf": account["bili_jct"],
                    "refresh_csrf": refresh_csrf,
                    "source": "main_web",
                    "refresh_token": refresh_token,
                },
            )
            refresh_data = refresh_resp.json()
            if refresh_data.get("code") != 0:
                return {"success": False, "message": f"Refresh failed: {refresh_data.get('message')}"}

            new_cookies = dict(refresh_resp.cookies)
            new_sessdata = new_cookies.get("SESSDATA", "")
            new_bili_jct = new_cookies.get("bili_jct", "")
            new_refresh_token = refresh_data.get("data", {}).get("refresh_token", "")

            if not new_sessdata or not new_bili_jct:
                return {"success": False, "message": "Refresh succeeded but new cookies missing"}

            # Step 4: Confirm refresh
            confirm_cookies = {"SESSDATA": new_sessdata, "bili_jct": new_bili_jct}
            async with httpx.AsyncClient(cookies=confirm_cookies, headers=headers, timeout=10.0) as cc:
                await cc.post(
                    "https://passport.bilibili.com/x/passport-login/web/confirm/refresh",
                    data={"csrf": new_bili_jct, "refresh_token": refresh_token},
                )

            # Step 5: Update DB
            await execute_query(
                """UPDATE accounts SET sessdata = ?, bili_jct = ?, refresh_token = ?,
                   status = 'valid', last_check_at = strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE id = ?""",
                (new_sessdata, new_bili_jct, new_refresh_token, account_id),
            )
            await invalidate_cache("active_accounts")
            logger.info("[Auth] Cookies refreshed for account %d", account_id)
            return {"success": True, "message": "Cookies refreshed successfully"}

    except Exception as e:
        logger.error("[Auth] Cookie refresh failed for account %d: %s", account_id, e)
        return {"success": False, "message": str(e)}
