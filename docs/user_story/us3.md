# US3 — Filter & sort funds (Executive-demo quality)

## User story
As a user, I want to filter by category/AMC/risk/fee band and sort results so that I can narrow options efficiently.

## Executive “wow” intent
- Make discovery feel premium by enabling “search + filters + sort” to work together seamlessly.
- Prove that a large across-AMC universe is still navigable in seconds.

---

## Scope

### In scope
- Filter controls on the Fund Catalog screen:
  - Category
  - AMC
  - Risk Level
  - Fee Band (only if fee/expense data supports it)
- Sorting control that re-orders results without losing search query or filters.
- **Instant apply** behavior for filters and sorting.
- “Clear all” action to reset filters to default.
- Active filter visibility (chips or summary) so the user understands what constraints are applied.
- Pagination remains within the current constraints (search + filters + sort).

### Out of scope
- Advanced multi-step filter builder (AND/OR groups)
- Saved filters / preferences (anonymous-first)
- Multi-select UI complexity beyond basic checklists
- Any “recommended filters” logic (later enhancement)

---

## UX requirements (behavioral spec)

### Filter UI layout (MVP-friendly)
- A filter panel (sidebar on desktop, drawer/modal on mobile) with sections:
  - Category
  - AMC
  - Risk Level
  - Fee Band (only shown if enabled)
- Each section supports multi-select (checkbox list) except:
  - Sorting is single-select.

### Instant apply behavior
- When the user changes any filter:
  - The list refreshes immediately using the new constraints
  - Reset pagination to page 1 for the new constraint set
  - Show a lightweight loading state (no blank screen)
- When the user changes sort:
  - Re-fetch results under the same constraints
  - Reset pagination to page 1

### Active constraint visibility
- Display active constraints as chips above the list (recommended):
  - Example: “AMC: ABC”, “Category: Equity”, “Risk: 5”
- Each chip has an “x” to remove that constraint instantly.
- “Clear all” removes all filters (not the search query unless explicitly designed that way).

### Clear all behavior
- Clears all selected filters back to default (none selected).
- Preserves search query (recommended) so the user doesn’t lose context.
- Resets to page 1 and default sort.

### Loading / empty / error states (within filtered mode)
- Loading: show skeleton rows or inline loading indicator while maintaining layout.
- Empty: “No results for the current filters” + Clear all.
- Error: inline error + Retry; Retry repeats the last request with the same constraints.

---

## Data rules (MVP)

### Available filters (must be data-driven)
- Category: derived from fund master classification
- AMC: derived from fund master
- Risk Level: derived from available risk label/number (nullable)
- Fee Band: derived from `expense_ratio` if present for enough funds

### Fee band definition (simple, deterministic)
If fee/expense exists, bucket into bands (example):
- Low: <= 1.0%
- Medium: > 1.0% and <= 2.0%
- High: > 2.0%
If the fee data coverage is insufficient, hide the Fee Band filter entirely.

### Missing data handling
- Funds with missing values for a filter dimension:
  - Should still appear when that filter is not selected.
  - Should be excluded when the user selects a filter that requires that value.
  - Optional enhancement: add an “Unknown” option per filter (not required for MVP).

---

## Sorting (MVP)

### Sort options (recommended minimum)
- Name A–Z
- Name Z–A
Optional (only if data exists and is reliable):
- Fee low to high (requires expense_ratio coverage)
- Risk low to high (requires risk level coverage)

### Sorting rules
- Sorting must not clear search query or filters.
- Sorting resets to page 1, keeps constraints intact.
- When sorting by fee/risk, funds missing that value:
  - Place them at the end (recommended) and keep deterministic tie-breaker by name.

---

## API contract (composable with US1/US2)

### Endpoint
GET /funds?limit=25&cursor=<token>&q=<query>&amc=<amc_ids>&category=<category_ids>&risk=<risk_values>&fee_band=<fee_band>&sort=<sort_key>

### Notes
- All query params are optional.
- When any constraint changes (including sort), the client drops cursor and re-requests page 1.
- The server returns:
  - items: FundSummary[]
  - next_cursor: string | null
  - (optional) facets: available values + counts (nice-to-have; not required for MVP)

---

## Non-functional requirements (MVP guardrails)
- Must remain responsive under 5,000–20,000 funds.
- Instant apply should feel fast:
  - lightweight loading indicator
  - no UI jumpiness
- Avoid request spam:
  - If the user toggles multiple checkboxes quickly, coalesce requests (simple 150–300ms debounce on filter changes is acceptable).

---

## Acceptance Criteria (demo-ready)

### AC1 — Filters available and data-driven
- Category, AMC, Risk Level filters are available.
- Fee Band appears only when fee/expense data supports it (otherwise hidden).

### AC2 — Instant apply and composability
- Selecting/deselecting a filter updates results immediately.
- Search query (US2) remains active and combined with filters.
- Sorting changes ordering without losing search query or filters.

### AC3 — Clear all behavior
- “Clear all” resets filters to default.
- Search query is preserved (recommended default).
- Results return to page 1 under default sort.

### AC4 — Pagination within constraints
- Load more continues fetching within the current search + filter + sort constraints.
- Changing any constraint resets pagination to page 1.

### AC5 — Active constraints visibility
- Active filters are visible (chips or summary).
- User can remove a single filter via chip “x” and results update instantly.

### AC6 — Empty state for constrained results
- If constraints produce zero results:
  - Show “No results for current filters”
  - Provide Clear all action

### AC7 — Error + Retry
- If a constrained request fails:
  - Inline error is shown with Retry
  - Retry repeats the last request with the same constraints

---

## Definition of Done (DoD)
- Filter panel + sort control implemented.
- Instant apply implemented with stable state management (query + filters + sort + cursor).
- Tested scenarios:
  - apply 2+ filters together
  - remove a single filter chip
  - clear all
  - search + filter combined
  - change sort keeps constraints
  - load more works under constraints
  - empty state under constraints
  - API failure + retry

---

## Short executive demo script (45–60s)
1. Start with a broad catalog (“across AMCs”).
2. Type a search term (US2) to narrow broadly.
3. Apply Category + AMC filters: list tightens instantly (premium feel).
4. Change sort (Name A–Z): constraints remain.
5. Clear all filters: returns to broad catalog without losing the search term (or optionally clears search if you decide).
6. Close: “Even at full coverage, users can find candidates in seconds.”
