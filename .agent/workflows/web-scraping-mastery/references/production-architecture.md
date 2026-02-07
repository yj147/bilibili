# Production-Grade Scraper Architecture Patterns

> Distilled from battle-tested open-source multi-platform scraper frameworks (7+ platforms, 7000+ lines).

## Table of Contents
- [ABC + Factory Architecture](#abc--factory-architecture)
- [Platform-Isolated Module Structure](#platform-isolated-module-structure)
- [Dual-Mode Browser Strategy](#dual-mode-browser-strategy)
- [Browser-Based Request Signing](#browser-based-request-signing)
- [Login Strategy Pattern](#login-strategy-pattern)
- [Cache-First Deduplication](#cache-first-deduplication)
- [Proxy Pool with Auto-Refresh](#proxy-pool-with-auto-refresh)
- [Async Semaphore Concurrency Control](#async-semaphore-concurrency-control)
- [Three-Level Configuration](#three-level-configuration)
- [Dual-Entry Architecture](#dual-entry-architecture)
- [Anti-Detection Layered Defense](#anti-detection-layered-defense)
- [API Response Layered Error Handling](#api-response-layered-error-handling)
- [Proxy Auto-Refresh Mixin](#proxy-auto-refresh-mixin)
- [Slider CAPTCHA Auto-Handling](#slider-captcha-auto-handling)

---

## ABC + Factory Architecture

Define strict interface contracts via ABCs; instantiate via Factory registry. New platform = implement ABC + register, zero core changes.

```python
from abc import ABC, abstractmethod

class AbstractCrawler(ABC):
    @abstractmethod
    async def start(self): ...
    @abstractmethod
    async def search(self): ...
    @abstractmethod
    async def launch_browser(self, chromium, proxy, user_agent, headless): ...

class AbstractLogin(ABC):
    @abstractmethod
    async def begin(self): ...
    @abstractmethod
    async def login_by_qrcode(self): ...
    @abstractmethod
    async def login_by_mobile(self): ...
    @abstractmethod
    async def login_by_cookies(self): ...

class AbstractStore(ABC):
    @abstractmethod
    async def store_content(self, content_item: dict): ...
    @abstractmethod
    async def store_comment(self, comment_item: dict): ...
```

**Factory pattern** (same pattern for crawler, store, cache, proxy, login):

```python
class CrawlerFactory:
    CRAWLERS = {
        "xhs": XiaoHongShuCrawler, "dy": DouyinCrawler,
        "ks": KuaishouCrawler, "bili": BilibiliCrawler,
        "wb": WeiboCrawler, "tieba": TieBaCrawler,
    }
    @staticmethod
    def create_crawler(platform: str) -> AbstractCrawler:
        cls = CrawlerFactory.CRAWLERS.get(platform)
        if not cls:
            raise ValueError(f"Unknown platform: {platform}")
        return cls()

class StoreFactory:
    STORES = {"csv": CsvStore, "json": JsonStore, "db": DbStore, "sqlite": SqliteStore}
    @staticmethod
    def create_store() -> AbstractStore:
        cls = StoreFactory.STORES.get(config.SAVE_DATA_OPTION)
        if not cls:
            raise ValueError(f"Invalid: {config.SAVE_DATA_OPTION}")
        return cls()
```

**Key insight**: Every pluggable subsystem follows ABC+Factory, creating uniform extension across the codebase.

---

## Platform-Isolated Module Structure

Each platform is a self-contained package:

```
media_platform/
├── xhs/
│   ├── core.py       # Crawler orchestration
│   ├── client.py     # HTTP client, request signing
│   ├── login.py      # Login strategies
│   ├── field.py      # Enums
│   └── help.py       # Platform utilities
├── douyin/
│   ├── core.py / client.py / login.py / ...
└── ...
```

Platforms are fully decoupled — independently tested, maintained, or removed.

---

## Dual-Mode Browser Strategy

Support Playwright (clean) and CDP (reuse running browser):

```python
async def start(self):
    async with async_playwright() as playwright:
        if config.ENABLE_CDP_MODE:
            self.browser_context = await self.launch_browser_with_cdp(
                playwright, proxy, user_agent, headless=config.CDP_HEADLESS
            )
        else:
            chromium = playwright.chromium
            self.browser_context = await self.launch_browser(
                chromium, proxy, user_agent, headless=config.HEADLESS
            )
            await self.browser_context.add_init_script(path="libs/stealth.min.js")
```

| Mode | Use Case | Advantage |
|------|----------|----------|
| Playwright | CI/CD, headless | Clean, reproducible |
| CDP | Fingerprint bypass | Reuses real session, cookies persist |

**Persistent login** via `launch_persistent_context`:

```python
if config.SAVE_LOGIN_STATE:
    user_data_dir = f"browser_data/{config.PLATFORM}_user_data"
    browser_context = await chromium.launch_persistent_context(
        user_data_dir=user_data_dir, headless=headless,
        viewport={"width": 1920, "height": 1080}, user_agent=user_agent,
    )
```

---

## Browser-Based Request Signing

Execute platform JS in browser context instead of reverse-engineering:

```python
class PlatformClient:
    async def _pre_headers(self, url: str, data=None) -> dict:
        encrypt_params = await self.playwright_page.evaluate(
            "([url, data]) => window._webmsxyw(url, data)", [url, data]
        )
        return {
            "x-s": encrypt_params.get("X-s", ""),
            "x-t": str(encrypt_params.get("X-t", "")),
        }
```

**Advantage**: When platform updates signing, no re-reverse-engineering needed — browser runs latest JS automatically.

---

## Login Strategy Pattern

Multiple strategies behind unified interface:

```python
class PlatformLogin(AbstractLogin):
    async def begin(self):
        if config.LOGIN_TYPE == "qrcode":
            await self.login_by_qrcode()
        elif config.LOGIN_TYPE == "phone":
            await self.login_by_mobile()
        elif config.LOGIN_TYPE == "cookie":
            await self.login_by_cookies()
        await self.check_login_state()

    async def login_by_cookies(self):
        for key, value in utils.convert_str_cookie_to_dict(self.cookie_str).items():
            await self.browser_context.add_cookies([{
                "name": key, "value": value,
                "domain": ".platform.com", "path": "/"
            }])
```

**Cookie persistence**: After login, serialize cookies to cache with TTL:
```python
cache_client.set(f"{platform}_cookies", cookie_str, expire=86400)
```

---

## Cache-First Deduplication

Two-layer dedup prevents re-scraping:

```python
# Layer 1: Memory/Redis cache (fast, pre-request)
cached = cache_client.get(f"note:{note_id}")
if cached:
    return  # Skip

# Layer 2: DB unique constraint (idempotent write)
class Note(Base):
    __tablename__ = "notes"
    note_id = Column(String, unique=True, index=True)
# INSERT ... ON CONFLICT DO UPDATE (upsert)
```

**Cache abstraction** (same ABC+Factory pattern):
```python
class AbstractCache(ABC):
    @abstractmethod
    def get(self, key: str) -> Any: ...
    @abstractmethod
    def set(self, key: str, value: Any, expire_time: int) -> None: ...

class CacheFactory:
    @staticmethod
    def create_cache(cache_type: str) -> AbstractCache:
        return RedisCache() if cache_type == "redis" else LocalCache()
```

---

## Proxy Pool with Auto-Refresh

Abstract providers behind a pool that validates, rotates, and refreshes:

```python
class ProxyProvider(ABC):
    @abstractmethod
    async def get_proxy(self, num: int) -> List[IpInfoModel]: ...

class ProxyIpPool:
    def __init__(self, pool_count, enable_validate, provider: ProxyProvider):
        self.proxy_list: List[IpInfoModel] = []
        self.provider = provider

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    async def get_proxy(self) -> IpInfoModel:
        if not self.proxy_list:
            await self._reload_proxies()
        proxy = random.choice(self.proxy_list)
        self.proxy_list.remove(proxy)
        if self.enable_validate and not await self._is_valid(proxy):
            raise Exception("Invalid proxy")
        self.current_proxy = proxy
        return proxy

    async def get_or_refresh_proxy(self, buffer_seconds=30) -> IpInfoModel:
        if self.current_proxy and self.current_proxy.is_expired(buffer_seconds):
            return await self.get_proxy()
        return self.current_proxy
```

---

## Async Semaphore Concurrency Control

`asyncio.Semaphore` for precise concurrency window:

```python
async def batch_get_note_details(self, note_ids: list):
    semaphore = asyncio.Semaphore(config.MAX_CONCURRENCY_NUM)
    tasks = [self.get_note_detail(nid, semaphore) for nid in note_ids]
    await asyncio.gather(*tasks)

async def get_note_detail(self, note_id: str, semaphore: asyncio.Semaphore):
    async with semaphore:
        result = await self.client.get_note_by_id(note_id)
        await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
        await self.store.store_content(result)
```

**Key**: Semaphore limits concurrent in-flight requests; `sleep()` adds per-request delay. Together: throughput control + rate limiting.

---

## Three-Level Configuration

```
base_config.py        → Global defaults (all platforms)
├── xhs_config.py     → Platform-specific overrides
├── dy_config.py      → Platform-specific overrides
└── .env              → Secrets, deployment overrides
```

```python
PLATFORM = "xhs"
LOGIN_TYPE = "qrcode"           # qrcode | phone | cookie
CRAWLER_TYPE = "search"          # search | detail | creator
MAX_CONCURRENCY_NUM = 4
SAVE_DATA_OPTION = "json"        # json | csv | db | sqlite | mongodb | excel
ENABLE_CDP_MODE = False
```

**ContextVar** for async state passing:
```python
from contextvars import ContextVar
crawler_type_var: ContextVar[str] = ContextVar("crawler_type", default="")
source_keyword_var: ContextVar[str] = ContextVar("source_keyword", default="")
```

---

## Dual-Entry Architecture

CLI (developer) + WebUI (non-technical) sharing same core:

```python
# CLI: main.py
crawler = CrawlerFactory.create_crawler(args.platform)
await crawler.start()

# WebUI: FastAPI
app = FastAPI()
app.include_router(crawler_router, prefix="/api")
app.include_router(websocket_router, prefix="/api")  # Real-time logs
```

Both entries share `CrawlerFactory → AbstractCrawler → platform impl`. Zero code duplication.

---

## Anti-Detection Layered Defense

| Layer | Technique | Implementation |
|-------|-----------|----------------|
| L1 | CDP browser reuse | Connect to user's real Chrome |
| L2 | stealth.min.js | Anti-fingerprinting on page init |
| L3 | Real browser UA | Extract from running browser |
| L4 | Proxy rotation | Auto-rotating pool with expiry |
| L5 | Random delays | Configurable sleep + exponential backoff |
| L6 | Platform-specific | Custom anti-detection per platform |

**Example** (Tieba: navigate via Baidu homepage to mimic real user):
```python
async def _navigate_to_tieba_via_baidu(self):
    await self.page.goto("https://www.baidu.com/")
    await asyncio.sleep(config.CRAWLER_MAX_SLEEP_SEC)
    tieba_link = await self.page.wait_for_selector('a.mnav:has-text("Tieba")')
    async with self.browser_context.expect_page() as new_page_info:
        await tieba_link.click()
    self.context_page = await new_page_info.value
```

---

## API Response Layered Error Handling

Custom exception hierarchy for precise retry logic:

```python
class DataFetchError(RequestError):
    """API returned unexpected data"""
class IPBlockError(RequestError):
    """IP blocked by rate limiting"""
class NoteNotFoundError(RequestError):
    """Content removed or doesn't exist"""
class CaptchaRequiredError(RequestError):
    """CAPTCHA challenge triggered"""
```

**Response classification with tenacity:**

```python
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_not_exception_type

class PlatformClient:
    @retry(
        stop=stop_after_attempt(3), wait=wait_fixed(1),
        retry=retry_if_not_exception_type(NoteNotFoundError)
    )
    async def request(self, method, url, **kwargs):
        await self._refresh_proxy_if_expired()
        async with httpx.AsyncClient(proxy=self.proxy) as client:
            response = await client.request(method, url, timeout=self.timeout, **kwargs)

        if response.status_code in (471, 461):
            raise CaptchaRequiredError(f"CAPTCHA: {response.headers.get('Verifytype')}")

        data = response.json()
        if data["success"]:
            return data.get("data", {})
        elif data["code"] == self.IP_ERROR_CODE:
            raise IPBlockError("IP blocked")           # retries
        elif data["code"] == self.NOTE_NOT_FOUND_CODE:
            raise NoteNotFoundError("Not found")       # skips retry
        else:
            raise DataFetchError(data.get("msg", ""))   # retries
```

**Key**: `retry_if_not_exception_type(NoteNotFoundError)` — don't retry "not found"; `IPBlockError` triggers retry for proxy rotation; `CaptchaRequiredError` caught at orchestration layer.

---

## Proxy Auto-Refresh Mixin

Inject automatic proxy expiry checking into any client:

```python
class ProxyRefreshMixin:
    _proxy_ip_pool: Optional[ProxyIpPool] = None

    def init_proxy_pool(self, proxy_ip_pool: Optional[ProxyIpPool]) -> None:
        self._proxy_ip_pool = proxy_ip_pool

    async def _refresh_proxy_if_expired(self) -> None:
        if self._proxy_ip_pool is None:
            return
        if self._proxy_ip_pool.is_current_proxy_expired():
            new_proxy = await self._proxy_ip_pool.get_or_refresh_proxy()
            self.proxy = f"http://{new_proxy.ip}:{new_proxy.port}"

# Usage: class XHSClient(AbstractApiClient, ProxyRefreshMixin):
#     async def request(self, ...):
#         await self._refresh_proxy_if_expired()
```

Mixin avoids duplicating refresh logic across all platform clients.

---

## Slider CAPTCHA Auto-Handling

**Architecture**: Detect → screenshot → calculate gap (OpenCV) → generate trajectory (easing) → drag → verify → retry if failed.

**Gap detection (OpenCV):**
```python
import cv2

class Slide:
    def discern(self) -> int:
        gap_img = self.clear_white(self.gap)
        gap_edges = cv2.Canny(cv2.cvtColor(gap_img, cv2.COLOR_RGB2GRAY), 100, 200)
        bg_edges = cv2.Canny(cv2.imread(self.bg, cv2.COLOR_RGB2GRAY), 100, 200)
        result = cv2.matchTemplate(
            cv2.cvtColor(bg_edges, cv2.COLOR_GRAY2RGB),
            cv2.cvtColor(gap_edges, cv2.COLOR_GRAY2RGB),
            cv2.TM_CCOEFF_NORMED
        )
        _, _, _, max_loc = cv2.minMaxLoc(result)
        return max_loc[0]  # x-coordinate of gap
```

**Human-like trajectory (easing functions):**
```python
import numpy as np

def ease_out_expo(x):
    return 1 if x == 1 else 1 - pow(2, -10 * x)

def get_tracks(distance, seconds, ease_func) -> list:
    tracks, offsets = [0], [0]
    for t in np.arange(0.0, seconds, 0.1):
        offset = round(ease_func(t / seconds) * distance)
        tracks.append(offset - offsets[-1])
        offsets.append(offset)
    return tracks
```

**CAPTCHA loop** (max 20 attempts, click refresh on failure):
```python
async def check_page_display_slider(self, move_step=10):
    try:
        await self.page.wait_for_selector("#captcha-verify-image", timeout=5000)
    except PlaywrightTimeoutError:
        return  # No CAPTCHA

    for attempt in range(20):
        try:
            await self.move_slider(back_selector, gap_selector, move_step)
            await self.page.wait_for_selector(back_selector, state="hidden", timeout=3000)
            return  # Success
        except Exception:
            await self.page.click("//a[contains(@class, 'captcha_refresh')]")
            await asyncio.sleep(1)
    raise Exception("Slider verification failed after max attempts")
```

For higher accuracy, integrate third-party services (2Captcha, Anti-CAPTCHA).
