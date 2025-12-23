# Switch Impact Simulator — Working Backwards (PR/FAQ + MVP Plan)

## 0) One open question (with recommendation)
**Question:** For MVP, do we support **Thailand-domiciled mutual funds only** (including offshore feeder funds sold locally), or also **direct offshore funds/ETFs**?

**Recommendation:** Start with **Thailand-domiciled funds only** for MVP to keep data normalization (fees, classes, tax), corporate actions, and time-series coverage consistent—while still claiming “across all AMCs.” Add offshore/ETF as Phase 2 once the portfolio math + switch workflow is proven.

---

## 1) Press Release (Internal Draft)

### Introducing Switch Impact Simulator — Know what changes *before* you switch mutual funds
**Bangkok, Thailand —** Today we’re launching the MVP of **Switch Impact Simulator**, a portfolio-first decision tool for investors who are considering switching mutual funds and want to understand **portfolio-level consequences**—not just side-by-side fund stats.

Most fund platforms do a decent job at:
- Fund discovery (search, filters, ranking)
- Fund detail pages (performance, fees, factsheet)
- Basic comparisons (Fund A vs Fund B)

But when a user asks the real decision question—**“If I switch, what happens to my portfolio outcome?”**—they usually have to do the reasoning themselves.

**Switch Impact Simulator** closes that gap by combining:
1) **On-par discovery & comparison** (the top-of-funnel users expect), and  
2) A dedicated **Switch Impact Workspace** that shows the before/after impact in one place:
- Expected risk/return shift (simple, transparent assumptions)
- Fee drag and switching costs
- Portfolio concentration and diversification change
- Scenario outcomes over a selected horizon
- A clear recommendation summary: “Worth switching?” with trade-offs

The product is designed so discovery becomes the **main funnel**:
- Users discover a fund → compare it → then see a prominent CTA: **“Simulate Switch Impact”**
- Advanced users can also jump straight into **Switch Impact** from the main navigation.

### Target customer
Mass-affluent and self-directed investors who already hold mutual funds (or are close to investing) and:
- Want to upgrade holdings (fees, style fit, risk)
- Are overwhelmed by performance chasing
- Don’t have a portfolio-level view of switching trade-offs

### Customer quote (desired)
“I finally understand whether switching is actually worth it—beyond last year’s performance chart.”

### What’s new / why it matters
- **From fund-level to portfolio-level:** The core decision is about the user’s outcome, not just a fund.
- **Decision workspace, not just content:** A guided flow with outputs that feel like a professional impact memo.
- **Discovery as a funnel:** Users arrive for catalog/comparison, then convert to impact simulation.

### Call to action
Users can:
1) Browse funds across AMCs  
2) Compare options  
3) Click **Simulate Switch Impact** to see portfolio consequences before executing a switch

---

## 2) FAQ (Internal)

### 2.1 Customer & value
**Q: What problem are we solving?**  
A: Users can compare funds, but they cannot easily answer: **“What does this switch do to my portfolio outcome?”** Most platforms leave users to guess trade-offs across return, risk, fees, and concentration.

**Q: Who is this for in MVP?**  
A: Investors who already hold at least one fund (even if entered manually) and are considering switching due to performance, fees, or fit.

**Q: What is the primary “job to be done”?**  
A: “Help me decide whether to switch funds with confidence, using portfolio-level impact—not just fund stats.”

---

### 2.2 Product positioning
**Q: How is this different from a fund supermarket’s compare page?**  
A: Compare pages answer “Which fund looks better?”  
Switch Impact answers “**Should I switch** given my holdings, horizon, and costs?”

**Q: Why keep discovery if our differentiation is switch impact?**  
A: Discovery is the highest-intent acquisition loop. Users naturally start by searching, filtering, and comparing funds. The product then converts that intent into the differentiated workflow via a clear CTA and guided workspace.

**Q: Can users still jump straight to Switch Impact?**  
A: Yes. MVP supports two entry paths:
- **Discovery-led (primary funnel):** Fund page / Compare → “Simulate Switch Impact”
- **Direct entry (secondary):** Nav → “Switch Impact”

---

### 2.3 MVP scope decisions (to keep it buildable and demo-ready)
**Q: What does “Switch Impact” calculate in MVP (minimum credible)?**  
A: A transparent, explainable model:
- Historical performance bands (e.g., 1Y/3Y/5Y) as reference, not promises
- Volatility / max drawdown approximations (where data exists)
- Fee impact using published expense ratios + estimated holding period
- Switching cost inputs (user-provided or rules-based defaults)
- Portfolio concentration shifts (asset class/category exposures from fund metadata)
- Scenario projection (base / optimistic / pessimistic) using simple assumptions and clear disclaimers

**Q: What is explicitly out of scope for MVP?**  
A:
- Automated execution of switching trades
- Personalized tax advice (beyond simple “tax-aware flags”/disclaimers)
- Full holdings look-through via daily portfolio files from brokers/banks
- Complex optimization (mean-variance optimizer, factor models)
- Real-time streaming or intraday pricing (NAV is sufficient for mutual funds)

**Q: How do we handle data limitations?**  
A: MVP uses a “best available + transparent confidence” approach:
- Show data source coverage per fund
- If a metric is unavailable, degrade gracefully and explain what’s missing
- Always show disclaimers: informational tool, not financial advice

---

