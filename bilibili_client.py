import httpx
import random
import asyncio
from wbi_sign import BilibiliSign
from bilibili_auth import BilibiliAuth

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0"
]

class BilibiliClient:
    """Consolidated client for Bilibili reporting and interaction with anti-detection."""
    
    def __init__(self, auth: BilibiliAuth, account_index: int = 0):
        self.auth = auth
        self.account_index = account_index
        self.cookies = auth.get_cookies(account_index)
        self.headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://www.bilibili.com/",
            "Origin": "https://www.bilibili.com",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
        }

    async def _request(self, method: str, url: str, params: dict = None, data: dict = None, sign: bool = False, retries: int = 3):
        """Internal request helper with rate-limit handling and retries."""
        if params is None: params = {}
        if data is None: data = {}
        
        if sign:
            img_key, sub_key = self.auth.get_wbi_keys()
            signer = BilibiliSign(img_key, sub_key)
            params = signer.sign(params)

        for attempt in range(retries):
            async with httpx.AsyncClient(cookies=self.cookies, headers=self.headers, timeout=10.0) as client:
                if method == "POST":
                    # Add CSRF token for POST requests
                    data["csrf"] = self.cookies.get("bili_jct", "")
                    resp = await client.post(url, params=params, data=data)
                else:
                    resp = await client.get(url, params=params)
                
                res_json = resp.json()
                
                # Rate limit / Frequency control detection
                if res_json.get("code") in [-412, 862, 101]: # 412 is common for frequency
                    wait_time = (attempt + 1) * random.uniform(30, 60)
                    print(f"[{self.auth.accounts[self.account_index]['name']}] Frequency limit hit. Sleeping for {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
                
                return res_json
        return {"code": -999, "message": "Max retries reached due to rate limits"}

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

    async def report_user(self, mid: int, reason: str, reason_id: int = 1):
        """
        Reports a user (space report).
        reason_id: 1 (Content), 2 (Avatar/Name), 3 (Spam), etc.
        """
        url = "https://api.bilibili.com/x/space/report"
        data = {
            "mid": mid,
            "reason": reason_id,
            "content": reason,
            "csrf": self.cookies.get("bili_jct", "")
        }
        return await self._post(url, data=data)

    async def report_comment(self, oid: int, rpid: int, reason: int, content: str = "", type_code: int = 1):
        """
        Reports a comment.
        type_code: 1 for video, 6 for dynamic, 12 for article, etc.
        reason: 1 (Ad), 2 (Porn), 3 (Spam), 7 (Personal Attack), etc.
        """
        url = "https://api.bilibili.com/x/v2/reply/report"
        data = {
            "type": type_code,
            "oid": oid,
            "rpid": rpid,
            "reason": reason,
            "content": content
        }
        return await self._post(url, data=data)

    async def report_video(self, aid: int, reason: int, content: str = ""):
        """
        Reports a video.
        aid: Archive ID (numeric cid/avid)
        reason: 1 (Ad), 2 (Porn), etc. (Video report codes may differ from comment codes)
        """
        url = "https://api.bilibili.com/x/web-interface/archive/report"
        data = {
            "aid": aid,
            "reason": reason,
            "content": content
        }
        return await self._post(url, data=data)

    async def send_private_message(self, receiver_id: int, content: str):
        """Sends a private message to a user."""
        url = "https://api.vc.bilibili.com/web_im/v1/web_im/send_msg"
        data = {
            "msg[sender_uid]": self.auth.accounts[self.account_index].get("uid", 0), # Optional if cookies are valid
            "msg[receiver_id]": receiver_id,
            "msg[receiver_type]": 1,
            "msg[msg_type]": 1,
            "msg[content]": f'{{"content":"{content}"}}',
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
