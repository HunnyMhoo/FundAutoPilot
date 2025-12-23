# US4 — View fund detail (lean, side panel)

## One open question (with recommendation)
**Question:** When the side panel is open, should background interactions be:
- A) Locked (modal behavior; prevents accidental catalog changes)
- B) Allowed (non-modal; user can still scroll/use catalog behind panel)

**Recommendation:** A) Locked (modal behavior) for MVP. It is simpler to implement, avoids confusing state changes behind the panel, and is more reliable for an executive demo.

**Assumption for this story (until you override):** A) Locked (modal)

---

## User story
As a user, I want a lean fund detail view so that I can decide to compare or simulate.

## Executive “wow” intent
- Keep the user in discovery mode while giving “just enough” detail to act.
- Make the experience feel premium by minimizing page transitions and maintaining context.

---

## Scope

### In scope
- Clicking a fund in the catalog opens a **side panel** with key facts.
- Side panel content (lean):
  - Fund Name
  - AMC
  - Category
  - Risk Level (if available)
  - Fee/Expense ratio (if available)
  - Inception date (if available)
  - Basic performance reference (NAV mini-chart or trailing return) if data exists; else “Not available”
- CTAs inside the panel:
  - Add to Compare
  - Simulate Switch Impact
- Panel states: loading, error with retry, partial data “Not available”
- Close behavior returns user to the exact catalog state (scroll position, loaded pages, applied search/filters/sort).

### Out of scope
- Full factsheet download
- Full analytics, exposures, holdings breakdown
- Editing compare tray behavior beyond add/remove (US5)
- Full simulation flow (US7+)

---

## UX requirements (behavioral spec)

### Panel entry
- User clicks a fund row/card (or a “View details” action).
- Side panel slides in from the right.
- Background is dimmed and locked (modal).

### Panel layout (recommended)
- Header:
  - Fund Name
  - Close (X)
- Body sections:
  1) Key facts (AMC, Category, Risk, Fee, Inception)
  2) Performance reference (mini chart or trailing return summary)
  3) Data coverage note (optional, small)
- Footer (sticky):
  - Primary CTA: “Simulate Switch Impact”
  - Secondary CTA: “Add to Compare” (or toggle state if already added)

### Panel close behavior
- Close via X, Esc, or clicking backdrop.
- On close:
  - Return to catalog exactly as before (including loaded pages and scroll position).
  - Compare tray state (if any) remains unchanged.

### Loading and error states
- Loading:
  - Panel opens immediately with skeleton placeholders.
- Error:
  - Inline error message in panel body + Retry.
  - Catalog behind remains unchanged.

### Missing data handling
- If a field is missing/null:
  - Show “Not available” (no blanks).
- If performance data is missing:
  - Show “Not available” and a short explanation (e.g., “Insufficient NAV history”).

---

## Data requirements

### Minimum identifiers
- `fund_id` is required to fetch details.

### Panel data fields
- fund_id
- fund_name
- amc_name
- category (nullable)
- risk_level (nullable)
- expense_ratio (nullable)
- inception_date (nullable)
- performance_reference (nullable)
  - Either a small NAV series window or trailing returns summary

---

## API contract (MVP)

### Option 1 (recommended): separate detail endpoint
GET /funds/{fund_id}

Response:
- FundDetail object with the fields listed above

### Option 2: expand summary endpoint
GET /funds?include=detail_min&fund_id=<id>
(less clean; only if you want fewer endpoints)

### Performance reference dependency
- If performance is powered by NAV data, this endpoint can:
  - return precomputed trailing returns, or
  - return a small NAV window for charting (e.g., last 6–12 months)

---

## Non-functional requirements (MVP guardrails)
- Panel should open instantly (skeleton while fetching).
- Detail fetch should not block the catalog rendering.
- No layout break when data fields are missing.

---

## Acceptance Criteria (demo-ready)

### AC1 — Panel opens and closes reliably
- Clicking a fund opens a side panel.
- Closing returns to the same catalog state (scroll + loaded pages + constraints preserved).

### AC2 — Key facts render with graceful degradation
- Panel shows Fund Name and AMC.
- Category/Risk/Fee/Inception show value or “Not available”.

### AC3 — Performance reference handling
- If performance data exists, show a basic reference (mini chart or trailing returns).
- If not, show “Not available” (no broken UI).

### AC4 — CTAs present and functional
- Panel includes “Add to Compare” and “Simulate Switch Impact”.
- Add to Compare updates compare tray state (or local state) immediately.
- Simulate Switch Impact routes into scenario builder (even if it’s a stub in Phase 1).

### AC5 — Loading and error states
- Panel shows loading skeleton while fetching.
- If the detail request fails, show error + Retry within the panel.

---

## Definition of Done (DoD)
- Side panel component implemented with modal locking and accessible close methods (X/Esc/backdrop).
- Detail fetch implemented with skeleton loading.
- Tested scenarios:
  - open panel, close panel, verify catalog state preserved
  - missing optional fields
  - missing performance data
  - API failure + retry success
  - add to compare from panel reflects immediately

---

## Short executive demo script (30–45s)
1. Browse catalog and click a fund → side panel opens instantly (premium feel).
2. Point to “lean key facts” (no clutter).
3. Show performance reference or “Not available” handled cleanly.
4. Click “Add to Compare” and “Simulate Switch Impact” CTAs.
5. Close panel → you are back exactly where you were in the catalog (context preserved).
