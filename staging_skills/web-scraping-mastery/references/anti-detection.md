# Anti-Detection Patterns

## Table of Contents
- [Stealth JavaScript Injection](#stealth-javascript-injection)
- [Rate Limiting Strategy](#rate-limiting-strategy)
- [Anti-Bot Error Handling](#anti-bot-error-handling)
- [Browser Launch Configuration](#browser-launch-configuration)
- [2026 Tool Selection](#2026-tool-selection)
- [Debugging-Induced Anti-Bot Triggers](#debugging-induced-anti-bot-triggers)
- [Browser Behavior Simulation](#browser-behavior-simulation)
- [Proxy Strategy: Sticky vs Rotating](#proxy-strategy-sticky-vs-rotating)
- [Session Health Monitoring](#session-health-monitoring)

---

## Stealth JavaScript Injection

Essential properties to override when using Playwright:

```javascript
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
delete navigator.__proto__.webdriver;

window.chrome = {
    runtime: { id: 'mocked' },
    loadTimes: function() { return {}; },
    csi: function() { return {}; },
    app: { isInstalled: false },
};

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
        { name: 'Native Client', filename: 'internal-nacl-plugin' },
    ],
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['zh-CN', 'zh', 'en-US', 'en'],
});
```

## Rate Limiting Strategy

```python
import random

# Base delay between pages
delay = random.uniform(4, 8)

# Extra pause every N pages (simulate human behavior)
if (page_num - 1) % 10 == 0:
    delay += random.uniform(15, 25)
```

## Anti-Bot Error Handling

When encountering anti-bot responses (e.g., RGV587, CAPTCHA):

1. Save current progress immediately
2. Exponential backoff: `wait = min(30 + attempt * 30, 180)`
3. Set a maximum retry count (e.g., 5) before stopping gracefully
4. Log the error type for debugging

## Browser Launch Configuration

```python
context = await pw.chromium.launch_persistent_context(
    user_data_dir="./browser_profile",
    headless=False,
    viewport={"width": 1440, "height": 900},
    locale="zh-CN",
    args=[
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-dev-shm-usage",
    ],
)
await context.add_init_script(STEALTH_JS)
```

## Debugging-Induced Anti-Bot Triggers

A critical lesson from production scraping: **development/debugging activity itself triggers anti-bot systems.**

Common mistakes that accumulate anti-bot score:
- Running the scraper 10+ times in quick succession during debugging
- Batch-testing API filter parameters (13 calls in 1 minute)
- Probing multiple product IDs to find test targets
- Token refresh loops that make 6+ calls without data

Prevention:
- Space test runs 5+ minutes apart after failures
- Test with a single product, single page first
- One full test run is better than many partial runs
- If RGV587 triggers, wait 10+ minutes before retrying (not 30 seconds)
- Clear browser profile + cookies if consistently blocked

## 2026 Tool Selection

| Tool | Purpose | Install | When to Use |
|------|---------|---------|-------------|
| curl_cffi | TLS/JA3 fingerprint spoofing | `pip install curl_cffi` | Default for HTTP mode |
| Camoufox | Firefox C++ level fingerprint | `pip install camoufox` | Heavy anti-bot (Cloudflare) |
| Patchright | Playwright CDP leak patches | `pip install patchright` | CDP detection bypass |

### curl_cffi Example
```python
from curl_cffi.requests import AsyncSession

async with AsyncSession(impersonate="chrome110") as session:
    resp = await session.get(url)
```

### Camoufox Example
```python
from camoufox.sync_api import Camoufox

with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto(url)
```

### Patchright Example
```python
from patchright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    # CDP leaks patched automatically
```

---

## Browser Behavior Simulation

Modern anti-bot systems analyze mouse movement, scroll patterns, and interaction timing — not just request fingerprints. When using browser mode (Playwright/Patchright/Camoufox), inject human-like behavior between actions.

### Page Scroll Simulation

```python
import random

async def human_scroll(page, scroll_count=3):
    """Simulate human reading behavior: scroll down in chunks, pause, occasionally scroll up."""
    for i in range(scroll_count):
        # Scroll down a random amount (300-700px)
        delta = random.randint(300, 700)
        await page.mouse.wheel(0, delta)
        await asyncio.sleep(random.uniform(0.8, 2.5))

        # 20% chance to scroll back up slightly (re-reading behavior)
        if random.random() < 0.2:
            await page.mouse.wheel(0, -random.randint(100, 200))
            await asyncio.sleep(random.uniform(0.5, 1.0))
```

### Mouse Movement Simulation

```python
async def human_mouse_move(page, target_x, target_y, steps=None):
    """Move mouse to target with Bezier-like curve, not a straight line."""
    box = page.viewport_size
    # Start from a random position if mouse hasn't moved yet
    start_x = random.randint(0, box["width"])
    start_y = random.randint(0, box["height"])

    steps = steps or random.randint(15, 30)
    for i in range(steps):
        t = (i + 1) / steps
        # Ease-out cubic for natural deceleration
        t = 1 - (1 - t) ** 3
        x = start_x + (target_x - start_x) * t + random.uniform(-2, 2)
        y = start_y + (target_y - start_y) * t + random.uniform(-2, 2)
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.005, 0.02))
```

### When to Use

| Scenario | Behavior to Inject |
|----------|-------------------|
| Before clicking a button | `human_mouse_move` to target, pause 0.3-1s, then click |
| After page load | `human_scroll` 2-4 times before extracting data |
| Form filling | Type with `page.type()` using `delay=50-150` ms per char |
| Between paginated requests | Scroll to bottom, pause, click next page |
| Login flow | Move mouse to input, click, type slowly, tab, type, click submit |

**Key principle**: Anti-bot scores accumulate. A single missing behavior won't trigger detection, but the combination of instant clicks + no scrolling + no mouse movement + fixed timing = obvious bot.

---

## Proxy Strategy: Sticky vs Rotating

### Decision Matrix

| Scenario | Proxy Type | Reason |
|----------|-----------|--------|
| Login + session-based scraping | **Sticky** (same IP) | IP change mid-session triggers re-auth or ban |
| Large-scale listing crawl (no login) | **Rotating** (per request) | Distributes load, avoids per-IP rate limits |
| Paginated API with cookies | **Sticky** (per target) | Session cookies bound to IP on some platforms |
| Search result scraping | **Rotating** (per query) | Each query is independent, no session state |
| Social media with login | **Sticky** (per account) | Platform links account activity to IP |

### Implementation Pattern

```python
class ProxyStrategy:
    def __init__(self, proxies: list[str], mode: str = "rotating"):
        self.proxies = proxies
        self.mode = mode  # "sticky" or "rotating"
        self._sticky_map: dict[str, str] = {}  # target_key -> proxy
        self._index = 0

    def get_proxy(self, target_key: str = "") -> str:
        if self.mode == "sticky" and target_key:
            if target_key not in self._sticky_map:
                self._sticky_map[target_key] = self.proxies[self._index % len(self.proxies)]
                self._index += 1
            return self._sticky_map[target_key]
        else:
            proxy = self.proxies[self._index % len(self.proxies)]
            self._index += 1
            return proxy
```

### Proxy Type Comparison

| Type | Trust Level | Speed | Cost | Best For |
|------|:----------:|:-----:|:----:|----------|
| Residential | High | Slow | $$$ | Heavy anti-bot sites (Cloudflare, Akamai) |
| Datacenter | Low | Fast | $ | Low-security targets, high throughput |
| Mobile/4G | Highest | Medium | $$$$ | Social media, strictest anti-bot |
| ISP (static residential) | High | Fast | $$ | Long sessions, account-based scraping |

**Free proxy warning**: Public proxy lists have 90%+ failure rate and introduce security risks (MITM). Only use for non-sensitive testing. For production, invest in residential or ISP proxies.

---

## Session Health Monitoring

Monitor cookie count as a proxy for session health. Session cookies degrade silently — the API returns SUCCESS but empty data, not errors. Cookie count is the only reliable indicator.

When count drops below threshold, re-navigate to main domain then target page to refresh cookies. See [taobao-mtop.md](taobao-mtop.md#session-management) for Taobao-specific thresholds and recovery code.
