# Chinese E-Commerce Scraping Patterns

## Table of Contents

- [Taobao/Tmall mtop API](#taobaotmall-mtop-api)
- [Token Handshake Protocol](#token-handshake-protocol)
- [Login Flow](#login-flow)
- [Session Management](#session-management)
- [Known API Limitations](#known-api-limitations)
- [Common Pitfalls](#common-pitfalls)

## Taobao/Tmall mtop API

mtop is Alibaba's mobile API gateway. Key endpoints:

- Reviews: `mtop.taobao.rate.detaillist.get` (v6.0)
- Base URL: `https://h5api.m.taobao.com/h5/{api_name}/{version}/`
- Auth: MD5 signature + session cookies from H5 mobile page

### Signature Computation

```python
import hashlib, json, time

APP_KEY = "12574478"

def build_sign(token, t, data):
    raw = f"{token}&{t}&{APP_KEY}&{data}"
    return hashlib.md5(raw.encode()).hexdigest()

def build_params(token, item_id, page, page_size=20):
    t = str(int(time.time() * 1000))
    data = json.dumps({
        "auctionNumId": item_id,
        "bizCode": "ali.china.tmall",
        "channel": "pc_detail",
        "pageSize": page_size,
        "currentPage": page,
    }, separators=(",", ":"))
    return {
        "jsv": "2.7.2", "appKey": APP_KEY, "t": t,
        "sign": build_sign(token, t, data),
        "api": "mtop.taobao.rate.detaillist.get",
        "v": "6.0", "timeout": "10000",
        "dataType": "json", "data": data,
    }
```

### Headers

Must match H5 mobile context:

```python
headers = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 12; Pixel 6) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    "Referer": f"https://h5.m.taobao.com/awp/core/detail.htm?id={item_id}",
    "Origin": "https://h5.m.taobao.com",
}
```

## Token Handshake Protocol

The mtop API uses `_m_h5_tk` cookie for token-based signing. Critical discovery:

1. Browser visits H5 page -> gets `_m_h5_tk` cookie
2. httpx MUST NOT reuse browser's `_m_h5_tk` directly
3. Delete `_m_h5_tk` from cookies, use token "0"
4. First API call returns `FAIL_SYS_TOKEN_EXOIRED` (sic) + new token via Set-Cookie
5. Second call with new token returns actual data

**Why**: The mtop API binds tokens to the HTTP client's session. Browser's token is bound to the browser session, not httpx's session. httpx must establish its own binding.

```python
# Remove browser token, force API to issue new one
api_cookies = {k: v for k, v in cookies.items() if "_m_h5_tk" not in k}
token = "0"

# Call 1: TOKEN_EXPIRED -> get new token from Set-Cookie
# Call 2: SUCCESS with data
```

**Failure pattern without this**: API returns `SUCCESS` but `data.module` is empty. No error, just missing data. Very confusing to debug.

## Login Flow

### QR Code Login

```python
await page.goto(
    "https://login.taobao.com/member/login.jhtml"
    "?redirectURL=https%3A%2F%2Fwww.taobao.com"
)
# Wait for URL to change from login.taobao.com
for i in range(180):
    await asyncio.sleep(1)
    if "login.taobao.com" not in page.url:
        break
```

### Critical: Redirect Destination

- `www.taobao.com` redirect = session works for mtop API
- `i.taobao.com` redirect = session DOES NOT work (different cookie set)

Always force redirect via URL parameter AND add post-login navigation:

```python
if "www.taobao.com" not in page.url:
    await page.goto("https://www.taobao.com")
```

## Session Management

### Cookie Extraction Order

1. Visit `www.taobao.com` first (establishes base `.taobao.com` cookies)
2. Then visit H5 product page (establishes `_m_h5_tk` and mobile cookies)
3. Extract ALL cookies from Playwright context
4. Convert to plain dict with parent-domain priority

### Session Health Checks

| Cookie Count | Status |
|-------------|--------|
| 130+ | Fresh login, optimal |
| 69-89 | Working, normal |
| <60 | Degraded, may fail |
| cookie2 missing | Need re-login |

### Session Degradation

Persistent browser profile cookies degrade over time:
- `cookie2` persists but session tokens expire
- API returns SUCCESS but empty data
- Solution: Keep browser open during entire scraping session
- If session expires mid-scrape: re-extract cookies from still-open browser

## Known API Limitations

### mtop.taobao.rate.detaillist.get

- **Hard pagination limit**: 50 pages max (`totalPage` capped at 50)
- **Page size**: 20 items per page
- **Max reviews per product**: ~1000 (50 * 20)
- **Filter parameters ignored**: `rateType`, `hasPic`, `hasAppend`, `tagId`, `order`, `folded` — all silently ignored in v6.0
- **Deduplication needed**: Later pages overlap with earlier pages (~18 new per 20 returned)

## Common Pitfalls

1. **Using PC page cookies for H5 API**: Must use `h5.m.taobao.com` cookies, not `item.taobao.com`
2. **Reusing browser token in httpx**: Causes SUCCESS + empty data (see Token Handshake above)
3. **Using `httpx.Cookies` with domain awareness**: Too strict for cross-subdomain APIs, use plain dict
4. **Batch testing filter parameters**: Rapid-fire API calls trigger RGV587 anti-bot
5. **Closing browser before httpx completes**: Session invalidation
6. **Trusting `totalPage` for planning**: Always capped at 50 regardless of actual review count
7. **Not monitoring cookie count**: Session degradation is silent — only detectable by cookie count drop
