---
name: web-scraping-mastery
description: "Production-grade web scraping patterns. Triggers: scrape, crawl, spider, data extraction, anti-bot, Cloudflare, Playwright, httpx, curl_cffi, cookie, session, Taobao, Tmall, mtop, XiaoHongShu, Douyin, Kuaishou, Bilibili, Weibo, Tieba, API reverse-engineering, token refresh, signature computation, TLS fingerprint, residential proxy, WBI, a_bogus, GraphQL. Covers architecture decisions, authentication flows, anti-detection, platform-specific patterns, and large-scale collection."
---

# Web Scraping Mastery

## Task Entry Point

**Start here**: [workflow.md](references/workflow.md) — 6-phase execution framework + troubleshooting decision tree

**Executable template**: `scripts/unified_scraper.py` + `scripts/config.yaml`

---

## Scenario Router

| Scenario | Reference | Section |
|----------|-----------|--------|
| **New task** | workflow.md | Quick Start |
| SPA/XHR reverse | api-discovery.md | Phase 1-3 |
| Taobao/Tmall mtop | taobao-mtop.md | Token Handshake |
| Anti-bot blocked | workflow.md | Phase 5 Symptom Table |
| Stealth config | anti-detection.md | Browser Launch |
| Browser behavior bypass | anti-detection.md | Browser Behavior Simulation |
| Proxy strategy choice | anti-detection.md | Sticky vs Rotating |
| Cross-domain cookies | scraping-patterns.md | Cookie Domain Priority |
| 10K+ URLs | infrastructure.md | Large-Scale Patterns |
| Data cleaning/export | data-pipeline.md | Multi-Format Export |
| MediaCrawler arch | production-architecture.md | ABC+Factory |
| **小红书** scraping | xiaohongshu.md | Signature Headers |
| **抖音** scraping | douyin.md | Signature System |
| **快手** scraping | kuaishou.md | GraphQL API Pattern |
| **B站** scraping | bilibili.md | WBI Signature System |
| **微博** scraping | weibo.md | Container-Based API |
| **贴吧** scraping | tieba.md | Full Browser Scraping |

---

## Architecture Decision Matrix

| Signal | Approach |
|--------|----------|
| Static HTML | `curl_cffi` + `BeautifulSoup` |
| JS-rendered | Playwright + stealth |
| XHR in DevTools | Direct API calls |
| Mobile app exists | Reverse mobile API |
| Cloudflare/WAF | Browser + residential proxy |
| Login required | Playwright auth → cookie extract → httpx fetch |

---

## 7 Battle-Tested Lessons

### 1. Browser Must Stay Open
Closing Playwright invalidates cookies even if saved to disk. Keep browser open until scraping completes.

### 2. Forced Token Refresh
httpx needs its own token binding. Delete browser tokens, use `token="0"` to trigger `TOKEN_EXPIRED`.
**Symptom**: SUCCESS but empty data → 99% this is the cause.

### 3. Login Redirect Target
Must redirect to main domain (`www.taobao.com`), not subdomain (`i.taobao.com`).

### 4. Cookie Count Monitoring
- 69-130 = healthy
- <60 = needs re-login

### 5. Plain Dict Beats httpx.Cookies
Cross-subdomain APIs need plain dict; domain-aware cookies are too strict.

### 6. Debug Density Triggers Anti-Bot
Rapid test runs accumulate and trigger RGV587. Wait 5+ minutes after failures.

### 7. API Pagination Hard Limits
mtop caps at 50 pages = 1000 items. Test API limits before designing.

---

## Reference Files

| File | Content | Lines |
|------|---------|-------|
| [workflow.md](references/workflow.md) | **Entry point** - 6-phase flow, decision tree | ~200 |
| [scraping-patterns.md](references/scraping-patterns.md) | Cookie handling, token refresh, browser-open arch | ~120 |
| [anti-detection.md](references/anti-detection.md) | Stealth JS, rate control, 2026 tools, behavior simulation, proxy strategy | ~250 |
| [taobao-mtop.md](references/taobao-mtop.md) | Taobao mtop signature, token protocol, login | ~160 |
| [production-architecture.md](references/production-architecture.md) | MediaCrawler ABC arch, proxy pool, CAPTCHA | ~480 |
| [api-discovery.md](references/api-discovery.md) | SPA reverse, session extraction, CAPTCHA bypass | ~320 |
| [infrastructure.md](references/infrastructure.md) | Storage, large-scale, distributed, tools | ~480 |
| [data-pipeline.md](references/data-pipeline.md) | Data cleaning, validation, export, media download | ~360 |
| [xiaohongshu.md](references/xiaohongshu.md) | X-S/X-T signing, CAPTCHA 471/461, xsec_token | ~140 |
| [douyin.md](references/douyin.md) | a_bogus signing, msToken, device params | ~140 |
| [kuaishou.md](references/kuaishou.md) | GraphQL API, dual-host, cursor pagination | ~100 |
| [bilibili.md](references/bilibili.md) | WBI signature, wbi_img_urls, exponential backoff | ~130 |
| [weibo.md](references/weibo.md) | Container API, error 432, image anti-hotlinking | ~110 |
| [tieba.md](references/tieba.md) | Playwright HTML scraping, Baidu SSO cookies | ~100 |

---

## Scripts

| File | Purpose |
|------|--------|
| `scripts/unified_scraper.py` | Production scraper template (curl_cffi + Playwright) |
| `scripts/config.yaml` | YAML configuration template |

**Usage**:
```bash
cd scripts
# Edit config.yaml with target settings
python unified_scraper.py
```
