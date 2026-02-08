# State Management

> How state is managed in Bili-Sentinel frontend.

---

## Overview

No global state library (no Redux/Zustand). State at three levels:

1. **Server state**: SWR (cache + revalidation)
2. **Component state**: React `useState`
3. **Real-time state**: WebSocket hook

---

## Server State (SWR)

All backend data managed by SWR hooks in `lib/swr.ts`:
- Automatic caching and revalidation
- Loading and error states
- Focus-based refresh, interval polling for critical data

```typescript
const { data, error, isLoading, mutate } = useAccounts();
```

After mutations, call `mutate()` to trigger revalidation.

---

## Component State (useState)

Local UI state managed directly in components:

| State | Purpose |
|-------|--------|
| `loading` | Button loading during mutations |
| `isDialogOpen` | Modal visibility |
| `selectedItem` | Currently selected item |
| `formData` | Form input values |
| `mobileOpen` | Mobile sidebar toggle |

---

## Real-Time State (WebSocket)

```typescript
const { logs, connected } = useLogStream(50);
```

- Sliding window of recent log entries
- Auto-reconnects on disconnection
- Dashboard merges WS + API logs with dedup

---

## What NOT to Do

1. **Don't add a global store** — SWR + useState is sufficient
2. **Don't duplicate server data in useState** — use SWR directly
3. **Don't forget default values** — SWR data is `undefined` on first render

```typescript
// Good
const { data: accounts = [] } = useAccounts();

// Bad — may crash
const { data: accounts } = useAccounts();
accounts.map(...);
```
