import asyncio
import random
from bilibili_client import BilibiliClient
from bilibili_auth import BilibiliAuth

class ReportingManager:
    """Manages mass reporting using multiple accounts."""
    
    def __init__(self, auth: BilibiliAuth):
        self.auth = auth

    async def mass_report_comment(self, oid: int, rpid: int, reason: int, content: str = ""):
        """Reports a comment using all available accounts with random delays."""
        results = []
        for i in range(len(self.auth.accounts)):
            client = BilibiliClient(self.auth, account_index=i)
            print(f"Reporting comment {rpid} using account: {self.auth.accounts[i]['name']}")
            
            try:
                res = await client.report_comment(oid, rpid, reason, content)
                results.append({"account": self.auth.accounts[i]['name'], "result": res})
                
                # Randomized delay to avoid detection
                wait = random.uniform(2, 5)
                await asyncio.sleep(wait)
            except Exception as e:
                results.append({"account": self.auth.accounts[i]['name'], "error": str(e)})
        
        return results

    async def mass_report_video(self, aid: int, reason: int, content: str = ""):
        """Reports a video using all available accounts."""
        results = []
        for i in range(len(self.auth.accounts)):
            client = BilibiliClient(self.auth, account_index=i)
            print(f"Reporting video {aid} using account: {self.auth.accounts[i]['name']}")
            
            try:
                res = await client.report_video(aid, reason, content)
                results.append({"account": self.auth.accounts[i]['name'], "result": res})
                
                wait = random.uniform(2, 5)
                await asyncio.sleep(wait)
            except Exception as e:
                results.append({"account": self.auth.accounts[i]['name'], "error": str(e)})
        
        return results

    async def mass_report_user(self, mid: int, reason: str, reason_id: int = 1):
        """Reports a user space using all available accounts."""
        results = []
        for i in range(len(self.auth.accounts)):
            client = BilibiliClient(self.auth, account_index=i)
            print(f"Reporting user {mid} using account: {self.auth.accounts[i]['name']}")
            try:
                res = await client.report_user(mid, reason, reason_id)
                results.append({"account": self.auth.accounts[i]['name'], "result": res})
                wait = random.uniform(2, 5)
                await asyncio.sleep(wait)
            except Exception as e:
                results.append({"account": self.auth.accounts[i]['name'], "error": str(e)})
        return results

    async def mass_report_comment_section(self, oid: int, reason: int, content: str = "", type_code: int = 1, max_comments: int = 10):
        """Fetches comments and reports each using multiple accounts."""
        # 1. Fetch some comments first using the first account
        client = BilibiliClient(self.auth, account_index=0)
        comments_res = await client.get_comments(oid, type_code, ps=max_comments)
        
        if comments_res.get("code") != 0:
            return {"error": "Could not fetch comments", "detail": comments_res}
            
        rpids = [r["rpid"] for r in comments_res.get("data", {}).get("replies", [])]
        print(f"Found {len(rpids)} comments to report in section {oid}")
        
        all_results = []
        for rpid in rpids:
            res = await self.mass_report_comment(oid, rpid, reason, content)
            all_results.append({"rpid": rpid, "results": res})
            # Small break between different comments
            await asyncio.sleep(random.uniform(5, 10))
            
        return all_results
