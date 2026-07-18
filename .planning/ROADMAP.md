# Roadmap: Popcorn Pilot

## Overview

Popcorn Pilot is built as a layered pipeline, not a set of independent features: a cache-first data/auth foundation, then a leakage-safe feature pipeline feeding a fully deterministic recommendation engine, then a multi-model prediction layer with honest walk-forward backtesting, then an LLM agent that reads (but never computes) on top of both, and finally a compliance audit and watchlist pass that closes the loop before launch. Each phase's correctness is a precondition for the one after it — most critically, the recommendation and prediction engines must be complete, deterministic, and testable with zero LLM dependency before the Gemini/LangGraph agent layer is built on top of them.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Foundation — Data Layer, Caching & Auth** - Cache-first market-data layer and Supabase auth/session foundation with strict per-user isolation
- [ ] **Phase 2: Investor Profile + Feature Engineering Foundation** - Profile builder UI plus a leakage-safe, point-in-time feature pipeline shared by later models
- [ ] **Phase 3: Deterministic Recommendation Engine** - Ranked, explainable, cross-asset-class shortlist from the hybrid factor + collaborative scorer, zero LLM dependency
- [ ] **Phase 4: Multi-Model Prediction + Walk-Forward Backtesting** - Per-asset forecasts (SMA/XGBoost/Prophet) with confidence intervals and walk-forward-validated accuracy
- [ ] **Phase 5: LLM Agent Layer (Rerank + Explain)** - Gemini/LangGraph agent reranks/annotates recommendations with a grounded plain-English thesis, read-only over the deterministic score
- [ ] **Phase 6: Compliance, Watchlist & Launch Readiness** - Disclaimer/non-directive-copy audit across every view, personal watchlist, app ready for deployment

## Phase Details

### Phase 1: Foundation — Data Layer, Caching & Auth

**Goal**: A secure, cache-first foundation exists: users can sign up and log in with strictly isolated sessions, and all market-data fetches are cached and resilient to rate limits.
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03
**Success Criteria** (what must be TRUE):

  1. A new user can sign up and log in via Supabase auth, and stays logged in across a page reload / new browser session.
  2. Two concurrent users each see only their own session state — no cached object or session value leaks between users.
  3. Repeated price-data fetches for the same ticker within the cache TTL return cached results instead of re-hitting yfinance, and the app degrades gracefully (stale-cache fallback + message, not a crash) when a fetch fails or is rate-limited.
  4. A signed-in user's data written to Supabase in one session is retrievable after logging back in on a new session or device.
  5. The base multipage app shell is navigable, with auth-gated pages rendering only for logged-in users.

**Plans**: 3/5 plans executed
Plans:
**Wave 1**

- [x] 01-01-PLAN.md — Dependency manifest, config module, Supabase profiles schema (RLS + trigger), local Supabase CLI stack

**Wave 2** *(blocked on Wave 1 completion)*

- [x] 01-02-PLAN.md — Auth session module: stateless cached client + require_auth() + sign-up/sign-in/magic-link/sign-out
- [x] 01-03-PLAN.md — Cache chokepoint: st.cache_data -> SQLite -> tenacity -> yfinance

**Wave 3** *(blocked on Wave 2 completion)*

- [ ] 01-04-PLAN.md — Login/signup page, placeholder home page, app entrypoint navigation (checkpoint)

**Wave 4** *(blocked on Wave 3 completion)*

- [ ] 01-05-PLAN.md — Two-session isolation, cross-session persistence, and RLS enforcement tests

**UI hint**: yes

### Phase 2: Investor Profile + Feature Engineering Foundation

**Goal**: Users can build and edit their investor profile, and a leakage-safe, point-in-time feature pipeline exists for the model layers to build on.
**Depends on**: Phase 1
**Requirements**: PROFILE-01, PROFILE-02
**Success Criteria** (what must be TRUE):

  1. User can complete a profile form (risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, existing holdings) that saves to Supabase.
  2. User can edit their existing profile and see the updated values reflected immediately on return to the profile screen (no stale cache).
  3. The feature engineering module computes technical/factor features using only point-in-time data; an automated leakage smoke test fails if any feature is built using future information.
  4. The same feature-computation functions serve both the (future) backtest harness and live inference without duplicated logic.

**Plans**: TBD
**UI hint**: yes

### Phase 3: Deterministic Recommendation Engine

