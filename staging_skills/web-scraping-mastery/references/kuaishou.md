# 快手 (Kuaishou) Anti-Detection

> Platform-specific patterns extracted from MediaCrawler. Covers GraphQL API, dual-host architecture, and operation patterns.

## Table of Contents
- [GraphQL API Pattern](#graphql-api-pattern)
- [Dual-Host Architecture](#dual-host-architecture)
- [Named Operations](#named-operations)
- [Cookie & Session](#cookie--session)
- [Pagination](#pagination)

---

## GraphQL API Pattern

Kuaishou uses GraphQL for most APIs — all requests share the same endpoint with different `operationName` + `query` + `variables`.

```python
async def graphql_request(operation_name: str, query: str, variables: dict) -> dict:
    payload = {
        "operationName": operation_name,
        "query": query,
        "variables": variables,
    }
    response = await session.post(
        "https://www.kuaishou.com/graphql",
        json=payload,
        headers={"Content-Type": "application/json"},
    )
    return response.json()
```

**Key difference from REST APIs**: No URL-based routing. All requests go to `/graphql`. The `operationName` determines what data is returned.

---

## Dual-Host Architecture

| Host | Protocol | Used For |
|------|----------|----------|
| `www.kuaishou.com/graphql` | GraphQL | Search, video detail, user profile, user posts |
| `www.kuaishou.com/rest/v/photo/comment/list` | REST v2 | Comments (not available via GraphQL) |

### Comment API (REST)

```python
async def get_comments(photo_id: str, cursor: str = "") -> dict:
    params = {
        "photoId": photo_id,
        "pcursor": cursor,  # Cursor-based pagination
        "count": 20,
    }
    response = await session.get(
        "https://www.kuaishou.com/rest/v/photo/comment/list",
        params=params,
    )
    return response.json()
```

---

## Named Operations

| Operation | Purpose | Key Variables |
|-----------|---------|---------------|
| `visionSearchPhoto` | Search videos | `keyword`, `pcursor`, `page` |
| `visionVideoDetail` | Video detail | `photoId`, `page` |
| `visionProfilePhotoList` | User's videos | `userId`, `pcursor`, `page` |
| `visionProfile` | User profile | `userId` |

### Search Example

```python
variables = {
    "keyword": "search term",
    "pcursor": "",  # Empty for first page
    "page": "search",
}
result = await graphql_request("visionSearchPhoto", SEARCH_QUERY, variables)
feeds = result["data"]["visionSearchPhoto"]["feeds"]
next_cursor = result["data"]["visionSearchPhoto"]["pcursor"]
```

---

## Cookie & Session

Kuaishou requires browser-established cookies. Key cookies:

| Cookie | Purpose |
|--------|---------|
| `did` | Device ID |
| `didv` | Device ID version |
| `kpf` | Platform flag |
| `kpn` | Product name |
| `clientid` | Client identifier |

**Session establishment**: Visit `www.kuaishou.com` in Playwright first to acquire cookies, then use them for GraphQL/REST requests.

---

## Pagination

All Kuaishou APIs use cursor-based pagination (`pcursor`):

```python
pcursor = ""  # Start empty
while True:
    result = await graphql_request(op_name, query, {"pcursor": pcursor, **params})
    data = result["data"][op_name]
    feeds = data.get("feeds", [])
    if not feeds:
        break
    process(feeds)
    pcursor = data.get("pcursor", "")
    if not pcursor or pcursor == "no_more":
        break
```

**Note**: `pcursor` value `"no_more"` indicates end of results.
