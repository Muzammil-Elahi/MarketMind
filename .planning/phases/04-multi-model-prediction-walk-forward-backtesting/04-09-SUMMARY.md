---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 09
subsystem: ui
tags: [streamlit, st.dialog, st.toast, prediction, backtesting]

# Dependency graph
requires:
  - phase: 04-multi-model-prediction-walk-forward-backtesting (Plan 08)
    provides: resolve_forecast_request cache boundary, MODEL_LABELS, _render_backtest_metrics_table, single-model _render_prediction_section flow on src/pages/search.py
provides:
  - "D-06 'Compare All Models' action: st.dialog modal + persistent st.warning banner + sequential 3-model comparison loop + completion st.toast + 3-column fixed-order results view"
affects: [phase-04-verification, phase-04-ui-review]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.dialog-decorated trigger function that only sets session_state and reruns (closes dialog), with the actual work performed by a separate session_state-gated block on the next rerun -- decouples the modal's lifecycle from the long-running computation"
    - "Sequential (never parallel) multi-model comparison loop over MODEL_LABELS' declared dict order, reusing the same st.cache_data-wrapped resolve_forecast_request per model so a previously-generated single-model forecast is a cache hit inside the compare loop"

key-files:
  created: []
  modified:
    - src/pages/search.py
    - tests/test_prediction_search.py

key-decisions:
  - "_render_compare_all_models is called from _render_prediction_section immediately after the insufficient-data early-return and before the model_choice-is-None early-return, so 'Compare All Models' is reachable without ever picking a model or generating a single-model forecast (D-06 standalone reachability)"
  - "The compare loop's st.spinner label reuses COMPARE_MODAL_HEADING ('Comparing All Models') rather than inventing new spinner copy, since the UI-SPEC's Copywriting Contract has no dedicated spinner-text row for this state"

patterns-established:
  - "@st.dialog trigger-then-rerun handoff pattern for any future long-running, dialog-initiated Streamlit action"

requirements-completed: [PRED-02, PRED-04]

coverage:
  - id: D1
    description: "'Compare All Models' button opens an @st.dialog modal and, once started, renders a persistent yellow st.warning banner for the duration of a sequential 3-model comparison"
    requirement: PRED-02
    verification:
      - kind: unit
        ref: "tests/test_prediction_search.py#test_render_compare_all_models_calls_resolve_forecast_request_in_fixed_order"
        status: pass
      - kind: other
        ref: "grep -c 'st.dialog' src/pages/search.py >= 1; grep -c 'st.toast' src/pages/search.py >= 1"
        status: pass
    human_judgment: true
    rationale: "Visual confirmation that the modal actually renders, the banner persists across the dialog closing, and the toast fires exactly once requires an interactive Streamlit session -- deferred to the phase's end-of-phase human-check checkpoint per config.json's human_verify_mode=end-of-phase."
  - id: D2
    description: "Sequential 3-model comparison always calls resolve_forecast_request in the fixed sma, xgboost, prophet order (MODEL_LABELS' insertion order), never re-sorted by any metric"
    requirement: PRED-04
    verification:
      - kind: unit
        ref: "tests/test_prediction_search.py#test_render_compare_all_models_calls_resolve_forecast_request_in_fixed_order"
        status: pass
    human_judgment: false
  - id: D3
    description: "3-column compare results view degrades gracefully -- a prophet_unavailable status in the Prophet column never blocks or hides the SMA/XGBoost columns' results, reusing _render_backtest_metrics_table unmodified"
    requirement: PRED-04
    verification: []
    human_judgment: true
    rationale: "The status-branch code path (prophet_unavailable vs error vs ok) is straightforward to read but its real-world trigger (Prophet actually failing to import on this machine/Cloud build) is environment-dependent and better confirmed visually at the phase's end-of-phase human-check checkpoint than asserted via a narrow unit mock."

duration: 20min
completed: 2026-08-17
status: complete
---

# Phase 4 Plan 9: Compare All Models (D-06) Summary

