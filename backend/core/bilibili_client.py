import httpx
import json
import math
import random
import asyncio
import time
from backend.core.wbi_sign import BilibiliSign
from backend.core.bilibili_auth import BilibiliAuth
from backend.config import HTTP_TIMEOUT, MAX_RETRIES, USER_AGENTS
from backend.logger import logger


def _human_delay(min_s: float, max_s: float) -> float:
    """Generate a human-like delay using log-normal distribution (long-tail)."""
    mu = math.log((min_s + max_s) / 2)
    sigma = 0.5
    delay = random.lognormvariate(mu, sigma)
    return max(min_s, min(delay, max_s * 1.5))


class BilibiliClient:
    """Consolidated client for Bilibili reporting and interaction with anti-detection."""
    
    def __init__(self, auth: BilibiliAuth, account_index: int = 0):
        self.auth = auth
        self.account_index = account_index
        self.cookies = auth.get_cookies(account_index)

        # Anti-detection: randomize request fingerprint
        ua = random.choice(USER_AGENTS)

        # Randomize Accept-Encoding combinations
        encodings = ["gzip", "deflate", "br"]
        random.shuffle(encodings)
        accept_encoding = ", ".join(encodings[:random.randint(2, 3)])

        # Extract platform from UA for Sec-Ch-Ua-Platform
        if "Windows" in ua:
            platform = '"Windows"'
        elif "Macintosh" in ua:
            platform = '"macOS"'
        elif "Linux" in ua or "X11" in ua:
            platform = '"Linux"'
        else:
            platform = '"Windows"'

        # Generate random Chrome version for Sec-Ch-Ua (129-131 range)
        chrome_version = random.randint(129, 131)
        sec_ch_ua = f'"Chromium";v="{chrome_version}", "Not_A Brand";v="24"'

        self.headers = {
            "User-Agent": ua,
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Accept-Encoding": accept_encoding,
            "Connection": "keep-alive",
            "DNT": str(random.randint(0, 1)),
            "Sec-Ch-Ua": sec_ch_ua,
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": platform,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }
        self._client = httpx.AsyncClient(cookies=self.cookies, headers=self.headers, timeout=HTTP_TIMEOUT)

    async def close(self):
        """Close the underlying httpx client."""
        await self._client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    async def _request(self, method: str, url: str, params: dict = None, data: dict = None, sign: bool = False, retries: int = None):
        """Internal request helper with rate-limit handling and retries."""
        if retries is None: retries = MAX_RETRIES
        if params is None: params = {}
        if data is None: data = {}

        account_name = self.auth.accounts[self.account_index]["name"]

        # Auto-refresh WBI keys if stale and signing is needed
        if sign and BilibiliAuth.wbi_keys_stale():
            logger.info("[%s] WBI keys stale, refreshing...", account_name)
            await self.auth.refresh_wbi_keys()

        if sign:
            img_key, sub_key = self.auth.get_wbi_keys()
            signer = BilibiliSign(img_key, sub_key)
            params = signer.sign(params)

        last_error = None
        for attempt in range(retries):
            try:
                if method == "POST":
                    data["csrf"] = self.cookies.get("bili_jct", "")
                    resp = await self._client.post(url, params=params, data=data)
                else:
                    resp = await self._client.get(url, params=params)
                
                res_json = resp.json()
                code = res_json.get("code")

                # -412: Too many requests — exponential backoff
                if code == -412:
                    wait_time = 5 * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning("[%s] Rate limited (-412). Backoff %.1fs...", account_name, wait_time)
                    await asyncio.sleep(wait_time)
                    continue

                # -352: Risk control — fail fast, don't block for 5 minutes
                if code == -352:
                    logger.warning("[%s] Risk control (-352). Account flagged, skipping.", account_name)
                    return res_json

                # -101: Not logged in — mark and stop retrying
                if code == -101:
                    logger.error("[%s] Not logged in (-101). Account may be invalid.", account_name)
                    return res_json

                # -799: Human verification required — stop immediately
                if code == -799:
                    logger.error("[%s] Human verification required (-799). Account flagged.", account_name)
                    return res_json

                # 862/101: Other frequency limits
                if code in (862, 101):
                    wait_time = 5 * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning("[%s] Frequency limit (code %s). Backoff %.1fs...", account_name, code, wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                
                return res_json
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                wait_time = (attempt + 1) * 2
                logger.warning("[%s] Network error: %s. Retrying in %ds...", account_name, e, wait_time)
                await asyncio.sleep(wait_time)
        return {"code": -999, "message": f"Max retries reached: {last_error or 'rate limits'}"}

    async def _post(self, url: str, params: dict = None, data: dict = None, sign: bool = False):
        return await self._request("POST", url, params, data, sign)

    async def _get(self, url: str, params: dict = None, sign: bool = False):
        return await self._request("GET", url, params, None, sign)

    async def get_video_info(self, bvid: str):
        """Gets video info including aid from bvid."""
        url = "https://api.bilibili.com/x/web-interface/view"
        params = {"bvid": bvid}
        return await self._get(url, params=params)

    async def get_comments(self, oid: int, type_code: int = 1, pn: int = 1, ps: int = 20):
        """Fetches a page of comments."""
        url = "https://api.bilibili.com/x/v2/reply"
        params = {
            "type": type_code,
            "oid": oid,
            "pn": pn,
            "ps": ps,
            "sort": 0 # 0 for time, 1 for like, 2 for hot
        }
        return await self._get(url, params=params)

    async def report_user(self, mid: int, reason_v2: int = 4, reason: int = 1):
        """
        Reports a user via space.bilibili.com/ajax/report/add.
        reason: content type - 1=avatar, 2=nickname, 3=signature
        reason_v2: report category - 4=personal_attack, etc.
        Uses _request_cross_domain to get retry logic on the cross-subdomain request.
        """
        url = "https://space.bilibili.com/ajax/report/add"
        data = {
            "mid": mid,
            "reason": reason,
            "reason_v2": reason_v2,
        }
        result = await self._request_cross_domain(
            url, data=data,
            referer=f"https://space.bilibili.com/{mid}/",
            origin="https://space.bilibili.com",
        )
        if result.get("status") is True:
            return {"code": 0, "message": result.get("data", "OK")}
        return {"code": -1, "message": result.get("data", "Unknown error")}

    async def _request_cross_domain(self, url: str, data: dict = None, referer: str = "", origin: str = "", retries: int = None):
        """Request helper for cross-subdomain endpoints (e.g. space.bilibili.com) with retry logic."""
        if retries is None: retries = MAX_RETRIES
        if data is None: data = {}

        account_name = self.auth.accounts[self.account_index]["name"]
        bili_jct = self.cookies.get("bili_jct", "")
        data["csrf"] = bili_jct

        # Properly escape cookie values to handle special characters
        from urllib.parse import quote
        cookie_parts = [f"{k}={quote(str(v), safe='')}" for k, v in self.cookies.items()]
        cookie_header = "; ".join(cookie_parts)

        headers = {
            "User-Agent": self._client.headers.get("User-Agent", ""),
            "Referer": referer,
            "Origin": origin,
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie_header,
        }

        last_error = None
        for attempt in range(retries):
            try:
                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as tmp_client:
                    resp = await tmp_client.post(url, data=data, headers=headers)
                res_json = resp.json()

                # Check for Bilibili error codes that warrant retry
                code = res_json.get("code")
                if code == -412:
                    wait_time = 5 * (2 ** attempt) + random.uniform(0, 2)
                    logger.warning("[%s] Rate limited (-412). Backoff %.1fs...", account_name, wait_time)
                    await asyncio.sleep(wait_time)
                    continue
                # -352: Risk control — fail fast, don't block for 5 minutes
                if code == -352:
                    logger.warning("[%s] Risk control (-352). Account flagged, skipping.", account_name)
                    return res_json

                return res_json
            except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as e:
                last_error = e
                wait_time = (attempt + 1) * 2
                logger.warning("[%s] Network error: %s. Retrying in %ds...", account_name, e, wait_time)
                await asyncio.sleep(wait_time)
        return {"status": False, "data": f"Max retries reached: {last_error or 'rate limits'}"}

    async def report_comment(self, oid: int, rpid: int, reason: int, content: str = "", type_code: int = 1, bvid: str = ""):
        """
        Reports a comment.
        type_code: 1 for video, 6 for dynamic, 12 for article, etc.
        reason: 1 (Ad), 2 (Porn), 3 (Spam), 7 (Personal Attack), etc.
        """
        if bvid:
            self._client.headers["Referer"] = f"https://www.bilibili.com/video/{bvid}/"
        url = "https://api.bilibili.com/x/v2/reply/report"
        data = {
            "type": type_code,
            "oid": oid,
            "rpid": rpid,
            "reason": reason,
            "content": content
        }
        result = await self._post(url, data=data)
        self._client.headers["Referer"] = "https://www.bilibili.com/"
        return result

    async def report_video(self, aid: int, reason: int, content: str = "", bvid: str = ""):
        """
        Reports a video.
        aid: Archive ID (numeric cid/avid)
        reason: 1 (Ad), 2 (Porn), etc.
        """
        # Dynamic Referer to mimic browsing the actual video page
        if bvid:
            self._client.headers["Referer"] = f"https://www.bilibili.com/video/{bvid}/"
        url = "https://api.bilibili.com/x/web-interface/archive/report"
        data = {
            "aid": aid,
            "reason": reason,
            "content": content
        }
        result = await self._post(url, data=data)
        self._client.headers["Referer"] = "https://www.bilibili.com/"
        return result

    async def send_private_message(self, receiver_id: int, content: str):
        """Sends a private message to a user."""
        url = "https://api.vc.bilibili.com/web_im/v1/web_im/send_msg"
        data = {
            "msg[sender_uid]": self.auth.accounts[self.account_index].get("uid", 0), # Optional if cookies are valid
            "msg[receiver_id]": receiver_id,
            "msg[receiver_type]": 1,
            "msg[msg_type]": 1,
            "msg[content]": json.dumps({"content": content}),
            "msg[dev_id]": self.cookies.get("buvid3", ""),
            "msg[timestamp]": int(time.time()),
            "csrf": self.cookies.get("bili_jct", "")
        }
        return await self._post(url, data=data)

    async def get_recent_sessions(self):
        """Fetches recent private message sessions."""
        url = "https://api.vc.bilibili.com/web_im/v1/web_im/get_sessions"
        params = {
            "mobi_app": "web",
            "page_size": 20,
            "last_ts": int(time.time() * 1000)
        }
        return await self._get(url, params=params)
