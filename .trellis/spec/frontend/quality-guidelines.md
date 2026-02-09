# Quality Guidelines

> Code quality standards for Bili-Sentinel frontend.

---

## Tech Stack

| Technology | Version | Purpose |
|-----------|---------|--------|
| Next.js | 16 | App framework (App Router) |
| React | 19 | UI library |
| TypeScript | 5.9+ | Type safety |
| Tailwind CSS | 4 | Styling |
| SWR | 2.4 | Data fetching |
| Framer Motion | 12 | Animations |
| Lucide React | Latest | Icons |
| shadcn/ui | Latest | UI primitives |

---

## Required Patterns

1. **SWR for all server data** (not raw fetch/useEffect)
2. **api client for mutations** (centralized auth/error handling)
3. **cn() for conditional classes** (`import { cn } from "@/lib/utils"`)
4. **Default values for SWR data** (`const { data: accounts = [] } = useAccounts()`)
5. **ErrorBoundary wrapping** (via layout.tsx)

---

## Forbidden Patterns

1. **No Server Components for interactive pages** — all feature pages need `"use client"`
2. **No importing backend code** — communicate only via HTTP/WS
3. **No global CSS for component styles** — use Tailwind utilities
4. **No hardcoded API base URL** — use `process.env.NEXT_PUBLIC_API_BASE || '/api'`
5. **No `alert()` calls** — use the Toast component for all user notifications
6. **No `any` types** — use `unknown` with proper narrowing instead

---

## UI/UX Standards

- **Dark theme**: `bg-black`, `text-white`, glass-card effects
- **Status colors**: Green=active, Red=failed, Blue=connected, Yellow=warning
- **Loading**: `animate-spin` on buttons, empty state messages in Chinese
- **Language**: UI text in Chinese, code in English

---

## Common Commands

```bash
cd frontend
npm run dev       # Development server
npm run build     # Production build
npm run lint      # ESLint
```

---

## Pre-Commit Checklist

- [ ] `"use client"` on pages using hooks
- [ ] SWR hooks for data fetching
- [ ] `mutate()` called after mutations
- [ ] Default values for SWR data
- [ ] Chinese text for UI labels
- [ ] Types match backend schemas

---

## Styling Conventions Clarification

### cn() vs Template Literals

- **Use `cn()`** when combining multiple conditional classes or merging Tailwind classes that may conflict
- **Template literals are acceptable** for simple, single-condition toggles:

```tsx
// cn() — multiple conditionals or class conflicts
<div className={cn("base", isActive && "bg-green-500", isError && "bg-red-500")} />

// Template literal — simple single toggle (acceptable)
<div className={`w-2 h-2 rounded-full ${isActive ? 'bg-green-500' : 'bg-red-500'}`} />
```

### Toast Dedup Pattern (useRef + Set)

When SWR polling causes re-renders, use `useRef<Set>` to prevent duplicate side effects:

```tsx
const notifiedRef = useRef(new Set<number>());
useEffect(() => {
  items.forEach(item => {
    if (shouldNotify(item) && !notifiedRef.current.has(item.id)) {
      notifiedRef.current.add(item.id);
      showNotification(item);
    }
  });
}, [items]);
```

**Why**: SWR `refreshInterval` triggers re-renders every cycle. Without dedup, notifications fire repeatedly.
