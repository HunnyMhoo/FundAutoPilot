# Project Progress (Current Snapshot)

## 1. What This Repo Does

Switch Impact Simulator is a portfolio-first decision tool for mutual fund investors. The system enables users to browse, search, filter, and compare Thai mutual funds across all Asset Management Companies (AMCs) using data from SEC Thailand.

The application consists of:
- **Backend**: FastAPI service (`backend/`) providing REST API for fund data with cursor-based pagination, search, filtering, and sorting
- **Frontend**: Next.js 16 application (`frontend/`) with App Router providing the Fund Catalog UI
- **Data Ingestion**: Python script (`backend/app/services/ingestion/ingest_funds.py`) that fetches fund data from SEC Thailand API and stores it in PostgreSQL

## 2. Implemented Features (User-Visible)

### Fund Catalog Browse
- **What it does**: Displays paginated list of active mutual funds with fund name, AMC, category, risk level, and AIMC classification type
- **Where it lives**: `frontend/app/funds/page.tsx`, `frontend/components/FundCatalog/`
- **How to verify**: Navigate to `/funds` route, see paginated fund cards with "Load More" button. Fund cards show Risk and AIMC Type (Fee column removed).
- **Current limitations**: None

### AIMC Fund Classification
- **What it does**: Displays AIMC (Association of Investment Management Companies) fund classification category for each fund. Uses AIMC CSV as primary source (57% coverage), falls back to SEC API code mapping (37% coverage) with visual indicator (*). Classification shown in fund catalog cards and fund detail page.
- **Where it lives**: 
  - Backend: `backend/app/models/fund_orm.py` (database columns: `aimc_category`, `aimc_code`, `aimc_category_source`), `backend/app/services/ingestion/ingest_aimc_categories.py` (ingestion script), `backend/app/services/ingestion/migrate_aimc_columns.py` (migration script)
  - Frontend: `frontend/components/FundCatalog/FundCard.tsx` (catalog display), `frontend/components/FundDetail/KeyFactsCard.tsx` (detail page display)
- **How to verify**: 
  - Fund catalog cards show "AIMC Type" column with category name (e.g., "Equity Large Cap", "Japan Equity")
  - SEC_API fallback shows asterisk (*) indicator
  - Fund detail page shows AIMC Type in Tier 1 hero section
  - Database contains `aimc_category` field populated for 94% of funds (3,139 from AIMC CSV, 2,040 from SEC API fallback)
- **Current limitations**: 6% of funds (330) have no AIMC classification available

### Fund Detail Page
- **What it does**: Displays comprehensive fund information including fund classification (Risk Level, AIMC Type), investment requirements, share class navigation, fee breakdown, investment strategy, and distribution policy. Multi-card layout with data fetched from SEC API.
- **Where it lives**: 
  - `frontend/app/funds/[fundId]/page.tsx`, `frontend/components/FundDetail/FundDetailView.tsx`
  - `frontend/components/FundDetail/KeyFactsCard.tsx` - Fund Classification (Risk Level, AIMC Type) and Investment Requirements
  - `frontend/components/FundDetail/ShareClassCard.tsx` - Share class navigation (2.1)
  - `frontend/components/FundDetail/FeeBreakdownCard.tsx` - Detailed fee breakdown with Max/Actual values (2.2)
  - `frontend/components/FundDetail/FundPolicyCard.tsx` - Investment strategy and management style (2.3)
  - `frontend/components/FundDetail/DistributionPolicyCard.tsx` - Dividend/distribution policy (2.5)
- **How to verify**: Click on any fund card, see fund detail page with:
  - Fund name, AMC, category in header
  - "Fund Classification" section with Risk Level (badge), AIMC Type (with * if SEC_API fallback)
  - "Investment Requirements" section with minimum investment, redemption, balance, and redemption period
  - "Share Classes" card showing current class and links to sibling classes (when multiple classes exist)
  - "Fee Structure" card with Transaction Fees and Recurring Fees sections, showing Max (prospectus) and Actual (charged) rates, Total Expense Ratio
  - "Investment Strategy" card with Policy Type, AIMC Category, and Management Style (Passive/Active with description)
  - "Distribution Policy" card showing dividend policy (Income/Accumulating) with description
  - "Add to Compare" button
  - Data freshness badge
- **Current limitations**: Investment constraints, fees, policy, and dividend data fetched on-demand from SEC API (may be slow for first load)

### Compare Funds (US-N6)
- **What it does**: Compare 2-3 funds side-by-side with fees breakdown (front-end, back-end, switching, ongoing), risk levels, dealing constraints (cut-off times, minimums, settlement), and distribution data. Persistent compare tray at bottom of screen shows selected funds with add/remove functionality. URL-first state management enables shareable comparison links.
- **Where it lives**: 
  - Backend: `backend/app/services/compare_service.py`, `backend/app/api/funds.py` (GET `/funds/compare`), `backend/app/utils/fee_grouping.py`
  - Frontend: `frontend/app/compare/page.tsx`, `frontend/components/Compare/` (CompareTray, ComparePage, CompareFundColumn, useCompareState)
- **How to verify**: 
  - Add funds to compare from catalog cards or detail pages using "+ Compare" button
  - Compare tray appears at bottom showing selected funds (max 3)
  - Click "Compare" button to view side-by-side comparison at `/compare?ids=<id1>,<id2>`
  - Verify fee groups (Front-end fee, Back-end fee, Ongoing fees, etc.)
  - Verify missing data shows "Not available" with tooltips
  - Copy and share URL - comparison persists on reload
- **Current limitations**: Class selector not implemented (uses deterministic default class selection)

### Switch Impact Preview (US-N8)
- **What it does**: Preview the impact of switching from a current fund to a target fund, showing fee impact estimate (annual fee drag difference), risk level change, category/AIMC type change, and key dealing constraints differences (minimums, redemption period, cut-off times). Explainable calculations with formulas, assumptions, and disclaimers. Data coverage classification (HIGH/MEDIUM/LOW/BLOCKED) with per-section missing flags. Preview requests are logged for traceability.
- **Where it lives**: 
  - Backend: `backend/app/services/switch_service.py`, `backend/app/api/switch.py` (POST `/switch/preview`), `backend/app/models/fund_orm.py` (SwitchPreviewLog table)
  - Frontend: `frontend/app/switch/page.tsx`, `frontend/components/Switch/` (SwitchPreviewPage, FeeImpactCard, RiskChangeCard, CategoryChangeCard, ConstraintsDeltaCard, ExplanationCard), `frontend/components/Compare/SwitchPreviewPanel.tsx`
- **How to verify**: 
  - Navigate to `/compare?ids=<id1>,<id2>` and click "Switch Preview" button
  - Select current and target funds from compared set, enter amount (default 100,000 THB)
  - View preview showing annual fee delta estimate, risk change (integer delta), category change flag, and constraints differences
  - Verify explanation section shows formulas and assumptions
  - Verify missing data sections show "Not available" with appropriate flags
  - Check data freshness badge shows snapshot date
  - Preview request is persisted to `switch_preview_log` table
- **Current limitations**: Uses actual expense ratio from SEC API fee breakdown (matches fund detail page), falls back to stored expense_ratio if API unavailable

### Search Funds
- **What it does**: Case-insensitive search across fund names and abbreviations with debounced input, multi-tier ranking (exact match → prefix match → substring match), search-specific empty state with clear action
- **Where it lives**: `frontend/components/FundCatalog/SearchInput.tsx`, search logic in `backend/app/services/fund_service.py` (SQL fallback) and `backend/app/services/search/elasticsearch_backend.py` (Elasticsearch)
- **How to verify**: Type in search bar on `/funds` page, results filter in real-time. Search "K" returns "K Equity Fund" and funds containing 'k'. Search "MFC" returns MFC funds. No-match queries show "No funds match '<query>'" with clear button.
- **Current limitations**: Elasticsearch index requires manual population via ingestion script; currently falls back to SQL search when ES index is empty

### Filter and Sort
- **What it does**: Filter by AMC, category, risk level, fee band (low/medium/high); sort by name, fee, or risk (ascending/descending). Filter options are dataset-driven (categories, risks, and AMCs loaded from API with counts). AMC filter supports typeahead search with pagination.
- **Where it lives**: `frontend/components/FundCatalog/FilterPanel.tsx`, `frontend/components/FundCatalog/SortControl.tsx`, backend filtering in `backend/app/services/fund_service.py` (lines 68-100), filter metadata endpoints in `backend/app/api/funds.py`
- **How to verify**: Use sidebar filters and sort dropdown on `/funds` page. Filter options show counts and are loaded from API. AMC filter supports search beyond top 10.
- **Current limitations**: None

