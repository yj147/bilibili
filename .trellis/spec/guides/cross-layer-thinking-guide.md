# Cross-Layer Thinking Guide

> **Purpose**: Think through data flow across layers before implementing.

---

## The Problem

**Most bugs happen at layer boundaries**, not within layers.

Common cross-layer bugs:
- API returns format A, frontend expects format B
- Database stores X, service transforms to Y, but loses data
- Multiple layers implement the same logic differently

---

## Before Implementing Cross-Layer Features

### Step 1: Map the Data Flow

Draw out how data moves:

```
Source → Transform → Store → Retrieve → Transform → Display
```

For each arrow, ask:
- What format is the data in?
- What could go wrong?
- Who is responsible for validation?

### Step 2: Identify Boundaries

| Boundary | Common Issues |
|----------|---------------|
| API ↔ Service | Type mismatches, missing fields |
| Service ↔ Database | Format conversions, null handling |
| Backend ↔ Frontend | Serialization, date formats |
| Component ↔ Component | Props shape changes |

### Step 3: Define Contracts

For each boundary:
- What is the exact input format?
- What is the exact output format?
- What errors can occur?

---

## Common Cross-Layer Mistakes

### Mistake 1: Implicit Format Assumptions

**Bad**: Assuming date format without checking

**Good**: Explicit format conversion at boundaries

### Mistake 2: Scattered Validation

**Bad**: Validating the same thing in multiple layers

**Good**: Validate once at the entry point

### Mistake 3: Leaky Abstractions

**Bad**: Component knows about database schema

**Good**: Each layer only knows its neighbors

---

## Checklist for Cross-Layer Features

Before implementation:
- [ ] Mapped the complete data flow
- [ ] Identified all layer boundaries
- [ ] Defined format at each boundary
- [ ] Decided where validation happens

After implementation:
- [ ] Tested with edge cases (null, empty, invalid)
- [ ] Verified error handling at each boundary
- [ ] Checked data survives round-trip

---

## When to Create Flow Documentation

Create detailed flow docs when:
- Feature spans 3+ layers
- Multiple teams are involved
- Data format is complex
- Feature has caused bugs before

---

## Case Study: QR Login Flow (Cross-Layer)

This feature spans 4 layers:

```
QRLoginModal (Frontend) → Next.js API Proxy → FastAPI Router → auth_service → Bilibili API
```

### Data Flow

| Step | Frontend | Backend | Bilibili |
|------|----------|---------|----------|
| 1. Generate | `api.auth.qrGenerate()` | `POST /api/auth/qr/generate` | `passport.bilibili.com/x/passport-login/web/qrcode/generate` |
| 2. Poll | `api.auth.qrPoll(key)` every 2s | `GET /api/auth/qr/poll?qrcode_key=X` | `passport.bilibili.com/x/passport-login/web/qrcode/poll` |
| 3. Save | `api.auth.qrLogin(key)` | `POST /api/auth/qr/login` | Internal: parse cookies + fetch buvid |
| 4. Status | `api.auth.cookieStatus(id)` | `GET /api/auth/cookie-status/{id}` | `passport.bilibili.com/x/passport-login/web/cookie/info` |

### Gotchas at Boundaries

1. **Bilibili → Backend**: QR poll returns status codes (86101=waiting, 86090=scanned, 86038=expired, 0=success) — NOT HTTP status codes
2. **Backend → Frontend**: These are mapped to a `status` string field in the response schema
3. **Frontend timing**: Poll interval must be >=2s to avoid Bilibili rate limiting
4. **Post-login**: buvid3/buvid4 require a separate API call after saving the session
