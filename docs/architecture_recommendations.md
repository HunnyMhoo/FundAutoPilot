# Architecture & Tech Stack Recommendations: Switch Impact Simulator

## 1. Executive Summary
The **Switch Impact Simulator** is a "Portfolio-First" decision tool. Unlike typical fund supermarkets that focus on *Discovery*, this product focuses on *Decision Support* (Simulation).
The technical architecture must support two distinct behaviors:
1.  **SEO-heavy, fast Content Delivery** for the Discovery phase (low interactivity, high read volume).
2.  **Rich, Client-heavy Interactivity** for the Switch Workspace (complex state, real-time recalculation, private user data).

## 2. Recommended Tech Stack (MVP)

### Frontend & Framework
*   **Framework:** **Next.js (App Router)**.
    *   *Why:* Best-in-class for hybrid applications. Use **Static Generation (SSG)** or **ISR** for Fund Catalog/Details (SEO, Speed) and **Client Components** for the Simulator Workspace.
*   **Language:** **TypeScript**.
    *   *Why:* Strict typing is critical for financial calculations (NAV, fees, units) to avoid precision errors and runtime bugs.
*   **Styling:** **Vanilla CSS with CSS Modules** or **Utility-first CSS (Tailwind)**.
    *   *Recommendation:* Even though "Vanilla CSS" is a constraint, for a rapid MVP with "Premium" aesthetics, a utility framework (Tailwind) allows faster iteration on consistent design tokens (colors, spacing). If strict Vanilla is required, use **CSS Variables** heavily for theming.
*   **State Management:** **Zustand** or **React Context**.
    *   *Why:* The "Switch Impact Workspace" is a complex multi-step wizard. You need a global store to hold the "Scenario" state (Selected Fund, Target Fund, Horizon, Amounts) across steps without prop drilling.

### Backend & Database
### Backend & Database
*   **Backend:** **Python (FastAPI)**.
    *   *Why:* Chosen for its strong integration with data science libraries (`pandas`, `numpy`) and ability to handle complex impact simulations.
*   **Database:** **PostgreSQL** (Managed via Supabase/Neon).
*   **Communication:** REST API (JSON) between Next.js (Frontend) and FastAPI (Backend).

### Selected Stack: Python (FastAPI)
**The "Quant & Data" Choice.**
We have selected Python to leverage the rich financial ecosystem.

*   **Key Advantages:**
    *   **Financial Ecosystem:** Direct access to battle-hardened libraries like `pandas` (data manipulation), `numpy` (vectorized math), `scipy` (optimization), and `pyportfolioopt`.
    *   **Talent Pool:** Easier for Data Scientists/Quants to contribute models directly.
*   **Implementation Strategy:**
    *   **FastAPI** handles all "Impact" logic, Simulations, and User Data persistence.
    *   **Next.js** handles the UI rendering and proxying requests (or calling directly if clean).

### Infrastructure
*   **Hosting:** **Vercel** (preferred for Next.js) or **AWS Amplify**.
*   **CI/CD:** GitHub Actions.

## 3. Architecture Patterns

### Hybrid Rendering Strategy
*   **Public Pages (Catalog, Fund Details):** Use **Server Components**. Fetch data at build time (or cached). These must load instantly for SEO/SEM landing.
*   **Workspace (The Simulator):** Use **Client Components**. The "Impact" calculation should happen *in the browser* primarily for immediate feedback.
    *   *Benefit:* Zero latency when user adjusts the "Switch amount" slider. No server round-trips for simple math.

### Domain Separation
Organize code by **Feature** rather than Type.
*   `features/catalog`: Search, Filter, Fund Cards.
*   `features/simulator`: Wizard steps, Math Engine, Charts.
*   `features/user`: Profile, Saved Scenarios.

### The "Math Core"
Isolate the financial logic (CAGR, Fee Drag, Drawdown) into a pure, testable library (`lib/financial-math`).
*   **Critical:** This logic must be unit-tested heavily.
*   **Reuse:** Can be used by the UI for live preview and by the API for generating PDF reports/emails later.

## 4. Project Structure Recommendation

/
├── frontend/                   # Next.js App Router (UI Layer)
│   ├── app/                    # Pages & Layouts
│   ├── components/             
│   └── lib/                    # API clients (fetchers)
├── backend/                    # Python FastAPI (Logic Layer)
│   ├── app/
│   │   ├── api/                # Endpoints (v1/impact, v1/funds)
│   │   ├── core/               # Config, DB connection
│   │   ├── models/             # Pydantic models & DB schemas
│   │   └── services/           # Business Logic
│   │       ├── calculation/    # The "Quant" Core (pandas/numpy)
│   │       └── ingestion/      # NAV import scripts
│   ├── tests/                  # Pytest
│   └── main.py                 # App entrypoint
└── docs/                       # Architecture decisions, Press Release

## 5. MVP Data Strategy
*   **Fund Data:** Do not try to stream real-time. Use **End-of-Day (EOD)** data.
*   **Ingestion:** A nightly script (GitHub Action or Vercel Cron) to fetch NAVs from source -> Upsert to DB.
*   **Caching:** Cache fund metadata heavily. It rarely changes.

## 6. Next Steps
1.  **Initialize Repository:** Set up Next.js + TypeScript.
2.  **Design System:** Define the "Premium" look (Fonts, Color Palette) in `globals.css` / Tailwind config.
3.  **Core Math Library:** Implement the `calculateImpact(current, target, horizon)` function first (TDD approach).
4.  **Prototype Workspace:** Build the Simulator UI with mock data to validate the UX.
