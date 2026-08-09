# Phase 4: Multi-Model Prediction + Walk-Forward Backtesting - Context

**Gathered:** 2026-08-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-model price prediction (SMA baseline, XGBoost, Prophet) with confidence intervals, surfaced on an asset's drill-in page, backed by walk-forward-validated backtest accuracy metrics (RMSE, directional accuracy, Sharpe) computed with no lookahead bias.

Explicitly NOT this phase: LLM reranking/annotation (Phase 5), news-sentiment features (deferred to v2 SENT-01), additional models beyond SMA/XGBoost/Prophet (deferred to v2 MODEL-01), recommendation scoring changes (Phase 3, already shipped).

</domain>

<decisions>
## Implementation Decisions

### Model selection UX
- **D-01:** Model picker is a dropdown — one model (SMA baseline / XGBoost / Prophet) shown at a time, not tabs and not a permanent side-by-side layout. Switching models re-renders the same forecast+backtest layout.
- **D-02:** No model is pre-selected by default. The drill-in page shows only the historical price chart until the user explicitly picks a model.

### Forecast horizon & generation trigger
- **D-03:** Forecast horizon is a fixed preset selector: 7 / 30 / 90 days — not a free slider, not a single hardcoded horizon.
- **D-04:** Generating a forecast is an explicit action (a "Generate Forecast" button), not automatic on model/horizon change. Rationale: avoids surprising the user with a multi-second XGBoost/Prophet training delay on every dropdown change — especially relevant given Prophet's cmdstanpy cold-start risk already flagged in STATE.md as needing empirical validation this phase.

### Backtest accuracy display
- **D-05:** Backtested accuracy (RMSE, directional accuracy, Sharpe) renders as a metrics table below the forecast chart, for the currently selected model — mirrors Phase 3's Score Breakdown pattern (`components/charts.py`'s `render_breakdown_bar_chart`) for UI consistency.
- **D-06:** The default view shows metrics for the selected model only, but there is a separate **"Compare all models"** action the user can trigger to see all 3 models' backtest metrics side-by-side. Because this may require training/backtesting models not yet computed for this asset, the UI must show, together: (a) a popup/modal when the user selects "Compare all models", and (b) a persistent yellow warning banner on the page — both stating the comparison may take time. When the comparison finishes, show a completion notification (toast/success banner — Streamlit has no true push notifications, so this is the closest equivalent; exact widget is Claude's discretion).