**D-06's "Compare All Models" action shipped on `src/pages/search.py` -- an `@st.dialog` modal, a persistent `st.warning` banner, a sequential (never parallel) 3-model comparison loop reusing Plan 08's cached `resolve_forecast_request`, a completion `st.toast`, and a 3-column fixed-order (sma, xgboost, prophet) results view with graceful per-column Prophet-unavailable degradation.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-08-17
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Added `_compare_all_models_dialog` (`@st.dialog(COMPARE_MODAL_HEADING)`) that warns about the time cost and, on "Start Comparison", sets `comparing_{ticker}` session state and reruns to close the dialog.
- Added `_render_compare_all_models`, wired into `_render_prediction_section` immediately after the insufficient-data early-return and before the model_choice-is-None early-return, so the button is reachable independent of the single-model forecast flow (D-06 standalone reachability).
- The comparison loop iterates `MODEL_LABELS` in its declared dict order (`sma`, `xgboost`, `prophet`) and calls `resolve_forecast_request` for each -- sequentially, never via `st.fragment(parallel=True)` or a thread pool, matching the single-CPU free-tier container constraint.
- After the loop: persists `compare_results_{ticker}_{horizon_days}` in session state, clears the `comparing_{ticker}` flag, fires `st.toast("Model comparison ready.", icon=":material/check_circle:")` exactly once, then reruns so the persistent banner disappears cleanly.
- The 3-column results view renders each model in `MODEL_LABELS`' fixed order; a `"prophet_unavailable"` status renders `PROPHET_UNAVAILABLE_MESSAGE`, `"error"` renders `FORECAST_ERROR_MESSAGE`, and `"ok"` reuses Plan 08's `_render_backtest_metrics_table` unmodified (no second, bespoke comparison-table implementation).
- Added a unit test proving the sequential call order is exactly `["sma", "xgboost", "prophet"]` by patching `resolve_forecast_request` with an order-recording `side_effect` and calling `_render_compare_all_models` directly in Streamlit's bare (no-runtime) mode.

## Task Commits

Each task was committed atomically:

1. **Task 1: Compare All Models -- dialog + persistent banner + toast + 3-column results** - `2ffef85` (feat)

## Files Created/Modified
- `src/pages/search.py` - Added `COMPARE_*` constants, `_compare_all_models_dialog`, `_render_compare_all_models`, and the call-site wiring into `_render_prediction_section`.
- `tests/test_prediction_search.py` - Added `test_render_compare_all_models_calls_resolve_forecast_request_in_fixed_order`, proving the fixed sma/xgboost/prophet call order.

## Decisions Made
- `_render_compare_all_models` is called right after the insufficient-data early-return (not after the single-model flow's later early-returns), per the plan's explicit placement requirement -- this is the one call site that makes "Compare All Models" reachable without a prior single-model "Generate Forecast" click.
- Reused `COMPARE_MODAL_HEADING` as the `st.spinner` label during the comparison loop rather than inventing new copy, since the UI-SPEC's Copywriting Contract table has no dedicated spinner-text row and the plan's prohibition list only carves out one exception (`COMPARE_START_BUTTON_LABEL`) for new copy.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Streamlit's bare-mode (no `ScriptRunContext`) behavior for `st.button`/`st.session_state`/`st.columns`/`st.rerun` was verified empirically before writing the ordering test -- each degrades to a safe no-op (or, for `st.button`, returns `False`) rather than raising, which let the ordering test call `_render_compare_all_models` directly without a full `AppTest` harness.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

D-06 completes this phase's full requirements/decision coverage (PRED-01 through PRED-04, D-01 through D-08). All 198 tests in the suite pass (`python -m pytest -q`), including the new ordering test and the full existing regression suite against the local Supabase Docker stack. Interactive visual verification of the modal/banner/toast sequence and Prophet-unavailable degradation is deferred to the phase's end-of-phase human-check checkpoint per `config.json`'s `human_verify_mode: end-of-phase`.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-17*

## Self-Check: PASSED
