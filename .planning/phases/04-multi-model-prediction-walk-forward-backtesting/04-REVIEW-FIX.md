---
phase: 04-multi-model-prediction-walk-forward-backtesting
fixed_at: 2026-08-17T04:30:00Z
review_path: .planning/phases/04-multi-model-prediction-walk-forward-backtesting/04-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 04: Code Review Fix Report

**Fixed at:** 2026-08-17T04:30:00Z
**Source review:** .planning/phases/04-multi-model-prediction-walk-forward-backtesting/04-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (fix_scope: critical_warning — 1 Critical + 4 Warning; Info findings IN-01/IN-02/IN-03 out of scope)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: XGBoost quantile regressors are not monotonicity-checked — the rendered confidence band can invert

**Files modified:** `src/prediction/xgboost_model.py`, `tests/test_prediction_xgboost.py`
**Commit:** 7ed12c8
**Applied fix:** In `fit_predict`, the three independently-predicted quantile endpoint values (`ci_lower_endpoint`, `forecast_endpoint`, `ci_upper_endpoint`) are now run through `sorted(...)` before being returned, guaranteeing `ci_lower_endpoint <= forecast_endpoint <= ci_upper_endpoint` even when the underlying quantile regressors cross. Per the task instructions, this went beyond the review's suggested fix: added a new regression test (`test_fit_predict_sorts_endpoints_when_quantile_regressors_cross`) that monkeypatches `XGBRegressor.predict` to return deliberately out-of-order quantile values (0.1→150, 0.5→200, 0.9→100) and asserts `fit_predict` still returns a correctly-ordered triple — proving the guard actually holds rather than relying on the existing clean-synthetic-fixture test, which the review noted would not reliably catch crossing.

### WR-01: Search page fetches the same ticker's OHLCV data twice per render (1y and 5y), doubling live-fetch/rate-limit exposure

**Files modified:** `src/pages/_universe_loader.py`, `src/pages/search.py`, `tests/test_universe_loader.py`, `tests/test_recommendation_search.py`
**Commit:** 6e1852f
**Applied fix:** `fetch_scorable_row` now accepts an optional `ohlcv_df` parameter — when provided, it's used directly instead of triggering a fresh `fetch_ohlcv` call. `resolve_search_result` gained an optional `prediction_data` parameter; when the caller (`render_search_page`) has already fetched the 5y prediction frame, `resolve_search_result` slices it to the trailing ~1 year (`_slice_trailing_year`) and passes it through as `ohlcv_df`, preserving the existing 1y scoring/display window while eliminating the redundant live fetch for the searched ticker. `render_search_page` now fetches `fetch_prediction_data(active_ticker)` once and threads the result into both `resolve_search_result` and `_render_prediction_section` (which no longer performs its own internal fetch). Both new optional parameters default to the prior behavior, so existing callers/tests are unaffected. Added two regression tests asserting the underlying `fetch_ohlcv` chokepoint is not called when a pre-fetched frame is supplied.

### WR-02: Sharpe-ratio annualization ignores `horizon_days`, producing magnitudes that are not comparable across the horizon selector

**Files modified:** `src/prediction/metrics.py`, `src/prediction/backtest.py`, `tests/test_prediction_metrics.py`
**Commit:** 1297b9e
**Applied fix:** `sharpe_ratio` now takes a required `horizon_days` parameter and scales the annualization factor by `periods_per_year / horizon_days` instead of a flat `periods_per_year`, so the number of horizon-length periods assumed per year shrinks as the horizon grows (matching each `captured_returns` element actually being realized over `horizon_days`, not one trading day). `run_backtest` now passes its own `horizon_days` through. Updated the three existing tests to pass `horizon_days` and added `test_sharpe_ratio_scales_annualization_by_horizon_days`, which asserts the exact expected formula at two different horizons for the same returns array and confirms the annualized magnitude shrinks as the horizon grows.

### WR-03: `HORIZON_LABELS` in `search.py` is a hand-maintained constant, not derived from/validated against `engine.VALID_HORIZONS`

**Files modified:** `src/prediction/engine.py`, `src/pages/search.py`, `tests/test_prediction_engine.py`
**Commit:** 59be9ef
**Applied fix:** Moved `HORIZON_LABELS` into `src/prediction/engine.py` alongside `MODEL_LABELS` and `VALID_HORIZONS` (single source of truth), matching the existing `MODEL_LABELS` centralization pattern. `search.py` now imports `HORIZON_LABELS` from `engine.py` instead of hand-declaring it locally. Added `test_horizon_labels_keys_match_valid_horizons_exactly`, which asserts `set(HORIZON_LABELS) == VALID_HORIZONS` so any future divergence fails a test instead of surfacing as an uncaught `KeyError` in `format_func` at render time.

### WR-04: `run_backtest`'s per-fold return calculation has no zero-division guard, unlike its own `sharpe_ratio` helper

**Files modified:** `src/prediction/backtest.py`, `tests/test_prediction_backtest.py`
**Commit:** be5ec88
**Applied fix:** `run_backtest`'s `captured_returns` calculation now guards against a zero `actual_start`: zero values are replaced with `NaN` before division (`np.where(actual_starts == 0, np.nan, actual_starts)`), and the resulting `NaN` return contribution is converted to `0.0` via `np.nan_to_num` — matching the codebase's existing zero-division guard convention (`metrics.sharpe_ratio`'s `std == 0 -> 0.0`, `similarity.py`'s cosine-similarity zero-vector guard). Added `test_run_backtest_zero_actual_start_does_not_produce_nan_or_inf_metrics`, which forces the last fold's final training price to `0.0` (chosen specifically because expanding-window folds share prefix training data — zeroing an earlier fold's train_index[-1] would corrupt later folds' `pct_change()`-based drift/sigma computation with an unrelated `inf`, so the last fold's train_index[-1] is the only point that isolates the guard under test) and asserts every returned metric (`rmse`, `directional_accuracy`, `sharpe`) is finite.

## Skipped Issues

None — all in-scope findings were fixed.

## Out of Scope (fix_scope: critical_warning)

- IN-01: `_render_compare_all_models`'s disabled-check is unreachable dead logic
- IN-02: Round-half-up rounding for negative Sharpe values rounds toward +infinity
- IN-03: `run_backtest` raises an undocumented raw `KeyError` for an unrecognized `model_name`

## Verification

- Every fix verified via Tier 1 (re-read modified sections) and Tier 2 (Python `ast.parse` syntax check on every modified file).
- Targeted test files re-run after each fix; full test suite (`pytest tests/`, 204 tests, live Supabase Docker stack) run as a final regression check after all 5 fixes: **204 passed, 0 failed**.

---

_Fixed: 2026-08-17T04:30:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
