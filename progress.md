# Project Progress (Current Snapshot)

## 1. What This Repo Does

Switch Impact Simulator is a portfolio-first decision tool for mutual fund investors. The system enables users to browse, search, filter, and compare Thai mutual funds across all Asset Management Companies (AMCs) using data from SEC Thailand.

The application consists of:
- **Backend**: FastAPI service (`backend/`) providing REST API for fund data with cursor-based pagination, search, filtering, and sorting
- **Frontend**: Next.js 16 application (`frontend/`) with App Router providing the Fund Catalog UI
- **Data Ingestion**: Python script (`backend/app/services/ingestion/ingest_funds.py`) that fetches fund data from SEC Thailand API and stores it in PostgreSQL

## 2. Implemented Features (User-Visible)

### Fund Catalog Browse
- **What it does**: Displays paginated list of active mutual funds with fund name, AMC, category, risk level, and expense ratio
- **Where it lives**: `frontend/app/funds/page.tsx`, `frontend/components/FundCatalog/`
- **How to verify**: Navigate to `/funds` route, see paginated fund cards with "Load More" button
- **Current limitations**: Fund detail page (`/funds/[fundId]`) shows placeholder only

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

`fund` (`backend/app/models/fund_orm.py` lines 28-75)
- Primary key: `proj_id` (String(50))
- Foreign key: `amc_id` → `amc.unique_id`
- Fields: `fund_name_th`, `fund_name_en`, `fund_abbr`, `fund_status` (required), `regis_date`, `category`, `risk_level`, `expense_ratio`, `last_upd_date`, `data_snapshot_id`
- Normalized search fields: `fund_name_norm`, `fund_abbr_norm` (nullable, not currently populated)
- Indexes:
  - `idx_fund_name_asc` on (`fund_name_en`, `proj_id`)
  - `idx_fund_status` on (`fund_status`)
  - `idx_fund_search` on (`fund_name_norm`, `fund_abbr_norm`)
  - `idx_fund_category` on (`fund_status`, `category`) - Composite for filtering + aggregation (US-N3)
  - `idx_fund_risk` on (`fund_status`, `risk_level`) - Composite for filtering + aggregation (US-N3)
  - `idx_fund_amc` on (`fund_status`, `amc_id`) - For AMC filtering and aggregation (US-N3)

`amc` (`backend/app/models/fund_orm.py` lines 11-30)
- Primary key: `unique_id` (String(20))
- Fields: `name_th`, `name_en`, `last_upd_date`
- Relationship: One-to-many with `fund`
- Indexes:
  - `idx_amc_name_search` on (`name_en`, `name_th`) - For typeahead search (US-N3)

**Migration/Seeding**: Tables created via `Base.metadata.create_all()` in ingestion script (`backend/app/services/ingestion/ingest_funds.py` line 194). No Alembic migrations present.

### Business Logic / Domain Services

**FundService** (`backend/app/services/fund_service.py`)
- `list_funds()`: Cursor-based pagination with keyset method, supports nullable sort columns, handles search via Elasticsearch (with SQL fallback), applies filters (AMC, category, risk, fee_band), supports 6 sort options
- `_list_funds_elasticsearch()`: Uses Elasticsearch search backend with automatic fallback to SQL when ES index is empty
- `_list_funds_sql()`: SQL-based search using normalized fields with fallback to raw fields when normalized is NULL
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
- `store_funds()`: Upserts active funds (status="RG") with category inference from name patterns, populates `fund_name_norm` and `fund_abbr_norm` using normalization utility, syncs to Elasticsearch index
- `_infer_category()`: Keyword-based categorization (Equity, Fixed Income, Money Market, Mixed, Property/REIT, Commodity, Foreign Investment)
- Rate limiting: 100ms delay between requests (safe for 3000/300s limit)
- Snapshot tracking: Creates `data_snapshot_id` timestamp per ingestion run

### Integrations

**SEC Thailand API** (`backend/app/services/ingestion/ingest_funds.py`)
- Base URL: `https://api.sec.or.th/FundFactsheet`
- Endpoints used: `/fund/amc`, `/fund/amc/{amc_id}`
- Authentication: `Ocp-Apim-Subscription-Key` header from `SEC_FUND_FACTSHEET_API_KEY` env var
- Configuration: `backend/app/core/config.py` (lines 14-15)

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
- Placeholder implementation only
- Shows "Full fund details will be available in US4" message
- Navigation: Back link to catalog