### Insufficient-data handling
- **D-07:** Prediction/backtesting needs its own minimum-history threshold, stricter than Phase 3's `MIN_HISTORY_ROWS` (20) — enough real history to run several walk-forward train/test folds, not just compute one point-in-time feature row. Exact value is Claude's discretion at planning/research time, but it must be visibly larger than 20 and justified against the walk-forward fold count/window chosen.
- **D-08:** When an asset has enough history for the price chart but not enough for a reliable backtest, the price chart still renders (same non-blocking precedent as Phase 3's D-08 for scoring) but the model dropdown / "Generate Forecast" button is disabled with an explanatory message (e.g. "Not enough price history to generate a reliable forecast for this asset.").

### Claude's Discretion
- Exact minimum-history threshold value for D-07 and the walk-forward fold/window scheme it must support.
- Exact widget/mechanism for the D-06 completion notification (Streamlit `st.toast`, `st.success`, or similar).
- Whether the new prediction code lives in `src/prediction/` as its own package (mirroring `src/recommendation/`'s zero-I/O-except-chokepoints structure) — strongly implied by the existing architecture but not explicitly discussed.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — core value, constraints ($0 budget, free-tier-only), model set decision (SMA + XGBoost + Prophet for v1, not the full 7-model source spec)
- `.planning/REQUIREMENTS.md` — PRED-01, PRED-02, PRED-03, PRED-04 requirement definitions and traceability
- `.planning/ROADMAP.md` §"Phase 4: Multi-Model Prediction + Walk-Forward Backtesting" — goal, success criteria, dependencies (depends on Phase 3)
- `CLAUDE.md` — Installation/Version Compatibility tables: `xgboost==3.3.0`, `prophet==1.2.1` (cmdstanpy auto-installed dep, slow/flaky first-import risk on Streamlit Cloud), `scikit-learn==1.9.0`; none of these three are installed yet (`requirements.txt` currently has no xgboost/prophet/scikit-learn entries) — expect a Package Legitimacy Gate blocking-human checkpoint for each, same pattern as Phase 3's numpy/plotly (`03-03-PLAN.md`)

### Prior phase artifacts (inputs this phase consumes)
- `.planning/STATE.md` Blockers/Concerns — explicitly flags "Prophet/cmdstanpy cold-start behavior on Streamlit Community Cloud's ephemeral build environment needs empirical validation in Phase 4, not just documentation research"
- `.planning/phases/02-investor-profile-feature-engineering-foundation/02-CONTEXT.md` D-11 — the leakage-smoke-test pattern (inject a synthetic future-only signal, assert the pipeline does NOT show improved accuracy from it) — directly applicable to this phase's no-lookahead-bias walk-forward requirement (PRED-04)
- `.planning/phases/03-deterministic-recommendation-engine/03-CONTEXT.md` D-08 — the insufficient-data-but-still-show-chart precedent this phase's D-08 extends with a stricter threshold
- `src/features/technical.py`, `src/features/feature_frame.py` — the point-in-time feature computation (`assemble_feature_frame`) this phase's models consume as input
- `src/data/cache.py` — the single yfinance chokepoint (`fetch_ohlcv`); note the MultiIndex-columns bug fixed today (quick task `260809-j0k`, commit `4a15535`) — this phase's models now get correctly-shaped real data, but be aware this chokepoint's shape is easy to get wrong if touched again

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/pages/search.py` — the existing `require_auth()`-gated drill-in page. It already resolves a ticker → `chart_df` and renders the price history chart via `render_price_history_chart`. This phase's forecast/backtest UI most likely extends this page (or its `resolve_search_result`-style core) rather than building a new drill-in surface from scratch.
- `src/components/charts.py` — `build_price_history_figure`/`render_price_history_chart` already exist and are reused by `search.py`. They currently render a plain price line with no confidence-interval band — will need a new `build_forecast_figure` (or an extension) that overlays historical price + forecast + CI band.
- `src/components/disclaimer.py` — the shared disclaimer banner from Phase 3; prediction views need it too per CLAUDE.md's compliance constraint ("every prediction/recommendation view must show an educational-use disclaimer").

### Established Patterns
- Page-thin/module-thick split: `src/recommendation/` (Phase 3) keeps all scoring math in pure, zero-I/O modules and pages only orchestrate + render. The same split is expected for prediction: pure model/backtest logic in a new package, pages stay thin.
- Single-chokepoint pattern: all yfinance access routes through `src/data/cache.py` → `src/data/prices.py`. Prediction code must consume `fetch_ohlcv` and `assemble_feature_frame`, never fetch or reimplement feature math itself.
- `require_auth()`-first pattern on every page, unchanged.

### Integration Points
- Likely new `src/prediction/` package (e.g. `models.py` or per-model files for SMA/XGBoost/Prophet, `backtest.py` for walk-forward validation), pure functions of (feature/price data, model choice, horizon) → forecast + confidence interval + backtest metrics, independently unit-testable with no network calls (matching `src/recommendation/engine.py`'s zero-I/O design goal).
- Extends `src/pages/search.py` (or a sibling drill-in page) with the model dropdown, horizon selector, "Generate Forecast" button, forecast chart, backtest metrics table, and the "Compare all models" action from D-06.

</code_context>

<specifics>
## Specific Ideas

- The "Compare all models" warning must be **both** a modal popup AND a persistent yellow banner — not either/or. The user was explicit that both surfaces should carry the same time-cost warning.
- A completion notification when the multi-model comparison finishes was explicitly requested — this is a real UX requirement, not a nice-to-have, even though the exact widget is left to implementation.

</specifics>

<deferred>
## Deferred Ideas

None raised during this discussion — session stayed within phase scope. (Note: two related enhancement ideas — richer scoring explanation and portfolio-aware recommendations — were captured separately as backlog Phase 999.1 in an earlier conversation, not during this discussion session.)

### Reviewed Todos (not folded)
None — `todo.match-phase` returned zero matches for Phase 4.

</deferred>

---

*Phase: 4-Multi-Model Prediction + Walk-Forward Backtesting*
*Context gathered: 2026-08-09*
