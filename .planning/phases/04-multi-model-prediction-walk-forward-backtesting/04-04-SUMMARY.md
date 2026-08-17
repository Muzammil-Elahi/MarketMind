---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 04
subsystem: prediction
tags: [xgboost, numpy, pandas, quantile-regression, forecasting, confidence-intervals]

# Dependency graph
requires:
  - phase: 04-multi-model-prediction-walk-forward-backtesting
    provides: "Plan 01 -- xgboost==3.3.0/prophet==1.2.1/scikit-learn==1.9.0 pinned in requirements.txt after the package-legitimacy checkpoint"
provides:
  - "src/prediction/sma_model.py -- forecast_forward(close, horizon_days) -> {forecast, ci_lower, ci_upper}, Z_80PCT"
  - "src/prediction/xgboost_model.py -- fit_predict(features, close, horizon_days) -> endpoint dict, forecast_forward(features, close, horizon_days) -> path dict, QUANTILES"
  - "One uniform forecast_forward(..., horizon_days) -> {forecast, ci_lower, ci_upper} interface shared by both non-Prophet models"
affects: [04-05-prophet-model, 04-06-backtest-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/prediction/ mirrors src/features/'s pure zero-I/O module-boundary discipline -- numpy/pandas(/xgboost) only, no streamlit/yfinance/sqlite3 import, no network call"
    - "Uniform forecast_forward(..., horizon_days) -> {forecast, ci_lower, ci_upper} dict-of-numpy-arrays interface, shared across sma_model.py and xgboost_model.py so engine.py (Plan 06) can dispatch to either with the identical call signature"
    - "XGBoost direct-horizon quantile regression (never recursive one-step-ahead): 3 XGBRegressor models trained on close.shift(-horizon_days), predicting a single endpoint, then linearly interpolated into a day-by-day path with sqrt(t/horizon_days)-scaled CI width"

key-files:
  created:
    - src/prediction/sma_model.py
    - src/prediction/xgboost_model.py
    - tests/test_prediction_sma.py
    - tests/test_prediction_xgboost.py
  modified: []

key-decisions:
  - "Corrected a plan <behavior>-bullet ambiguity for XGBoost's forecast_forward band width: the plan's exact action-code recipe (days = np.arange(1, horizon_days+1), t_fraction = days/horizon_days) means the returned array samples t=1..horizon_days, never literally t=0 -- so band_width[0] is a small partial width (endpoint_width * sqrt(1/horizon_days)), not a literal zero. The test was corrected to assert this actual sqrt(t/horizon_days)-scaled progression (matching must_haves.truths' 'zero-width band at t=0' as the continuous function's boundary condition, not a literal array element) instead of the behavior bullet's more literal 'i=0 is zero-width' phrasing."

patterns-established:
  - "Pattern: forecast_forward(..., horizon_days) -> {forecast: ndarray, ci_lower: ndarray, ci_upper: ndarray} is the single shared model interface every src/prediction/ model (SMA, XGBoost, and Prophet in Plan 05) must expose, enabling engine.py to dispatch to any model through one identical call signature."

requirements-completed: [PRED-02, PRED-03]

coverage:
  - id: D1
    description: "sma_model.forecast_forward returns a random-walk-with-drift forward forecast with a square-root-of-time-widening 80% confidence band, including a safe zero-variance edge case"
    requirement: "PRED-02, PRED-03"
    verification:
      - kind: unit
        ref: "tests/test_prediction_sma.py -- 7 tests covering shape, drift-driven growth, CI bounds, sqrt(time) band widening, and zero-variance collapse"
        status: pass
    human_judgment: false
  - id: D2
    description: "xgboost_model.fit_predict trains 3 direct-horizon quantile XGBRegressor models (never recursive one-step-ahead) on a target shifted by horizon_days, dropping rows with no valid target before fitting"
    requirement: "PRED-02"
    verification:
      - kind: unit
        ref: "tests/test_prediction_xgboost.py::test_fit_predict_trains_on_exactly_masked_direct_horizon_rows -- asserts exactly 53 of 60 rows used for horizon_days=7"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_xgboost.py::test_fit_predict_returns_valid_endpoint_dict -- asserts ci_lower_endpoint <= forecast_endpoint <= ci_upper_endpoint"
        status: pass
    human_judgment: false
  - id: D3
    description: "xgboost_model.forecast_forward exposes the same {forecast, ci_lower, ci_upper} path-shaped dict as sma_model.forecast_forward via linear interpolation between today's price and fit_predict's endpoint, with CI band width scaled by sqrt(t/horizon_days)"
    requirement: "PRED-02, PRED-03"
    verification:
      - kind: unit
        ref: "tests/test_prediction_xgboost.py -- 5 tests covering shape, interpolation direction (day 1 closer to today than the endpoint), band-width scaling progression, and CI bounds holding at every step"
        status: pass
    human_judgment: false

duration: 11min
completed: 2026-08-17
status: complete
---

# Phase 4 Plan 04: SMA Baseline + XGBoost Direct-Horizon Quantile Models Summary

**Two zero-I/O forecast models -- SMA random-walk-with-drift baseline and XGBoost direct-horizon quantile regression -- behind one uniform `forecast_forward(..., horizon_days) -> {"forecast","ci_lower","ci_upper"}` interface, both proven by real (non-mocked) fits on small synthetic fixtures.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-08-16T20:33:09-04:00
- **Completed:** 2026-08-16T20:44:10-04:00
- **Tasks:** 2 completed
- **Files modified:** 4 (2 created source, 2 created test)

## Accomplishments
- `src/prediction/sma_model.py`: random-walk-with-drift `forecast_forward(close, horizon_days)` with a square-root-of-time-widening 80% confidence band (`Z_80PCT = 1.2816`), including a safe zero-variance collapse (no NaN, no raise) for a perfectly flat close series
- `src/prediction/xgboost_model.py`: `fit_predict(features, close, horizon_days)` trains 3 `XGBRegressor(objective="reg:quantileerror")` models (quantile_alpha 0.1/0.5/0.9) on a direct-horizon shifted target, dropping rows with no valid target before fitting -- never a recursive one-step-ahead loop
- `xgboost_model.forecast_forward(features, close, horizon_days)` interpolates `fit_predict`'s single endpoint prediction into a `horizon_days`-length path via linear interpolation + `sqrt(t/horizon_days)`-scaled CI width, matching `sma_model.forecast_forward`'s exact dict shape -- proving both models are interchangeable behind one call signature for Plan 06's `engine.py`
- Both modules verified zero-I/O (no `streamlit`/`yfinance`/`sqlite3` import) via passing negative-grep checks
- XGBoost test suite completes in ~8-10s (well under the plan's 30-second budget) with real, non-mocked `XGBRegressor.fit` calls on a 60-row synthetic fixture

## Task Commits

Each task followed the RED -> GREEN TDD cycle (test committed first and verified failing via a temporary implementation removal, then the implementation committed to make it pass):

1. **Task 1: SMA baseline model** -
   - `b0f5e8f` test(04-04): add failing test for SMA baseline forecast_forward
   - `daa4b32` feat(04-04): implement SMA baseline random-walk-with-drift forecast
2. **Task 2: XGBoost direct-horizon quantile regression model** -
   - `8ffa2eb` test(04-04): add failing test for XGBoost direct-horizon quantile model
   - `15166e8` feat(04-04): implement XGBoost direct-horizon quantile forecast model (includes a test correction, see Deviations)

**Plan metadata:** committed separately as part of this SUMMARY.md commit.

_Note: RED status for both tasks was verified empirically -- the implementation file was temporarily renamed, `pytest` was run and confirmed to fail with `ModuleNotFoundError`, then the implementation was restored before the GREEN commit._

## Files Created/Modified
- `src/prediction/sma_model.py` - Random-walk-with-drift forecast + sqrt(time) CI (`forecast_forward`, `Z_80PCT`)
- `src/prediction/xgboost_model.py` - Direct-horizon quantile regression forecast + interpolated CI (`fit_predict`, `forecast_forward`, `QUANTILES`)
- `tests/test_prediction_sma.py` - 7 tests covering every `<behavior>` bullet for the SMA model
- `tests/test_prediction_xgboost.py` - 8 tests covering every `<behavior>` bullet for the XGBoost model

## Decisions Made
- Corrected a minor ambiguity between the plan's `<behavior>` bullet text ("band width is 0 at i=0") and its own `<action>` code recipe (`days = np.arange(1, horizon_days + 1)`, which never actually samples `t=0` in the returned array -- index 0 corresponds to day 1, i.e. `t=1`). Implemented exactly per the `<action>` code (matching `must_haves.truths`' framing of "zero-width band at t=0" as the continuous scaling function's boundary condition, not a literal array element), and wrote the test to assert the actual `sqrt(t/horizon_days)`-scaled progression from a small partial width at day 1 to the full endpoint width at the last day. See Deviations below.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug, in test authorship] Test assertion did not match the plan's own action-code recipe**
- **Found during:** Task 2 (XGBoost `forecast_forward` GREEN verification)
- **Issue:** My first draft of `test_forecast_forward_band_width_zero_at_start_full_at_end` asserted `band_width[0] == 0.0`, taking the `<behavior>` bullet's "band width is 0 at i=0 (today, no uncertainty)" phrasing literally. Running it against the plan's exact `<action>` code (`days = np.arange(1, horizon_days + 1)`, `t_fraction = days / horizon_days`, `width_at_t = endpoint_width * np.sqrt(t_fraction)`) failed: at `i=0`, `t_fraction = 1/horizon_days` (not `0`), so `width_at_t[0]` is a small nonzero value, not zero. The implementation was written exactly per the plan's own code recipe and per `must_haves.truths`' more precise framing ("zero-width band at t=0" describing the continuous scaling function's boundary, with the returned array sampling only `t=1..horizon_days` since "today," t=0, needs no forecast).
- **Fix:** Rewrote the test (`test_forecast_forward_band_width_scales_from_partial_to_full_endpoint_width`) to assert the actual behavior: `band_width[0] == endpoint_width * sqrt(1/horizon_days)` (correctly scaled partial width at day 1) and `band_width[-1] == endpoint_width` (full width at the last day), plus a monotonic non-decreasing check across the whole array. No implementation code changed -- only the test's assertion was corrected to match the plan's own authoritative action-code recipe.
- **Files modified:** `tests/test_prediction_xgboost.py`
- **Verification:** `pytest tests/test_prediction_xgboost.py -x -q` -- 8/8 pass
- **Committed in:** `15166e8` (part of Task 2's feat commit, since the test correction happened during GREEN verification before that commit)

---

**Total deviations:** 1 auto-fixed (1 bug, in test authorship -- no implementation code affected)
**Impact on plan:** No scope creep; the implementation matches the plan's `<action>` code and `must_haves.truths` verbatim. Only a test assertion (my own draft, not plan-authored code) was corrected to match the plan's own specified formula.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Both non-Prophet models are complete, unit-tested, and expose the identical `forecast_forward(..., horizon_days) -> {"forecast","ci_lower","ci_upper"}` interface that Plan 05 (Prophet) must also match and Plan 06's `backtest.py`/`engine.py` will dispatch to.
- No blockers for Plan 05 or Plan 06 -- this plan has no unresolved dependencies on either.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-17*

## Self-Check: PASSED

All created files verified present on disk (`src/prediction/sma_model.py`, `src/prediction/xgboost_model.py`, `tests/test_prediction_sma.py`, `tests/test_prediction_xgboost.py`, this SUMMARY.md). All 5 commit hashes (`b0f5e8f`, `daa4b32`, `8ffa2eb`, `15166e8`, `a6c7f7b`) verified present in `git log --oneline --all`.
