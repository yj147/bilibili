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

## useReducer for Complex State

When a component has 3+ related boolean/modal states, consolidate into `useReducer`:

```typescript
// Good — single reducer for related state
type ModalState = {
  showAdd: boolean; showEdit: boolean;
  editingTarget: TargetType | null;
};

type ModalAction =
  | { type: "OPEN_ADD" }
  | { type: "CLOSE_ADD" }
  | { type: "OPEN_EDIT"; target: TargetType }
  | { type: "CLOSE_EDIT" };

const [modal, dispatch] = useReducer(modalReducer, initialState);

// Bad — multiple useState for related state
const [showAdd, setShowAdd] = useState(false);
const [showEdit, setShowEdit] = useState(false);
const [editingTarget, setEditingTarget] = useState<TargetType | null>(null);
```

**When to use**: 3+ related booleans, or state transitions that must be atomic (e.g., opening edit modal must also set the editing target).

**Pattern**: Also applies to loading states — use `Set<number>` in reducer when tracking concurrent operations per item:

```typescript
type LoadingState = {
  checking: Set<number>;
  refreshing: Set<number>;
};
```

---

## ID-Based Deduplication for Merged Data

When merging WebSocket real-time data with API historical data, use ID-based Set lookup instead of time-window comparison:

```typescript
// Good — ID-based dedup (reliable)
const wsLogIds = new Set(wsLogs.filter(l => l.id > 0).map(l => l.id));
const merged = [
  ...wsLogs,
  ...apiLogs.filter(l => !wsLogIds.has(l.id)),
].slice(0, 50);

// Bad — time-window dedup (unreliable with clock drift)
const TWO_SEC = 2000;
const merged = [...wsLogs, ...apiLogs.filter(al =>
  !wsLogs.some(wl => Math.abs(wl.timestamp - al.timestamp) < TWO_SEC)
)];
```

**Why**: Time-based comparison fails with clock differences between server and client, or when multiple events share similar timestamps.

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