### Components

**FundCatalog** (`frontend/components/FundCatalog/FundCatalog.tsx`)
- Main catalog container with header, filters sidebar, search, sort controls, fund grid, load more button
- Shows "Showing results for '<query>'" label when search is active
- States: loading_initial, loaded, error_initial, loading_more, error_load_more, end_of_results, idle
- Uses `useFundCatalog` hook for state management

**EmptyState** (`frontend/components/FundCatalog/EmptyState.tsx`)
- Search-specific empty state: Shows "No funds match '<query>'" with helpful message and "Clear search" button
- Generic empty state: Shows "No funds available" when no search query

**FundCard** (`frontend/components/FundCatalog/FundCard.tsx`)
- Displays individual fund summary (name, AMC, category, risk, fee)
- Links to fund detail page

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
- `fetchCategories()`: Calls `/funds/categories` endpoint, returns `CategoryListResponse` (US-N3)
- `fetchRisks()`: Calls `/funds/risks` endpoint, returns `RiskListResponse` (US-N3)
- `fetchAMCs()`: Calls `/funds/amcs` endpoint with optional search, limit, and cursor params, returns `AMCListResponse` (US-N3)
- Uses `NEXT_PUBLIC_API_URL` env var (defaults to `http://localhost:8000`)
- Real API integration (not mocked)

### Navigation/Routing

- Next.js App Router with file-based routing
- Routes: `/` (home), `/funds` (catalog), `/funds/[fundId]` (detail)
- Client-side navigation via Next.js `Link` component

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
- Test files: `test_funds_api.py`, `test_filter_metadata_api.py`
- Test coverage:
  - `TestListFunds`: Success cases, filters, sort, cursor pagination, limit validation, empty results
  - `TestHealthCheck`: Health endpoint
  - `TestRootEndpoint`: Root endpoint
  - `TestGetCategories`: Success with counts, excludes nulls, ordering, empty results, error handling (US-N3)
  - `TestGetRisks`: Success with counts, excludes nulls, ordering, empty results (US-N3)
  - `TestGetAMCs`: Basic listing, search functionality, pagination, limit validation, empty results, cursor handling, combined params (US-N3)
  - `TestFilterMetadataIntegration`: Response structure validation for all filter metadata endpoints (US-N3)
- Mocking: Uses `unittest.mock` to mock `FundService`
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

## 9. Known Gaps / Not Implemented Yet

### Product Gaps (UX/Workflows)

- Fund detail page is placeholder only (`frontend/app/funds/[fundId]/page.tsx` shows "Full fund details will be available in US4")
- Home page is default Next.js template, not customized for project
- No compare tray functionality (mentioned in US1 as out of scope)
- No user authentication or personalization
- No trending/popularity ranking

### Backend Gaps

**Data Ingestion**:
- Risk level and expense ratio are set to NULL in ingestion (lines 124-125 of `ingest_funds.py`) - requires additional API calls per fund
- No database migrations system (Alembic) - tables created via `create_all()`

**API Endpoints**:
- Individual fund detail endpoint exists (`GET /funds/{fund_id}`) - implemented in previous work
- No fund comparison endpoint
- No switch impact simulation endpoint (core product feature)

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

## 10. Next Best Tasks (Small, Testable Increments)

1. **[DONE] Populate normalization fields during ingestion**: Normalization utility created (`backend/app/utils/normalization.py`), ingestion script updated to populate `fund_name_norm` and `fund_abbr_norm`.

2. **[DONE] Implement relevance ranking for search**: Multi-tier search ranking implemented in Elasticsearch backend (exact match → prefix match → substring match). SQL fallback also improved with normalized + raw field search.

3. **Add tests for normalization and search**: Create unit tests for `normalize_search_text()` function, Elasticsearch search backend, and SQL fallback logic. Verify test coverage.

4. **Add frontend tests for EmptyState**: Test search-specific empty state and clearSearch functionality. Verify by running Jest tests.

5. **Populate Elasticsearch index**: Run ingestion script to sync fund data to Elasticsearch for full multi-tier ranking. Verify by searching and checking result order prioritizes exact matches.

6. **Create fund detail API endpoint**: Add `GET /funds/{fund_id}` in `backend/app/api/funds.py` returning full fund details. Add test in `test_funds_api.py`. Verify via API docs at `/docs`.

