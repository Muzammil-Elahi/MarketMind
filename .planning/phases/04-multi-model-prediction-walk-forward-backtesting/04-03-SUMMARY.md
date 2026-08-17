---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 03
subsystem: prediction
tags: [sklearn, numpy, walk-forward-validation, backtesting, no-lookahead-bias]

# Dependency graph
requires:
  - phase: 03-recommendation-engine
    provides: "src/recommendation/universe.py's MIN_HISTORY_ROWS + module-boundary discipline convention, src/recommendation/engine.py's _round_half_up precedent, src/recommendation/similarity.py's division-by-zero guard convention"
provides:
  - "make_folds(n_rows, horizon_days, n_folds=N_FOLDS) -- the single shared TimeSeriesSplit-based walk-forward fold generator every model backtest (Plans 04/05/06) must call"
  - "N_FOLDS=5, MIN_PREDICTION_HISTORY_ROWS=750 -- shared constants for backtest fold count and minimum prediction history gate"
  - "rmse/directional_accuracy/sharpe_ratio/format_metrics_for_display -- the single shared metrics formula set for apples-to-apples model comparison"
affects: ["04-04 (SMA baseline backtest)", "04-05 (XGBoost backtest)", "04-06 (Prophet backtest + engine.py orchestrator)", "04-07 (_prediction_loader.py MIN_PREDICTION_HISTORY_ROWS gate)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/prediction/ mirrors src/recommendation/'s zero-I/O module-boundary discipline (only pandas/numpy/sklearn imports, never streamlit/yfinance/sqlite3)"
    - "Walk-forward folds are always generated via sklearn.model_selection.TimeSeriesSplit, never a hand-rolled index loop"
    - "Sharpe ratio annualization is asset-class-aware (TRADING_DAYS_PER_YEAR.get(asset_class, DEFAULT_TRADING_DAYS_PER_YEAR)), never a flat constant"
    - "Display formatting uses a generalized _round_half_up(value, decimals), extending REC-02's integer-only precedent to arbitrary decimal precision"

key-files:
  created:
    - src/prediction/walk_forward.py
    - src/prediction/metrics.py
    - tests/test_prediction_walk_forward.py
    - tests/test_prediction_metrics.py
  modified: []

key-decisions:
  - "04-RESEARCH.md Pitfall 2's boundary-test derivation (752/701 must raise) does not match sklearn's actual TimeSeriesSplit(test_size=...) behavior -- empirically verified the real failure boundary is n_rows <= n_folds*horizon_days (450 raises, 451 succeeds); the boundary test was adjusted to assert against this verified value instead of the plan's incorrect 701/702 figures, while preserving the intended proof (MIN_PREDICTION_HISTORY_ROWS=750 sits well above the literal sklearn failure floor)"

patterns-established:
  - "Pattern: walk_forward.py and metrics.py are the single source of truth for fold-splitting and metric formulas that every model backtest module (Plans 04-06) must import, never reimplement"

requirements-completed: [PRED-04]

coverage:
  - id: D1
    description: "make_folds() generates expanding-window walk-forward folds exclusively via sklearn.model_selection.TimeSeriesSplit, with a structural no-lookahead-bias proof (max(train_index) < min(test_index), expanding-window supersets)"
    requirement: "PRED-04"
    verification:
      - kind: unit
        ref: "tests/test_prediction_walk_forward.py#test_folds_never_overlap_and_test_always_after_train"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_walk_forward.py#test_expanding_window_train_sets_are_supersets"
        status: pass
    human_judgment: false
  - id: D2
    description: "MIN_PREDICTION_HISTORY_ROWS=750 and N_FOLDS=5 are declared once and are visibly larger than Phase 3's MIN_HISTORY_ROWS=20"
    requirement: "PRED-04"
    verification:
      - kind: unit
        ref: "tests/test_prediction_walk_forward.py#test_min_prediction_history_rows_is_750_and_larger_than_phase3_gate"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_walk_forward.py#test_n_folds_is_5"
        status: pass
    human_judgment: false
  - id: D3
    description: "rmse/directional_accuracy/sharpe_ratio share one formula set with asset-class-aware Sharpe annualization (365 crypto, 252 default) and a division-by-zero guard"
    requirement: "PRED-04"
    verification:
      - kind: unit
        ref: "tests/test_prediction_metrics.py#test_sharpe_ratio_crypto_differs_from_stocks_for_nonzero_variance"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_metrics.py#test_sharpe_ratio_zero_std_returns_zero_never_nan_or_inf"
        status: pass
      - kind: unit
        ref: "tests/test_prediction_metrics.py#test_sharpe_ratio_unrecognized_asset_class_falls_back_to_default"
        status: pass
    human_judgment: false
  - id: D4
    description: "format_metrics_for_display uses round-half-up (never Python's banker's-rounding round())"
    requirement: "PRED-04"
    verification:
      - kind: unit
        ref: "tests/test_prediction_metrics.py#test_format_metrics_for_display_round_half_up_regression_vs_python_round"
        status: pass
    human_judgment: false

duration: 10min
completed: 2026-08-16
status: complete
---

# Phase 4 Plan 3: Walk-Forward Fold Generator + Backtest Metrics Summary

**Zero-I/O `make_folds` (sklearn TimeSeriesSplit-based, expanding-window, no-lookahead-proven) and `metrics.py` (asset-class-aware RMSE/directional-accuracy/Sharpe) shared by every model backtest in the phase**

## Performance

- **Duration:** ~10 min
- **Tasks:** 2 completed
- **Files modified:** 4 (all created)

## Accomplishments
- `src/prediction/walk_forward.py`: `make_folds(n_rows, horizon_days, n_folds=N_FOLDS)` wraps `sklearn.model_selection.TimeSeriesSplit` exclusively; `N_FOLDS=5` and `MIN_PREDICTION_HISTORY_ROWS=750` declared once with arithmetic-justification comments, ready for every Plan 04-07 module to import rather than redeclare
- `src/prediction/metrics.py`: `rmse`, `directional_accuracy`, `sharpe_ratio` (asset-class-aware annualization), and `format_metrics_for_display` (round-half-up) give every model's backtest one shared, apples-to-apples formula set (D-06)
- Both modules proven zero-I/O (no `streamlit`/`yfinance`/`sqlite3` imports) via automated negative-grep verification
- Structural D-11-style no-lookahead-bias proof: every fold's `max(train_index) < min(test_index)`, and expanding-window train sets are strict supersets across consecutive folds

## Task Commits

Each task followed the RED -> GREEN TDD cycle with two commits:

1. **Task 1: Walk-forward fold generator**
   - `c7b137c` - test(04-03): add failing test for walk-forward fold generator
   - `65964f8` - feat(04-03): implement walk-forward fold generator
2. **Task 2: Shared backtest metrics module**
   - `5820fab` - test(04-03): add failing test for backtest metrics module
   - `0b1414d` - feat(04-03): implement shared backtest metrics module

**Plan metadata:** committed alongside this SUMMARY.md (worktree mode -- orchestrator merges and finalizes)

_Note: No REFACTOR commits were needed -- GREEN implementations passed cleanly on first attempt for both tasks._

## Files Created/Modified
- `src/prediction/walk_forward.py` - `make_folds`, `N_FOLDS=5`, `MIN_PREDICTION_HISTORY_ROWS=750`
- `src/prediction/metrics.py` - `rmse`, `directional_accuracy`, `sharpe_ratio`, `format_metrics_for_display`, `TRADING_DAYS_PER_YEAR`, `DEFAULT_TRADING_DAYS_PER_YEAR`
- `tests/test_prediction_walk_forward.py` - 9 tests covering fold correctness, no-lookahead structural proof, and constants
- `tests/test_prediction_metrics.py` - 10 tests covering all four metric functions and the round-half-up regression

## Decisions Made
- Adjusted the boundary-condition test's exact row-count assertions (see Deviations below) -- the underlying design intent (prove `MIN_PREDICTION_HISTORY_ROWS=750`'s safety margin is genuinely conservative, not exactly at a failure edge) was preserved using empirically-correct values.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected the walk-forward boundary test's row-count assertions to match sklearn's actual `TimeSeriesSplit` behavior**
- **Found during:** Task 1 (writing the RED test for the `n_rows=701` boundary case specified in the plan)
- **Issue:** 04-RESEARCH.md Pitfall 2's derivation implies `TimeSeriesSplit(n_splits=5, test_size=90)` fails at `n_rows=701` (one row short of the `702 = 252 + 5*90` arithmetic target). Empirically verifying against the actually-installed `scikit-learn` showed this is incorrect: `TimeSeriesSplit` with an explicit `test_size` only requires `n_samples > n_splits * test_size` (450); it succeeded at `n_rows=701` (and even `n_rows=451`) with a smaller-than-252-row first fold train window. Writing the test as literally specified would have asserted behavior the real library does not exhibit, silently masking a wrong assumption rather than proving anything.
- **Fix:** Verified the true sklearn-enforced boundary empirically (`n_rows=450` raises `ValueError`, `n_rows=451` succeeds) and rewrote the boundary test to assert against that verified value instead of the plan's incorrect 701/702 figures. The test's original intent -- proving `MIN_PREDICTION_HISTORY_ROWS=750`'s safety margin is genuinely conservative, not exactly at a failure edge -- is preserved and still demonstrated (750 sits 300 rows above the literal sklearn failure floor of 450).
- **Files modified:** `tests/test_prediction_walk_forward.py`
- **Verification:** `pytest tests/test_prediction_walk_forward.py -x -q` passes (9/9); implementation code (`make_folds`) itself is an unmodified, exact thin wrapper of sklearn's `TimeSeriesSplit` per the plan's `<action>` -- only the test's asserted boundary value changed, not the production code's behavior or guarantees.
- **Committed in:** `c7b137c` (Task 1 RED commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix in test assertions, no production code deviation)
**Impact on plan:** No scope creep, no change to `make_folds`'s implementation or public contract. The fix corrects a test-authoring assumption against verified library behavior; `MIN_PREDICTION_HISTORY_ROWS=750`'s conservatism claim is still proven, just against the mathematically-correct boundary.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/prediction/walk_forward.py` and `src/prediction/metrics.py` are ready for Plans 04-06 (SMA/XGBoost/Prophet backtests and the `backtest.py`/`engine.py` orchestrator) to import directly -- no rework needed, no risk of divergent per-model fold-splitting or metric-formula implementations.
- Plan 07's `_prediction_loader.py` can import `MIN_PREDICTION_HISTORY_ROWS` directly rather than redeclaring it.
- No blockers identified for downstream plans in this phase.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-16*

## Self-Check: PASSED

All 5 created files found on disk (`src/prediction/walk_forward.py`, `src/prediction/metrics.py`, `tests/test_prediction_walk_forward.py`, `tests/test_prediction_metrics.py`, this SUMMARY.md). All 5 commit hashes (`c7b137c`, `65964f8`, `5820fab`, `0b1414d`, `40e083d`) verified present in `git log`.
