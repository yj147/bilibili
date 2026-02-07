# Data Pipeline: Cleaning, Validation, Export & Analysis

> Patterns for transforming raw scraped data into clean, validated, multi-format output.

## Table of Contents
- [Data Cleaning & Normalization](#data-cleaning--normalization)
- [Data Quality Validation](#data-quality-validation)
- [Incremental Crawling](#incremental-crawling)
- [Multi-Format Export](#multi-format-export)
- [API & GraphQL Crawling](#api--graphql-crawling)
- [Media File Download](#media-file-download)
- [Data Analysis & Reporting](#data-analysis--reporting)

---

## Data Cleaning & Normalization

### HTML to Plain Text
```python
from bs4 import BeautifulSoup
import re

def html_to_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()
```

### Date Normalization
```python
DATE_FORMATS = [
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y/%m/%d %H:%M", "%b %d, %Y", "%d %b %Y",
]

def normalize_date(raw: str) -> Optional[str]:
    raw = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).isoformat()
        except ValueError:
            continue
    return None
```

### Unicode Cleanup
```python
import unicodedata

def clean_text(text: str) -> str:
    text = unicodedata.normalize("NFC", text)
    text = "".join(c for c in text if unicodedata.category(c)[0] != "C" or c in "\n\t")
    text = text.replace("\u201c", '"').replace("\u201d", '"')
    text = text.replace("\u2018", "'").replace("\u2019", "'")
    return text.strip()
```

### Field-Level Pipeline
```python
def clean_item(raw: dict) -> dict:
    return {
        "title": clean_text(raw.get("title", "")),
        "content": html_to_text(raw.get("content_html", "")),
        "author": clean_text(raw.get("author", "")).strip("@"),
        "publish_date": normalize_date(raw.get("date", "")),
        "url": raw.get("url", "").split("?")[0],
        "tags": [t.strip().lower() for t in raw.get("tags", []) if t.strip()],
        "view_count": parse_number(raw.get("views", "0")),
    }

def parse_number(s: str) -> int:
    s = s.strip().replace(",", "")
    multipliers = {"k": 1000, "K": 1000, "m": 1_000_000, "M": 1_000_000, "w": 10_000, "万": 10_000}
    for suffix, mult in multipliers.items():
        if s.endswith(suffix):
            return int(float(s[:-len(suffix)]) * mult)
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0
```

---

## Data Quality Validation

Pydantic models enforce schema before storage:

```python
from pydantic import BaseModel, Field, field_validator, HttpUrl

class ScrapedItem(BaseModel):
    url: HttpUrl
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(default="")
    author: str = Field(default="unknown")
    publish_date: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    view_count: int = Field(default=0, ge=0)

    @field_validator("title")
    @classmethod
    def title_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v or v.lower() in ("untitled", "no title", "n/a"):
            raise ValueError("Title is empty or placeholder")
        return v
```

**Validation pipeline:**
```python
def validate_batch(items: list[dict]) -> tuple[list[dict], list[dict]]:
    valid, rejected = [], []
    for raw in items:
        try:
            item = ScrapedItem(**raw)
            valid.append(item.model_dump())
        except Exception as e:
            rejected.append({"data": raw, "error": str(e)})
    return valid, rejected
```

---

## Incremental Crawling

### Content Hash Comparison
```python
class IncrementalCache:
    def __init__(self, filepath: str = ".content_hashes.json"):
        self.filepath = filepath
        self.hashes: dict[str, str] = {}
        self._load()

    def has_changed(self, url: str, content: str) -> bool:
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        if self.hashes.get(url) == content_hash:
            return False
        self.hashes[url] = content_hash
        return True

    def save(self):
        with open(self.filepath, "w") as f:
            json.dump(self.hashes, f)
```

### HTTP Conditional Requests (ETag/Last-Modified)
```python
async def fetch_if_modified(session, url: str, cache: dict) -> tuple[str, bool]:
    headers = {}
    if url in cache:
        if "etag" in cache[url]:
            headers["If-None-Match"] = cache[url]["etag"]
        if "last_modified" in cache[url]:
            headers["If-Modified-Since"] = cache[url]["last_modified"]

    resp = await session.get(url, headers=headers)
    if resp.status_code == 304:
        return "", False  # Not modified

    cache[url] = {
        "etag": resp.headers.get("ETag", ""),
        "last_modified": resp.headers.get("Last-Modified", ""),
    }
    return resp.text, True
```

---

## Multi-Format Export

### Excel (openpyxl)
```python
def export_excel(results: list[dict], filepath: str):
    from openpyxl import Workbook
    from openpyxl.styles import Font, Alignment
    wb = Workbook()
    ws = wb.active
    if not results:
        wb.save(filepath); return
    headers = list(results[0].keys())
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.font = Font(bold=True)
    for row_idx, item in enumerate(results, 2):
        for col_idx, key in enumerate(headers, 1):
            val = item.get(key, "")
            ws.cell(row=row_idx, column=col_idx, value=str(val) if not isinstance(val, list) else ", ".join(str(v) for v in val))
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = min(max(len(str(c.value or "")) for c in col) + 2, 50)
    wb.save(filepath)
```

### SQLite
```python
def export_sqlite(results: list[dict], db_path: str, table: str = "scraped_data"):
    if not results: return
    conn = sqlite3.connect(db_path)
    keys = list(results[0].keys())
    cols = ", ".join(f'"{ k}" TEXT' for k in keys)
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (id INTEGER PRIMARY KEY AUTOINCREMENT, {cols})')
    placeholders = ", ".join(["?"] * len(keys))
    col_names = ", ".join(f'"{k}"' for k in keys)
    rows = [tuple(str(item.get(k, "")) for k in keys) for item in results]
    conn.executemany(f'INSERT INTO "{table}" ({col_names}) VALUES ({placeholders})', rows)
    conn.commit(); conn.close()
```

### Parquet
```python
def export_parquet(results: list[dict], filepath: str):
    import pandas as pd
    pd.DataFrame(results).to_parquet(filepath, index=False, engine="pyarrow")
```

### MongoDB
```python
async def export_mongodb(results: list[dict], uri: str, db_name: str, collection: str):
    from motor.motor_asyncio import AsyncIOMotorClient
    from pymongo import UpdateOne
    client = AsyncIOMotorClient(uri)
    coll = client[db_name][collection]
    ops = [UpdateOne({"url": item["url"]}, {"$set": item}, upsert=True) for item in results]
    if ops:
        await coll.bulk_write(ops)
```

---

## API & GraphQL Crawling

### Page-Based Pagination
```python
async def crawl_paginated_api(session, base_url, params, page_key="page", max_pages=100):
    all_items, page = [], 1
    while page <= max_pages:
        params[page_key] = page
        data = (await session.get(base_url, params=params)).json()
        items = data.get("data", data.get("results", data.get("items", [])))
        if not items: break
        all_items.extend(items)
        if not data.get("has_more", data.get("has_next", True)): break
        page += 1
        await asyncio.sleep(random.uniform(0.5, 1.5))
    return all_items
```

### Cursor-Based Pagination
```python
async def crawl_cursor_api(session, url, cursor_key="cursor", data_key="data", max_pages=100):
    all_items, cursor = [], ""
    for _ in range(max_pages):
        params = {cursor_key: cursor} if cursor else {}
        data = (await session.get(url, params=params)).json()
        items = data.get(data_key, [])
        if not items: break
        all_items.extend(items)
        cursor = data.get(cursor_key, data.get("next_cursor", ""))
        if not cursor: break
        await asyncio.sleep(random.uniform(0.5, 1.5))
    return all_items
```

### Token Refresh
```python
class TokenManager:
    def __init__(self, client_id, client_secret, token_url):
        self.client_id, self.client_secret, self.token_url = client_id, client_secret, token_url
        self.access_token, self.expires_at = "", 0

    async def get_token(self, session) -> str:
        if time.time() < self.expires_at - 60:
            return self.access_token
        resp = await session.post(self.token_url, data={
            "grant_type": "client_credentials",
            "client_id": self.client_id, "client_secret": self.client_secret,
        })
        data = resp.json()
        self.access_token = data["access_token"]
        self.expires_at = time.time() + data.get("expires_in", 3600)
        return self.access_token
```

---

## Media File Download

```python
async def download_media(session, url, save_dir, filename="", chunk_size=8192) -> str:
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    if not filename:
        filename = url.split("/")[-1].split("?")[0] or "unnamed"
    filepath = save_path / filename

    headers = {}
    if filepath.exists():
        headers["Range"] = f"bytes={filepath.stat().st_size}-"

    resp = await session.get(url, headers=headers)
    if resp.status_code == 416: return str(filepath)  # Already complete

    mode = "ab" if resp.status_code == 206 else "wb"
    async with aiofiles.open(filepath, mode) as f:
        await f.write(resp.content)
    return str(filepath)
```

**Filename generation** (hash-based for uniqueness):
```python
def generate_filename(url: str, content_type: str = "", index: int = 0) -> str:
    ext_map = {"image/jpeg": ".jpg", "image/png": ".png", "video/mp4": ".mp4"}
    ext = ext_map.get(content_type, Path(urlparse(url).path).suffix or ".bin")
    return f"{index:04d}_{hashlib.md5(url.encode()).hexdigest()[:8]}{ext}"
```

---

## Data Analysis & Reporting

```python
from collections import Counter

def generate_crawl_report(results: list[dict]) -> dict:
    total = len(results)
    if not total: return {"total": 0}

    field_counts = {}
    for key in results[0].keys():
        filled = sum(1 for r in results if r.get(key))
        field_counts[key] = {"filled": filled, "pct": round(filled / total * 100, 1)}

    dates = [r["publish_date"] for r in results if r.get("publish_date")]
    all_tags = [t for r in results for t in r.get("tags", [])]
    authors = [r.get("author", "unknown") for r in results]

    return {
        "total_items": total,
        "field_completeness": field_counts,
        "date_range": {"earliest": min(dates), "latest": max(dates)} if dates else {},
        "top_tags": Counter(all_tags).most_common(20),
        "top_authors": Counter(authors).most_common(10),
        "report_generated": datetime.now().isoformat(),
    }
```

**Markdown report export:**
```python
def report_to_markdown(report: dict) -> str:
    lines = [f"# Crawl Report", f"**Total**: {report['total_items']}"]
    if report.get("date_range"):
        lines += [f"\n## Date Range", f"- Earliest: {report['date_range']['earliest']}", f"- Latest: {report['date_range']['latest']}"]
    lines += [f"\n## Field Completeness", "| Field | Filled | % |", "|-------|--------|---|"]
    for field, s in report.get("field_completeness", {}).items():
        lines.append(f"| {field} | {s['filled']} | {s['pct']}% |")
    if report.get("top_tags"):
        lines += [f"\n## Top Tags"] + [f"- **{t}**: {c}" for t, c in report["top_tags"]]
    return "\n".join(lines)
```
