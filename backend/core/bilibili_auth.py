import asyncio
import json
import os
import time
import httpx

from backend.logger import logger

# Module-level WBI key cache shared across all BilibiliAuth instances
_wbi_cache: dict = {"img_key": "", "sub_key": "", "refreshed_at": 0.0}
_wbi_refresh_lock = asyncio.Lock()
_WBI_TTL_SECONDS = 3600  # Refresh WBI keys every 1 hour


class BilibiliAuth:
    """Manages Bilibili credentials and WBI keys."""
    
    def __init__(self, credentials_path: str = "credentials.json"):
        self.credentials_path = credentials_path
        self.accounts = self._load_accounts()
        self.wbi_keys = {"img_key": "", "sub_key": ""}

    def _load_accounts(self) -> list[dict]:
        if os.path.exists(self.credentials_path):
            with open(self.credentials_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def save_accounts(self):
        with open(self.credentials_path, "w", encoding="utf-8") as f:
            json.dump(self.accounts, f, indent=4)

    def add_account(self, sessdata: str, bili_jct: str, buvid3: str = "", name: str = "Default"):
        """Add a new Bilibili account credential."""
        self.accounts.append({
            "name": name,
            "SESSDATA": sessdata,
            "bili_jct": bili_jct,
            "buvid3": buvid3
        })
        self.save_accounts()

    def get_cookies(self, index: int = 0) -> dict:
        """Returns cookies for the specified account index."""
        if 0 <= index < len(self.accounts):
            acc = self.accounts[index]
            cookies = {
                "SESSDATA": acc["SESSDATA"],
                "bili_jct": acc["bili_jct"],
                "buvid3": acc.get("buvid3", ""),
            }
            if acc.get("buvid4"):
                cookies["buvid4"] = acc["buvid4"]
            if acc.get("uid"):
                cookies["DedeUserID"] = str(acc["uid"])
            if acc.get("dedeuserid_ckmd5"):
                cookies["DedeUserID__ckMd5"] = acc["dedeuserid_ckmd5"]
            return cookies
        return {}

    async def refresh_wbi_keys(self) -> bool:
        """Fetches fresh WBI keys from Bilibili's nav API and updates module cache."""
        global _wbi_cache

        async with _wbi_refresh_lock:
            # Double-check to avoid redundant refreshes
            if not self.wbi_keys_stale():
                return True

            url = "https://api.bilibili.com/x/web-interface/nav"

            cookies = self.get_cookies(0) if self.accounts else {}

            try:
                async with httpx.AsyncClient(cookies=cookies, timeout=10.0) as client:
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "https://www.bilibili.com/"
                    }
                    resp = await client.get(url, headers=headers)
                    data = resp.json()
                    if data["code"] == 0:
                        wbi_img = data["data"].get("wbi_img")
                        if not wbi_img:
                            return False
                        img_url = wbi_img["img_url"]
                        sub_url = wbi_img["sub_url"]

                        img_key = img_url.split("/")[-1].split(".")[0]
                        sub_key = sub_url.split("/")[-1].split(".")[0]

                        # Update module-level cache
                        _wbi_cache["img_key"] = img_key
                        _wbi_cache["sub_key"] = sub_key
                        _wbi_cache["refreshed_at"] = time.monotonic()

                        # Update instance keys
                        self.wbi_keys["img_key"] = img_key
                        self.wbi_keys["sub_key"] = sub_key
                        logger.info("WBI Keys refreshed: %s...", img_key[:4])
                        return True
                    elif data["code"] == -101:
                        logger.warning("WBI refresh failed: not logged in (code -101)")
                        return False
            except Exception as e:
                logger.error("WBI refresh failed: %s", e)
            return False

    def get_wbi_keys(self) -> tuple[str, str]:
        """Return WBI keys, preferring module cache if instance keys are empty."""
        img = self.wbi_keys.get("img_key") or _wbi_cache.get("img_key", "")
        sub = self.wbi_keys.get("sub_key") or _wbi_cache.get("sub_key", "")
        return img, sub

    @staticmethod
    def wbi_keys_stale() -> bool:
        """Check if the module-level WBI keys cache has expired."""
        if not _wbi_cache["img_key"]:
            return True
        return (time.monotonic() - _wbi_cache["refreshed_at"]) > _WBI_TTL_SECONDS

    @classmethod
    def from_db_account(cls, account_dict: dict, wbi_keys: dict = None) -> "BilibiliAuth":
        """Create a BilibiliAuth instance from a database account dict."""
        instance = cls.__new__(cls)
        instance.credentials_path = ""
        instance.accounts = [{
            "name": account_dict.get("name", ""),
            "SESSDATA": account_dict.get("sessdata", ""),
            "bili_jct": account_dict.get("bili_jct", ""),
            "buvid3": account_dict.get("buvid3", ""),
            "buvid4": account_dict.get("buvid4", ""),
            "dedeuserid_ckmd5": account_dict.get("dedeuserid_ckmd5", ""),
            "uid": account_dict.get("uid", 0),
        }]
        instance.wbi_keys = wbi_keys or {"img_key": "", "sub_key": ""}
        return instance
