---
quick_id: 260809-j0k
subsystem: data
tags: [yfinance, pandas, MultiIndex, cache, regression-test]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine
    provides: fetch_scorable_row / assemble_feature_frame consumers that surfaced the "insufficient_data" symptom
provides:
  - Flat (non-MultiIndex) OHLCV columns from src/data/cache.py's yfinance chokepoint for every ticker
  - Regression test proving MultiIndex-columned yf.download() output is flattened before caching/return
affects: [phase-03-recommendation-engine, phase-04-prediction-backtesting]

# Tech tracking
tech-stack:
  added: []
  patterns: []

key-files:
  created: []
  modified:
    - src/data/cache.py
    - tests/test_cache.py

key-decisions:
  - "Fix applied exclusively at the single yfinance chokepoint (_fetch_live in src/data/cache.py) per the module's own docstring — no changes to src/features/technical.py or any downstream consumer"

patterns-established: []

requirements-completed: []

coverage:
  - id: D1
    description: "fetch_ohlcv() returns flat (non-MultiIndex) columns for every ticker, including single-ticker fetches"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_multiindex_columns_from_live_fetch_are_flattened"
        status: pass
      - kind: integration
        ref: "python -c ... fetch_ohlcv('AAPL') live-network verification (plan Task 1 <verify> block)"
        status: pass
    human_judgment: false
  - id: D2
    description: "assemble_feature_frame(df).dropna() retains real rows instead of dropping every row to NaN"
    requirement: null
    verification:
      - kind: integration
        ref: "python -c ... assemble_feature_frame(fetch_ohlcv('AAPL')[0]).dropna() >= MIN_HISTORY_ROWS (plan Task 1 <verify> block)"
        status: pass
    human_judgment: false
  - id: D3
    description: "Full existing pytest suite still passes after the fix"
    verification:
      - kind: unit
        ref: "python -m pytest -q (full suite)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-08-09
status: complete
---

# Quick Task 260809-j0k: Fix MultiIndex columns bug in src/data/cache.py Summary

**Flattened yf.download()'s MultiIndex columns at the single yfinance chokepoint so `df["Close"]` resolves to a Series again, unblocking Phase 3's Recommendations page and every future consumer of `fetch_ohlcv()`.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified:** 2

## Accomplishments
- `_fetch_live()` in `src/data/cache.py` now detects a `pd.MultiIndex` column shape returned by `yf.download()` and flattens it via `df.columns.get_level_values(0)` before the DataFrame is cached or returned.
- Verified live against a real `fetch_ohlcv('AAPL')` call: columns are now `['Close', 'High', 'Low', 'Open', 'Volume']` (flat `Index`), and `assemble_feature_frame(df).dropna()` retains 231 rows (well above the `MIN_HISTORY_ROWS = 20` threshold), versus 0 rows before the fix.
- Added a new regression test (`test_multiindex_columns_from_live_fetch_are_flattened`) in `tests/test_cache.py` that mocks `yf.download` to return a MultiIndex-columned DataFrame and asserts `fetch_ohlcv()` flattens it — closing the gap where every pre-existing test in the file mocked already-flat columns and would not have caught this bug class.
- Full existing pytest suite (130 tests, including the new regression test) passes with zero failures.

## Task Commits

Each task was committed atomically:

1. **Task 1: Flatten MultiIndex columns at the yfinance chokepoint** - `4a15535` (fix)
2. **Task 2: Add MultiIndex regression test and run the full suite** - `c79d41d` (test)

**Plan metadata:** commit pending (orchestrator handles docs commit)

## Files Created/Modified
- `src/data/cache.py` - `_fetch_live()` now flattens a `pd.MultiIndex` column shape from `yf.download()` to a flat `pd.Index` via `get_level_values(0)` before returning
- `tests/test_cache.py` - new regression test `test_multiindex_columns_from_live_fetch_are_flattened` mocking a MultiIndex-shaped `yf.download()` return value

## Decisions Made
- Fix applied exclusively at the single yfinance chokepoint (`_fetch_live` in `src/data/cache.py`), per the module's own docstring ("Single yfinance chokepoint for the whole codebase") — no changes made to `src/features/technical.py`, `src/pages/_universe_loader.py`, or any other downstream consumer.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 3's Recommendations page and Search page now receive real, non-NaN feature data for every ticker in the curated universe — the root cause of the "insufficient_data" failure diagnosed as `REC-01` is resolved at its single chokepoint.
- Phase 4 (Multi-Model Prediction + Walk-Forward Backtesting), which consumes the same `fetch_ohlcv()` entry point, will not hit this same MultiIndex bug class since the fix lives at the shared chokepoint rather than in any per-phase consumer code.
- No blockers identified for Phase 4 planning as a result of this fix.

---
*Quick task: 260809-j0k*
*Completed: 2026-08-09*

## Self-Check: PASSED

- FOUND: src/data/cache.py
- FOUND: tests/test_cache.py
- FOUND: 4a15535 (fix commit)
- FOUND: c79d41d (test commit)
