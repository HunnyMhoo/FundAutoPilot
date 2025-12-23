# US-N1 — Search That Actually Works (Normalization + Fallback + Clear Empty States)

## Problem / Opportunity
Search is the first credibility check. If users cannot reliably find a known fund by typing what they see on statements, ads, or RM messages (name/abbr with inconsistent casing, spacing, punctuation), the product immediately feels untrustworthy and users abandon discovery → detail → compare.

## User story
As a user, I want search to reliably find mutual funds by **name** or **abbreviation** regardless of casing, spacing, and common punctuation, so that I can quickly discover the right fund without guessing the “correct” formatting.

## Executive “wow” intent
Make search feel “production-grade” immediately: any reasonable input finds the fund, and when it doesn’t, the UI explains why and provides a one-click recovery.

## User value / business value
- Restores trust: removes “search feels broken” perception.
- Improves funnel conversion: more users reach fund detail and compare flows.
- Reduces support noise: fewer “can’t find fund” questions.

## In scope
### Data / Ingestion
- Persist **normalized** search keys for each fund record:
  - `fund_name_norm`
  - `fund_abbr_norm`
- Normalize on every upsert (create/update) so the index is always consistent.

### Backend search behavior
- Query strategy prioritizes normalized fields:
  1) Exact match on normalized abbreviation/name  
  2) Prefix match (starts-with) on normalized fields  
  3) Substring match (contains) on normalized fields  
- Defensive fallback:
  - If normalized fields are missing for some records (legacy/partial data), include a fallback query against raw fields for those records.
- Return metadata needed by UI:
  - `match_type` (exact | prefix | substring | fallback)
  - `matched_field` (abbr | name)

### UI behavior
- Clear, consistent search feedback:
  - Results label: e.g., “Showing results for ‘k-usx’” (echo input)
  - Optional: small hint when fallback was used (“Some results matched legacy formatting”)
- Strong empty state:
  - Summary: “No funds match ‘<query>’”
  - Primary action: “Clear search”
  - Secondary guidance: “Try fund abbreviation or fewer keywords”
  - Retain existing filters/sort state when clearing the search term

## Out of scope
- Semantic search, Thai tokenization, ML ranking, embeddings.
- Complex relevance tuning beyond deterministic ordering rules above.
- Fuzzy edit-distance (typo tolerance) and synonyms.

## Functional requirements
### Normalization rules (MVP-safe)
- Lowercase (ASCII + Unicode casefold where applicable)
- Trim leading/trailing whitespace
- Collapse consecutive whitespace to a single space
- Strip common punctuation characters: `- _ . , / ( ) [ ] : ; ' "`
- Preserve alphanumerics and Thai characters as-is (no Thai segmentation in this story)

### Search rules
- Input query is normalized with the same function used in ingestion.
- Deterministic ordering:
  1) Exact abbreviation match
  2) Exact name match
  3) Prefix abbreviation match
  4) Prefix name match
  5) Substring abbreviation match
  6) Substring name match
  7) Fallback matches (raw fields) ordered last

## Acceptance criteria (Given / When / Then)
### AC1 — Case-insensitive abbreviation match
- **Given** a fund exists with abbreviation `K-USX`  
- **When** I search `k-usx` or `K-usx`  
- **Then** the fund appears in results and is ranked as an exact match.

### AC2 — Whitespace normalization
- **Given** a fund exists with name `Kasikorn US Equity`  
- **When** I search `  kasikorn   us   equity `  
- **Then** the fund appears in results.

### AC3 — Punctuation stripping
- **Given** a fund exists with abbreviation `KUSX` and/or name containing punctuation variants  
- **When** I search `K-USX`, `K_USX`, or `K.USX`  
- **Then** the fund appears in results consistently.

### AC4 — Fallback for missing normalized fields
- **Given** at least one fund record is missing `fund_name_norm` and/or `fund_abbr_norm`  
- **When** I search for a term that exists in its raw fields  
- **Then** the fund can still be returned via fallback, and `match_type = fallback`.

### AC5 — Empty state UX and recovery
- **Given** I search a query with no matches  
- **Then** I see an empty state showing:
  - the query echo
  - a “Clear search” action
  - retained filters and sort settings
- **When** I click “Clear search”  
- **Then** the catalog list is restored with the same filters/sort preserved.

### AC6 — Automated coverage
- At least **3 backend tests** exist and pass:
  - normalization function (case/space/punctuation)
  - query ranking order (exact > prefix > substring)
  - fallback behavior when normalized fields are missing
- At least **1 UI test** (or equivalent automated check) confirms empty state + clear action preserves filters.

## Non-functional requirements
- Search response time remains acceptable for catalog browsing (target: no noticeable regression versus current baseline).
- Normalization must be deterministic and versioned (changes require migration/backfill plan).

## Demo script (30–60s)
1. Open Fund Catalog.
2. Search `K-USX`, then `k usx`, then `K.USX` → show the same fund consistently at/near top.
3. Search a known fund by name with messy spacing → results still appear.
4. Search a nonsense term → show empty state and click “Clear search” → catalog restores with filters intact.

## Implementation plan (vertical slices)
### Increment A — Credibility win (smallest demoable slice)
- Add normalization function + populate `*_norm` fields during ingestion/upsert.
- Backend queries use normalized fields for exact + prefix matching.
- Minimal UI: results label + simple empty state.

### Increment B — Trust hardening
- Add substring matching and deterministic ordering rules.
- Add fallback query path for records missing normalized fields.
- Polish empty state with “Clear search” and guidance text.

### Increment C — Optional polish
- Add lightweight “match type” indicator for internal debugging (hidden behind dev flag).
- Add monitoring counters (e.g., fallback hit rate) if available in the stack (optional).

## Dependencies / prerequisites
- Fixture dataset that includes:
  - at least 1 fund with punctuation in abbreviation/name variants
  - at least 1 legacy fund missing normalized fields (to validate fallback)
- Ability to run ingestion locally or via test harness to verify persisted normalized fields.

## Risks & mitigations
- **Risk:** Over-aggressive normalization breaks legitimate identifiers (false positives/negatives).  
