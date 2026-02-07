# 贴吧 (Tieba) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers Playwright-based scraping, HTML parsing, and login detection.

## Table of Contents
- [Architecture: Full Browser Scraping](#architecture-full-browser-scraping)
- [HTML Parsing](#html-parsing)
- [Login & Cookie Detection](#login--cookie-detection)
- [Pagination](#pagination)
- [API Endpoints](#api-endpoints)

---

## Architecture: Full Browser Scraping

Tieba does **not** expose usable XHR/Fetch APIs for web scraping. All data extraction uses Playwright page rendering + HTML parsing.

```python
async def get_post_content(page, post_url: str) -> dict:
    """Navigate to post and extract content via HTML parsing."""
    await page.goto(post_url)
    await page.wait_for_load_state("networkidle")
    content = await page.content()
    return TieBaExtractor.extract_post(content)
```

**Why not API**: Tieba's APIs require complex signing (`sign` parameter with MD5) and frequently change. Browser rendering is more stable.

### Sync Request Wrapper

Some Tieba endpoints use synchronous HTTP. Wrap in `asyncio.to_thread` for async compatibility:

```python
import requests
import asyncio

async def fetch_sync_endpoint(url: str, params: dict) -> dict:
    def _fetch():
        resp = requests.get(url, params=params)
        return resp.json()
    return await asyncio.to_thread(_fetch)
```

---

## HTML Parsing

Tieba uses a custom `TieBaExtractor` for structured data extraction from rendered HTML:

### Post List Extraction

```python
from bs4 import BeautifulSoup

def extract_post_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    posts = []
    for item in soup.select(".threadlist_lz"):
        posts.append({
            "title": item.select_one(".threadlist_title a").get_text(strip=True),
            "url": item.select_one(".threadlist_title a")["href"],
            "author": item.select_one(".threadlist_author").get_text(strip=True),
            "reply_count": item.select_one(".threadlist_rep_num").get_text(strip=True),
        })
    return posts
```

### Comment Extraction

```python
def extract_comments(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    comments = []
    for item in soup.select(".l_post"):
        data_field = json.loads(item.get("data-field", "{}"))
        comments.append({
            "author": data_field.get("author", {}).get("user_name", ""),
            "content": item.select_one(".d_post_content").get_text(strip=True),
            "time": item.select_one(".tail-info:last-child").get_text(strip=True),
        })
    return comments
```

---

## Login & Cookie Detection

Tieba login status is detected by checking for specific cookies:

| Cookie | Purpose | Logged In? |
|--------|---------|------------|
| `STOKEN` | Session token | Required |
| `PTOKEN` | Persistent token | Required |
| `BDUSS` | Baidu unified session | Required |

```python
def is_logged_in(cookies: dict) -> bool:
    required = ["STOKEN", "PTOKEN", "BDUSS"]
    return all(cookies.get(k) for k in required)
```

**Note**: Tieba uses Baidu's SSO (Single Sign-On). Login at `passport.baidu.com`, then cookies work across `tieba.baidu.com`.

---

## Pagination

Tieba uses page-number-based pagination (`pn` parameter):

```python
async def crawl_post_comments(page, post_id: str, max_pages: int = 50):
    base_url = f"https://tieba.baidu.com/p/{post_id}"
    all_comments = []
    for pn in range(1, max_pages + 1):
        url = f"{base_url}?pn={pn}"
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        html = await page.content()
        comments = extract_comments(html)
        if not comments:
            break
        all_comments.extend(comments)
        await asyncio.sleep(random.uniform(1, 3))
    return all_comments
```

---

## API Endpoints

While primarily browser-scraped, some data is available via URLs:

| URL Pattern | Content |
|------------|---------|
| `tieba.baidu.com/f?kw={forum_name}` | Forum post list |
| `tieba.baidu.com/p/{post_id}` | Post detail + comments |
| `tieba.baidu.com/p/{post_id}?pn={page}` | Comment pagination |
| `tieba.baidu.com/home/main?id={user_id}` | User profile |

**Anti-bot signals**: Tieba is relatively lenient compared to other platforms. Main risks are:
- Rapid page navigation (keep 1-3s between pages)
- Missing Baidu cookies (ensure SSO login is complete)
- IP-based rate limiting (less aggressive than XiaoHongShu/Douyin)
