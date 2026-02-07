import json
import os
import httpx
import re

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
            return {
                "SESSDATA": acc["SESSDATA"],
                "bili_jct": acc["bili_jct"],
                "buvid3": acc.get("buvid3", "")
            }
        return {}

    async def refresh_wbi_keys(self):
        """Fetches fresh WBI keys from Bilibili's nav API."""
        url = "https://api.bilibili.com/x/web-interface/nav"
        
        # Use cookies from the first account to ensure we get valid keys
        cookies = self.get_cookies(0) if self.accounts else {}
        
        async with httpx.AsyncClient(cookies=cookies) as client:
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
                
                # Extract keys from URLs (filename without extension)
                self.wbi_keys["img_key"] = img_url.split("/")[-1].split(".")[0]
                self.wbi_keys["sub_key"] = sub_url.split("/")[-1].split(".")[0]
                print(f"WBI Keys refreshed: {self.wbi_keys['img_key'][:4]}...")
                return True
        return False

    def get_wbi_keys(self) -> tuple[str, str]:
        return self.wbi_keys["img_key"], self.wbi_keys["sub_key"]

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
            "uid": account_dict.get("uid", 0),
        }]
        instance.wbi_keys = wbi_keys or {"img_key": "", "sub_key": ""}
        return instance