7. **Implement fund detail page**: Replace placeholder in `frontend/app/funds/[fundId]/page.tsx` with real data fetch and display. Verify by clicking fund card and seeing details.

8. **Add database migrations**: Set up Alembic in `backend/`, create initial migration from existing schema. Verify by running migration on fresh database.

9. **[DONE] Fetch category options from API**: Created `GET /funds/categories` and `GET /funds/risks` endpoints returning distinct values with counts, upgraded `GET /funds/amcs` with search and pagination, updated `FilterPanel.tsx` to fetch all filter options from API. Filter options now show counts and support full AMC coverage via typeahead search. Verified by checking filter dropdowns show actual dataset values with counts.

10. **Add frontend Dockerfile**: Create `frontend/Dockerfile` for production build. Verify by running `docker-compose up --build`.

11. **[PARTIAL] Improve error handling in API**: Added error handling with HTTPException to filter metadata endpoints (`/funds/categories`, `/funds/risks`, `/funds/amcs`) returning 500 with error details. Added tests for error cases. Still need specific exception types and status codes (400 for validation, 404 for not found) for other endpoints.

12. **Add database health check**: Update `/health` endpoint to verify database connectivity. Verify by stopping database and checking health endpoint returns unhealthy.

13. **Add frontend error boundary**: Create error boundary component to catch React errors. Verify by intentionally causing error and seeing boundary.

14. **Populate risk level and expense ratio**: Extend ingestion to fetch per-fund details from SEC API (may require additional endpoint). Add rate limiting consideration. Verify by checking database has non-null values.

15. **Add API request logging**: Add structured logging middleware to FastAPI for request/response logging. Verify by checking logs during API calls.

## 11. Appendix: Evidence Index

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
- `backend/app/models/fund_orm.py` - SQLAlchemy ORM models (includes filter metadata indexes for US-N3)
- `backend/app/models/fund.py` - Pydantic request/response schemas (includes CategoryItem, RiskItem, AMCItem, CategoryListResponse, RiskListResponse, AMCListResponse for US-N3)
- `backend/app/core/config.py` - Application configuration (includes Elasticsearch settings)
- `backend/app/core/database.py` - Database connection and session management
- `backend/app/core/elasticsearch.py` - Elasticsearch client initialization
- `backend/tests/test_funds_api.py` - API endpoint tests
- `backend/tests/test_filter_metadata_api.py` - Filter metadata endpoint tests (US-N3)
- `backend/tests/conftest.py` - Pytest configuration
- `backend/requirements.txt` - Python dependencies (includes elasticsearch, aiohttp)
- `backend/Dockerfile` - Backend container definition

### Frontend Files
- `frontend/app/page.tsx` - Home page
- `frontend/app/funds/page.tsx` - Fund catalog page
- `frontend/app/funds/[fundId]/page.tsx` - Fund detail page (placeholder)
- `frontend/app/layout.tsx` - Root layout
- `frontend/components/FundCatalog/FundCatalog.tsx` - Main catalog component with search results label
- `frontend/components/FundCatalog/useFundCatalog.ts` - Catalog state management hook with clearSearch
- `frontend/components/FundCatalog/FilterPanel.tsx` - Filter sidebar with API-driven options, typeahead AMC search, loading/error states (US-N3)
- `frontend/components/FundCatalog/FilterSection.tsx` - Filter section component with conditional title rendering
- `frontend/components/FundCatalog/SearchInput.tsx` - Search input component
- `frontend/components/FundCatalog/EmptyState.tsx` - Search-specific and generic empty states
- `frontend/utils/api/funds.ts` - API client functions
- `frontend/types/fund.ts` - TypeScript type definitions
- `frontend/package.json` - Node.js dependencies and scripts

### Configuration Files
- `docker-compose.yml` - Multi-container orchestration
- `README.md` - Project overview and setup instructions

### Documentation Files
- `docs/user_story/us1.md` - User story 1: Browse fund catalog
- `docs/user_story/us2.md` - User story 2: Search funds
- `docs/user_story/us-n1.md` - User story N1: Search normalization and ranking
- `docs/user_story/us-n3.md` - User story N3: Data-driven filter metadata (categories, risks, full AMC search)
- `docs/architecture_recommendations.md` - Architecture guidance

