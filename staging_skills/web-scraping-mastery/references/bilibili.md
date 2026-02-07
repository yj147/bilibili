# B站 (Bilibili) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers WBI signature, search/comment APIs, and retry strategies.

## Table of Contents
- [WBI Signature System](#wbi-signature-system)
- [API Endpoints](#api-endpoints)
- [Retry Strategy](#retry-strategy)
- [Search with Time Range](#search-with-time-range)
- [Cookie & Session](#cookie--session)

---

## WBI Signature System

Bilibili uses a WBI (Web Browser Interface) signature to protect API endpoints.

### Key Extraction

```python
async def get_wbi_keys(page) -> tuple[str, str]:
    """Extract img_key and sub_key from localStorage."""
    wbi_img_urls = await page.evaluate(
        "() => localStorage.getItem('wbi_img_urls')"
    )
    # wbi_img_urls format: "img_url,sub_url"
    # Extract hash from URL path: .../wbi/xxx.png -> xxx is the key
    img_key = extract_key_from_url(wbi_img_urls.split(",")[0])
    sub_key = extract_key_from_url(wbi_img_urls.split(",")[1])
    return img_key, sub_key
```

### Signature Computation

```python
class BilibiliSign:
    """WBI parameter signing."""
    MIXIN_KEY_ENC_TAB = [...]  # 64-element shuffle table

    def __init__(self, img_key: str, sub_key: str):
        raw = img_key + sub_key
        self.mixin_key = "".join(raw[i] for i in self.MIXIN_KEY_ENC_TAB)[:32]

    def sign(self, params: dict) -> dict:
        params["wts"] = int(time.time())
        # Sort params, URL-encode, append mixin_key, MD5 hash
        query = urlencode(sorted(params.items()))
        params["w_rid"] = md5((query + self.mixin_key).encode()).hexdigest()
        return params
```

**Flow**:
1. Extract `img_key` + `sub_key` from localStorage `wbi_img_urls`
2. Build `mixin_key` via shuffle table (first 32 chars)
3. Add `wts` (timestamp) to params
4. Sort params, URL-encode, concatenate mixin_key
5. MD5 hash → `w_rid` parameter

**Refresh**: WBI keys rotate periodically. Re-extract from localStorage when requests start failing.

---

## API Endpoints

| Endpoint | Purpose | Signature |
|----------|---------|----------|
| `/x/web-interface/wbi/search/type` | Search by type | WBI (w_rid + wts) |
| `/x/v2/reply/wbi/main` | Video comments | WBI (w_rid + wts) |
| `/x/v2/reply/reply` | Sub-comments | WBI (w_rid + wts) |
| `/x/web-interface/card` | User card/profile | None |
| `/x/polymer/web-dynamic/v1/feed/space` | User dynamics | WBI |
| `/x/space/wbi/arc/search` | User videos | WBI |
| `/x/relation/stat` | Followers/following count | None |

### Search Parameters

```python
search_params = {
    "search_type": "video",  # or "bili_user", "media_bangumi"
    "keyword": "search term",
    "page": 1,
    "page_size": 20,
    "order": "",       # "totalrank", "click", "pubdate", "dm"
    "duration": "",    # "1" (0-10min), "2" (10-30min), "3" (30-60min), "4" (60+min)
}
```

---

## Retry Strategy

Bilibili uses exponential backoff with jitter:

```python
import random

async def request_with_retry(url, params, max_retries=3):
    for attempt in range(max_retries):
        resp = await session.get(url, params=params)
        data = resp.json()
        if data.get("code") == 0:
            return data
        # Exponential backoff: 5*2^attempt + random jitter
        wait = 5 * (2 ** attempt) + random.uniform(0, 2)
        await asyncio.sleep(wait)
    raise MaxRetriesExceeded()
```

| Response Code | Meaning | Action |
|---------------|---------|--------|
| 0 | Success | Process data |
| -101 | Not logged in | Re-login |
| -352 | Risk control triggered | Switch IP, wait 5+ min |
| -400 | Invalid request | Check parameters |
| -412 | Too many requests | Exponential backoff |

---

## Search with Time Range

Bilibili search supports time-range filtering for incremental crawling:

```python
import datetime

def generate_time_ranges(start_date: str, end_date: str, days_per_range: int = 7):
    """Split date range into chunks for search API."""
    start = datetime.datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(end_date, "%Y-%m-%d")
    ranges = []
    while start < end:
        chunk_end = min(start + datetime.timedelta(days=days_per_range), end)
        ranges.append((start.strftime("%Y-%m-%d"), chunk_end.strftime("%Y-%m-%d")))
        start = chunk_end
    return ranges

# Usage in search: add pubtime_begin_s and pubtime_end_s (Unix timestamps)
```

---

## Cookie & Session

### Key Cookies

| Cookie | Purpose | Required |
|--------|---------|----------|
| `SESSDATA` | Auth session | For logged-in APIs |
| `bili_jct` | CSRF token | For POST requests |
| `buvid3` | Device fingerprint | Always |
| `buvid4` | Extended device ID | Always |

**Session establishment**: Visit `www.bilibili.com` in Playwright, then extract cookies. WBI keys must also be extracted from the same browser context.
