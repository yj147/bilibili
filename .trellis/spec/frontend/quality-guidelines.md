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
| sonner | Latest | Toast notifications |

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
5. **No `alert()` or `confirm()` calls** — use sonner for toasts, `useConfirm` hook for confirmations
6. **No `any` types** — use `unknown` with proper narrowing instead

---

## UI/UX Standards

- **Light theme**: B站-inspired with pink primary (`#fb7299`), blue accent (`#00a1d6`)
- **Background**: Subtle gradient (`bg-gradient-subtle`), cards use `card-elevated` for hover depth
- **Status colors**: Green=active, Red=failed, Blue=connected, Yellow=warning
- **Loading**: `animate-spin` on buttons, empty state messages in Chinese
- **Language**: UI text in Chinese, code in English

---

## Accessibility (WCAG Level A)

### Icon Button Labels

**Problem**: Icon-only buttons are not accessible to screen readers.

**Solution**: Add `aria-label` to all icon buttons.

```tsx
// Good — accessible icon button
<Button
  variant="ghost"
  size="icon"
  onClick={() => handleEdit(target)}
  aria-label="编辑目标"
>
  <Pencil size={16} />
</Button>
```

**Why**: Screen readers can announce button purpose to visually impaired users.

### Color-Independent Status Indicators

**Problem**: Status indicators that rely only on color fail WCAG guidelines and are inaccessible to colorblind users.

**Solution**: Add screen-reader-only text alongside color indicators.

```tsx
// Good — color + text
<div className="flex items-center justify-center gap-1">
  <div className={`w-2 h-2 rounded-full ${statusColor}`} />
  <span className="sr-only">{statusLabel}</span>
</div>
```

**Why**: Provides status information through multiple channels (color + text), ensuring accessibility for all users.
- **Confirmations**: shadcn AlertDialog via `useConfirm` hook (not native `confirm()`)
- **Toasts**: sonner (`toast.success/error/warning` + `<Toaster richColors />`)

---

## Common Commands

```bash
cd frontend
bun run dev       # Development server
bun run build     # Production build
bun run lint      # ESLint
```

---

## UI Automation Reliability (agent-browser)

### Problem: false failures from stale browser session state

When `agent-browser` reuses a long-lived default session, UI巡检 may report stale chunk-load errors from older runs, even though current page/network status is healthy.

### Required Pattern

1. Use a **dedicated session id** per test run (for example `ui-smoke-<timestamp>`).
2. Keep checks inside one run/session and avoid cross-run state reuse.
3. If `agent-browser` is unavailable or unstable, **fallback to chrome-devtools MCP** for page巡检.

```bash
# Good: isolated session for this run
agent-browser --session "ui-smoke-1700000000" open http://127.0.0.1:3000
agent-browser --session "ui-smoke-1700000000" wait --load networkidle
agent-browser --session "ui-smoke-1700000000" errors
```

### Why

- Prevents false positives caused by cached runtime/chunk metadata from previous runs.
- Keeps UI automation deterministic for long-loop regression pipelines.

## Target Batch Import Tokenization

### Problem: newline-only split merges multiple targets

If batch input is parsed only with `split("\n")`, content like `BV1a BV1b` or `BV1a,BV1b` can be treated as one identifier.

### Required Pattern

Use delimiter normalization that supports whitespace and common separators:

```ts
const identifiers = raw
  .split(/[\s,;]+/)
  .map((s) => s.trim())
  .filter(Boolean);
```

### Why

- Keeps batch import behavior consistent with actual user input habits.
- Avoids hidden data quality issues where one malformed identifier contains multiple targets.
- Improves E2E reliability for frontend automation scripts.

## Full Frontend Browser Automation Baseline

- For "frontend all features" validation, run `tests/run_ui_agent_browser_full.py`.
- This script must cover all six pages and assert key side effects through API, not only page load checks.
- Keep `tests/run_ui_agent_browser_smoke.py` as a fast precheck; treat it as smoke only, not full coverage.

## Scenario: Full Frontend Browser Automation Contract (agent-browser + proxy API)

### 1. Scope / Trigger

- Trigger: when requirement is "前端全部功能覆盖" or when sticky UI automation bugs were fixed.
- Scope: dashboard / accounts / targets / autoreply / scheduler / config full interaction path.

### 2. Signatures

```bash
# Fast precheck (smoke only)
python3 tests/run_ui_agent_browser_smoke.py

# Full feature coverage (required for "all frontend features")
python3 tests/run_ui_agent_browser_full.py
```

### 3. Contracts (request/response/env)

- Env contract:
  - backend process must run with `SENTINEL_API_KEY=<key>`
  - frontend process must run with `NEXT_PUBLIC_API_KEY=<key>`
- Connectivity contract:
  - `GET http://127.0.0.1:8000/health` returns `200`
  - `GET http://127.0.0.1:3000/` returns `200`
  - `GET http://127.0.0.1:3000/api/accounts/` returns `200`
- Execution contract:
  - use dedicated session id (`ui-full-<timestamp>` / `ui-smoke-<timestamp>`)
  - full script must assert side effects through frontend proxy API or backend route log evidence, not only UI clicks

### 4. Validation & Error Matrix

| Condition | Validation | Failure Signal | Required Action |
|---|---|---|---|
| agent-browser unavailable | `agent-browser --help` | script exits with code `2` | stop and fallback to `chrome-devtools` MCP |
| stale session contamination | unique session per run | false chunk/open errors across rounds | regenerate isolated session id and rerun |
| React controlled input not synced | verify saved value via API | UI shows updated text but API value unchanged | use prototype setter + dispatch `input` and `change` |
| "full coverage" run | full report/checklist | less than all checks PASS | treat as incomplete, do not mark done |

### 5. Good / Base / Bad Cases

- Good: `tests/run_ui_agent_browser_full.py` reports `43/43 PASS` with report artifact and checklist artifact.
- Base: `tests/run_ui_agent_browser_smoke.py` reports page health only (smoke gate).
- Bad: only running smoke and claiming full coverage, or only checking page loads without API-side assertions.

### 6. Tests Required (assertion points)

- Smoke required:
  - 6 pages * 3 rounds load checks (readyState complete, no console errors).
- Full coverage required:
  - all 6 pages include functional actions (create/edit/delete/toggle/submit/save paths).
  - assert key effects by API/log, e.g.:
    - accounts actions call corresponding `/api/accounts/*` or `/api/auth/*`
    - targets execute/batch/scan paths call `/api/reports/*`
    - config save persists all changed fields in `/api/config/`

### 7. Wrong vs Correct

#### Wrong

```js
// Looks changed in DOM but may not update React controlled state.
input.value = "new value";
input.dispatchEvent(new Event("change", { bubbles: true }));
```

#### Correct

```js
// Use native setter + input/change to notify React value tracker.
const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, "value")?.set;
setter?.call(input, "new value");
input.dispatchEvent(new Event("input", { bubbles: true }));
input.dispatchEvent(new Event("change", { bubbles: true }));
```

---

## Pre-Commit Checklist

- [ ] `"use client"` on pages using hooks
- [ ] SWR hooks for data fetching
- [ ] `mutate()` called after mutations
- [ ] Default values for SWR data
- [ ] Chinese text for UI labels
- [ ] Types match backend schemas
- [ ] No `confirm()` or `alert()` calls

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
