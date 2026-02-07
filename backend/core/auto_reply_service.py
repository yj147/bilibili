import asyncio
import time
import json
import os
from backend.core.bilibili_client import BilibiliClient
from backend.core.bilibili_auth import BilibiliAuth

class AutoReplyService:
    """Polls for new private messages and sends automated replies for all configured accounts."""
    
    def __init__(self, auth: BilibiliAuth, config_path: str = "reply_config.json"):
        self.auth = auth
        self.config_path = config_path
        self.replies = self._load_config()
        self.running = False
        self.last_timestamps = {} # account_index -> last_ts

    def _load_config(self) -> dict:
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"default": "你好，我现在不在位子，稍后回复。", "keywords": {}}

    async def _poll_account(self, account_index: int, interval: int):
        client = BilibiliClient(self.auth, account_index)
        account_name = self.auth.accounts[account_index]['name']
        print(f"Starting auto-reply for account: {account_name}")
        
        self.last_timestamps[account_index] = int(time.time())
        
        while self.running:
            try:
                sessions = await client.get_recent_sessions()
                if sessions.get("code") == 0:
                    for session in sessions.get("data", {}).get("session_list", []):
                        if session["last_msg"]["timestamp"] > self.last_timestamps[account_index]:
                            uid = session["talker_id"]
                            
                            # Skip if message is from ourselves
                            if str(uid) == str(self.auth.accounts[account_index].get("uid", "")):
                                continue
                                
                            # Basic content check
                            last_msg = session.get("last_msg", {})
                            msg_content = last_msg.get("content", "")
                            
                            # Simple keyword matching
                            reply_text = self.replies["default"]
                            for kw, text in self.replies.get("keywords", {}).items():
                                if kw in str(msg_content):
                                    reply_text = text
                                    break
                            
                            print(f"[{account_name}] Sending auto-reply to {uid}: {reply_text}")
                            await client.send_private_message(uid, reply_text)
                
                self.last_timestamps[account_index] = int(time.time())
            except Exception as e:
                print(f"[{account_name}] Auto-reply error: {e}")
            
            await asyncio.sleep(interval)

    async def start(self, interval: int = 30):
        """Starts polling loops for all accounts."""
        if not self.auth.accounts:
            print("No accounts available for auto-reply.")
            return
            
        self.running = True
        tasks = []
        for i in range(len(self.auth.accounts)):
            tasks.append(self._poll_account(i, interval))
        
        await asyncio.gather(*tasks)

    def stop(self):
        self.running = False