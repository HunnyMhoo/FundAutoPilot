# US-N3 — Filters That Match the Dataset (Data-Driven Categories/Risk + Full AMC Search)

## One open question (with recommendation)
**Question:** For AMC selection, do you want **(A)** typeahead search with a paginated results list (recommended), or **(B)** a full scrollable AMC list (potentially long) with client-side search?

**Recommendation:** Choose **(A) typeahead + pagination**. It scales with dataset growth, performs reliably, and feels production-grade without loading thousands of AMCs into the browser.

---

## Problem / Opportunity
Hardcoded filter options create immediate distrust (“demo app smell”) and limit discovery to top AMCs/categories. Filters must be sourced from the dataset so users can confidently narrow results and explore niche funds.

## User story
As a user, I want filter options (category and risk) to reflect the actual fund dataset and the AMC filter to let me find any AMC, so that I can narrow results confidently and discover relevant funds beyond the “top 10.”

## Executive “wow” intent
Make discovery feel production-grade: filters look authoritative, complete, and responsive—no hardcoded lists, no missing AMCs.

## User value / business value
- Improves usability and trust through dataset-aligned filters.
- Unlocks meaningful discovery for smaller AMCs and niche categories.
- Increases engagement by making exploration faster and more precise.

## In scope
### Backend — Filter metadata APIs
Provide API-driven filter metadata with distinct values + counts:

1) **Categories**
- `GET /funds/categories`
- Returns list of `{ category, count }`
- Excludes null/empty categories
- Ordered by count desc, then alpha as tie-breaker (deterministic)

2) **Risk levels**
- `GET /funds/risks`
- Returns list of `{ risk_level, count }`
- Excludes null risk values
- Ordered by risk_level asc (or business-defined order), deterministic

3) **AMCs (full coverage)**
- Upgrade `GET /funds/amcs` to support:
  - `q` (search term, prefix/contains) for typeahead
  - pagination: `limit`, `cursor` (or `offset`)
- Returns list of `{ amc_id, amc_name, count }` (count optional but recommended)

### Frontend — Filter panel behavior
- Filter options are loaded from APIs (no hardcoded enumerations).
- Categories and risk filters:
  - show label + count
  - selectable multi-select or single-select per your current UX pattern (keep consistent)
- AMC filter:
  - search input (typeahead)
  - results list supports pagination/loading more
  - selection works for any AMC, not only a top list
- Active filter chips:
  - show selected filters clearly
  - each chip removable
  - “Clear all” restores default catalog state

## Out of scope
- Dynamic faceting where counts recalculate live based on other selected filters.
- Taxonomy governance UI (admin tools, mapping, category renaming).
- ML-based “smart filters” or recommendations.

## Functional requirements
### Metadata contract
- Categories response example shape:
  - `items: [{ value: "Equity", count: 128 }, ...]`
- Risks response example shape:
  - `items: [{ value: 4, count: 52 }, ...]`
- AMCs response example shape:
  - `items: [{ id: "KASSET", name: "KAsset", count: 240 }, ...]`
  - `next_cursor` (if paginated)

### Performance & caching
- Filter metadata endpoints should be cacheable (server-side or client-side) with a short TTL.
- Queries must be index-backed (category/risk/amc) to avoid slow aggregations.

### UX details (minimum)
- Show loading placeholders for filter sections until data arrives.
- If a metadata endpoint fails:
  - show a small inline error with a retry action for that section
  - do not break the entire catalog page

## Acceptance criteria (Given / When / Then)
### AC1 — Categories are dataset-driven
- **Given** categories exist in the DB
- **When** I open the filter panel
- **Then** the category options exactly match distinct non-null categories in the DB (not hardcoded), and each displays a count from the API.

### AC2 — Risks show only available values
- **Given** some funds have `risk_level = null`
- **When** I open the risk filter
- **Then** only non-null risk levels appear, each with a count from the API.

### AC3 — AMC filter finds beyond top 10
- **Given** an AMC exists outside the top 10 by fund count
- **When** I search its name in the AMC filter
- **Then** it appears in results and can be selected and applied.

### AC4 — Applying filters updates results and chips
- **When** I apply any category/risk/AMC filter
- **Then** the fund results list updates accordingly and active filter chips appear reflecting my selections.

### AC5 — Clearing filters restores default catalog
- **When** I click “Clear all” (or remove all chips)
- **Then** the catalog returns to its default state (no filters applied), without requiring a page reload.

### AC6 — Backend automated tests
- Backend includes tests validating:
  - categories endpoint excludes nulls and returns correct counts
  - risks endpoint excludes nulls and returns correct counts
  - AMCs endpoint supports search and pagination (returns stable next_cursor/offset behavior)

## Demo script (30–60s)
1. Open Filters → show categories loaded from API with counts (call out: “no hardcoded list”).
2. In AMC filter, type a smaller AMC name → select it.
3. Results update immediately; active chips reflect chosen filters.
4. Click “Clear all” → full catalog returns.

## Implementation notes (key components touched)
- Backend:
  - Distinct + count aggregations for categories/risks
  - AMC search endpoint with pagination
  - Index verification on `category`, `risk_level`, `amc_id` (and/or `amc_name_norm` if needed)
- Frontend:
  - Fetch filter metadata on panel open (or on catalog load) with caching in state
  - Typeahead AMC search with debouncing and paginated fetch
  - Chips component and clear-all behavior wired to catalog query state

## Dependencies / prerequisites
- Risk coverage improves after US-N4 (data coverage expansion), but risk filter must still work correctly with partial coverage now.

## Risks & mitigations
- **Risk:** Aggregation queries are slow without indexes.
  - **Mitigation:** Add/verify indexes on category/risk/amc fields; consider precomputed counts if needed later.
- **Risk:** Inconsistent category naming in source data (e.g., “Equity”, “Equities”).
  - **Mitigation:** Keep this story dataset-reflective; address normalization/governance in a separate story.

## Delivery plan (vertical slices)
### Increment A — Categories (fast trust win)
- Backend: `GET /funds/categories` with counts
- Frontend: categories filter reads from API + chips + clear

### Increment B — Full AMC coverage (production-grade discovery)
- Backend: upgrade `GET /funds/amcs` with `q` + pagination
- Frontend: AMC typeahead search + selection

### Increment C — Risk filter + polish
- Backend: `GET /funds/risks` with counts and null exclusion
- Frontend: risk filter integration + failure states + loading polish
