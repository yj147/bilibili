import re
import httpx

async def resolve_url(url: str) -> str:
    """Follows redirects for short URLs like b23.tv."""
    if "b23.tv" in url:
        async with httpx.AsyncClient() as client:
            resp = await client.head(url, follow_redirects=True)
            return str(resp.url)
    return url

def parse_bilibili_input(input_str: str):
    """
    Parses input string to identify if it's a BV, AID, UID, or URL.
    Returns: {'type': 'video|user', 'id': 'BVxxx|12345'}
    """
    # 1. Check for BV
    bv_match = re.search(r"(BV[a-zA-Z0-9]+)", input_str)
    if bv_match:
        return {"type": "video", "id": bv_match.group(1)}
    
    # 2. Check for Space/UID
    uid_match = re.search(r"space\.bilibili\.com/(\d+)", input_str)
    if uid_match:
        return {"type": "user", "id": int(uid_match.group(1))}
    
    # 3. Check for raw numeric UID or AID (ambiguous, but we'll try)
    if input_str.isdigit():
        return {"type": "unknown_id", "id": int(input_str)}
        
    return None
