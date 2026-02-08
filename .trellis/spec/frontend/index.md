# Frontend Development Guidelines

> Best practices for frontend development in Bili-Sentinel.

---

## Overview

Bili-Sentinel frontend is a **Next.js 16** app with **React 19**, using **SWR** for data fetching, **Tailwind CSS 4** for styling, **shadcn/ui** for components, and **Framer Motion** for animations.

Dark-themed dashboard with cyberpunk/sentinel aesthetic, real-time WebSocket logs, bento grid layout, and glassmorphism effects.

---

## Guidelines Index

| Guide | Description | Status |
|-------|-------------|--------|
| [Directory Structure](./directory-structure.md) | File organization, naming | Done |
| [Component Guidelines](./component-guidelines.md) | Component patterns, styling | Done |
| [Hook Guidelines](./hook-guidelines.md) | SWR hooks, WebSocket, API client | Done |
| [State Management](./state-management.md) | SWR server state, local state | Done |
| [Quality Guidelines](./quality-guidelines.md) | Code standards, UI/UX patterns | Done |
| [Type Safety](./type-safety.md) | TypeScript interfaces, backend sync | Done |

---

## Quick Reference

### Key Files

| File | Purpose |
|------|--------|
| `lib/api.ts` | API client with auth headers |
| `lib/swr.ts` | SWR hooks per resource |
| `lib/types.ts` | TypeScript interfaces (mirrors backend) |
| `lib/websocket.ts` | Real-time log stream hook |
| `app/layout.tsx` | Root layout with Sidebar |
| `app/api/[...path]/route.ts` | API proxy to backend |

### Commands

```bash
cd frontend
npm run dev       # Development
npm run build     # Build
npm run lint      # Lint
```
