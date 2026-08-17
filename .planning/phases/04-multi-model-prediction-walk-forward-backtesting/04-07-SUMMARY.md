---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 07
subsystem: data-loading
tags: [pandas, prediction, feature-frame, yfinance, discriminated-union]

# Dependency graph
requires:
  - phase: 04-multi-model-prediction-walk-forward-backtesting
    provides: "MIN_PREDICTION_HISTORY_ROWS (Plan 03's src/prediction/walk_forward.py) and the fetch_ohlcv/assemble_feature_frame chokepoints (Phase 2)"
provides:
  - "fetch_prediction_data(ticker) -> dict -- 5-year fetch + D-07/D-08 minimum-history gate + aligned feature_frame/price_series for one asset"
affects: ["04-06 (xgboost_model.fit_predict consumer)", "04-08 (search-page prediction extension, direct caller)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/pages/_prediction_loader.py mirrors src/pages/_universe_loader.py's exact discriminated-union return shape (not_found/insufficient_data/ok) and try/except/logger.exception convention"

key-files:
  created:
    - src/pages/_prediction_loader.py
    - tests/test_prediction_loader.py
  modified: []

key-decisions:
  - "fetch_prediction_data takes only ticker (no asset_class/sector) -- deliberate single-responsibility deviation from _universe_loader.fetch_scorable_row's wider signature, since prediction has no profile-fit/sector logic"
  - "Test fixtures compute the exact raw row count needed for a target post-dropna feature-row count via a self-verifying probe (measure warm-up offset once, then n_rows = target + warm_up) rather than a hardcoded guess, per the plan's explicit self-verification requirement"

patterns-established:
  - "Pattern: any future single-asset I/O loader under src/pages/ should follow this file's exact discriminated-union + try/except/logger.exception shape rather than inventing a new one"

requirements-completed: [PRED-01, PRED-02]

coverage:
  - id: D1
    description: "fetch_prediction_data(ticker) fetches 5y history via fetch_ohlcv(ticker, period=\"5y\") and returns {status: not_found} on fetch exception or empty DataFrame"
    requirement: "PRED-01"
    verification:
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_not_found_on_exception"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_not_found_on_empty_dataframe"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_calls_fetch_ohlcv_with_5y_period"
        status: pass
    human_judgment: false
  - id: D2
    description: "D-07/D-08 MIN_PREDICTION_HISTORY_ROWS=750 gate is inclusive-boundary-correct: exactly 749 post-dropna feature rows -> insufficient_data, exactly 750 -> ok"
    requirement: "PRED-02"
    verification:
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_insufficient_data_at_749_rows"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_ok_at_750_rows_boundary"
        status: pass
    human_judgment: false
  - id: D3
    description: "ok-status result returns chart_df (full, untruncated fetch result), a NaN-free feature_frame, and price_series aligned (.loc) to feature_frame's post-dropna index"
    requirement: "PRED-01"
    verification:
      - kind: unit
        ref: "tests/test_prediction_loader.py#test_fetch_prediction_data_ok_at_750_rows_boundary"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-08-16
status: complete
---

# Phase 04 Plan 07: Prediction Data Loader Summary

**`fetch_prediction_data(ticker)` fetches 5 years of history and applies an inclusive-boundary D-07/D-08 750-row minimum-history gate, returning an aligned feature_frame/price_series pair plus the full untruncated chart_df.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 1
- **Files modified:** 2 (both new)

## Accomplishments
- `src/pages/_prediction_loader.py` created with `fetch_prediction_data(ticker) -> dict`, mirroring `_universe_loader.py`'s discriminated-union return shape (`not_found` / `insufficient_data` / `ok`) and `try/except/logger.exception` convention
- Calls `fetch_ohlcv(ticker, period="5y")` (never the default `period="1y"`) so this loader's cache entry is independent of Phase 3's `_universe_loader.py` entry for the same ticker, per 04-RESEARCH.md Pitfall 3
- D-07/D-08 gate uses `MIN_PREDICTION_HISTORY_ROWS` imported from `src.prediction.walk_forward` (never re-declared), proven inclusive-boundary-correct at exactly 749 (insufficient) vs. exactly 750 (ok) post-dropna feature rows
- `price_series` is `df["Close"].loc[feature_frame.index]` -- aligned to `feature_frame`'s post-dropna index, not the raw unaligned `Close` column -- required for Plan 06's `xgboost_model.fit_predict` direct-target-shift alignment
- `chart_df` in every status branch is the raw, full 5-year `fetch_ohlcv` result (never dropna'd/truncated), so the historical price chart always shows complete fetched history regardless of the gate outcome
- Fully-mocked test suite (`tests/test_prediction_loader.py`, 5 tests) with zero live network calls, patching `src.pages._prediction_loader.fetch_ohlcv` exactly as `tests/test_universe_loader.py` does

## Task Commits

Each task was committed atomically:

1. **Task 1: Prediction data loader (D-07/D-08's stricter minimum-history gate)** - `b4af8a4` (feat)

**Plan metadata:** (this SUMMARY.md commit)

## Files Created/Modified
- `src/pages/_prediction_loader.py` - `fetch_prediction_data(ticker)`: I/O-performing loader (5y fetch + feature assembly + D-07/D-08 gate)
- `tests/test_prediction_loader.py` - Fully-mocked unit tests covering not_found, insufficient_data, and the exact-749-vs-exact-750 ok boundary, plus the `period="5y"` call-args assertion

## Decisions Made
- `fetch_prediction_data` takes only `ticker` (no `asset_class`/`sector`) -- a deliberate single-responsibility deviation from `_universe_loader.fetch_scorable_row`'s wider signature, documented in the module docstring per the plan's prohibition clause
- Test fixtures compute their exact required raw row count via a self-verifying probe (measure the rolling-window warm-up offset once from an over-provisioned probe frame, then `n_rows = target + warm_up`) rather than hardcoding a guessed warm-up constant, with an explicit `assert actual == target` self-check before any status assertion -- matches the plan's `<action>` requirement precisely

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. A background full-suite pytest run stalled once during a connectivity interruption mid-session; re-run after reconnection confirmed all 177 tests in the suite (including this plan's 5) pass cleanly against the live local Supabase Docker stack, with no regressions attributable to this plan's changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
`fetch_prediction_data` is ready for Plan 08's search-page extension to call immediately after a ticker resolves (no rework needed) and for Plan 06's `xgboost_model.fit_predict` to consume the aligned `feature_frame`/`price_series` pair.
No blockers identified.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-16*

## Self-Check: PASSED

- FOUND: src/pages/_prediction_loader.py
- FOUND: tests/test_prediction_loader.py
- FOUND: b4af8a4 (task commit)
