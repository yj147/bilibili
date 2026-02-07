# Scraping Architecture Patterns

## Table of Contents
- [Token/Signature Computation](#tokensignature-computation)
- [Cookie Domain Priority](#cookie-domain-priority)
- [Forced Token Refresh Pattern](#forced-token-refresh-pattern)
- [Pagination with Error Recovery](#pagination-with-error-recovery)
- [Browser-Open Architecture](#browser-open-architecture-recommended)
- [Cookie Extraction Sequence](#cookie-extraction-sequence)

---

## Token/Signature Computation

Many Chinese e-commerce APIs use MD5-based signatures: `md5(token&timestamp&appKey&data)`. See [taobao-mtop.md](taobao-mtop.md#signature-computation) for Taobao mtop implementation.

---

## Cookie Domain Priority

When converting browser cookies to HTTP client format, handle domain conflicts.

**Use plain dict, NOT `httpx.Cookies` with domain awareness.** Domain-aware cookies are too strict for cross-subdomain APIs (e.g., cookies from `.taobao.com` not sent to `h5api.m.taobao.com`).

```python
def pw_cookies_to_dict(pw_cookies: list[dict]) -> dict[str, str]:
    """Prioritize .parent-domain.com cookies over subdomain cookies."""
    priority = {}
    for c in pw_cookies:
        name = c["name"]
        domain = c.get("domain", "")
        if name not in priority or domain in (".parent-domain.com", "parent-domain.com"):
            priority[name] = c["value"]
    return priority
```

**Why plain dict wins**: When Playwright extracts 130 cookies across multiple domains, `httpx.Cookies` with domain-aware storage only sends cookies matching the exact request domain. A plain dict sends ALL cookies regardless of domain, which is what cross-subdomain APIs expect.

---

## Forced Token Refresh Pattern

When the HTTP client needs its own token binding (separate from browser's):

```python
# Strip browser auth tokens
api_cookies = {k: v for k, v in cookies.items() if "auth_token_name" not in k}
token = "0"  # Invalid token forces TOKEN_EXPIRED response

async with httpx.AsyncClient(cookies=api_cookies) as client:
    # Call 1: TOKEN_EXPIRED -> server sets new token via Set-Cookie
    data, new_token = await call_api(client, token, ...)
    token = new_token  # Now bound to httpx session

    # Call 2: SUCCESS with actual data
    data, token = await call_api(client, token, ...)
```

**Symptom without this**: API returns SUCCESS but response body has empty data module. No error returned — extremely confusing.

---

## Pagination with Error Recovery

```python
consecutive_empty = 0
rgv587_count = 0

for page_num in range(2, max_pages + 1):
    data = await fetch_page(page_num)

    if data.has_results:
        process(data)
        consecutive_empty = 0
    elif data.is_anti_bot:
        rgv587_count += 1
        save_progress()  # Save before waiting
        await exponential_backoff(rgv587_count)
        if rgv587_count >= 5:
            break
    elif data.is_token_expired:
        await refresh_token()
        retry()
    else:
        consecutive_empty += 1
        if consecutive_empty >= 3:
            break
```

---

## Browser-Open Architecture (Recommended)

Keep browser open during ENTIRE scraping session. This is critical — closing browser invalidates session cookies even if they're extracted.

```python
async with async_playwright() as pw:
    context = await pw.chromium.launch_persistent_context(
        user_data_dir="./browser_profile",
        headless=False,
        ...
    )
    page = context.pages[0]

    # Login if needed
    if not has_valid_session(context):
        await do_login(page)

    # Extract cookies for httpx
    cookies = await extract_cookies(context, page, item_id)

    # Fetch with httpx (faster than browser JS)
    result = await fetch_first_page(cookies, headers)

    # If session expired, re-extract from STILL-OPEN browser (no re-login!)
    if result is None:
        cookies = await extract_cookies(context, page, item_id)
        result = await fetch_first_page(cookies, headers)

    # Paginated fetching
    async with httpx.AsyncClient(cookies=result.cookies) as client:
        for page_num in range(2, max_pages + 1):
            # ... fetch pages ...

    # Browser closes LAST
    await context.close()
```

**Why not close-then-httpx**: Playwright persistent context saves cookies to disk, but the server-side session binding is lost. The saved cookies look valid (cookie2 exists) but API returns empty data.

---

## Cookie Extraction Sequence

Order matters for getting complete cookies:

1. Visit main domain first — establishes base cookies
2. Wait 3-5s for async cookie setting
3. Visit target page (e.g., mobile/H5 product page) — establishes API-specific cookies
4. Wait 5-8s for full page load and cookie injection
5. Extract ALL cookies from context (not just current page domain)

See [taobao-mtop.md](taobao-mtop.md#session-management) for Taobao-specific extraction code.
