# Infrastructure: Storage, Concurrency & Large-Scale Patterns

> Storage solutions, concurrency models, large-scale scraping patterns, distributed task management.

## Table of Contents
- [Storage Solutions](#storage-solutions)
- [Concurrency & Performance](#concurrency--performance)
- [Legal & Ethical Standards](#legal--ethical-standards)
- [Memory-Efficient Streaming](#memory-efficient-streaming)
- [Chunked Storage](#chunked-storage)
- [Backpressure & Flow Control](#backpressure--flow-control)
- [Progress Tracking & Resume](#progress-tracking--resume)
- [Database Bulk Operations](#database-bulk-operations)
- [Resource Monitoring](#resource-monitoring)
- [Distributed Task Patterns](#distributed-task-patterns)
- [URL List Management](#url-list-management)
- [Error Handling & Monitoring](#error-handling--monitoring)
- [Tools & Frameworks](#tools--frameworks)

---

## Storage Solutions

| Solution | Type | Best For |
|:---|:---:|:---|
| JSONL | File | Default choice, streaming writes, large datasets |
| JSON | File | Small datasets, human readable |
| CSV | File | Tabular data, Excel compatible |
| SQLite | Embedded DB | Medium datasets, queryable, single machine |
| PostgreSQL | RDBMS | Structured data, complex queries |
| MongoDB | NoSQL | Semi-structured, flexible schema |
| Redis | Cache/Queue | URL dedup, task queues, high-speed cache |

**Best practice**: Hybrid — Redis for dedup/queuing, DB for persistence, files for archival.

---

## Concurrency & Performance

| Technique | Best For | Notes |
|:---|:---|:---|
| **asyncio** | I/O-bound (first choice) | Lowest resource, highest concurrency |
| Multi-threading | I/O-bound (fallback) | Limited by GIL |
| Multi-processing | CPU-bound parsing | High overhead |

```python
# Semaphore for concurrency control
semaphore = asyncio.Semaphore(5)
async with semaphore:
    await fetch(url)
```

**Tips**: Use `uvloop` as event loop replacement for performance boost.

---

## Legal & Ethical Standards

### robots.txt
Always check and comply with `robots.txt` before scraping. Voluntary protocol, not legally enforceable.

### Frequency Limits
- Add random delays between requests (e.g., `time.sleep(1~3)`)
- Keep concurrency reasonable (2-5 for polite scraping)
- Use adaptive throttling based on server response times

### Data Privacy
- Avoid scraping PII unless necessary; comply with GDPR/CCPA
- Anonymize personal data before storage
- Use encryption for sensitive data at rest

---

## Memory-Efficient Streaming

Never hold all results in a list for 10K+ URLs. Stream to disk as they arrive.

### Streaming JSONL Writer
```python
import json, aiofiles
from pathlib import Path

class StreamingWriter:
    def __init__(self, filepath: str):
        self.filepath = Path(filepath)
        self.filepath.parent.mkdir(parents=True, exist_ok=True)
        self._count = 0
        self._file = None

    async def open(self):
        self._file = await aiofiles.open(self.filepath, "w", encoding="utf-8")
        self._count = 0

    async def write(self, item: dict):
        if self._file is None: await self.open()
        await self._file.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._count += 1
        if self._count % 100 == 0:
            await self._file.flush()

    async def close(self):
        if self._file:
            await self._file.flush()
            await self._file.close()

    @property
    def count(self) -> int:
        return self._count
```

### Generator-Based URL Loading
```python
def load_urls_from_file(filepath: str):
    with open(filepath, "r") as f:
        for line in f:
            url = line.strip()
            if url and not url.startswith("#"):
                yield url
```

---

## Chunked Storage

For 100K+ records, split output into manageable chunks.

```python
class ChunkedWriter:
    def __init__(self, base_path: str, chunk_size: int = 10_000):
        self.base_path = Path(base_path)
        self.chunk_size = chunk_size
        self._current_chunk = 0
        self._current_count = 0
        self._file = None

    def _chunk_path(self) -> Path:
        stem, suffix = self.base_path.stem, self.base_path.suffix or ".jsonl"
        self.base_path.parent.mkdir(parents=True, exist_ok=True)
        return self.base_path.parent / f"{stem}_{self._current_chunk:04d}{suffix}"

    async def write(self, item: dict):
        if self._file is None or self._current_count >= self.chunk_size:
            await self._rotate()
        await self._file.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._current_count += 1

    async def _rotate(self):
        if self._file:
            await self._file.flush(); await self._file.close()
            self._current_chunk += 1; self._current_count = 0
        self._file = await aiofiles.open(self._chunk_path(), "w", encoding="utf-8")

    async def close(self):
        if self._file:
            await self._file.flush(); await self._file.close()
```

Result: `output/data_0000.jsonl`, `data_0001.jsonl`, etc. Each ≤10K records.

---

## Backpressure & Flow Control

### Bounded Queue
```python
queue = asyncio.Queue(maxsize=1000)  # Producers block when full
await queue.put((url, depth))        # Auto-waits if full
url, depth = await queue.get()       # Consumer at own pace
```

### Adaptive Rate Limiting
```python
class AdaptiveRateLimiter:
    def __init__(self, base_delay=1.0, max_delay=30.0):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.current_delay = base_delay
        self._errors = 0
        self._successes = 0

    def record_success(self):
        self._successes += 1; self._errors = 0
        if self._successes >= 10:
            self.current_delay = max(self.base_delay, self.current_delay * 0.8)
            self._successes = 0

    def record_error(self):
        self._errors += 1; self._successes = 0
        self.current_delay = min(self.max_delay, self.current_delay * 2)

    async def wait(self):
        await asyncio.sleep(self.current_delay + random.uniform(0, 0.5))
```

---

## Progress Tracking & Resume

### Progress Tracker
```python
import time, json
from dataclasses import dataclass, field, asdict

@dataclass
class CrawlProgress:
    total_urls: int = 0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = field(default_factory=time.time)
    failed_urls: list = field(default_factory=list)

    @property
    def rate(self) -> float:
        elapsed = time.time() - self.start_time
        return (self.completed / elapsed * 60) if elapsed > 0 else 0

    @property
    def eta_seconds(self) -> float:
        remaining = self.total_urls - self.completed - self.failed - self.skipped
        return (remaining / self.rate * 60) if self.rate > 0 else float("inf")

    def log_status(self):
        pct = (self.completed + self.failed + self.skipped) / max(self.total_urls, 1) * 100
        logger.info(f"Progress: {pct:.1f}% | Done: {self.completed} | Failed: {self.failed} | Rate: {self.rate:.1f}/min | ETA: {self.eta_seconds/60:.1f}min")

    def save(self, filepath=".crawl_progress.json"):
        with open(filepath, "w") as f:
            json.dump(asdict(self), f, indent=2)
```

### Checkpoint-Based Resume
```python
class CheckpointManager:
    def __init__(self, filepath=".crawl_checkpoint.json", interval=100):
        self.filepath = filepath
        self.interval = interval
        self._ops = 0

    def should_save(self) -> bool:
        self._ops += 1
        if self._ops >= self.interval:
            self._ops = 0; return True
        return False

    def save(self, state: dict):
        with open(self.filepath, "w") as f:
            json.dump(state, f)

    def load(self) -> dict:
        try:
            with open(self.filepath) as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

def resume_crawl(urls: list[str], checkpoint_file: str) -> list[str]:
    state = CheckpointManager(checkpoint_file).load()
    completed = set(state.get("completed", []))
    remaining = [u for u in urls if u not in completed]
    logger.info(f"Resuming: {len(completed)} done, {len(remaining)} remaining")
    return remaining
```

---

## Database Bulk Operations

For 10K+ records, individual INSERTs are too slow.

### SQLite Batch Insert
```python
def bulk_insert_sqlite(items: list[dict], db_path: str, table: str, batch_size=5000):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA cache_size=-64000")  # 64MB cache

    keys = list(items[0].keys())
    cols = ", ".join(f'"{ k}"' for k in keys)
    placeholders = ", ".join(["?"] * len(keys))
    col_defs = ", ".join(f'"{k}" TEXT' for k in keys)
    conn.execute(f'CREATE TABLE IF NOT EXISTS "{table}" (id INTEGER PRIMARY KEY, {col_defs})')

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        rows = [tuple(str(item.get(k, "")) for k in keys) for item in batch]
        conn.executemany(f'INSERT INTO "{table}" ({cols}) VALUES ({placeholders})', rows)
        conn.commit()
    conn.close()
```

### PostgreSQL COPY (10-100x faster than INSERT)
```python
async def bulk_copy_postgres(items: list[dict], conn, table: str):
    if not items: return
    keys = list(items[0].keys())
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=keys, extrasaction="ignore")
    for item in items:
        writer.writerow({k: str(item.get(k, "")) for k in keys})
    buffer.seek(0)
    await conn.copy_to_table(table, source=buffer, columns=keys, format="csv")
```

---

## Resource Monitoring

Prevent OOM or file descriptor exhaustion.

```python
import psutil, os

class ResourceMonitor:
    def __init__(self, memory_limit_pct=85.0):
        self.memory_limit_pct = memory_limit_pct
        self.process = psutil.Process(os.getpid())

    def check(self) -> dict:
        mem = self.process.memory_info()
        return {
            "rss_mb": mem.rss / 1024 / 1024,
            "system_pct": psutil.virtual_memory().percent,
        }

    def is_memory_critical(self) -> bool:
        return psutil.virtual_memory().percent > self.memory_limit_pct

    async def guard(self):
        while self.is_memory_critical():
            logger.warning(f"Memory at {psutil.virtual_memory().percent}% — pausing")
            import gc; gc.collect()
            await asyncio.sleep(5)
```

Integrate: call `await monitor.guard()` every 50 URLs in worker loop.

---

## Distributed Task Patterns

For 100K+ URLs, single machine may not suffice.

### Redis Task Queue
```python
import redis.asyncio as aioredis

class RedisTaskQueue:
    def __init__(self, redis_url="redis://localhost:6379", queue_name="crawl_queue"):
        self.redis = aioredis.from_url(redis_url)
        self.queue_name = queue_name
        self.seen_set = f"{queue_name}:seen"

    async def enqueue(self, url: str) -> bool:
        added = await self.redis.sadd(self.seen_set, url)
        if added:
            await self.redis.rpush(self.queue_name, url)
            return True
        return False

    async def dequeue(self, timeout=5) -> str:
        result = await self.redis.blpop(self.queue_name, timeout=timeout)
        return result[1].decode() if result else ""
```

### File-Based Sharding (no infrastructure)
```python
def shard_urls(urls: list[str], num_shards: int) -> list[list[str]]:
    shards = [[] for _ in range(num_shards)]
    for i, url in enumerate(urls):
        shards[i % num_shards].append(url)
    return shards
# Run: python scraper.py --shard 0 --total-shards 4
```

---

## URL List Management

### Bloom Filter Dedup (memory-efficient for millions)
```python
import hashlib

class BloomFilterDedup:
    def __init__(self, expected_items=1_000_000):
        self.size = expected_items * 10
        self.bits = bytearray(self.size // 8 + 1)
        self.hash_count = 7

    def _hashes(self, url: str) -> list[int]:
        h = hashlib.md5(url.encode()).hexdigest()
        return [int(h[i*4:(i+1)*4], 16) % self.size for i in range(self.hash_count)]

    def add(self, url: str):
        for h in self._hashes(url):
            self.bits[h // 8] |= 1 << (h % 8)

    def might_contain(self, url: str) -> bool:
        return all(self.bits[h // 8] & (1 << (h % 8)) for h in self._hashes(url))
```

~1% false positive at 1M URLs with 10MB memory. For exact dedup use `set` (~100MB/1M URLs).

### Priority URL Queue
```python
import heapq
from dataclasses import dataclass, field

@dataclass(order=True)
class PrioritizedUrl:
    priority: int
    url: str = field(compare=False)
    depth: int = field(compare=False, default=0)

class PriorityUrlQueue:
    def __init__(self):
        self._heap: list[PrioritizedUrl] = []

    def push(self, url: str, priority: int = 5, depth: int = 0):
        heapq.heappush(self._heap, PrioritizedUrl(priority, url, depth))

    def pop(self) -> tuple[str, int]:
        item = heapq.heappop(self._heap)
        return item.url, item.depth

# pq.push(listing_url, priority=1)   # Listing pages first
# pq.push(detail_url, priority=5)    # Detail pages later
```

---

## Error Handling & Monitoring

### Retry Strategy
- Catch specific exceptions (`Timeout`, `ConnectionError`), not generic `Exception`
- **Exponential backoff** for transient errors (5xx, network jitter)
- Set reasonable timeouts on all requests
- Handle HTTP codes explicitly: 404→skip, 403/429→wait+rotate IP

### Logging & KPIs
- Level-based logging (DEBUG/INFO/WARNING/ERROR)
- Track: crawl speed (pages/min), success rate, error rate, data volume
- Alert when error rate > threshold (e.g., 10% for 5min)

---

## Tools & Frameworks

| Tool/Framework | Type | Best For |
|:---|:---|:---|
| Requests + BeautifulSoup | Library | Simple static pages, learning |
| **Playwright** | Browser | Dynamic sites, cross-browser, auto-wait |
| Scrapy | Framework | Large-scale, high-concurrency, distributed |
| Selenium | Browser | Legacy projects, specific WebDriver needs |
| httpx / curl_cffi | HTTP client | Fast static scraping, TLS fingerprint bypass |

**Decision**: Static → `httpx`/`curl_cffi`. Dynamic → `Playwright`. Large-scale → `Scrapy`. Pick one → **Playwright** (covers 90%).

### Data Parsing Techniques

| Feature | CSS Selectors | XPath | Regex |
|:---|:---:|:---:|:---:|
| Power | Strong | **Very Strong** | Weak (for HTML) |
| Ease of Use | **Easy** | Medium | Difficult |
| Stability | Good | Good | Poor |

**Priority**: CSS Selectors > XPath > Regex. Use CSS for most cases; XPath when axis navigation needed; Regex only for text extraction within located blocks.

### Browser Automation Hierarchy
1. **CDP** (Chrome DevTools Protocol): Lowest level, ~300+ commands, highest performance
2. **Playwright/Puppeteer**: High-level wrappers over CDP with friendly APIs
3. **MCP** (Model Context Protocol): LLM-friendly browser interaction

| Scenario | Best Tool | Reason |
|:---|:---|:---|
| Static pages | `httpx` / `curl_cffi` | No browser needed, fastest |
| Dynamic + cross-browser | **Playwright** | Modern API, auto-waits |
| Peak performance | Direct CDP (pydoll, go-rod) | 15-20% faster than Playwright |
| AI agent interaction | **Playwright MCP** | Accessibility tree, LLM-friendly |
| Enterprise distributed | **Scrapy + Redis** | Mature ecosystem, scalable |
