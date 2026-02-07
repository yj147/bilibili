# 小红书 (XiaoHongShu) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers signature generation, CAPTCHA handling, and session management.

## Table of Contents
- [Signature Headers](#signature-headers)
- [CAPTCHA Detection & Recovery](#captcha-detection--recovery)
- [Session & Cookie Management](#session--cookie-management)
- [API Endpoints](#api-endpoints)
- [Error Codes](#error-codes)
- [Retry Strategy](#retry-strategy)

---

## Signature Headers

XiaoHongShu requires 4 custom headers computed via browser JS injection:

| Header | Source | Purpose |
|--------|--------|--------|
| `X-S` | Playwright JS `window._webmsxyw` | Request signature |
| `X-T` | Playwright JS (timestamp) | Signature timestamp |
| `x-S-Common` | Playwright JS `window._webmsxyw` | Common signature |
| `X-B3-Traceid` | Random hex generation | Distributed tracing ID |

### Signing Flow

```python
async def sign_with_playwright(uri: str, data: dict, a1: str, web_session: str) -> dict:
    """Sign request via Playwright page.evaluate()."""
    # 1. Build plaintext: uri + sorted query + cookie a1 + web_session
    # 2. Call window._webmsxyw(plaintext) in browser context
    # 3. Returns {"X-S": ..., "X-T": ..., "x-S-Common": ...}
    encrypt_params = await self.playwright_page.evaluate(
        "([url, data]) => window._webmsxyw(url, data)",
        [uri, data]
    )
    return encrypt_params
```

**Critical**: The `a1` cookie is used as input to the signature function. If `a1` is missing or expired, all signed requests fail silently (return empty data, not errors).

### X-B3-Traceid Generation

```python
import random
def get_traceid() -> str:
    return "".join(random.choice("0123456789abcdef") for _ in range(16))
```

---

## CAPTCHA Detection & Recovery

### Status Codes

| HTTP Status | Meaning | Response Headers |
|-------------|---------|------------------|
| 471 | CAPTCHA required (image verify) | `Verifytype`, `Verifyuuid` |
| 461 | CAPTCHA required (slider verify) | `Verifytype`, `Verifyuuid` |

### Detection Pattern

```python
if response.status_code == 471 or response.status_code == 461:
    verify_type = response.headers.get("Verifytype")
    verify_uuid = response.headers.get("Verifyuuid")
    # Trigger CAPTCHA solving flow
    raise CaptchaRequiredError(verify_type, verify_uuid)
```

### Recovery
1. Pause all requests immediately
2. Solve CAPTCHA (manual or third-party solver)
3. Wait 30-60 seconds after solving
4. Resume with same session cookies

---

## Session & Cookie Management

### Required Cookies

| Cookie | Purpose | Acquisition |
|--------|---------|-------------|
| `a1` | Signature input + session ID | Set on first visit |
| `web_session` | Auth session token | Set after login |
| `webId` | Device fingerprint | Set on first visit |
| `xsec_token` | Content access token | Returned per note/comment API |

### xsec_token Flow

The `xsec_token` is required for note detail and comment APIs. It's returned in search/feed results and must be passed when fetching individual notes.

```python
# From search results, extract xsec_token per note
note_info = {
    "note_id": item["id"],
    "xsec_token": item.get("xsec_token", ""),
    "xsec_source": "pc_search",  # or "pc_feed", "pc_user"
}

# When fetching note detail, include xsec params
async def get_note_detail(note_id: str, xsec_token: str, xsec_source: str):
    params = {"source_note_id": note_id, "xsec_token": xsec_token, "xsec_source": xsec_source}
    # Sign and send request
```

---

## API Endpoints

| Endpoint | Purpose | Method |
|----------|---------|--------|
| `/api/sns/web/v1/search/notes` | Search notes | POST |
| `/api/sns/web/v1/feed` | Note detail | POST |
| `/api/sns/web/v2/comment/page` | Note comments | GET |
| `/api/sns/web/v2/comment/sub/page` | Sub-comments | GET |
| `/api/sns/web/v1/user_posted` | User's notes | GET |
| `/api/sns/web/v1/user/otherinfo` | User profile | GET |

### Base Headers

```python
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...",
    "Origin": "https://www.xiaohongshu.com",
    "Referer": "https://www.xiaohongshu.com/",
    "Content-Type": "application/json;charset=UTF-8",
}
```

---

## Error Codes

| Code | Meaning | Action |
|------|---------|--------|
| 300012 | IP blocked | Switch proxy, wait 10+ min |
| -510000 | Note not found / deleted | Skip (do not retry) |
| 471/461 | CAPTCHA triggered | Solve CAPTCHA, then resume |
| SUCCESS + empty | Token/cookie expired | Re-sign with fresh `a1` |

---

## Retry Strategy

```python
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type

class NoteNotFoundError(Exception):
    """Note deleted or unavailable — skip, don't retry."""
    pass

@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_not_exception_type(NoteNotFoundError),
)
async def get_note_detail(self, note_id, xsec_token, xsec_source):
    # ... request logic ...
    if error_code == -510000:
        raise NoteNotFoundError(f"Note {note_id} not found")
```

**Key principle**: Never retry on "not found" errors — they waste quota and trigger anti-bot.
