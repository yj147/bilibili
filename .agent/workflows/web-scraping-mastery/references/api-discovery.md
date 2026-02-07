# API Discovery: Browser Recon → Direct HTTP Scraper

> Pattern for scraping SPAs by discovering hidden APIs through browser DevTools, then building lightweight direct HTTP scrapers.

## Table of Contents
- [When to Use This Pattern](#when-to-use-this-pattern)
- [Phase 1: Browser Reconnaissance](#phase-1-browser-reconnaissance)
- [Phase 2: API Analysis](#phase-2-api-analysis)
- [Phase 3: Direct HTTP Scraper](#phase-3-direct-http-scraper)
- [Session Cookie Extraction](#session-cookie-extraction)
- [CAPTCHA Avoidance via API](#captcha-avoidance-via-api)
- [Common SPA API Patterns](#common-spa-api-patterns)
- [Real-World Example: Huitun Data](#real-world-example-huitun-data)

---

## When to Use This Pattern

| Signal | Action |
|:---|:---|
| SPA with hash routing (`#/app/...`) | API discovery first |
| Login-required data analytics platform | Session cookie + direct API |
| Playwright not installed / heavy dep | Direct HTTP preferred |
| CAPTCHA on page but not on API | Direct API bypasses CAPTCHA |
| Data comes from XHR/Fetch, not SSR | API is the real data source |
| Need high throughput (100+ pages) | Direct HTTP 10x faster than browser |

**Key insight**: Most SPAs are thin frontends over REST APIs. The API is the real target — the browser is just the discovery tool.

---

## Phase 1: Browser Reconnaissance

Use Chrome DevTools (via CDP MCP or manual) to explore the target site and capture API calls.

### Step 1: Navigate and Observe
```
1. Open target site in Chrome with DevTools
2. Navigate to the page with target data
3. Open Network tab, filter by XHR/Fetch
4. Perform the action (search, paginate, click detail)
5. Identify API requests that return the data
```

### Step 2: Capture Key Information
For each discovered API endpoint, record:
```
- Full URL with query parameters
- HTTP method (GET/POST)
- Request headers (especially Cookie, Authorization, Content-Type)
- Request body (for POST)
- Response structure (JSON schema)
- Pagination mechanism (page number, cursor, offset)
- Authentication method (Cookie, Bearer token, API key)
```

### Using Chrome DevTools MCP
```
# List pages
mcp__chrome-devtools__list_pages

# Navigate
mcp__chrome-devtools__navigate_page(url=...)

# Capture network requests (filter by xhr/fetch)
mcp__chrome-devtools__list_network_requests(resourceTypes=["xhr", "fetch"])

# Get full request/response details
mcp__chrome-devtools__get_network_request(reqid=N)

# Extract cookies from request headers
# Look for Cookie: header in request details
```

### Using Browser Console
```javascript
// Extract all cookies (non-httpOnly only)
document.cookie

// For httpOnly cookies: check Network tab request headers
// The Cookie: header in API requests contains ALL cookies including httpOnly
```

---

## Phase 2: API Analysis

### Identify Pagination
```
Common pagination parameter patterns:
- `from=1` / `page=1` (page number)
- `offset=0` / `skip=0` (offset-based)
- `cursor=abc` / `after=abc` (cursor-based)
- `_t=1234567890` (timestamp, anti-cache)
```

### Identify Authentication
```
Priority order for auth discovery:
1. Cookie header → Session-based auth (most common for web apps)
2. Authorization: Bearer → JWT/OAuth token
3. Custom headers → X-Api-Key, X-Token, etc.
4. Query params → api_key=..., token=...
```

### Map Response Structure
```json
// Typical paginated API response
{
  "status": 200,
  "code": 0,
  "total": 10001,
  "data": [
    { "id": "...", "title": "...", ... },
    ...
  ]
}
```

Key fields to identify:
- Status/error indicators (`status`, `code`, `message`)
- Total count (`total`, `count`, `totalCount`)
- Data array (`data`, `list`, `items`, `records`, `results`)
- Per-item fields and their types

---

## Phase 3: Direct HTTP Scraper

### Minimal Template
```python
import json, time, random, requests, yaml
from pathlib import Path
from datetime import datetime

class APIScraper:
    def __init__(self, config):
        self.session = requests.Session()
        self.session.cookies.set(
            "SESSION", config["auth"]["session_cookie"],
            domain="api.example.com"
        )
        self.session.headers.update({
            "Accept": "application/json",
            "Origin": "https://example.com",
            "Referer": "https://example.com/",
            "User-Agent": "Mozilla/5.0 ...",
        })
        self.products = []

    def fetch_page(self, keyword, page_num):
        params = {
            "_t": str(int(time.time() * 1000)),
            "from": str(page_num),
            "keyword": keyword,
            "sortField": "sales",
            "sortMod": "desc",
        }
        resp = self.session.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        body = resp.json()
        return body.get("data", []), body.get("total", 0)

    def run(self, keyword, max_pages=5):
        for page in range(1, max_pages + 1):
            data, total = self.fetch_page(keyword, page)
            if not data:
                break
            self.products.extend(data)
            if page * 20 >= total:
                break
            time.sleep(random.uniform(2, 4))
```

### Critical Headers
```python
# These headers are often required for cross-origin API calls from SPAs
headers = {
    "Accept": "application/json",
    "Content-Type": "application/x-www-form-urlencoded",  # or application/json
    "Origin": "https://frontend-domain.com",  # CORS origin
    "Referer": "https://frontend-domain.com/",  # CORS referer
    "User-Agent": "...",  # Match browser UA
}
```

**Common gotcha**: API and frontend on different subdomains (e.g., `dy.huitun.com` frontend, `dyapi.huitun.com` API). The `Origin` and `Referer` must match the frontend domain.

---

## Session Cookie Extraction

### From Chrome DevTools MCP
```
1. list_network_requests → find any API request
2. get_network_request(reqid=N) → read Cookie header
3. Extract SESSION=... or session_id=... value
```

### From Browser Console (non-httpOnly only)
```javascript
document.cookie  // Won't include httpOnly cookies
```

### httpOnly Cookie Workaround
httpOnly cookies cannot be read via `document.cookie`. Extract them from:
1. Network request headers (DevTools MCP `get_network_request`)
2. Chrome DevTools Application > Cookies panel
3. `document.cookie` only returns non-httpOnly cookies

---

## CAPTCHA Avoidance via API

**Key discovery**: Many SPAs trigger CAPTCHA only on frontend page loads, not on API calls. If you have a valid session cookie:

1. CAPTCHA blocks browser page rendering
2. But direct API calls with the same session cookie work fine
3. This is because CAPTCHAs are often injected by frontend JS, not enforced at API level

**Strategy**:
```
1. Login via browser manually (handle CAPTCHA once)
2. Extract session cookie from browser
3. Use direct HTTP calls — CAPTCHA never triggers
4. Only re-login when session expires
```

**Warning**: Some platforms enforce CAPTCHA at API level too (rate limiting). In that case, reduce request frequency or rotate sessions.

---

## Common SPA API Patterns

### Hash Router SPAs
```
URL: https://example.com/app/#/goods/search
API: https://api.example.com/search/v2/goods?keyword=...

The hash fragment (#/...) is client-side routing.
API base URL often follows pattern: api.example.com or exampleapi.example.com
```

### Timestamp Anti-Cache
```
Most SPA APIs include a timestamp parameter:
?_t=1770374208734  (milliseconds since epoch)

Always include this — servers may reject requests without it.
```

### Empty Parameter Convention
```
Many SPA APIs send ALL filter parameters, even when empty:
?keyword=纸&catIds=&prices=&salesC=&...

Reproduce this exactly — some APIs reject requests with missing params.
```

---

## Real-World Example: Huitun Data

### Discovery Process
```
Target: dy.huitun.com (Douyin e-commerce analytics)
Auth: Cookie SESSION (httpOnly)
API Base: https://dyapi.huitun.com

1. Navigated to goods search page via Chrome DevTools MCP
2. Captured network requests → found /search/v2/goods endpoint
3. Extracted SESSION cookie from request headers
4. Built requests-based scraper with cookie auth
5. CAPTCHA appeared on page loads but NOT on direct API calls
```

### API Endpoint
```
GET https://dyapi.huitun.com/search/v2/goods
  ?_t={timestamp_ms}
  &from={page_number}
  &keyword={search_term}
  &sortField=gmv7
  &sortMod=desc
  &searchType=1
  &catIds=&prices=&salesC=&...  (empty filters)

Headers:
  Cookie: SESSION={session_value}
  Origin: https://dy.huitun.com
  Referer: https://dy.huitun.com/
```

### Response Structure
```json
{
  "status": 200,
  "code": 0,
  "total": 10001,
  "data": [
    {
      "pid": "3789779973435425154",
      "title": "商品名称",
      "price": 5575.0,
      "salesC": "7.5k-1w",
      "salesCIndex": "11641.5",
      "liveSalesC": "5k-7.5k",
      "shop": "店铺名",
      "score": "4.6",
      "trend": [7.6, 2.62, 1.37, 13.98, 1.92, 2.92, 12.71]
    }
  ]
}
```

### Key Lessons
1. **API provides richer data than DOM** — includes precise numeric values (`salesCIndex`) alongside display strings (`salesC`)
2. **Session cookie is httpOnly** — must extract from network request headers, not `document.cookie`
3. **CAPTCHA only on frontend** — direct API calls with valid session work fine
4. **Cross-origin setup** — API on `dyapi.huitun.com`, frontend on `dy.huitun.com`, requires correct Origin/Referer
5. **Empty params required** — all filter params must be present even when empty
6. **20 items per page, page number in `from` param** — different from typical `page`/`offset` naming
