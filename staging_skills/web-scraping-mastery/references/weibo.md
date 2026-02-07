# 微博 (Weibo) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers container-based API, error recovery, and image anti-hotlinking.

## Table of Contents
- [Container-Based API](#container-based-api)
- [Response Format](#response-format)
- [Error Recovery](#error-recovery)
- [Image Anti-Hotlinking Bypass](#image-anti-hotlinking-bypass)
- [Cookie & Session](#cookie--session)

---

## Container-Based API

Weibo mobile web uses a container-based API where `containerid` determines the content type.

### Endpoint

```
GET https://m.weibo.cn/api/container/getIndex
```

### Container ID Patterns

| Container ID Format | Content |
|--------------------|---------|
| `100103type=1&q={keyword}` | Search results |
| `107603{user_id}` | User's posts |
| `230413{user_id}_-_WEIBO_SECOND_PROFILE_WEIBO` | User's secondary posts |

### M_WEIBOCN_PARAMS Cookie

Some container IDs are extracted from the `M_WEIBOCN_PARAMS` cookie set when visiting a user's page:

```python
from urllib.parse import unquote

def extract_container_id(m_weibocn_params: str) -> str:
    """Parse containerid from M_WEIBOCN_PARAMS cookie value."""
    decoded = unquote(m_weibocn_params)
    params = dict(p.split("=", 1) for p in decoded.split("&") if "=" in p)
    return params.get("containerid", "")
```

---

## Response Format

Weibo API uses `ok` field (not HTTP status) for success/failure:

```python
async def weibo_request(url: str, params: dict) -> dict:
    resp = await session.get(url, params=params)
    data = resp.json()
    if data.get("ok") != 1:
        raise WeiboAPIError(f"API error: ok={data.get('ok')}, msg={data.get('msg')}")
    return data["data"]
```

| `ok` Value | Meaning |
|------------|--------|
| 1 | Success |
| 0 | Error (check `msg` field) |

---

## Error Recovery

### Error 432: Cookie Refresh

Weibo returns error 432 when cookies become stale. Recovery requires re-navigating to the host page.

```python
async def handle_error_432(page, target_url: str) -> dict:
    """Refresh cookies by re-visiting the page."""
    # 1. Navigate to weibo host page
    await page.goto("https://m.weibo.cn")
    await asyncio.sleep(3)
    # 2. Navigate to target page
    await page.goto(target_url)
    await asyncio.sleep(5)
    # 3. Extract fresh cookies
    cookies = await page.context.cookies()
    return {c["name"]: c["value"] for c in cookies}
```

**Key insight**: Error 432 is not an IP ban — it's a session validation failure. Don't switch proxies; refresh cookies instead.

---

## Image Anti-Hotlinking Bypass

Weibo images return 403 when accessed with a non-Weibo `Referer`. Use a proxy service:

```python
def bypass_hotlink(image_url: str) -> str:
    """Replace Weibo CDN host with WordPress proxy."""
    # i1.wp.com proxies images without Referer checking
    from urllib.parse import urlparse
    parsed = urlparse(image_url)
    return image_url.replace(parsed.netloc, "i1.wp.com/" + parsed.netloc)
```

**Alternative**: Set `Referer: https://m.weibo.cn/` in request headers when downloading images directly.

---

## Cookie & Session

### Key Cookies

| Cookie | Purpose |
|--------|---------|
| `SUB` | Auth session token |
| `SUBP` | Extended session |
| `XSRF-TOKEN` | CSRF protection |
| `M_WEIBOCN_PARAMS` | Container ID carrier |

### Pagination

Weibo uses page-based pagination with `page` parameter:

```python
for page in range(1, max_pages + 1):
    params = {"containerid": container_id, "page_type": "searchall", "page": page}
    data = await weibo_request(API_URL, params)
    cards = data.get("cards", [])
    if not cards:
        break
```

**Note**: Search results max out at ~50 pages. Filter by time range for broader coverage.