### Data Freshness Display
- **What it does**: Shows "Data updated" date badge in catalog header
- **Where it lives**: `frontend/components/FundCatalog/FundCatalog.tsx` (lines 87-92), data from `as_of_date` in API response
- **How to verify**: Check header on `/funds` page for date badge
- **Current limitations**: None

## 3. Implemented Backend Capabilities

### APIs / Routes

**GET /funds** (`backend/app/api/funds.py` lines 13-44)
- Purpose: List funds with pagination, search, filtering, and sorting
- Handler: `list_funds()` in `backend/app/api/funds.py`
- Query parameters: `limit` (1-100, default 25), `cursor`, `sort`, `q` (search), `amc[]`, `category[]`, `risk[]`, `fee_band[]`
- Returns: `FundListResponse` with items, next_cursor, as_of_date, data_snapshot_id
- Share class support: Returns separate entries for each share class. `fund_id` in response uses `class_abbr_name` when available, otherwise `proj_id`.

**GET /funds/count** (`backend/app/api/funds.py` lines 47-54)
- Purpose: Get total count of active funds
- Handler: `get_fund_count()` in `backend/app/api/funds.py`
- Returns: `{"count": int}`

**GET /funds/categories** (`backend/app/api/funds.py` lines 63-75)
- Purpose: Get distinct categories with fund counts (dataset-driven filter metadata)
- Handler: `get_categories()` in `backend/app/api/funds.py`
- Returns: `CategoryListResponse` with items array of `{value: str, count: int}` ordered by count desc, then alphabetically
- Excludes null categories

**GET /funds/risks** (`backend/app/api/funds.py` lines 78-90)
- Purpose: Get distinct risk levels with fund counts (dataset-driven filter metadata)
- Handler: `get_risks()` in `backend/app/api/funds.py`
- Returns: `RiskListResponse` with items array of `{value: str, count: int}` ordered by risk_level ascending (numeric if applicable)
- Excludes null risk levels

**GET /funds/amcs** (`backend/app/api/funds.py` lines 93-115)
- Purpose: Get list of AMCs with active fund counts, supporting search and pagination
- Handler: `get_amcs()` in `backend/app/api/funds.py`
- Query parameters: `q` (search term for typeahead), `limit` (1-100, default 20), `cursor` (pagination)
- Returns: `AMCListResponse` with items array of `{id: str, name: str, count: int}` and `next_cursor` for pagination
- Supports full AMC coverage beyond top 10 via search and pagination

