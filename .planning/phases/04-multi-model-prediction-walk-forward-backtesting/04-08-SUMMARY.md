---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 08
subsystem: ui
tags: [streamlit, prediction, forecasting, caching, plotly]

# Dependency graph
requires:
  - phase: 04-multi-model-prediction-walk-forward-backtesting (Plan 02)
    provides: src/pages/_prediction_loader.py fetch_prediction_data (D-07/D-08 gate)
  - phase: 04-multi-model-prediction-walk-forward-backtesting (Plan 03)
    provides: src/prediction/metrics.py format_metrics_for_display (round-half-up display formatting)
  - phase: 04-multi-model-prediction-walk-forward-backtesting (Plan 06)
    provides: src/prediction/engine.py generate_forecast (validated dispatch/orchestration core)
  - phase: 04-multi-model-prediction-walk-forward-backtesting (Plan 07)
    provides: src/components/charts.py build_forecast_figure/render_forecast_chart (CI-band chart)
provides:
  - "resolve_forecast_request(ticker, model, horizon_days, feature_frame, price_series, asset_class) -- st.cache_data-wrapped page-layer caching boundary for generate_forecast (T-04-03 DoS mitigation)"
  - "_render_prediction_section(ticker, asset_class) -- D-01/D-02/D-03/D-04/D-05/D-07/D-08 single-model prediction flow wired into render_search_page()"
  - "_render_backtest_metrics_table(backtest_metrics) -- RMSE/Directional Accuracy/Sharpe Ratio (Simulated) bordered-card display"
  - "Session-state key scheme (forecast_{ticker}_{model}_{horizon_days}) that Plan 09's Compare All Models view extends"
