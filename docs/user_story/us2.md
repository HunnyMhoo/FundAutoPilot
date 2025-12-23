# US2 — Search funds (Executive-demo quality)

## One open question (with recommendation)
**Question:** For MVP search results ordering, do you want:
- A) Deterministic ordering (Fund Name A–Z) within matches
- B) Relevance ordering (exact match > prefix > substring; ticker/alias boosted)

**Recommendation:** B) Relevance ordering, but keep it **simple and deterministic** (rule-based). It creates an immediate “premium” feel in the demo without requiring ML or analytics. If engineering time is tight, ship A first and add B as a small follow-up increment.

**Assumption for this story (unless you override):** B) Simple deterministic relevance ordering

---

## User story
As a user, I want to search funds by name/ticker/alias so that I can find a fund quickly.

## Executive “wow” intent
- Make discovery feel premium: “type a few characters → instantly find the fund.”
- Prove the catalog is truly broad (“across AMCs”) by making retrieval effortless even at scale.

---

## Scope

### In scope
- A search bar on the Fund Catalog screen (US1).
- Instant search with debounce (recommended: ~300ms) plus Enter-to-search.
- Case-insensitive partial match across:
  - Fund Name
  - Ticker (if available)
  - Alias / abbreviated name (if available)
- Search works with pagination:
  - Load more continues within the active search query
- States: loading, no results (with Reset), error (with Retry)
- “Clear X” on the search input to return to default catalog browse state.

### Out of scope
- Advanced query language (AND/OR, quotes)
- Fuzzy/typo tolerance (Levenshtein)
- Synonyms / semantic search
- Highlighting matched substrings (nice-to-have later)
- Filters/sort UI (US3) — but the contract must be composable with them

---

## Data source and indexing (MVP)

### Source of searchable fields
- Fund Master (ingested from your chosen authoritative source, e.g., SEC datasets) is the base.
- Maintain a `search_tokens` / normalized fields per fund:
  - `fund_name_norm`
  - `ticker_norm` (nullable)
  - `aliases_norm[]` (nullable)
- Aliases can include:
  - abbreviated fund name
  - common marketing short name
  - known legacy names (optional)

### Normalization rules
- Lowercase
- Trim leading/trailing whitespace
- Collapse multiple spaces
- Optional: strip punctuation for matching stability (e.g., “-”, “/”, “.”)

---

## UX requirements (behavioral spec)

### Search bar behavior
- Location: top of the catalog list.
- Placeholder: “Search by fund name or ticker”
- Clear button (X) appears when input is non-empty:
  - Clicking X clears input and returns to default browse list (page 1, default ordering).

### Triggering search
- Debounce: ~300ms after the last keystroke.
- Enter key triggers immediate search (bypass debounce).
- “Latest query wins”:
  - If multiple requests are in-flight, only the newest response is applied.

### Search results rendering
- The same list component renders search results (no new screen).
- Show a subtle label when search is active (optional):
  - “Results for: <query>”
- Load more:
  - Appears only when `next_cursor` exists for the current query.

### No results state
- Show:
  - Title: “No results”
  - Helper: “Try a different keyword.”
  - Primary action: “Reset” (clears query, returns to default browse list)

### Error state
- Inline error message near the list:
  - “We couldn’t run the search.”
  - Action: Retry (re-runs the last query request)
- If there were previous results, keep them visible (non-destructive error).

---

## API contract (MVP)

### Endpoint (composable)
GET /funds?limit=25&cursor=<token>&sort=<sort>&q=<query>

### Request rules
- `q` is trimmed; empty `q` means “no search” (default browse).
- `sort` defaults to `relevance` (assumption) or `name_asc` if you choose A.

### Response
- items: FundSummary[]
- next_cursor: string | null
- (optional but recommended) query_echo: string (server echoes applied query)

### Deterministic relevance (simple rules)
If you implement relevance (recommended), keep it rule-based and stable:
1) Exact match on ticker or alias (highest)
2) Prefix match on fund name
3) Substring match on fund nam
