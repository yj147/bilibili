# Frontend Architecture Guide

> Detailed guide for AI agents working on the Bili-Sentinel frontend.

---

## Tech Stack

- **Framework**: Next.js 16 (App Router)
- **React**: 19.2.3
- **TypeScript**: 5.9.3
- **Styling**: Tailwind CSS 4
- **UI Components**: shadcn/ui + Radix UI
- **Data Fetching**: SWR 2.4.0
- **Animation**: Framer Motion 12.33.0
- **Icons**: Lucide React 0.563.0
- **Toast**: Sonner 2.0.7

---

## Page Routes

All pages use `"use client"` (client-side rendering).

| Route | File | Purpose |
|-------|------|---------|
| `/` | `app/page.tsx` | Dashboard (overview, charts, logs) |
| `/accounts` | `app/accounts/page.tsx` | Account management, QR login |
| `/targets` | `app/targets/page.tsx` | Report targets (videos/comments/users) |
| `/autoreply` | `app/autoreply/page.tsx` | Auto-reply configuration |
| `/scheduler` | `app/scheduler/page.tsx` | Scheduled tasks |
| `/config` | `app/config/page.tsx` | System configuration |

---

## Component Hierarchy

```
RootLayout (layout.tsx)
├── Sidebar (fixed sidebar + mobile drawer)
│   ├── Logo + 6 navigation items
│   └── User info footer
├── ErrorBoundary (global error capture)
└── Page Content
    ├── Shared Components
    │   ├── QRLoginModal (QR login flow)
    │   ├── ConfirmDialog (useConfirm hook)
    │   ├── Toast (sonner)
    │   └── shadcn/ui components (21 primitives)
    └── Page-specific components
```

### shadcn/ui Components (21)

button, card, input, textarea, badge, label, dialog, alert-dialog, select, switch, separator, table, tabs, progress, skeleton, dropdown-menu, pagination

---

## Data Fetching

### SWR Hooks (`lib/swr.ts`)

```typescript
useAccounts()           // 30s refresh
useTargets(params)      // 30s refresh + 10s deduplication
useReportLogs(limit)
useAutoReplyConfigs()
useAutoReplyStatus()    // 30s refresh
useSchedulerTasks()
useSchedulerHistory(limit)
useConfigs()
useSystemInfo()         // 30s refresh
```

**Pattern**:
```typescript
const { data, error, isLoading, mutate } = useAccounts();
```

### API Client (`lib/api.ts`)

**Namespaced Organization**:
```typescript
api.accounts.*    // Account operations
api.targets.*     // Target operations
api.reports.*     // Report operations
api.autoreply.*   // Auto-reply operations
api.auth.*        // Auth operations
api.scheduler.*   // Scheduler operations
api.config.*      // Config operations
```

**Auto-inject `X-API-Key` header**:
```typescript
const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};
```

**Error Handling**:
```typescript
// B站 error code mapping
if (code === -352) return "账号被风控";
if (code === -101) return "账号未登录";
if (code === -799) return "需要人机验证";
if (code === -412) return "请求过于频繁";
```

### WebSocket (`lib/websocket.ts`)

**`useLogStream(maxLogs)` Hook**:
```typescript
const { logs, isConnected } = useLogStream(500);
```

**Features**:
- Auto-reconnect (exponential backoff 3s→30s)
- Subprotocol auth: `token.${API_KEY}`
- Filter heartbeat messages (heartbeat/pong/connected)

### API Proxy (`app/api/[...path]/route.ts`)

**Catch-all proxy** - forwards all `/api/*` to `http://127.0.0.1:8000`:

```typescript
export async function GET(req: Request, { params }: { params: { path: string[] } }) {
  const path = params.path.join("/");
  const url = `http://127.0.0.1:8000/${path}`;
  // ...
}
```

**Security**:
- Path whitelist validation (`ALLOWED_PATHS`)
- Timeout control (120s for long tasks, 30s for regular)
- Path normalization (prevent traversal attacks)

---

## Type System

### Auto-Generated Types (`lib/types.ts`)

**Source**: `backend/models/` → `scripts/sync-types.py` → `lib/types.ts`

**Header**:
```typescript
// AUTO-GENERATED FILE - DO NOT EDIT
// Generated from backend/models/ by scripts/sync-types.py
```

**Key Interfaces**:
```typescript
interface Account {
  id: number;
  uid: string;
  name: string;
  sessdata: string;
  bili_jct: string;
  status: "active" | "invalid" | "expiring";
  created_at: string;
  updated_at: string;
}

interface Target {
  id: number;
  type: "video" | "comment" | "user";
  aid?: number;
  oid?: number;
  rpid?: number;
  mid?: number;
  reason_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  retry_count: number;
}
```

**Type Aliases**:
```typescript
type TargetStatus = "pending" | "processing" | "completed" | "failed";
type TargetType = "video" | "comment" | "user";
type TaskType = "report_batch" | "autoreply_poll";
```

### Date Handling (`lib/datetime.ts`)

```typescript
export function parseDateWithUtcFallback(dateStr: string): Date {
  // Auto-add UTC suffix for backend timestamps
  if (!dateStr.endsWith("Z") && !dateStr.includes("+")) {
    return new Date(dateStr + "Z");
  }
  return new Date(dateStr);
}
```

---

## Styling

### Tailwind CSS 4 (`app/globals.css`)

**B站 Brand Colors**:
```css
--primary: #fb7299;  /* Pink */
--accent: #00a1d6;   /* Blue */
```

**Custom Utility Classes**:
```css
.card-elevated {
  @apply transition-all duration-300 hover:shadow-lg hover:-translate-y-1;
}