### 2.4 UX & workflow
**Q: What does the end-to-end workflow look like?**  
A:
1) Discovery: Search/filter → Fund detail  
2) Compare: Add 2–3 funds to compare  
3) CTA: “Simulate Switch Impact”  
4) Switch Impact Workspace:
   - Step 1: Confirm current holding(s) (manual input supported)
   - Step 2: Select target fund(s)
   - Step 3: Define switch amount + horizon + switching costs
   - Step 4: Review impact summary + detailed tabs (risk/return/fees/diversification)
   - Step 5: Save/share the scenario

**Q: What is the “wow moment” in the demo?**  
A: In one click from a compare page, the user sees:
- “Before vs After portfolio outcome”
- “Fee drag difference over X years”
- “Diversification impact” (concentration flags)
- A simple verdict: “Switch improves fee efficiency but increases volatility”

---

### 2.5 Success metrics
**Q: What metrics define MVP success?**  
A (instrumented from day 1):
- Funnel conversion: Discovery → Compare → Switch Impact (CTA click-through)
- Scenario completion rate (start → impact report viewed)
- Save/share rate (scenario saved, exported, or link shared)
- Return usage: repeat simulations per user in 7/30 days
- Qualitative: “Confidence gained” thumbs-up/down + reason tags

---

## 3) Working Backwards: Customer Experience (Narrative Spec)

### Primary entry (Discovery-led)
1) User searches “Global equity fund low fee”  
2) Filters by category, risk level, AMC, fee band  
3) Opens Fund A → adds Fund B → compares  
4) Sees CTA: **Simulate Switch Impact**  
5) Enters: current holding (Fund X, amount), switch amount, horizon, switching fee  
6) Receives an impact report:
   - Outcome summary (risk/return/fee/diversification)
   - Key trade-offs & “what would make this a bad idea”
   - Save scenario

### Secondary entry (Direct)
1) User clicks nav: “Switch Impact”  
2) Selects current holding and target fund  
3) Same impact workflow and outputs

---

## 4) MVP Feature Set (On-par Discovery + Differentiated Switch Impact)

### 4.1 Discovery & Comparison (Top-of-funnel)
**MVP includes**
- Fund catalog across AMCs
- Search + core filters (category, risk level, fee band, AMC, dividend policy)
- Fund detail page:
  - Basic performance table
  - Fees
  - Risk level / category labels
  - Factsheet link (if available)
- Compare 2–3 funds side-by-side
- Persistent “Compare tray” (add/remove funds)

**Deliberate constraints**
- No social feed, no community, no editorial content engine in MVP
- No personalized recommendations beyond simple “similar funds” rules

---

### 4.2 Switch Impact Workspace (Differentiation)
**MVP includes**
- Scenario builder:
  - Current holding fund(s) (manual add)
  - Target fund
  - Switch amount (partial/full)
  - Time horizon
  - Switching fee input (with sensible defaults)
- Impact summary card (single screen “executive view”):
  - Expected risk/return direction (up/down + magnitude bands)
  - Fee impact over horizon
  - Diversification / concentration flags
- Detail tabs:
  - Fees & costs breakdown
  - Risk snapshot (volatility/drawdown proxies where available)
  - Category/exposure deltas (metadata-based)
  - Scenarios (base/optimistic/pessimistic)
- Save scenario (local account storage) + export/share link

**Design principle**
- Always show **assumptions** and **confidence**. If data is incomplete, show what’s missing and degrade gracefully.

---

## 5) Information Architecture (Key Screens)
1) **Catalog** (search/filter)
2) **Fund Detail** (CTA to compare + simulate)
3) **Compare** (CTA to simulate)
4) **Switch Impact Workspace**
   - Stepper input
   - Impact report view
   - Save/export

---

## 6) Data & Calculation Approach (MVP-safe)
- **Fund metadata:** category, AMC, risk level, fee/expense ratio, inception date
- **NAV series:** to compute historical return references + volatility proxies (where possible)
- **Assumptions engine (explicit):**
  - Projection uses simple bands or historical-based proxies, clearly labeled “not guaranteed”
  - Fees modeled as annual drag over horizon
  - Switching cost modeled as one-time friction
- **Confidence score:**
  - Based on data completeness (NAV history length, fee availability, category mapping quality)

---

## 7) Demo Script (60–90 seconds)
1) Open **Fund Catalog** → filter to a category  
2) Compare **Fund A vs Fund B**  
3) Click **Simulate Switch Impact**  
4) Enter a current holding + horizon + switching fee  
5) Show the **Impact Summary**: fees down, volatility up, diversification change  
6) Save/export the scenario  
7) Close: “We’re on-par for discovery, but differentiated where it matters—portfolio-level switching decisions.”

---

## 8) Risks & Mitigations
- **Risk: Users misinterpret projections as promises**  
  Mitigation: strong labeling, assumptions panel, confidence score, “informational only” disclaimer
- **Risk: Data gaps across AMCs**  
  Mitigation: graceful degradation + transparent coverage
- **Risk: MVP feels like just another compare tool**  
  Mitigation: make Switch Impact outputs unmistakably portfolio-level and memo-like

---

## 9) Phaseing (Agile, demo-driven)
**Phase 1 (MVP demo-ready):**
- Catalog + Fund detail + Compare
- Switch Impact (single holding → single target)
- Save scenario + share/export

**Phase 2 (Expansion):**
- Multiple holdings / multi-leg switches
- Better exposure mapping
- Smarter defaults and “similar fund” discovery

**Phase 3 (Moat-building):**
- Tax-aware modules (jurisdiction-specific)
- Broker integrations / portfolio import
- More robust risk models (if data + compliance allow)

---
