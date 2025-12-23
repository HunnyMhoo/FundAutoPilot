# US1 — Browse fund catalog (Executive-demo quality)

## One open question (with recommendation)
**Question:** What is the default catalog ordering for MVP?
- A) Fund Name A–Z (deterministic)
- B) “Popular / trending” (requires analytics + ranking logic)
- C) “Curated collections” (requires curation rules)

**Recommendation:** A) Fund Name A–Z for MVP. It keeps pagination stable and makes “across all AMCs” feel credible without extra dependencies.

**Assumption for this story (until you override):** A) Fund Name A–Z

---

## User story
As a user, I want to browse a catalog of mutual funds across AMCs so that I can discover candidate funds.

## Executive “wow” intent
- Prove “Funds across all AMCs” through a premium discovery experience:
  - fast initial load
  - stable results
  - graceful handling of missing data
  - clean, predictable UX under scale

---

## Scope

### In scope
- Fund Catalog screen (anonymous-first)
- Server-side cursor pagination with a **Load more** button
- Fund list item displays:
  - Fund Name (required)
  - AMC (required)
  - Category (optional; show “Not available” if missing)
  - Risk Level (optional; show “Not available” if missing)
  - Fee/Expense (optional; show “Not available” if missing)
- UI states: initial loading, load-more loading, empty, error with retry
- Clicking a fund navigates to Fund Detail route (US4 content is not required in US1)

### Out of scope
- Search (US2)
- Filters & sorting UI (US3)
- Compare tray (US5)
- Trending/popularity ranking
- Login / profiles / personalization

---

## Fund data source and freshness (MVP)

### Source of truth (recommended)
- Use **Thai SEC open datasets (iDISC / SEC open data)** as the primary system-of-record for the fund universe and core attributes.
- Rationale: authoritative coverage “across AMCs”, consistent identifiers, and predictable ingestion.

### Data ingestion approach (MVP)
- Batch ingest into an internal **Fund Master** store (e.g., daily or weekly job depending on availability).
- Store a `data_snapshot_id` (or `as_of_date`) with each ingestion so the catalog results are reproducible for demo/debug.

### Field mapping for US1
- Fund Name: from fund master dataset
- AMC: from fund master dataset
- Category: from classification dataset (if present) else null
- Risk Level: if available from factsheet/classification else null
- Fee/Expense: if available from fees/expenses dataset else null

### Coverage rules (what users see)
- If optional fields are missing, the UI shows “Not available” (never blank, never broken layout).
- If required fields are missing (fund name / AMC / id), record is excluded from the catalog output (preferred), or rendered as a safe placeholder (minimum).

### Freshness badge (optional but high “wow”, still small scope)
- Show a small “Data updated: <as_of_date>” label in the catalog header.
- If not implemented, keep as a non-blocking enhancement.

---

## UX requirements (behavioral spec)

### Layout
- Header: “Fund Catalog”
- List rows/cards:
  - Primary: Fund Name
  - Secondary: AMC • Category
  - Metadata: Risk Level, Fee/Expense

### Initial load
- Show skeleton rows/spinner placeholders while fetching page 1.
- Do not show empty state until a successful response returns zero items.

### Load more button
- Visible only when `next_cursor` exists.
- On click:
  - Button becomes disabled and shows “Loading…”
  - Append new items below existing list (no reset / no jump to top)
  - Prevent concurrent requests (ignore clicks while in-flight)
- When `next_cursor` is null:
  - Replace with “End of results” (or disable/hide Load more)

### Empty state
- Message: “No funds available”
- Action: Retry (re-fetch page 1)

### Error states
- Initial load error:
  - Inline error message + Retry (re-fetch page 1)
- Load more error:
  - Keep existing items visible
  - Inline error near bottom + Retry (re-fetch with same cursor)

### Resilience rules
- De-duplicate appended results by `fund_id` to avoid duplicate rows if API returns overlaps.

---

## API contract (MVP)

### Endpoint
GET /funds?limit=25&cursor=<token>&sort=name_asc

### Response
- items: FundSummary[]
- next_cursor: string | null
- as_of_date: string (recommended)
- data_snapshot_id: string (optional but recommended)

### FundSummary (minimum)
- fund_id: string
- fund_name: string
- amc_name: string
- category?: string | null
- risk_level?: string | number | null
- expense_ratio?: number | null

### Determinism requirement
- For a given `data_snapshot_id`, the same inputs (limit/cursor/sort) return stable ordering and cursor progression.

---

## Non-functional requirements (MVP guardrails)
- Target dataset: 5,000–20,000 funds
- Page size default: 25 (configurable)
- UI remains responsive while appending at least 200 items (virtualization optional unless needed)
- No double-fetch on Load more

---

## Acceptance Criteria (demo-ready)

### AC1 — Minimum catalog content
- Catalog shows Fund Name and AMC for every rendered row.
- Category/Risk/Fee show value or “Not available”.
- Layout remains consistent even when optional fields are missing.

### AC2 — Initial loading / success / failure states
- On open: loading state is shown until response arrives.
- On success: list renders page 1.
- On failure: error state renders with Retry.

### AC3 — Load more works and is safe
- Load more appends results using server-side cursor pagination.
- Load more is disabled while in-flight.
- Duplicate fund rows are not shown (de-dupe by fund_id).

### AC4 — End of results
- When next_cursor is null, UI indicates end-of-results and prevents further loads.

### AC5 — Non-destructive load more error
- If load more fails, page 1 stays visible.
- Inline error near bottom shows Retry.
- Retry re-attempts the same cursor request.

### AC6 — Click-through navigation
- Clicking a fund navigates to the fund detail route using fund_id without breaking the catalog state.

### AC7 — Data coverage handling
- Missing optional fields do not break rendering.
- Missing required fields do not crash the UI and do not produce broken rows.

---

## Definition of Done (DoD)
- Implement catalog screen + API integration + Load more pagination.
- Test scenarios:
  - 3+ pages of results
  - missing optional fields across many rows
  - initial load error then retry success
  - load more error then retry success
  - next_cursor null (end-of-results)
  - duplicate fund_id across pages (de-dupe verified)
- Demo readiness:
  - page 1 loads quickly
  - load more shows smooth append
  - error states are clean and recoverable

---

## Short executive demo script (45–60s)
1. Open Fund Catalog: “This is the across-AMC universe.”
2. Scroll: point out clean rows and “Not available” handling (no broken UI).
3. Click Load more: show stable append without refresh.
4. Trigger a load-more failure: show inline error + Retry while list remains.
5. Retry succeeds: “This scales coverage without sacrificing UX.”