**GET /** (`backend/main.py` lines 30-37)
- Purpose: Root endpoint with API info
- Returns: API message, version, docs URL

**GET /funds/{fund_id}** (`backend/app/api/funds.py`)
- Purpose: Get detailed fund information by fund_id
- Handler: `get_fund_by_id()` in `backend/app/api/funds.py`
- Path parameter: `fund_id` - Can be class_abbr_name (e.g., "K-INDIA-A(A)") or proj_id for backward compatibility. URL-encoded characters (e.g., `%26` for `&`) are automatically decoded.
- Returns: `FundDetail` with fund information including AIMC classification, risk level, investment constraints, fund policy type, management style (with description), dividend policy, proj_id, and class_abbr_name for share class navigation
- Share class support: Supports lookup by class name. Returns class name as `fund_id` when class exists.
- Investment constraints: Fetches minimum investment, redemption, and balance from SEC API `/fund/{proj_id}/investment` endpoint
- Redemption period: Fetches redemption period from SEC API `/fund/{proj_id}/redemption` endpoint and formats for display
- Dividend policy: Fetches dividend policy from SEC API `/fund/{proj_id}/dividend` endpoint
- Fund policy: Fetches policy type and management style from SEC API `/fund/{proj_id}/policy` endpoint

**GET /funds/{fund_id}/share-classes** (`backend/app/api/funds.py`)
- Purpose: Get all share classes for a fund (feature 2.1)
- Handler: `get_share_classes()` in `backend/app/api/funds.py`
- Path parameter: `fund_id` - Can be class_abbr_name or proj_id
- Returns: `ShareClassListResponse` with proj_id, fund_name, current_class, classes array (class_abbr_name, class_name, class_description, is_current, dividend_policy), total_classes
- Data source: Fetches from SEC API `/fund/{proj_id}/class_fund` and `/fund/{proj_id}/dividend` endpoints

**GET /funds/{fund_id}/fees** (`backend/app/api/funds.py`)
- Purpose: Get detailed fee breakdown for a fund (feature 2.2)
- Handler: `get_fee_breakdown()` in `backend/app/api/funds.py`
- Path parameter: `fund_id` - Can be class_abbr_name or proj_id
- Returns: `FeeBreakdownResponse` with fund_id, class_abbr_name, sections array (transaction fees, recurring fees), total_expense_ratio, total_expense_ratio_actual, last_upd_date
- Fee sections: Transaction (front-end, back-end, switching, transfer) and Recurring (management, registrar, custodian, other)
- Data source: Fetches from SEC API `/fund/{proj_id}/fee` endpoint, filters by class

**GET /funds/compare** (`backend/app/api/funds.py`)
- Purpose: Compare 2-3 funds side-by-side with detailed comparison data
- Handler: `compare_funds()` in `backend/app/api/funds.py`
- Query parameters: `ids` - Comma-separated fund IDs (2-3 funds required)
- Returns: `CompareFundsResponse` with funds array (identity, risk, fees grouped by category, dealing constraints, distribution), missing_flags per fund, errors array for non-fatal issues
- Validation: Enforces 2-3 funds, removes duplicates, validates fund IDs
- Error handling: Returns 400 for invalid number of funds, 404 for not found, 500 for server errors

**POST /switch/preview** (`backend/app/api/switch.py`)
- Purpose: Generate switch impact preview for switching from current to target fund (US-N8)
- Handler: `get_switch_preview()` in `backend/app/api/switch.py`
- Request body: `SwitchPreviewRequest` with `current_fund_id`, `target_fund_id`, `amount_thb`
- Returns: `SwitchPreviewResponse` with calculated deltas (expense_ratio_delta, annual_fee_thb_delta, risk_level_delta, category_changed, constraints_delta), explainability (formulas, assumptions, disclaimers), coverage status (HIGH/MEDIUM/LOW/BLOCKED), per-section missing flags, data_snapshot_id, as_of_date
- Validation: Enforces different funds, positive amount, fund existence
- Error handling: Returns 400 for invalid request, 404 for fund not found, 500 for server errors
- Logging: Persists preview request to `switch_preview_log` table with deltas and missing flags

**GET /health** (`backend/main.py` lines 40-43)
- Purpose: Health check endpoint
- Returns: `{"status": "healthy"}`

### Data Model / Storage

**Database**: PostgreSQL (async via SQLAlchemy with asyncpg)

**Tables**:

`amc` (`backend/app/models/fund_orm.py` lines 11-25)
- Primary key: `unique_id` (String(20))
- Fields: `name_th`, `name_en`, `last_upd_date`
- Relationship: One-to-many with `fund`

`fund` (`backend/app/models/fund_orm.py` lines 33-90)
- Primary key: Composite `(proj_id, class_abbr_name)` - Supports share classes as separate funds
- Foreign key: `amc_id` → `amc.unique_id`
- Fields: `proj_id` (String(50)), `class_abbr_name` (String(50), empty string for funds without classes), `fund_name_th`, `fund_name_en`, `fund_abbr`, `fund_status` (required), `regis_date`, `category`, `risk_level`, `risk_level_int`, `risk_level_desc`, `risk_last_upd_date`, `expense_ratio`, `expense_ratio_last_upd_date`, `fee_data_raw` (JSONB), `fee_data_last_upd_date`, `last_upd_date`, `data_snapshot_id`, `data_source`, `aimc_category` (String(100)), `aimc_code` (String(20)), `aimc_category_source` (String(20))
- Normalized search fields: `fund_name_norm`, `fund_abbr_norm` (populated during ingestion)
- AIMC classification: `aimc_category` stores display category name, `aimc_code` stores raw SEC API code, `aimc_category_source` indicates source ('AIMC_CSV' or 'SEC_API')
- Share class support: Funds with multiple share classes (e.g., K-INDIA-A(A), K-INDIA-A(D)) are stored as separate records with same `proj_id` but different `class_abbr_name`. Class name used as `fund_abbr` and `fund_id` in API responses.
- Indexes:
  - `idx_fund_name_asc` on (`fund_name_en`, `proj_id`)
  - `idx_fund_status` on (`fund_status`)
  - `idx_fund_search` on (`fund_name_norm`, `fund_abbr_norm`)
  - `idx_fund_class_abbr` on (`class_abbr_name`) - For lookup by class name
  - `idx_fund_category` on (`fund_status`, `category`) - Composite for filtering + aggregation (US-N3)
  - `idx_fund_risk` on (`fund_status`, `risk_level`) - Composite for filtering + aggregation (US-N3)
  - `idx_fund_risk_int` on (`fund_status`, `risk_level_int`) - Composite for filtering + aggregation (US-N4)
  - `idx_fund_amc` on (`fund_status`, `amc_id`) - For AMC filtering and aggregation (US-N3)
  - `idx_fund_aimc_category` on (`fund_status`, `aimc_category`) - For AIMC category filtering

`amc` (`backend/app/models/fund_orm.py` lines 11-30)
- Primary key: `unique_id` (String(20))
- Fields: `name_th`, `name_en`, `last_upd_date`
- Relationship: One-to-many with `fund`
- Indexes:
  - `idx_amc_name_search` on (`name_en`, `name_th`) - For typeahead search (US-N3)

`switch_preview_log` (`backend/app/models/fund_orm.py`)
- Primary key: `id` (Integer, autoincrement)
- Fields: `created_at` (DateTime), `current_fund_id` (String(50)), `target_fund_id` (String(50)), `amount_thb` (Numeric(12, 2)), `deltas_json` (JSON), `missing_flags_json` (JSON), `data_snapshot_id` (String(50), nullable)
- Purpose: Log switch preview requests for traceability and demo verification (US-N8)
- Indexes:
  - `idx_switch_preview_log_created_at` on (`created_at`) - For querying recent previews

**Migration/Seeding**: Tables created via `Base.metadata.create_all()` in ingestion script (`backend/app/services/ingestion/ingest_funds.py` line 194). Schema migrations handled via `backend/app/services/ingestion/migrate_schema.py` script (adds columns, updates primary keys, creates indexes). AIMC classification columns added via `backend/app/services/ingestion/migrate_aimc_columns.py` script. Switch preview log table created via `backend/app/services/ingestion/migrate_switch_preview_log.py` script. No Alembic migrations present.

### Business Logic / Domain Services

**FundService** (`backend/app/services/fund_service.py`)
- `list_funds()`: Cursor-based pagination with keyset method, supports nullable sort columns, handles search via Elasticsearch (with SQL fallback), applies filters (AMC, category, risk, fee_band), supports 6 sort options. Returns separate entries for each share class with class name as `fund_id`. Includes AIMC classification fields in response.
- `_list_funds_elasticsearch()`: Uses Elasticsearch search backend with automatic fallback to SQL when ES index is empty
- `_list_funds_sql()`: SQL-based search using normalized fields with fallback to raw fields when normalized is NULL
- `get_fund_by_id()`: Supports lookup by class_abbr_name (e.g., "K-INDIA-A(A)") or proj_id. Returns class name as `fund_id` when class exists. Fetches investment constraints, redemption period, dividend policy, and fund policy from SEC API on-demand. Returns AIMC classification with source indicator, management style with description, dividend policy, and share class info (proj_id, class_abbr_name). Expense ratio now uses actual value from fee breakdown (matches fund detail page display), falling back to stored `expense_ratio` if fee breakdown unavailable.
- `_get_investment_constraints()`: Fetches investment constraints (minimum investment, redemption, balance) from SEC API `/fund/{proj_id}/investment` endpoint
- `_get_redemption_data()`: Fetches redemption period data from SEC API `/fund/{proj_id}/redemption` endpoint
- `_get_dividend_data()`: Fetches dividend/distribution data from SEC API `/fund/{proj_id}/dividend` endpoint, filters by class
- `_get_policy_data()`: Fetches fund policy data (policy type, management style) from SEC API `/fund/{proj_id}/policy` endpoint
- `_format_redemption_period()`: Formats SEC API redemption period codes (1-9, E, T) into human-readable text (e.g., "Every business day", "Monthly")
- `_format_management_style()`: Formats management style codes (AN → "Active", PN → "Passive (Index-tracking)")
- `_format_currency_amount()`: Formats currency amounts with thousand separators
- `get_share_classes()`: Returns all share classes for a fund from SEC API `/fund/{proj_id}/class_fund`, includes dividend policy per class, identifies current class (feature 2.1)
- `get_fee_breakdown()`: Returns detailed fee breakdown from SEC API `/fund/{proj_id}/fee`, categorizes into Transaction/Recurring sections, includes Max/Actual rates, handles class-specific filtering with contains-based Thai text matching (feature 2.2). Total expense ratio uses calculated value from fee data, no longer falls back to stored `expense_ratio`.
- `_get_fund_record()`: Helper to find fund ORM record by class_abbr_name or proj_id
- `get_fund_count()`: Counts active funds (status="RG")
- `get_categories_with_counts()`: Returns distinct categories with counts using Elasticsearch aggregation (with SQL fallback), ordered by count desc then alphabetically, excludes nulls (US-N3)
- `get_risks_with_counts()`: Returns distinct risk levels with counts using Elasticsearch aggregation (with SQL fallback), ordered ascending (numeric if possible), excludes nulls (US-N3)
- `get_amcs_with_fund_counts()`: Returns AMCs with fund counts, supporting search and pagination, uses Elasticsearch aggregation (with SQL fallback), cursor-based pagination (US-N3)
- Fee band classification: low (≤1.0%), medium (1-2%), high (>2%)

**SearchBackend** (`backend/app/services/search/backend.py`)
- Abstract interface for search implementations
- `SearchFilters`: Filter model for amc, category, risk, fee_band
- `SearchResult`: Result model with items, total, next_cursor

**ElasticsearchSearchBackend** (`backend/app/services/search/elasticsearch_backend.py`)
- Implements multi-tier search ranking: exact match (boost: 10) → prefix match (boost: 5) → substring match (boost: 2)
- Index: `funds` with mappings for `fund_name`, `fund_abbr`, `amc_name`, `category`, `risk_level`, `expense_ratio`, `fee_band`
- Supports cursor-based pagination via `search_after`
- Handles sorting by name, fee, risk (ascending/descending)
- `get_category_aggregation()`: Elasticsearch terms aggregation for categories with counts (US-N3)
- `get_risk_aggregation()`: Elasticsearch terms aggregation for risk levels with counts (US-N3)
- `get_amc_aggregation()`: Elasticsearch terms aggregation for AMCs with search and pagination support (US-N3)

**Normalization Utility** (`backend/app/utils/normalization.py`)
- `normalize_search_text()`: Lowercases (Unicode casefold), trims whitespace, collapses consecutive spaces, strips punctuation (- _ . , / ( ) [ ] : ; ' " `), preserves Thai characters

**SECFundIngester** (`backend/app/services/ingestion/ingest_funds.py`)
- `fetch_amcs()`: Fetches all AMCs from SEC Thailand API
- `fetch_funds_for_amc()`: Fetches funds for a specific AMC
- `store_amcs()`: Upserts AMCs with conflict resolution
- `store_funds()`: Upserts active funds (status="RG") with category inference from name patterns, populates `fund_name_norm` and `fund_abbr_norm` using normalization utility, syncs to Elasticsearch index. For funds with share classes, fetches class_fund data and creates separate records for each class using composite key `(proj_id, class_abbr_name)`. Uses class name as `fund_abbr` for display.
- `_store_fund_record()`: Helper method to store individual fund record (for specific class or fund without classes)
- `_infer_category()`: Keyword-based categorization (Equity, Fixed Income, Money Market, Mixed, Property/REIT, Commodity, Foreign Investment)
- Rate limiting: 100ms delay between requests (safe for 3000/300s limit)
- Snapshot tracking: Creates `data_snapshot_id` timestamp per ingestion run

**AIMCCategoryIngester** (`backend/app/services/ingestion/ingest_aimc_categories.py`)
- `ingest_aimc_data()`: Ingests AIMC classification data from AIMC CSV file and SEC API codes
- Matching strategy: Direct match by fund abbreviation, normalized match (removes spaces/dashes), fallback to SEC API code mapping
- Stores both AIMC CSV category (primary) and SEC API code (for reference) with source tracking
- Coverage: 57% from AIMC CSV (3,139 funds), 37% from SEC API fallback (2,040 funds), 6% unmatched (330 funds)
- SEC code mapping: Maps 44 unique SEC API codes to AIMC category names (e.g., "JPEQ" → "Japan Equity", "EG" → "Equity General")

**CompareService** (`backend/app/services/compare_service.py`)
- `compare_funds()`: Aggregates comparison data for 2-3 funds, fetches data from database and SEC API, applies class selection logic, groups fees into categories, structures response with missing flags and data freshness
- Class selection: Deterministic rule (exact match of fund_abbr, then prefer None/"/main", then alphabetical)
- Data sources: Fund identity from database, fees from `fee_data_raw` JSONB (cached) or SEC API, risk from database, dealing constraints from SEC API (`/redemption`, `/investment`), distribution from SEC API (`/dividend`)
- Partial success: Returns available sections even if some fail, populates `missing_flags` and `errors` array

**Fee Grouping Utility** (`backend/app/utils/fee_grouping.py`)
- `categorize_fee()`: Classifies fee rows into categories (front_end, back_end, switching, ongoing, other) based on fee_type_desc keywords (case-insensitive)
- `get_category_display_label()`: Returns user-friendly labels for fee categories
- `group_fees()`: Groups fee rows by category, preserves all fee row fields
- `select_default_class()`: Deterministic class selection from list of class-specific data (exact match, then prefer fund-level, then alphabetical)

**SwitchService** (`backend/app/services/switch_service.py`)
- `get_switch_preview()`: Calculates switch impact preview with fee delta, risk change, category change, and constraints delta (US-N8)
- `_get_expense_ratio_actual()`: Fetches actual expense ratio from SEC API fee breakdown (matches fund detail page logic), prioritizes `actual_value` from "Total Fees & Expenses" row, falls back to `rate`, then stored `expense_ratio`
- `_fetch_dealing_constraints()`: Fetches dealing constraints (minimums, redemption period, cut-off times) from SEC API for both funds
- `_calculate_constraints_delta()`: Compares dealing constraints between current and target funds, returns `ConstraintsDelta` with boolean flags for each constraint type
- `_classify_coverage_and_missing_flags()`: Classifies data coverage (HIGH/MEDIUM/LOW/BLOCKED) and returns per-section missing flags based on data availability
- Data sources: Fund identity and risk from database, expense ratio from SEC API fee breakdown, dealing constraints from SEC API (`/investment`, `/redemption`), category/AIMC from database
- Explainability: Returns formulas, assumptions, and disclaimers for all calculations

**SECAPIClient** (`backend/app/utils/sec_api_client.py`)
- `fetch_redemption()`: Fetches redemption/dealing constraints data from `/fund/{proj_id}/redemption`
- `fetch_investment()`: Fetches investment constraints (minimums) from `/fund/{proj_id}/investment` (returns array per class)
- `fetch_dividend()`: Fetches dividend/distribution data from `/fund/{proj_id}/dividend` (returns array per class)
- `fetch_fees()`: Fetches fee data from `/fund/{proj_id}/fee` (used by switch service for expense ratio calculation)

### Integrations

**SEC Thailand API** (`backend/app/services/ingestion/ingest_funds.py`, `backend/app/utils/sec_api_client.py`, `backend/app/services/fund_service.py`)
- Base URL: `https://api.sec.or.th/FundFactsheet`
- Endpoints used: 
  - `/fund/amc`, `/fund/amc/{amc_id}`, `/fund/{proj_id}/class_fund` (for share class data) - ingestion
  - `/fund/{proj_id}/suitability` - risk level data (enrichment)
  - `/fund/{proj_id}/fee` - fee data (enrichment, fund detail fee breakdown)
  - `/fund/{proj_id}/redemption` - redemption/dealing constraints (compare feature, fund detail page)
  - `/fund/{proj_id}/investment` - investment minimums (compare feature, fund detail page)
  - `/fund/{proj_id}/dividend` - distribution/dividend data (compare feature, fund detail page, share class display)
  - `/fund/{proj_id}/fund_compare` - AIMC classification code (ingestion)
  - `/fund/{proj_id}/policy` - fund policy type and management style (fund detail page)
- Authentication: `Ocp-Apim-Subscription-Key` header from `SEC_FUND_FACTSHEET_API_KEY` env var
- Configuration: `backend/app/core/config.py` (lines 14-15)
- `SECAPIClient.fetch_class_fund()`: Fetches share class data for a fund, returns list of class objects with `class_abbr_name` and `class_name`
- `SECAPIClient.fetch_redemption()`: Fetches redemption/dealing constraints (cut-off times, settlement period, redemption period codes)
- `SECAPIClient.fetch_investment()`: Fetches investment constraints (minimum subscription/redemption/balance) per class
- `SECAPIClient.fetch_dividend()`: Fetches dividend/distribution data (policy, recent dividends) per class
- `SECAPIClient.fetch_fund_compare()`: Fetches AIMC classification code from SEC API (returns code like "JPEQ", "EG", "USEQ")
- `SECAPIClient.fetch_policy()`: Fetches fund policy data (fund_policy_type, management_style code) from SEC API

**Elasticsearch** (`backend/app/services/search/elasticsearch_backend.py`)
- Index: `funds` with custom analyzers for Thai/English text
- Purpose: Full-text search with multi-tier relevance ranking
- Fallback: Automatic fallback to SQL when index is empty or unavailable
- Client: `elasticsearch>=8.11.0,<9.0.0` (async via aiohttp)
- Configuration: `backend/app/core/config.py` (elasticsearch_url, elasticsearch_enabled)

## 4. Implemented Frontend Capabilities

### Key Screens/Pages

**Home Page** (`frontend/app/page.tsx`)
- Default Next.js template page (not customized for project)

**Fund Catalog Page** (`frontend/app/funds/page.tsx`)
- Renders `FundCatalog` component
- Metadata: Title and description for SEO

**Fund Detail Page** (`frontend/app/funds/[fundId]/page.tsx`)
- Renders `FundDetailView` component with full fund information
- URL decoding: Automatically decodes URL-encoded fund IDs (e.g., `%26` → `&`)
- Navigation: Back link to catalog with state preservation

**Compare Page** (`frontend/app/compare/page.tsx`)
- Server-side route with async searchParams (Next.js 15)
- Validates 2-3 funds requirement, renders ComparePage component
- Metadata: Title and description for SEO

### Components

**FundCatalog** (`frontend/components/FundCatalog/FundCatalog.tsx`)
- Main catalog container with header, filters sidebar, search, sort controls, fund grid, load more button
- Shows "Showing results for '<query>'" label when search is active
- States: loading_initial, loaded, error_initial, loading_more, error_load_more, end_of_results, idle
- Uses `useFundCatalog` hook for state management

**CompareTray** (`frontend/components/Compare/CompareTray.tsx`)
- Fixed bottom bar showing selected funds (1-3 max) as chips with remove buttons
- Displays count ("2/3 selected"), "Clear all" button, and "Compare" button (enabled when 2-3 funds selected)
- Fetches fund names for display in chips, hidden on `/compare` page itself
- Uses `useCompareState` hook for URL-first state management

**ComparePage** (`frontend/components/Compare/ComparePage.tsx`)
- Side-by-side comparison page for 2-3 funds
- Sections: Fund Information, Risk & Suitability, Fees (grouped), Dealing Constraints, Distribution
- Handles loading, error, and invalid states (redirects if <2 or >3 funds)
- Displays non-fatal errors in banner
- Includes "Switch Preview" button that opens `SwitchPreviewPanel` modal/side panel

**SwitchPreviewPanel** (`frontend/components/Compare/SwitchPreviewPanel.tsx`)
- Inline panel on Compare page for switch impact preview (US-N8)
- Fund selection: Dropdowns for current and target funds (from compared set)
- Amount input: Default 100,000 THB with validation
- Renders preview cards: FeeImpactCard, RiskChangeCard, CategoryChangeCard, ConstraintsDeltaCard, ExplanationCard
- Handles loading, error, and "blocked" states (when data coverage is BLOCKED)
- Shows data freshness badge with `as_of_date`

**CompareFundColumn** (`frontend/components/Compare/CompareFundColumn.tsx`)
- Individual fund column in side-by-side comparison
- Renders all comparison sections with consistent styling
- Shows "Not available" with tooltips for missing data
- Displays fee groups (Front-end fee, Back-end fee, Ongoing fees, etc.) with individual fee rows

**useCompareState** (`frontend/components/Compare/useCompareState.ts`)
- URL-first state management hook for compare selection
- Stores selection in URL query parameter `ids` (comma-separated)
- Provides addFund, removeFund, clearAll methods
- Shareable URLs, reload-safe, preserves order

**EmptyState** (`frontend/components/FundCatalog/EmptyState.tsx`)
- Search-specific empty state: Shows "No funds match '<query>'" with helpful message and "Clear search" button
- Generic empty state: Shows "No funds available" when no search query

**FundCard** (`frontend/components/FundCatalog/FundCard.tsx`)
- Displays individual fund summary (name, AMC, category, risk, AIMC type)
- Two-column grid: Risk and AIMC Type (Fee column removed)
- AIMC Type displayed in green color with asterisk (*) indicator for SEC_API fallback
- Compare button: Inline icon button (+ / ✓) in header row next to fund name
- Links to fund detail page with state preservation
- Note: Dividend policy and management style badges removed from catalog (require per-fund SEC API calls, impacting list performance). These are displayed on fund detail page only.

**FilterPanel** (`frontend/components/FundCatalog/FilterPanel.tsx`)
- Sidebar with filter sections: Category, Risk Level, Fees, AMC
- Fetches categories from `/funds/categories` API (dataset-driven, shows counts)
- Fetches risks from `/funds/risks` API (dataset-driven, shows counts)
- AMC filter with typeahead search: Fetches from `/funds/amcs` API with search parameter, supports pagination with "Load more" button, debounced search (300ms)
- Loading and error states per filter section with retry functionality
- All filter options display fund counts

**SearchInput** (`frontend/components/FundCatalog/SearchInput.tsx`)
- Debounced search input with clear button
- Triggers search on Enter or after debounce delay

**SortControl** (`frontend/components/FundCatalog/SortControl.tsx`)
- Dropdown for sort options: name (asc/desc), fee (asc/desc), risk (asc/desc)

**ActiveFilters** (`frontend/components/FundCatalog/ActiveFilters.tsx`)
- Displays active filter chips with remove buttons
- Clear all filters action

**LoadMoreButton** (`frontend/components/FundCatalog/LoadMoreButton.tsx`)
- Load more button with loading state and end-of-results handling

**ErrorState** (`frontend/components/FundCatalog/ErrorState.tsx`)
- Error message display with retry action

**SkeletonLoader** (`frontend/components/FundCatalog/SkeletonLoader.tsx`)
- Loading skeleton for initial load

**FundDetailView** (`frontend/components/FundDetail/FundDetailView.tsx`)
- Main fund detail page component with header, fund name, AMC, category, and "Add to Compare" button
- Handles loading, error, and not-found states
- Navigation: Back link to catalog with state preservation

**KeyFactsCard** (`frontend/components/FundDetail/KeyFactsCard.tsx`)
- Two-tier layout for fund information display
- Tier 1 (Fund Classification): Two-column hero grid showing Risk Level (badge), AIMC Type (with fallback indicator). Expense ratio removed (now in FeeBreakdownCard for consistency with SEC API data)
- Tier 2 (Investment Requirements): Grid showing Minimum Investment, Minimum Redemption, Minimum Balance, and Redemption Period (when available)
- Fallback note: Shows indicator when AIMC category is derived from SEC API

**ShareClassCard** (`frontend/components/FundDetail/ShareClassCard.tsx`)
- Displays current share class info with name and description
- Lists other available share classes as clickable links
- Shows dividend policy badge (INC/ACC) per class
- Hidden when fund has only one share class
- Feature 2.1 implementation

**FeeBreakdownCard** (`frontend/components/FundDetail/FeeBreakdownCard.tsx`)
- Fetches fee data from `/funds/{fund_id}/fees` endpoint
- Displays fees organized by section: Transaction Fees and Recurring Fees
- Shows both Max (prospectus rate) and Actual (currently charged) values for each fee
- Displays Total Expense Ratio with Max and Actual values
- Includes legend explaining Max vs Actual and last update date
- Feature 2.2 implementation

**FundPolicyCard** (`frontend/components/FundDetail/FundPolicyCard.tsx`)
- Displays Policy Type (e.g., "Equity", "Fixed Income")
- Shows AIMC Category with source indicator (Official/Derived)
- Featured Management Style section with icon (📊 Passive, 🎯 Active), badge, and detailed description explaining implications
- Hidden when no policy data available
- Feature 2.3 implementation

**DistributionPolicyCard** (`frontend/components/FundDetail/DistributionPolicyCard.tsx`)
- Displays dividend policy as Income (Distributing) or Accumulating
- Shows policy description explaining what each type means
- Displays additional dividend policy remarks when available
- Shows hint for accumulating funds about dividend-paying share classes
- Feature 2.5 implementation

**SwitchPreviewPage** (`frontend/components/Switch/SwitchPreviewPage.tsx`)
- Standalone switch preview page at `/switch` route (US-N8)
- Fund selection and amount input interface
- Renders preview results in grid layout: FeeImpactCard, RiskChangeCard, CategoryChangeCard, ConstraintsDeltaCard, ExplanationCard
- Displays data freshness badge with `as_of_date`
- Handles loading, error, and blocked states

**FeeImpactCard** (`frontend/components/Switch/FeeImpactCard.tsx`)
- Displays annual fee drag difference in THB (rounded to nearest THB)
- Shows expense ratio delta (target - current) with percentage
- Displays formula: `Amount × (Target ER − Current ER)`
- Shows "Not available" when expense ratio data missing

**RiskChangeCard** (`frontend/components/Switch/RiskChangeCard.tsx`)
- Displays risk level change as integer delta (target - current)
- Shows risk level badges for current and target funds
- Indicates increase, decrease, or no change
- Shows "Not available" when risk level data missing

**CategoryChangeCard** (`frontend/components/Switch/CategoryChangeCard.tsx`)
- Displays category/AIMC type change as boolean flag
- Shows category names for current and target funds
- Indicates change or no change
- Shows "Not available" when category data missing

**ConstraintsDeltaCard** (`frontend/components/Switch/ConstraintsDeltaCard.tsx`)
- Displays dealing constraints differences (US-N8)
- Shows changes for: minimum subscription, minimum redemption, minimum balance, redemption period, cut-off times
- Grid layout with status indicators (Changed, Same, Not available)
- Shows "Not available" when constraints data missing

**ExplanationCard** (`frontend/components/Switch/ExplanationCard.tsx`)
- Displays explainability information: formulas, assumptions, disclaimers
- Shows calculation methodology for each metric
- Includes data coverage status (HIGH/MEDIUM/LOW/BLOCKED)

### State Management

**useFundCatalog Hook** (`frontend/components/FundCatalog/useFundCatalog.ts`)
- Manages funds list, pagination cursor, search query, filters, sort, loading/error states
- De-duplication by fund_id using ref
- Auto-reloads on search/filter/sort changes
- Prevents concurrent requests with `isLoadingRef`
- `clearSearch()`: Resets search query and reloads initial data while preserving filters and sort

### API Wiring

**API Client** (`frontend/utils/api/funds.ts`)
- `fetchFunds()`: Calls `/funds` endpoint with query params
- `fetchFundCount()`: Calls `/funds/count` endpoint
- `fetchFundDetail()`: Calls `/funds/{fund_id}` endpoint, returns `FundDetail`
- `fetchCategories()`: Calls `/funds/categories` endpoint, returns `CategoryListResponse` (US-N3)
- `fetchRisks()`: Calls `/funds/risks` endpoint, returns `RiskListResponse` (US-N3)
- `fetchAMCs()`: Calls `/funds/amcs` endpoint with optional search, limit, and cursor params, returns `AMCListResponse` (US-N3)
- `fetchCompareFunds()`: Calls `/funds/compare` endpoint with fund IDs array, validates 2-3 funds, returns `CompareFundsResponse`
- `fetchShareClasses()`: Calls `/funds/{fund_id}/share-classes` endpoint, returns `ShareClassListResponse` (feature 2.1)
- `fetchFeeBreakdown()`: Calls `/funds/{fund_id}/fees` endpoint, returns `FeeBreakdownResponse` (feature 2.2)
- Uses `NEXT_PUBLIC_API_URL` env var (defaults to `http://localhost:8000`)
- Real API integration (not mocked)

**Switch API Client** (`frontend/utils/api/switch.ts`)
- `fetchSwitchPreview()`: Calls `POST /switch/preview` endpoint with `SwitchPreviewRequest`, returns `SwitchPreviewResponse` (US-N8)
- Validates request parameters (different funds, positive amount)
- Handles error responses (400, 404, 500)

### Navigation/Routing

- Next.js App Router with file-based routing
- Routes: `/` (home), `/funds` (catalog), `/funds/[fundId]` (detail), `/compare` (compare page), `/switch` (switch preview page)
- Client-side navigation via Next.js `Link` component
- URL-first state management for compare selection (shareable URLs)

## 5. AI / LLM Integration Status (If Applicable)

Not applicable. No AI/LLM integration present in codebase.

## 6. Configuration & Environments

### Required Environment Variables

**Backend** (`backend/app/core/config.py`):
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://user:password@localhost:5432/switch_impact`)
- `SEC_FUND_FACTSHEET_API_KEY`: API key for SEC Thailand Fund Factsheet API
- `SEC_FUND_DAILY_INFO_API_KEY`: Defined but not used (reserved for future)
- `ELASTICSEARCH_URL`: Elasticsearch connection URL (default: `http://localhost:9200`)
- `ELASTICSEARCH_ENABLED`: Feature flag for Elasticsearch search backend (default: `True`)

**Frontend** (`frontend/utils/api/funds.ts`):
- `NEXT_PUBLIC_API_URL`: Backend API base URL (default: `http://localhost:8000`)

**Docker Compose** (`docker-compose.yml`):
- `DATABASE_URL`: Set to `postgresql://user:password@db:5432/switch_impact`
- `NEXT_PUBLIC_API_URL`: Set to `http://localhost:8000`
- Elasticsearch service: Port 9200, single-node mode, security disabled for local dev

### How to Run Locally

**Backend** (from `README.md`):
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

**Frontend** (from `README.md`):
```bash
cd frontend
npm install
npm run dev
```

**Docker Compose**:
```bash
docker-compose up --build
```

### Build/Deploy Artifacts

**Backend Dockerfile** (`backend/Dockerfile`):
- Base: `python:3.11-slim`
- Installs dependencies from `requirements.txt`
- Runs `uvicorn main:app` on port 8000

**Frontend**: No Dockerfile found in `frontend/` directory (Docker Compose references one but file not present)

**Docker Compose** (`docker-compose.yml`):
- Services: backend (port 8000), frontend (port 3000), db (PostgreSQL 15, port 5432), elasticsearch (port 9200)
- Volume mounts for development
- PostgreSQL volume for data persistence
- Elasticsearch volume (`es_data`) for index persistence
- Elasticsearch 8.11.0 with security disabled for local development

## 7. Testing & Quality

### Test Types Present

**Backend Tests** (`backend/tests/`):
- Framework: pytest with pytest-asyncio
- Test files: `test_funds_api.py`, `test_filter_metadata_api.py`, `test_compare_api.py`, `test_fee_grouping.py`
- Test coverage:
  - `TestListFunds`: Success cases, filters, sort, cursor pagination, limit validation, empty results
  - `TestHealthCheck`: Health endpoint
  - `TestRootEndpoint`: Root endpoint
  - `TestGetCategories`: Success with counts, excludes nulls, ordering, empty results, error handling (US-N3)
  - `TestGetRisks`: Success with counts, excludes nulls, ordering, empty results (US-N3)
  - `TestGetAMCs`: Basic listing, search functionality, pagination, limit validation, empty results, cursor handling, combined params (US-N3)
  - `TestFilterMetadataIntegration`: Response structure validation for all filter metadata endpoints (US-N3)
  - `TestCompareFunds`: Success with 2-3 funds, validation (too many/few), duplicate handling, whitespace trimming, order preservation, error handling (404, 500, validation errors)
  - `TestCategorizeFee`: Front-end/back-end/switching/ongoing/other keyword recognition, case-insensitive matching, partial keyword matching
  - `TestGroupFees`: Fee grouping by category, empty list handling, field preservation
  - `TestSwitchPreview`: Success cases, validation (same funds, invalid amount), missing data handling, constraints delta calculation, coverage classification, error handling (404, 500) (US-N8)
  - `TestSwitchService`: Expense ratio calculation from SEC API, constraints delta logic, coverage classification, missing flags (US-N8)
- Mocking: Uses `unittest.mock` to mock services
- Test client: httpx `AsyncClient` with `ASGITransport`

**Frontend Tests**: None found

### Lint/Format/Typecheck

**Backend**:
- Formatter: black (in `requirements.txt`)
- Linter: ruff (in `requirements.txt`)
- No configuration files present (uses defaults)

**Frontend**:
- Linter: ESLint with `eslint-config-next` (in `package.json`)
- Type checker: TypeScript (in `package.json`)
- Script: `npm run lint` (runs ESLint)

### Current Coverage Signals

No coverage tools or reports found in codebase.

## 8. Observability & Operations (If Present)

**Logging**:
- Ingestion script: Python `logging` module with INFO level, formatted timestamps (`backend/app/services/ingestion/ingest_funds.py` lines 26-31)
- API: No explicit logging configuration found (relies on uvicorn defaults)

**Error Handling**:
- API: Generic exception handling in endpoints returns 500 with error message (`backend/app/api/funds.py`). Filter metadata endpoints (`/funds/categories`, `/funds/risks`, `/funds/amcs`) have try-catch blocks with HTTPException (US-N3)
- Frontend: Error states with retry actions in `ErrorState` component and `useFundCatalog` hook. FilterPanel has per-section error handling with retry buttons (US-N3)
- Ingestion: Try-catch around API calls, error counter in stats (`backend/app/services/ingestion/ingest_funds.py` lines 74-81)

**Tracing/Metrics**: None present

**Dashboards**: None present

## 9. Implemented Features (Recent)

### Share Class Support
- **What it does**: Treats share classes (e.g., K-INDIA-A(A), K-INDIA-A(D)) as separate funds for presentation, matching industry standard (WealthMagik pattern)
- **Where it lives**: 
  - Database: Composite primary key `(proj_id, class_abbr_name)` in `backend/app/models/fund_orm.py`
  - Ingestion: `backend/app/services/ingestion/ingest_funds.py` fetches class_fund data and creates separate records
  - Enrichment: `backend/app/services/ingestion/enrich_funds.py` calculates class-specific expense ratios
  - API: `backend/app/services/fund_service.py` supports lookup by class name, returns class name as `fund_id`
- **How to verify**: 
  - Search for "K-INDIA" returns separate entries for K-INDIA-A(A) and K-INDIA-A(D)
  - `GET /funds/K-INDIA-A(A)` returns fund with class-specific data
  - Database shows separate records with same `proj_id` but different `class_abbr_name`
- **Current limitations**: Full re-ingestion required to populate class data for all funds. Base fund records (with empty `class_abbr_name`) may exist alongside class records.

## 10. Known Gaps / Not Implemented Yet

### Product Gaps (UX/Workflows)

- Home page is default Next.js template, not customized for project
- No user authentication or personalization
- No trending/popularity ranking

### Backend Gaps

**Data Ingestion**:
- Risk level and expense ratio are set to NULL in ingestion (lines 124-125 of `ingest_funds.py`) - requires additional API calls per fund via enrichment process
- No database migrations system (Alembic) - tables created via `create_all()`, schema changes handled via custom migration script

**API Endpoints**:
- Individual fund detail endpoint exists (`GET /funds/{fund_id}`) - supports lookup by class name or proj_id
- Fund comparison endpoint exists (`GET /funds/compare`) - accepts 2-3 fund IDs, returns side-by-side comparison data with fees, risk, dealing constraints, and distribution
- Switch impact preview endpoint exists (`POST /switch/preview`) - accepts current/target fund IDs and amount, returns calculated deltas, explainability, and coverage status (US-N8)

**Business Logic**:
- Category inference is keyword-based only, may miss funds
- AMC relationship eager loading has fallback N+1 query risk (see comment in `fund_service.py` lines 244-257)

**Testing**:
- No unit tests for normalization utility (`backend/app/utils/normalization.py`)
- No tests for Elasticsearch search backend and SQL fallback logic
- Filter metadata endpoints have comprehensive test coverage (`test_filter_metadata_api.py`) (US-N3)

### Frontend Gaps

- No frontend Dockerfile (referenced in docker-compose.yml but file missing)
- No error boundary components
- No loading states for individual fund cards
- Search debounce delay not configurable (hardcoded in component)
- No tests for EmptyState component and clearSearch functionality

### AI Gaps

Not applicable.

### Non-Functional Gaps

**Security**:
- No authentication/authorization
- CORS allows localhost only (hardcoded in `main.py` lines 17-19)
- No rate limiting on API endpoints
- API keys stored in env vars but no secrets management system

**Performance**:
- No query result caching
- No CDN or static asset optimization mentioned
- No database connection pooling configuration visible (uses SQLAlchemy defaults)

**Reliability**:
- No retry policies for external API calls (ingestion script)
- No circuit breakers
- No health check dependencies (database connectivity not verified in `/health`)

**Monitoring**:
- No structured logging format
- No error tracking service integration (Sentry, etc.)
- No performance monitoring (APM)

## 11. Next Best Tasks (Small, Testable Increments)

1. **[DONE] Populate normalization fields during ingestion**: Normalization utility created (`backend/app/utils/normalization.py`), ingestion script updated to populate `fund_name_norm` and `fund_abbr_norm`.

2. **[DONE] Implement relevance ranking for search**: Multi-tier search ranking implemented in Elasticsearch backend (exact match → prefix match → substring match). SQL fallback also improved with normalized + raw field search.

3. **Add tests for normalization and search**: Create unit tests for `normalize_search_text()` function, Elasticsearch search backend, and SQL fallback logic. Verify test coverage.

4. **Add frontend tests for EmptyState**: Test search-specific empty state and clearSearch functionality. Verify by running Jest tests.

5. **Populate Elasticsearch index**: Run ingestion script to sync fund data to Elasticsearch for full multi-tier ranking. Verify by searching and checking result order prioritizes exact matches.

6. **[DONE] Create fund detail API endpoint**: `GET /funds/{fund_id}` endpoint exists in `backend/app/api/funds.py` returning `FundDetail` with AIMC classification and investment constraints. Verified via API docs at `/docs`.

7. **[DONE] Implement fund detail page**: Fund detail page implemented in `frontend/app/funds/[fundId]/page.tsx` with `FundDetailView` component showing two-tier layout (Fund Classification and Investment Requirements). URL decoding for fund IDs with special characters. Verified by clicking fund card and seeing full details.

18. **[DONE] Implement AIMC fund classification**: Added database columns (`aimc_category`, `aimc_code`, `aimc_category_source`), migration script, ingestion script matching AIMC CSV (3,139 funds) and SEC API codes (2,040 funds), frontend display in catalog cards and detail page with fallback indicator. Verified by checking fund cards show AIMC Type and detail page shows classification with source tracking.

8. **Add database migrations**: Set up Alembic in `backend/`, create initial migration from existing schema. Verify by running migration on fresh database.

9. **[DONE] Fetch category options from API**: Created `GET /funds/categories` and `GET /funds/risks` endpoints returning distinct values with counts, upgraded `GET /funds/amcs` with search and pagination, updated `FilterPanel.tsx` to fetch all filter options from API. Filter options now show counts and support full AMC coverage via typeahead search. Verified by checking filter dropdowns show actual dataset values with counts.

10. **Add frontend Dockerfile**: Create `frontend/Dockerfile` for production build. Verify by running `docker-compose up --build`.

11. **[PARTIAL] Improve error handling in API**: Added error handling with HTTPException to filter metadata endpoints (`/funds/categories`, `/funds/risks`, `/funds/amcs`) returning 500 with error details. Added tests for error cases. Still need specific exception types and status codes (400 for validation, 404 for not found) for other endpoints.

12. **Add database health check**: Update `/health` endpoint to verify database connectivity. Verify by stopping database and checking health endpoint returns unhealthy.

13. **Add frontend error boundary**: Create error boundary component to catch React errors. Verify by intentionally causing error and seeing boundary.

14. **[DONE] Populate risk level and expense ratio**: Enrichment process implemented (`backend/app/services/ingestion/enrich_funds.py`) to fetch risk level from `/fund/{proj_id}/suitability` and expense ratio from `/fund/{proj_id}/fee`. Supports class-specific expense ratio calculation. Raw fee data stored in `fee_data_raw` JSONB column for analysis. Verified with K-INDIA showing 1.85% expense ratio for both classes.

15. **Add API request logging**: Add structured logging middleware to FastAPI for request/response logging. Verify by checking logs during API calls.

15. **[DONE] Implement share class support**: Added `class_abbr_name` field to Fund model, updated primary key to composite `(proj_id, class_abbr_name)`, modified ingestion to fetch and create separate records for each share class, updated enrichment to handle class-specific calculations, updated API to support class-based lookups. Tested with K-INDIA showing separate entries for K-INDIA-A(A) and K-INDIA-A(D). Verified by checking API returns class names as `fund_id` and list funds shows separate entries.

16. **[DONE] Implement fund comparison feature (US-N6)**: Created CompareService, compare API endpoint, fee grouping utility, compare data models, frontend CompareTray component, compare page with side-by-side layout, compare state hook with URL-first approach, "Add to Compare" buttons on FundCard and FundDetailView. Backend tests (26/26 passing) cover compare endpoint and fee grouping. Verified by adding 2-3 funds to compare, viewing side-by-side comparison with fees grouped by category, dealing constraints, and distribution data.

20. **[DONE] Implement Switch Impact Preview (US-N8)**: Created SwitchService with expense ratio calculation from SEC API fee breakdown (matches fund detail page), constraints delta calculation, coverage classification, and per-section missing flags. Backend endpoint `POST /switch/preview` returns calculated deltas, explainability, and coverage status. Frontend components: SwitchPreviewPage (standalone route), SwitchPreviewPanel (inline on Compare page), FeeImpactCard, RiskChangeCard, CategoryChangeCard, ConstraintsDeltaCard, ExplanationCard. Database table `switch_preview_log` for request traceability. Migration script `migrate_switch_preview_log.py` creates log table. Verified by navigating to compare page, clicking "Switch Preview", selecting funds and amount, viewing preview with fee impact, risk change, category change, and constraints differences. Expense ratio fix: Uses actual expense ratio from SEC API fee breakdown (actual_value from "Total Fees & Expenses" row), ensuring consistency with fund detail page display.

17. **Full re-ingestion for share classes**: Run ingestion script to populate class data for all funds with share classes. Verify by checking database has separate records for funds with multiple classes.

18. **Cleanup base fund records**: Remove base fund records (with empty `class_abbr_name`) for funds that have share classes. Verify by checking no duplicate entries in fund list.

19. **[DONE] Fund Detail Enhancements (Features 2.1, 2.2, 2.3, 2.5)**: Implemented based on SEC API data analysis (`backend/fund_data_analysis_SCBNK225E.md`):
    - **2.1 Share Class Display**: New ShareClassCard showing current class, sibling classes with navigation links, dividend policy badges (INC/ACC). Backend endpoint `GET /funds/{fund_id}/share-classes` returns classes from SEC API.
    - **2.2 Detailed Fee Breakdown**: New FeeBreakdownCard showing fees by section (Transaction/Recurring), with Max (prospectus) and Actual (charged) values, Total Expense Ratio. Backend endpoint `GET /funds/{fund_id}/fees` with contains-based Thai text matching for fee categorization.
    - **2.3 Investment Strategy Display**: New FundPolicyCard with Policy Type, AIMC Category (with source indicator), and Management Style with description (Passive: "tracks index, lower fees" / Active: "managers select investments, higher fees").
    - **2.5 Distribution Policy**: New DistributionPolicyCard showing Income/Accumulating classification with explanatory descriptions.
    - **Expense Ratio Consistency Fix**: Removed duplicate expense ratio from KeyFactsCard (was showing database value), consolidated in FeeBreakdownCard (shows SEC API values). KeyFactsCard grid changed from 3 to 2 columns.
    - Verified by viewing fund detail page showing all new cards with data from SEC API.

## 12. Appendix: Evidence Index

### Backend Files
- `backend/main.py` - FastAPI application entry point
- `backend/app/api/funds.py` - Fund API endpoints
- `backend/app/services/fund_service.py` - Fund business logic service with Elasticsearch/SQL search
- `backend/app/services/search/__init__.py` - Search module exports
- `backend/app/services/search/backend.py` - SearchBackend abstract interface and models
- `backend/app/services/search/elasticsearch_backend.py` - Elasticsearch search implementation
- `backend/app/services/ingestion/ingest_funds.py` - SEC Thailand data ingestion script with ES sync
- `backend/app/utils/__init__.py` - Utils module exports
- `backend/app/utils/normalization.py` - Text normalization utility for search
- `backend/app/models/fund_orm.py` - SQLAlchemy ORM models (includes composite primary key for share classes, filter metadata indexes for US-N3)
- `backend/app/services/ingestion/migrate_schema.py` - Database schema migration script (adds columns, updates primary keys)
- `backend/app/services/ingestion/migrate_aimc_columns.py` - Migration script for AIMC classification columns
- `backend/app/services/ingestion/ingest_aimc_categories.py` - AIMC classification ingestion script (matches AIMC CSV and SEC API codes)
- `backend/app/utils/sec_api_client.py` - SEC API client with `fetch_class_fund()` method for share class data and `fetch_fund_compare()` for AIMC codes
- `backend/app/services/ingestion/enrich_funds.py` - Fund enrichment service (risk level and expense ratio with class-specific support)
- `backend/app/services/compare_service.py` - Compare service aggregating fund comparison data (US-N6)
- `backend/app/services/switch_service.py` - Switch impact preview service with expense ratio calculation, constraints delta, and coverage classification (US-N8)
- `backend/app/utils/fee_grouping.py` - Fee categorization and grouping utility (US-N6)
- `backend/app/models/fund.py` - Pydantic request/response schemas (includes CategoryItem, RiskItem, AMCItem, CategoryListResponse, RiskListResponse, AMCListResponse for US-N3, CompareFundsResponse, CompareFundData, FeeGroup, DealingConstraints, DistributionData for US-N6, SwitchPreviewRequest, SwitchPreviewResponse, ConstraintsDelta, SwitchPreviewMissingFlags, Deltas, Explainability, Coverage for US-N8, AIMC classification fields and investment constraints for FundDetail and FundSummary, ShareClassInfo, ShareClassListResponse, FeeBreakdownItem, FeeBreakdownSection, FeeBreakdownResponse for fund detail enhancements)
- `backend/app/api/switch.py` - Switch impact preview API endpoint (US-N8)
- `backend/app/services/ingestion/migrate_switch_preview_log.py` - Migration script for switch preview log table (US-N8)
- `backend/app/core/config.py` - Application configuration (includes Elasticsearch settings)
- `backend/app/core/database.py` - Database connection and session management
- `backend/app/core/elasticsearch.py` - Elasticsearch client initialization
- `backend/tests/test_funds_api.py` - API endpoint tests
- `backend/tests/test_filter_metadata_api.py` - Filter metadata endpoint tests (US-N3)
- `backend/tests/test_compare_api.py` - Compare endpoint tests (US-N6)
- `backend/tests/test_fee_grouping.py` - Fee grouping utility tests (US-N6)
- `backend/tests/test_switch_api.py` - Switch preview API endpoint tests (US-N8)
- `backend/tests/test_switch_service.py` - Switch service business logic tests (US-N8)
- `backend/tests/conftest.py` - Pytest configuration
- `backend/requirements.txt` - Python dependencies (includes elasticsearch, aiohttp)
- `backend/Dockerfile` - Backend container definition

### Frontend Files
- `frontend/app/page.tsx` - Home page
- `frontend/app/funds/page.tsx` - Fund catalog page
- `frontend/app/funds/[fundId]/page.tsx` - Fund detail page with URL decoding
- `frontend/app/compare/page.tsx` - Compare page (US-N6)
- `frontend/app/switch/page.tsx` - Switch preview page (US-N8)
- `frontend/app/layout.tsx` - Root layout (includes CompareTray component)
- `frontend/components/FundCatalog/FundCatalog.tsx` - Main catalog component with search results label
- `frontend/components/FundCatalog/useFundCatalog.ts` - Catalog state management hook with clearSearch
- `frontend/components/FundCatalog/FilterPanel.tsx` - Filter sidebar with API-driven options, typeahead AMC search, loading/error states (US-N3)
- `frontend/components/FundCatalog/FilterSection.tsx` - Filter section component with conditional title rendering
- `frontend/components/FundCatalog/SearchInput.tsx` - Search input component
- `frontend/components/FundCatalog/EmptyState.tsx` - Search-specific and generic empty states
- `frontend/components/FundCatalog/FundCard.tsx` - Fund card component with AIMC Type display and inline compare button
- `frontend/components/FundDetail/FundDetailView.tsx` - Main fund detail view component with card-based layout
- `frontend/components/FundDetail/KeyFactsCard.tsx` - Two-tier fund information display (Classification with 2-column grid, Investment Requirements)
- `frontend/components/FundDetail/FreshnessBadge.tsx` - Data freshness badge component
- `frontend/components/FundDetail/ShareClassCard.tsx` - Share class navigation and display (feature 2.1)
- `frontend/components/FundDetail/FeeBreakdownCard.tsx` - Detailed fee breakdown with Max/Actual values (feature 2.2)
- `frontend/components/FundDetail/FundPolicyCard.tsx` - Investment strategy and management style display (feature 2.3)
- `frontend/components/FundDetail/DistributionPolicyCard.tsx` - Dividend/distribution policy display (feature 2.5)
- `frontend/components/FundDetail/index.ts` - Barrel exports for FundDetail components
- `frontend/components/Compare/CompareTray.tsx` - Persistent compare tray component (US-N6)
- `frontend/components/Compare/ComparePage.tsx` - Main compare page component (US-N6)
- `frontend/components/Compare/CompareFundColumn.tsx` - Individual fund column in comparison (US-N6)
- `frontend/components/Compare/CompareSection.tsx` - Reusable section wrapper component (US-N6)
- `frontend/components/Compare/useCompareState.ts` - URL-first compare state management hook (US-N6)
- `frontend/components/Compare/SwitchPreviewPanel.tsx` - Inline switch preview panel on Compare page (US-N8)
- `frontend/components/Switch/SwitchPreviewPage.tsx` - Standalone switch preview page component (US-N8)
- `frontend/components/Switch/FeeImpactCard.tsx` - Fee impact display card (US-N8)
- `frontend/components/Switch/RiskChangeCard.tsx` - Risk level change display card (US-N8)
- `frontend/components/Switch/CategoryChangeCard.tsx` - Category change display card (US-N8)
- `frontend/components/Switch/ConstraintsDeltaCard.tsx` - Dealing constraints differences display card (US-N8)
- `frontend/components/Switch/ExplanationCard.tsx` - Explainability information display card (US-N8)
- `frontend/utils/api/funds.ts` - API client functions (includes fetchCompareFunds for US-N6)
- `frontend/utils/api/switch.ts` - Switch API client functions (includes fetchSwitchPreview for US-N8)
- `frontend/types/fund.ts` - TypeScript type definitions (includes CompareFundsResponse, CompareFundData, FeeGroup, DealingConstraints, DistributionData for US-N6, AIMC classification fields and investment constraints for FundDetail and FundSummary, ShareClassInfo, ShareClassListResponse, FeeBreakdownItem, FeeBreakdownSection, FeeBreakdownResponse for fund detail enhancements)
- `frontend/types/switch.ts` - TypeScript type definitions for switch preview (SwitchPreviewRequest, SwitchPreviewResponse, ConstraintsDelta, SwitchPreviewMissingFlags, Deltas, Explainability, Coverage for US-N8)
- `frontend/package.json` - Node.js dependencies and scripts

### Configuration Files
- `docker-compose.yml` - Multi-container orchestration
- `README.md` - Project overview and setup instructions

### Documentation Files
- `docs/user_story/us1.md` - User story 1: Browse fund catalog
- `docs/user_story/us2.md` - User story 2: Search funds
- `docs/user_story/us-n1.md` - User story N1: Search normalization and ranking
- `docs/user_story/us-n3.md` - User story N3: Data-driven filter metadata (categories, risks, full AMC search)
- `docs/user_story/us-n4.md` - User story N4: Data completeness upgrade (risk level and expense ratio)
- `docs/user_story/us-n5.md` - User story N5: Home page funnel
- `docs/user_story/us-n6.md` - User story N6: Compare tray and side-by-side comparison
- `docs/user_story/us-n6-manual-verification.md` - Manual verification steps for compare feature
- `docs/user_story/us-n8.md` - User story N8: Switch Impact Preview v1 (Explainable, Constrained, Demo-Ready)
- `docs/share_class_implementation_plan.md` - Share class implementation plan and approach
- `docs/architecture_recommendations.md` - Architecture guidance