**Goal**: Users get a fully deterministic, ranked, explainable shortlist of assets across all supported asset classes, scored against their profile with zero LLM dependency.
**Depends on**: Phase 2
**Requirements**: REC-01, REC-02, REC-03, REC-04
**Success Criteria** (what must be TRUE):

  1. User can view a ranked list of recommended assets spanning stocks, ETFs, crypto, gold, and forex, generated by the hybrid factor + collaborative-filtering-style scorer with no network/LLM call required to compute the ranking.
  2. Each ranked asset shows a composite score alongside a visible breakdown of its contributing sub-factors (not a single opaque number).
  3. Each recommendation includes a one-sentence plain-English reason.
  4. User can search for and view any asset from any supported asset class, including ones not currently in their recommended list.

**Plans**: TBD
**UI hint**: yes

### Phase 4: Multi-Model Prediction + Walk-Forward Backtesting

**Goal**: Users can drill into any asset and see multi-model price forecasts with confidence intervals, backed by honest walk-forward-validated accuracy metrics.
**Depends on**: Phase 3
**Requirements**: PRED-01, PRED-02, PRED-03, PRED-04
**Success Criteria** (what must be TRUE):

  1. User can drill into any recommended or searched asset via its drill-in page and see a historical price chart.
  2. User can select a prediction model (SMA baseline, XGBoost, or Prophet) and a forecast horizon, and generate a forecast for that asset.
  3. The forecast chart displays confidence intervals around the future prediction.
  4. User can see backtested accuracy (RMSE, directional accuracy, Sharpe) per model, computed via walk-forward validation with no lookahead bias.

**Plans**: TBD
**UI hint**: yes

### Phase 5: LLM Agent Layer (Rerank + Explain)

**Goal**: An LLM agent reranks and annotates the deterministic recommendations with a plain-English investment thesis, strictly as a read-only overlay on the existing recommendation list view.
**Depends on**: Phase 3, Phase 4
**Requirements**: AGENT-01, AGENT-02
**Success Criteria** (what must be TRUE):

  1. On the recommendation list view, each asset displays an LLM-generated (Gemini via LangGraph) plain-English investment thesis grounded in and referencing its visible factor score.
  2. The underlying composite scores and rankings are identical whether or not the agent layer runs — the agent never recomputes or overrides the deterministic score.
  3. When the Gemini quota is exhausted or a call fails, the recommendation list view still renders correctly (agent commentary gracefully omitted) rather than the app breaking.

**Plans**: TBD
**UI hint**: yes

### Phase 6: Compliance, Watchlist & Launch Readiness

**Goal**: Every recommendation and prediction view carries a consistent, non-directive compliance disclaimer, users can manage a personal watchlist, and the app is ready for public deployment.
**Depends on**: Phase 5
**Requirements**: COMPLY-01, COMPLY-02, WATCH-01, WATCH-02
**Success Criteria** (what must be TRUE):

  1. Every recommendation list view and every prediction drill-in view displays an educational-only disclaimer (not financial advice; hypothetical, non-guaranteed results).
  2. An audit of all UI copy and LLM agent prompt/output confirms no directive language ("buy", "you should") appears anywhere in the app.
  3. User can save an asset to their personal watchlist from either the recommendation list view or the asset drill-in page.
  4. User can view their watchlist and remove assets from it, with changes persisting across sessions (via the Phase 1 persistence layer).

**Plans**: TBD
**UI hint**: yes

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation — Data Layer, Caching & Auth | 3/5 | In Progress|  |
| 2. Investor Profile + Feature Engineering Foundation | 0/TBD | Not started | - |
| 3. Deterministic Recommendation Engine | 0/TBD | Not started | - |
| 4. Multi-Model Prediction + Walk-Forward Backtesting | 0/TBD | Not started | - |
| 5. LLM Agent Layer (Rerank + Explain) | 0/TBD | Not started | - |
| 6. Compliance, Watchlist & Launch Readiness | 0/TBD | Not started | - |

## Deferred to v2

Not scheduled in this roadmap — tracked in REQUIREMENTS.md v2 section:

- **SENT-01**: FinBERT news-sentiment scoring as an optional prediction input
- **AGENT-03**: Multi-turn conversational follow-up Q&A beyond the initial thesis
- **MODEL-01**: Additional prediction models (LSTM, ARIMA, Linear Regression)

Trigger for re-evaluation: core recommendation+prediction loop validated in production and users requesting these. Isolated from the v1 critical path specifically because they carry the two most environment-specific risks identified in research (Streamlit Cloud's 1GB memory ceiling colliding with FinBERT, and NewsAPI's dev-only ToS breaking in production).

---
*Roadmap created: 2026-07-14*
*Granularity: standard*