.card-static {
  @apply shadow-md;
}

.bg-gradient-subtle {
  background: linear-gradient(135deg, #fef5f8 0%, #f5f5f5 50%, #e6f7ff 100%);
}

.shadow-pink-glow {
  box-shadow: 0 0 20px rgba(251, 114, 153, 0.3);
}
```

**Custom Scrollbar**:
```css
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
```

### Design Style

- **Glassmorphism** (frosted glass effects)
- **Cyberpunk aesthetic**
- **Dark theme support** (via CSS variables)
- **Elevation shadows** (card hover effects)
- **Gradient backgrounds** (subtle pink→gray→blue)

---

## Key Patterns

### 1. SWR Data Fetching

```typescript
// Pattern: Fetch + auto-refresh
const { data, error, isLoading, mutate } = useAccounts();

// Manual revalidation
await mutate();

// Optimistic update
mutate(newData, false);  // Update UI immediately
await api.accounts.update(id, newData);
mutate();  // Revalidate from server
```

### 2. WebSocket + SWR Merge

```typescript
// Dashboard: Merge real-time logs + historical logs
const { logs: wsLogs } = useLogStream(100);
const { data: apiLogs } = useReportLogs(100);

const allLogs = useMemo(() => {
  return [...wsLogs, ...(apiLogs || [])].sort((a, b) => 
    new Date(b.executed_at).getTime() - new Date(a.executed_at).getTime()
  );
}, [wsLogs, apiLogs]);
```

### 3. Toast Notifications

```typescript
import { toast } from "sonner";

// Success
toast.success("操作成功");

// Error
toast.error("操作失败", { description: error.message });

// Loading
const toastId = toast.loading("处理中...");
// ... operation ...
toast.success("完成", { id: toastId });
```

### 4. Confirm Dialog

```typescript
const { confirm } = useConfirm();

const handleDelete = async () => {
  const confirmed = await confirm({
    title: "确认删除",
    description: "此操作不可撤销",
  });
  if (confirmed) {
    await api.targets.delete(id);
  }
};
```

### 5. QR Login Flow

```typescript
// QRLoginModal.tsx
const [qrUrl, setQrUrl] = useState<string>("");
const [qrKey, setQrKey] = useState<string>("");

// 1. Generate QR code
const { qr_url, qr_key } = await api.auth.generateQR();
setQrUrl(qr_url);
setQrKey(qr_key);

// 2. Poll for scan result
const interval = setInterval(async () => {
  const result = await api.auth.pollQR(qr_key);
  if (result.status === "success") {
    clearInterval(interval);
    onSuccess(result.cookies);
  }
}, 2000);
```

---

## Common Gotchas

### 1. Type Sync

**Problem**: Frontend types out of sync with backend schemas.

**Solution**: Run `python scripts/sync-types.py` after backend schema changes.

### 2. Date Parsing

**Problem**: Backend returns ISO strings without `Z` suffix, causing timezone issues.

**Solution**: Use `parseDateWithUtcFallback()` from `lib/datetime.ts`.

### 3. SWR Deduplication

**Problem**: Multiple components fetching same data cause duplicate requests.

**Solution**: SWR auto-deduplicates within 10s window (configured in `lib/swr.ts`).

### 4. WebSocket Reconnection

**Problem**: WebSocket disconnects on network issues.

**Solution**: `useLogStream` auto-reconnects with exponential backoff (3s→30s).

### 5. API Proxy Timeout

**Problem**: Long operations (batch reports) timeout at 30s.

**Solution**: Proxy uses 120s timeout for specific paths (configured in `route.ts`).

---

## Development Workflow

### Before Coding

1. Read `.trellis/spec/frontend/index.md`
2. Read relevant topic docs (components, hooks, state management)

### During Development

1. Follow guidelines strictly
2. Run `bun run lint` frequently
3. Check browser console for errors

### After Development

1. Run `bun run lint`
2. Manual testing in browser
3. Check responsive design (mobile/desktop)

---

## Performance Optimization

### 1. useMemo for Expensive Computations

```typescript
const filteredTargets = useMemo(() => {
  return targets.filter(t => t.status === "pending");
}, [targets]);
```

### 2. Parallel Data Fetching

```typescript
// Fetch multiple resources in parallel
const { data: accounts } = useAccounts();
const { data: targets } = useTargets();
const { data: logs } = useReportLogs(100);
```

### 3. SWR Deduplication

```typescript
// Multiple components using same hook = single request
const { data } = useAccounts();  // Component A
const { data } = useAccounts();  // Component B (reuses A's request)
```

---

## Accessibility

- **Radix UI primitives** (ARIA labels, keyboard navigation)
- **Semantic HTML** (proper heading hierarchy)
- **Focus management** (modal traps, tab order)
- **Screen reader support** (aria-label, aria-describedby)

---

## Resources

- **Guidelines**: `.trellis/spec/frontend/`
- **Component Library**: `src/components/ui/`
- **API Client**: `src/lib/api.ts`
- **Type Definitions**: `src/lib/types.ts`
