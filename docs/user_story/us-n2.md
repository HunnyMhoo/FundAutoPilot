# US-N2 — Fund Detail That Feels Real (Detail API + Credible Key Facts + State-Preserving Navigation)

## One open question (with recommendation)
**Question:** For preserving catalog state when navigating back, do you want **(A)** URL-based state (query params like `?q=...&amc=...&cat=...`) or **(B)** router/session state only?

**Recommendation:** Choose **(A) URL-based state**. It is more reliable (refresh-safe), enables shareable deep links, and prevents “lost context” trust breaks during demos.

---

## Problem / Opportunity
Discovery is not complete until users can click a fund and evaluate it with real data. A thin or placeholder detail page breaks credibility and blocks downstream workflows (compare, switch simulation).

## User story
As a user, I want to open a fund and see a clear detail view with credible key facts and data freshness, so that I can evaluate it before comparing or simulating a switch.

## Executive “wow” intent
Complete the loop: **browse → click → evaluate** with a detail experience that feels production-grade (real data, freshness metadata, and graceful missing-data handling).

## User value / business value
- Creates an end-to-end complete discovery experience (no dead ends).
- Increases conversion into compare/switch workflows.
- Reduces user uncertainty by making data freshness and coverage explicit.

## In scope
### Backend — Fund Detail API
- Implement `GET /funds/{fund_id}` returning:
  - Fund identity: `fund_id`, `fund_name`, `fund_abbr`, `category`
  - AMC: `amc_id`, `amc_name` (embedded or flattened)
  - Key facts (nullable): `risk_level`, `expense_ratio`
  - Metadata: `as_of_date` (snapshot), `last_updated_at`, `data_source` (nullable), `data_version` (optional)
- Validation + error handling:
  - 400 for invalid `fund_id` shape (fail fast, no DB query)
  - 404 for well-formed `fund_id` not found
  - 500 for unexpected server errors (with safe error payload)

### Frontend — Fund Detail Page
- Detail view displays:
  - Header: fund name + abbreviation
  - Context row: AMC + category
  - “Key facts” card:
    - Risk level (with “Not available” handling)
    - Expense ratio (with “Not available” handling)
  - Data freshness badge:
    - Show `as_of_date` (primary) and/or `last_updated_at` (secondary)
    - Show `data_source` as a small metadata row or tooltip
- UX states:
  - Loading state (skeleton or spinner)
  - Error state with retry
  - 404 state: “Fund not found” + back to catalog
- Navigation:
  - “Back to catalog” restores prior catalog state (filters/search/sort) via URL-based state (recommended)

## Out of scope
- NAV/performance charts, holdings, portfolio analytics, factsheet PDF rendering.
- Favorites/watchlist, authentication, user personalization.
- Compare and switch simulator features (this story unblocks them but does not implement them).

## Functional requirements
### Data contract (minimum required to render credibly)
- Required fields for successful response (200):
  - `fund_id`, `fund_name`, `category`, `amc_name`
  - At least one freshness indicator: `as_of_date` OR `last_updated_at`
- Nullable fields:
  - `fund_abbr`, `risk_level`, `expense_ratio`, `data_source`

### Missing data handling (UI)
- If `risk_level` is null:
  - Display “Not available”
  - Show a short explanation tooltip/text: “Risk level not provided in current dataset.”
- If `expense_ratio` is null:
  - Display “Not available”
  - Show a short explanation tooltip/text: “Fee data not available for this fund yet.”
- Data coverage message (only when needed):
  - If any key fact is missing, show a subtle note: “Some data fields are still being populated.”

### State preservation
- Catalog page encodes state in URL:
  - Example: `/funds?q=k-usx&amc=KAsset&cat=Equity&sort=popularity`
- Fund detail page retains the catalog URL as the back target:
  - Example: from `/funds?...` to `/funds/{fund_id}?from=/funds?...` (or equivalent router pattern)
- Back action returns to catalog with the exact prior query params intact.

