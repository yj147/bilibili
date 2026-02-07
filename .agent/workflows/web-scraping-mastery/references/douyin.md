# 抖音 (Douyin) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers a_bogus signing, msToken management, and device fingerprint parameters.

## Table of Contents
- [Signature System](#signature-system)
- [Token Management](#token-management)
- [Common Device Parameters](#common-device-parameters)
- [API Endpoints](#api-endpoints)
- [Error Detection](#error-detection)
- [Short URL Resolution](#short-url-resolution)

---

## Signature System

### a_bogus Parameter

Douyin's primary anti-bot signature. Computed via browser JavaScript injection.

```python
async def get_a_bogus(params: str, post_data: str, user_agent: str) -> str:
    """Compute a_bogus via Playwright page.evaluate()."""
    a_bogus = await self.playwright_page.evaluate(
        "([params, post_data, ua]) => window.bdms.init._v[2].p[42](0, 1, 8, params, post_data, ua)",
        [params, post_data, user_agent]
    )
    return a_bogus
```

**Flow**:
1. Build query string from all parameters
2. Call `window.bdms.init._v[2].p[42]` in browser context
3. Append returned `a_bogus` value to request URL

### webid

```python
async def get_web_id() -> str:
    """Get webid from browser context (set on page load)."""
    # Retrieved from cookie or JS variable after page initialization
    return web_id
```

---

## Token Management

### msToken

Stored in localStorage under key `xmst`.

```python
async def get_ms_token(page) -> str:
    """Extract msToken from browser localStorage."""
    token = await page.evaluate("() => localStorage.getItem('xmst')")
    return token or ""
```

**Refresh**: msToken rotates periodically. Re-extract from localStorage before each batch of requests.

### ttwid

Set via `Set-Cookie` on first page visit. Must be included in all subsequent requests.

---

## Common Device Parameters

Douyin requires 20+ device/browser fingerprint parameters on every API call:

```python
COMMON_PARAMS = {
    "device_platform": "webapp",
    "aid": "6383",
    "channel": "channel_pc_web",
    "pc_client_type": "1",
    "version_code": "190500",
    "version_name": "19.5.0",
    "cookie_enabled": "true",
    "screen_width": "1920",
    "screen_height": "1080",
    "browser_language": "zh-CN",
    "browser_platform": "Win32",
    "browser_name": "Chrome",
    "browser_version": "120.0.0.0",
    "browser_online": "true",
    "engine_name": "Blink",
    "engine_version": "120.0.0.0",
    "os_name": "Windows",
    "os_version": "10",
    "cpu_core_num": "12",
    "device_memory": "8",
    "platform": "PC",
    "downlink": "10",
    "effective_type": "4g",
    "round_trip_time": "50",
    "msToken": "",  # Filled dynamically
    "a_bogus": "",  # Filled dynamically
}
```

**Warning**: Missing or inconsistent device params trigger silent blocking (200 OK but empty data).

---

## API Endpoints

| Endpoint | Purpose | Auth |
|----------|---------|------|
| `/aweme/v1/web/search/item/` | Search videos | a_bogus + msToken |
| `/aweme/v1/web/aweme/detail/` | Video detail | a_bogus + msToken |
| `/aweme/v1/web/comment/list/` | Video comments | a_bogus + msToken |
| `/aweme/v1/web/comment/list/reply/` | Sub-comments | a_bogus + msToken |
| `/aweme/v1/web/aweme/post/` | User's videos | a_bogus + msToken + verifyFp |
| `/aweme/v1/web/user/profile/other/` | User profile | a_bogus + msToken |

### User Posts Additional Params

User post listing requires extra fingerprint parameters:

```python
user_post_params = {
    "verifyFp": "",  # From cookie or JS
    "fp": "",         # Fingerprint from cookie
    "max_cursor": 0,  # Cursor-based pagination
    "count": 18,
}
```

---

## Error Detection

| Signal | Meaning | Action |
|--------|---------|--------|
| Response text contains `"blocked"` | Account/IP blocked | Switch account + proxy |
| 200 OK + empty `aweme_list` | Signature expired or invalid | Re-compute a_bogus, refresh msToken |
| `status_code != 0` in JSON | API error | Check specific code |
| Redirect to login page | Session expired | Re-login via Playwright |

```python
if "blocked" in response.text:
    raise AccountBlockedError("Account or IP is blocked by Douyin")
```

---

## Short URL Resolution

Douyin share links use `v.douyin.com` short URLs that need resolution:

```python
import httpx

async def resolve_short_url(short_url: str) -> str:
    """Resolve v.douyin.com short URL to full URL with aweme_id."""
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(short_url)
        # Extract aweme_id from final URL
        # e.g., https://www.douyin.com/video/7123456789
        return resp.url
```

**Tip**: Always resolve short URLs before scraping — the `aweme_id` in the full URL is needed for API calls.
