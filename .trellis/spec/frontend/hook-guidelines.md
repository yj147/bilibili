# Hook Guidelines

> Custom hooks and data fetching patterns in Bili-Sentinel.

---

## Overview

- **Data fetching**: SWR (stale-while-revalidate)
- **Real-time**: Custom WebSocket hook
- **Mutations**: Direct `api` client calls + `mutate()` for cache invalidation

---

## SWR Hooks (`lib/swr.ts`)

Each resource has a dedicated SWR hook:

```typescript
import useSWR from 'swr';

const fetcher = (path: string) => fetch(`${API_BASE}${path}`, {
  headers: API_KEY ? { 'X-API-Key': API_KEY } : {},
}).then(r => {
  if (!r.ok) throw new Error(`${r.status}`);
  return r.json();
});

export function useAccounts() {
  return useSWR<Account[]>('/accounts/', fetcher);
}

export function useTargets(params: Record<string, string> = {}) {
  const query = new URLSearchParams(params).toString();
  return useSWR<TargetListResponse>(`/targets/?${query}`, fetcher);
}
```

### Available Hooks

| Hook | Returns | Refresh |
|------|---------|--------|
| `useAccounts()` | `Account[]` | Every 30s |
| `useTargets(params)` | `TargetListResponse` | On focus |
| `useReportLogs(limit)` | `ReportLog[]` | On focus |
| `useAutoReplyConfigs()` | `AutoReplyConfig[]` | On focus |
| `useAutoReplyStatus()` | `AutoReplyStatus` | Every 5s |
| `useSchedulerTasks()` | `ScheduledTask[]` | On focus |
| `useSchedulerHistory(limit)` | `ReportLog[]` | On focus |
| `useConfigs()` | `Record<string, unknown>` | On focus |
| `useSystemInfo()` | System info object | Every 30s |

### Refresh Intervals

Some hooks use `refreshInterval` for polling:

```typescript
// Auto-refresh every 5 seconds
useSWR<AutoReplyStatus>('/autoreply/status', fetcher, { refreshInterval: 5000 });
```

---

## Mutation Pattern

For create/update/delete operations, use the `api` client then call `mutate()`:

```typescript
import { api } from "@/lib/api";
import { useAccounts } from "@/lib/swr";

function AccountsPage() {
  const { data: accounts, mutate } = useAccounts();

  const handleCreate = async (data: AccountCreate) => {
    await api.accounts.create(data);
    mutate(); // Revalidate the cache
  };

  const handleDelete = async (id: number) => {
    await api.accounts.delete(id);
    mutate(); // Revalidate
  };
}
```

---

## WebSocket Hook (`lib/websocket.ts`)

The `useLogStream` hook provides real-time log entries:

```typescript
const { logs, connected } = useLogStream(maxLogs);
```

### Behavior

- Connects to `ws://host/ws/logs`
- Auto-reconnects on disconnect (3s interval)
- Filters out heartbeat/pong/connected messages
- Maintains a sliding window of `maxLogs` entries (default 100)
- Returns `connected` boolean for connection status display

### LogEntry Type

```typescript
interface LogEntry {
  type: string;      // "report", "scheduler", "autoreply", "error"
  message: string;
  data: Record<string, unknown>;
  timestamp: number;
}
```

---

## API Client (`lib/api.ts`)

The `api` object provides typed methods for all backend endpoints:

```typescript
// Namespaced by resource
api.accounts.list()
api.accounts.create(data)
api.targets.list(params)
api.reports.execute(targetId, accountIds)
api.autoreply.start(interval)
api.config.update(key, value)
```

All methods:
- Add `Content-Type: application/json` header
- Add `X-API-Key` header if configured
- Throw `Error` with `detail` message on non-OK responses

---

## Common Mistakes

### Mistake 1: Forgetting to Call mutate() After Mutation

```typescript
// Bad — UI won't update
await api.accounts.delete(id);

// Good — triggers SWR revalidation
await api.accounts.delete(id);
mutate();
```

### Mistake 2: Using fetch() Directly Instead of api Client

```typescript
// Bad — loses auth headers, error handling
const res = await fetch('/api/accounts/');

// Good — consistent auth and error handling
const accounts = await api.accounts.list();
```

### Mistake 3: Not Handling Loading/Error States

SWR returns `undefined` before first load:

```typescript
const { data: accounts = [] } = useAccounts(); // Default to empty array
```

---

## React 19 Effect Rules (Critical)

React 19 enforces strict lint rules via `react-hooks/set-state-in-effect`. Violations will block lint.

### Forbidden: Synchronous setState in useEffect

```typescript
// FORBIDDEN — triggers cascading render lint error
useEffect(() => {
  if (data) setLocalState(data);  // sync setState in effect body
}, [data]);
```

### Pattern: Async Function Inside Effect

If the setState is after an `await`, it's allowed because it's in a microtask:

```typescript
// ALLOWED — setState is after await (async callback)
useEffect(() => {
  const load = async () => {
    const res = await api.auth.qrGenerate();
    setQrUrl(res.url);  // OK: after await
  };
  load();
}, []);
```

### Pattern: Ref Stability for Callbacks

Don't assign refs during render. Use a separate effect:

```typescript
// FORBIDDEN — ref assignment during render
const callbackRef = useRef(callback);
callbackRef.current = callback;  // Lint error: ref access during render

// ALLOWED — ref assignment inside effect
const callbackRef = useRef(callback);
useEffect(() => {
  callbackRef.current = callback;
});
```

### Pattern: Split Event Handler vs Effect Logic

Separate async-only logic (for effects) from sync+async logic (for button handlers):

```typescript
// For useEffect mount — async only, no sync setState
const fetchData = async () => {
  const res = await api.getData();
  setState(res);  // OK: after await
};

// For button click — can do anything
const handleRefresh = () => {
  setLoading(true);  // sync setState OK in event handler
  fetchData();
};

useEffect(() => { fetchData(); }, []);  // Mount
```

---

## Auth Hooks (`lib/api.ts` auth namespace)

Auth operations use the `api.auth` namespace directly (not SWR hooks), because they are imperative actions:

```typescript
api.auth.qrGenerate()     // Generate QR code URL + qrcode_key
api.auth.qrPoll(key)      // Poll QR scan status
api.auth.qrLogin(key)     // Save scanned session to DB
api.auth.cookieStatus(id) // Check cookie health
api.auth.refreshCookies(id) // Silent cookie refresh
```

These are NOT cached via SWR — they are one-shot mutations/queries.
