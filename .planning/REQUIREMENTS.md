# Requirements: Popcorn Pilot

**Defined:** 2026-07-14
**Core Value:** A user gets a ranked, explainable shortlist of assets matching their investor profile, and can drill into any of them to see a price forecast with confidence intervals and backtested accuracy — recommendation and prediction work together as one pipeline, not two disconnected tools.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Profile

- [x] **PROFILE-01**: User can build an investor profile (risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, existing holdings)
- [ ] **PROFILE-02**: User can edit their profile after creation and see recommendations update accordingly

### Authentication & Persistence

- [x] **AUTH-01**: User can sign up and log in (Supabase auth)
- [x] **AUTH-02**: User's profile, watchlist, and history persist across sessions and devices
- [x] **AUTH-03**: Auth/session state is strictly scoped per user (no session or cached-object leakage across concurrent users)

### Recommendation Engine

- [ ] **REC-01**: User can get a ranked list of recommended assets spanning stocks, ETFs, crypto, gold, and forex, scored against their profile using a deterministic hybrid model (factor + collaborative-filtering-style scoring)
- [ ] **REC-02**: Each ranked asset shows a composite score with a visible sub-factor breakdown (not an opaque single number)
- [ ] **REC-03**: Each recommendation includes a one-sentence plain-English reason
- [ ] **REC-04**: User can search for any asset across all supported asset classes, not just ones already recommended

### Price Prediction

- [ ] **PRED-01**: User can drill into any asset (recommended or searched) and see a historical price chart
- [ ] **PRED-02**: User can select a prediction model (SMA baseline, XGBoost, or Prophet) and a forecast horizon, and generate a forecast
- [ ] **PRED-03**: The forecast chart displays confidence intervals around the future prediction
- [ ] **PRED-04**: User can see backtested accuracy per model (RMSE, directional accuracy, Sharpe), computed via walk-forward validation with no lookahead bias

### LLM Agent

- [ ] **AGENT-01**: An LLM agent (Gemini free tier via LangGraph) reranks/annotates the recommendation list with a plain-English investment thesis per asset, grounded in the visible factor score
- [ ] **AGENT-02**: The agent is strictly read-only over the recommendation engine's output — it never computes or overrides the deterministic score

### Compliance

- [ ] **COMPLY-01**: Every recommendation and prediction view displays an educational-only disclaimer (not financial advice, hypothetical/non-guaranteed results)
- [ ] **COMPLY-02**: Neither UI copy nor LLM agent output uses directive language ("buy", "you should") — framed as informational, never personalized advice

### Watchlist

- [ ] **WATCH-01**: User can save an asset to a personal watchlist from the recommendation list or drill-in page
- [ ] **WATCH-02**: User can view and remove assets from their watchlist

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Sentiment

- **SENT-01**: User can optionally include FinBERT news-sentiment scoring as an input to price predictions

### Conversational Agent

- **AGENT-03**: User can ask follow-up conversational questions about a recommendation or prediction (multi-turn, beyond the initial thesis)

### Expanded Models

- **MODEL-01**: Additional prediction models (LSTM, ARIMA, Linear Regression) available alongside SMA/XGBoost/Prophet

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Real trade execution / brokerage integration | Crosses into broker-dealer/investment-adviser regulation (SEC/FINRA); educational tool only |
| Specific "buy at $X, sell at $Y" target prices | Crosses FINRA Rule 2111.03's educational safe-harbor line into personalized security advice |
| Real-time streaming quotes / sub-minute updates | Infeasible on free-tier data budget; encourages day-trading behavior misaligned with educational framing |
| Social / copy-trading features | Significant moderation and regulatory scope creep; dilutes focus from the core rec+prediction loop |
| Portfolio-level optimizer / walk-forward backtesting engine (PyPortfolioOpt, vectorbt) | Large orthogonal effort that doesn't block validating the core single-asset loop |
| Cross-user aggregate signals ("similar profiles are viewing X") | Needs meaningful user volume; risks looking like an unlicensed signal service if framed carelessly |
| LLM as the primary/sole recommendation engine | Non-deterministic, unauditable, hallucination-prone; agent stays in the rerank/explain role on top of the deterministic model |
| Guaranteed/marketed accuracy percentages in UI copy | Misleading and conflicts with FINRA Rule 2214's hypothetical/non-guaranteed disclosure requirement |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PROFILE-01 | Phase 2 | Complete |
| PROFILE-02 | Phase 2 | Pending |
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| REC-01 | Phase 3 | Pending |
| REC-02 | Phase 3 | Pending |
| REC-03 | Phase 3 | Pending |
| REC-04 | Phase 3 | Pending |
| PRED-01 | Phase 4 | Pending |
| PRED-02 | Phase 4 | Pending |
| PRED-03 | Phase 4 | Pending |
| PRED-04 | Phase 4 | Pending |
| AGENT-01 | Phase 5 | Pending |
| AGENT-02 | Phase 5 | Pending |
| COMPLY-01 | Phase 6 | Pending |
| COMPLY-02 | Phase 6 | Pending |
| WATCH-01 | Phase 6 | Pending |
| WATCH-02 | Phase 6 | Pending |

**Coverage:**

- v1 requirements: 19 total
- Mapped to phases: 19/19 ✓
- Unmapped: 0

---
*Requirements defined: 2026-07-14*
*Last updated: 2026-07-14 after roadmap creation (6 phases, full coverage)*
