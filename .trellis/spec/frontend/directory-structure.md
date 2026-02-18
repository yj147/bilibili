# Directory Structure

> How frontend code is organized in Bili-Sentinel.

---

## Overview

The frontend is a **Next.js 16** app using **React 19**, **Tailwind CSS 4**, **SWR** for data fetching, **Framer Motion** for animations, and **shadcn/ui** (Radix UI) for base components.

---

## Directory Layout

```
frontend/
├── next.config.ts              # Next.js configuration
├── package.json                # Dependencies
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout (Sidebar + ErrorBoundary)
│   │   ├── page.tsx            # Dashboard (/)
│   │   ├── globals.css         # Tailwind + custom styles
│   │   ├── accounts/page.tsx   # Account management
│   │   ├── targets/page.tsx    # Target management
│   │   ├── autoreply/page.tsx  # Auto-reply config
│   │   ├── scheduler/page.tsx  # Task scheduler
│   │   ├── config/page.tsx     # System configuration
│   │   └── api/[...path]/route.ts  # API proxy to backend
│   ├── components/
│   │   ├── Sidebar.tsx         # Navigation sidebar
│   │   ├── BentoCard.tsx       # Reusable bento grid card
│   │   ├── StatItem.tsx        # Statistics display
│   │   ├── ErrorBoundary.tsx   # React error boundary
│   │   └── ui/                 # shadcn/ui primitives
│   └── lib/                    # Shared utilities
│       ├── api.ts              # API client with auth headers
│       ├── types.ts            # TypeScript interfaces
│       ├── swr.ts              # SWR hooks per resource
│       ├── websocket.ts        # WebSocket hook for real-time logs
│       └── utils.ts            # cn() helper
```

---

## Key Conventions

### Pages
- Each page is `"use client"` (SWR requires client rendering)
- One page per route: `app/{feature}/page.tsx`
- Pages use SWR hooks for data, api client for mutations

### Components
- Custom components: `components/` (PascalCase filenames)
- UI primitives: `components/ui/` (shadcn/ui, lowercase filenames)

### Data Flow
```
Page -> SWR hook (lib/swr.ts) -> fetch (lib/api.ts) -> API proxy -> Backend
     -> api client (lib/api.ts) for mutations
     -> WebSocket hook (lib/websocket.ts) for real-time
```

---

## Naming Conventions

| Item | Convention | Example |
|------|-----------|--------|
| Pages | `page.tsx` in feature folder | `app/targets/page.tsx` |
| Components | PascalCase `.tsx` | `BentoCard.tsx` |
| UI primitives | lowercase `.tsx` | `button.tsx` |
| Lib modules | camelCase `.ts` | `api.ts`, `swr.ts` |
| Types | PascalCase interfaces | `Account`, `TargetListResponse` |
| SWR hooks | `use{Resource}` | `useAccounts()` |

---

## Anti-Patterns to Avoid

1. **Calling backend directly in page components**

```typescript
// Bad (inside app/*/page.tsx)
const res = await fetch("http://127.0.0.1:8000/api/accounts");
```

```typescript
// Good
const { data: accounts = [] } = useAccounts();
```

2. **Putting shared components under route folders**
- Shared widgets belong in `components/`, not `app/{feature}/`.
- Route folder should only keep page-local composition code.

3. **Duplicating API types outside `lib/types.ts`**
- Keep shared contracts centralized in `lib/types.ts`.
- Re-declaring the same interface in `page.tsx` causes drift and breaks sync.