## Acceptance criteria (Given / When / Then)
### AC1 — Real detail page (no placeholder)
- **Given** I am on the fund catalog
- **When** I click a fund card
- **Then** I see a fund detail page populated with real data from `GET /funds/{fund_id}` (not placeholder text).

### AC2 — Loading, error, retry
- **Given** the detail API call is in progress
- **Then** the page shows a loading state (skeleton/spinner) until data renders.
- **Given** the API call fails (network/server)
- **Then** an error state is shown with a “Retry” action that re-attempts the request.

### AC3 — Not found (404)
- **Given** I navigate to `/funds/{fund_id}` with a well-formed but nonexistent `fund_id`
- **Then** the UI shows “Fund not found” and offers “Back to catalog.”

### AC4 — Null key facts render safely
- **Given** `risk_level` and/or `expense_ratio` is null
- **When** the detail page renders
- **Then** those fields display “Not available” with a short explanation, and the page remains visually complete.

### AC5 — Data freshness visibility
- **Given** the API returns `as_of_date` and/or `last_updated_at`
- **Then** the UI shows a freshness badge including the date, and displays `data_source` if provided.

### AC6 — Back preserves catalog state
- **Given** I arrived from the catalog with search/filters applied
- **When** I press “Back to catalog” (or browser back)
- **Then** I return to the catalog with the same search term, filters, and sort intact.

### AC7 — Backend automated tests
- Backend includes tests for:
  - 200 success (valid ID returns expected payload shape)
  - 404 not found (valid shape, missing record)
  - 400 invalid ID shape (fails validation without DB query)

### AC8 — Frontend automated coverage (minimum)
- At least one automated check verifies:
  - 404 state renders correctly
  - Back navigation preserves URL query params (state restoration)

## Demo script (30–60s)
1. From Fund Catalog, apply a search/filter (so the state is visible).
2. Click a fund card → detail loads with “Key facts” and freshness badge.
3. Point out graceful “Not available” handling (if applicable).
4. Click “Back to catalog” → confirm the exact search/filter state is preserved.

## Implementation notes (key components touched)
- Backend:
  - Route: `GET /funds/{fund_id}`
  - Service: `getFundById(fund_id)`
  - DB query: fetch fund + AMC (join/lookup) + metadata snapshot fields
  - Validation: ID shape validator (shared utility)
- Frontend:
  - Route: `/funds/:fund_id`
  - Data fetch hook/service with retry support
  - UI components: Header, KeyFactsCard, FreshnessBadge, ErrorState/NotFoundState
  - Navigation: URL param preservation + back link construction

## Dependencies / prerequisites
- Stable, unique fund identifier used consistently across:
  - catalog list payload
  - detail endpoint path parameter
- Availability of AMC reference data (embedded in fund record or joinable by `amc_id`).

## Risks & mitigations
- **Risk:** Detail page feels thin due to missing fields in dataset.
  - **Mitigation:** Make “Key facts” visually strong, add “Not available” explanations, and include freshness/source metadata to maintain credibility.
- **Risk:** Back navigation loses state due to routing implementation.
  - **Mitigation:** Use URL-based state as the source of truth; add an automated test for state restoration.

## Delivery plan (vertical slices)
### Increment A — Minimal credible detail (smallest demoable slice)
- Backend: `GET /funds/{fund_id}` returns `fund_name`, `category`, `amc_name`, freshness field.
- Frontend: detail page renders header + basic info + loading/error states.

### Increment B — Full scope + trust UX
- Backend: add `fund_abbr`, `risk_level`, `expense_ratio`, `as_of_date`, `data_source`.
- Frontend: Key facts card with null handling + freshness badge + 404 state.
- Navigation: back-to-catalog state preservation (URL-based).

### Increment C — Optional executive polish
- “Share link” (copy-to-clipboard) for the fund detail URL (retains catalog origin where applicable).
- Compact “Key facts” card layout refinement for demo clarity.