affects: [04-09 (Compare All Models depends on this plan's session-state/loader/engine wiring)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Page-layer st.cache_data caching boundary wraps a zero-I/O engine function (generate_forecast), since the engine module cannot import streamlit itself"
    - "Session-state result caching keyed on ticker+model+horizon_days prevents stale forecast display across selection changes"

key-files:
  created:
    - tests/test_prediction_search.py
  modified:
    - src/pages/search.py

key-decisions:
  - "insufficient_data and scored branches of render_search_page() both fall through to a shared _render_prediction_section call instead of returning early, per the plan's explicit refactor instruction"
  - "Horizon selector defaults to index=1 (30 Days) while the model dropdown has no default (index=None) -- D-02's 'no default' rule applies to the model dropdown only, per 04-CONTEXT.md's exact wording"

patterns-established:
  - "T-04-03 DoS mitigation: st.cache_data(ttl=CACHE_TTL_SECONDS) on the page-layer forecast-request wrapper, deduplicating repeat Generate Forecast clicks with identical arguments"

requirements-completed: [PRED-01, PRED-02, PRED-03, PRED-04]

coverage:
  - id: D1
    description: "resolve_forecast_request is a cached thin wrapper that calls generate_forecast exactly once per unique argument set and returns its result unchanged"
    requirement: "PRED-02"
    verification:
      - kind: unit
        ref: "tests/test_prediction_search.py#test_resolve_forecast_request_calls_generate_forecast_once_and_returns_unchanged"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_search.py#test_resolve_forecast_request_deduplicates_identical_calls"
        status: pass
    human_judgment: false
  - id: D2
    description: "render_search_page() renders the D-01 model dropdown (no default), D-03 horizon selector (7/30/90), D-04 explicit Generate Forecast button, PRED-03 forecast+CI chart, and D-05 backtest metrics table below the historical price chart on the search/drill-in page"
    requirement: "PRED-01, PRED-03, PRED-04"
    verification:
      - kind: unit
        ref: "python -c \"import src.pages.search\" (clean import, structural presence check)"
        status: pass
    human_judgment: true
    rationale: "render_search_page() itself is only exercised by Streamlit-runtime UAT per this project's established convention (matches Phase 3's precedent) and this project's human_verify_mode=end-of-phase setting -- visual/interactive verification of the widget row, chart, and state transitions happens at the phase's end-of-phase human-check checkpoint, not in this plan's unit tests."
  - id: D3
    description: "Insufficient-history (D-07/D-08), Prophet-unavailable, and forecast-generation-error states each render the exact 04-UI-SPEC.md Copywriting Contract copy, with the historical price chart still rendering unconditionally above the insufficient-history state"
    requirement: "PRED-01, PRED-02"
    verification: []
    human_judgment: true
    rationale: "These are Streamlit-runtime rendering branches with no unit-test harness in this codebase's convention (render_search_page() is verified only via end-of-phase human UAT) -- correctness of the exact copy/branch selection was verified by code review against the plan's literal <action> text, not an automated assertion."

duration: 30min
completed: 2026-08-17
status: complete
---

# Phase 04 Plan 08: Single-Model Prediction Flow Summary

**Search/drill-in page now offers a model dropdown, 7/30/90-day horizon selector, and explicit Generate Forecast button that renders a forecast+CI chart and RMSE/Directional Accuracy/Sharpe backtest table, cached via a page-layer `st.cache_data` boundary around `generate_forecast`.**

## Performance

- **Duration:** ~30 min
- **Completed:** 2026-08-17
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments
- Added `resolve_forecast_request`, a `st.cache_data`-wrapped thin caching boundary around `src.prediction.engine.generate_forecast`, proven via mock call-count assertions to genuinely deduplicate identical repeat calls (T-04-03 DoS mitigation)
- Wired the D-01 (model dropdown, no default)/D-03 (horizon selector)/D-04 (explicit Generate Forecast button) controls into `render_search_page()`, converging both the Phase 3 `insufficient_data` and `scored` branches on a shared `_render_prediction_section` call instead of returning early
- Rendered the PRED-03 forecast chart with confidence-interval band (via `render_forecast_chart`) and the D-05 backtest metrics table (RMSE / Directional Accuracy / Sharpe Ratio (Simulated)) in a bordered card, gated by session-state keyed on `ticker`/`model`/`horizon_days` so a ticker/model/horizon switch never shows a stale prior forecast
- Handled D-07/D-08 insufficient-history, Prophet-unavailable fallback, and forecast-generation-error states with the exact 04-UI-SPEC.md Copywriting Contract strings, each as a module-level constant (never inlined)

## Task Commits

Each task was committed atomically (Task 1 is TDD: test then feat):

1. **Task 1: Testable forecast-request core** - `6e88b87` (test: failing RED test for cache dedup) then `7492590` (feat: `resolve_forecast_request` implementation, GREEN)
2. **Task 2: Render the single-model prediction section** - `862fd27` (feat)

## Files Created/Modified
- `src/pages/search.py` - Added `resolve_forecast_request` (cached forecast-request core), `_render_prediction_section` (D-01..D-05/D-07/D-08 controls + chart + metrics), `_render_backtest_metrics_table`, and 13 new copy constants sourced verbatim from 04-UI-SPEC.md's Copywriting Contract
- `tests/test_prediction_search.py` - Fully-mocked unit tests for `resolve_forecast_request`'s pass-through and cache-dedup behavior, mirroring `tests/test_cache.py`'s isolated-cache fixture convention

## Decisions Made
- `insufficient_data`/`scored` branches of `render_search_page()` both fall through to `_render_prediction_section` rather than returning early, per the plan's explicit instruction -- the historical price chart (Phase 3, PRED-01) remains unconditionally rendered first in every case except `not_found`
- Horizon selector's `index=1` default (30 Days) is intentional and distinct from the model dropdown's `index=None` (no default) -- D-02's "no default" rule is scoped to the model dropdown only, per 04-CONTEXT.md's exact wording quoted in the plan's `must_haves.truths`

## Deviations from Plan

None - plan executed exactly as written. Task 1 followed the TDD RED/GREEN cycle: the test file was written and verified to fail via `ImportError` against the pre-Task-1 committed `search.py` (RED), then the implementation was restored and both tests confirmed passing before committing GREEN.

## Issues Encountered

None. The full project test suite (`pytest`, 197 tests) passes with no regressions after both tasks, confirming no existing Phase 1/2/3 behavior was broken by this plan's new imports/refactor.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Plan 09 (D-06's "Compare All Models") can now build directly on this plan's `fetch_prediction_data` -> `resolve_forecast_request` -> `render_forecast_chart` wiring and its `forecast_{ticker}_{model}_{horizon_days}` session-state key scheme, per the plan's stated purpose. No blockers.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-17*
