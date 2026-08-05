---
phase: 03-deterministic-recommendation-engine
plan: 01
subsystem: recommendation-engine
tags: [pandas, recommendation, factor-scoring, streamlit, yfinance]

# Dependency graph
requires:
  - phase: 02-investor-profile-feature-engineering-foundation
    provides: "src/features/technical.py, src/features/feature_frame.py (assemble_feature_frame), src/pages/profile.py's SECTORS/ASSET_TYPE_OPTIONS constants"
provides:
  - "src/recommendation/universe.py: fixed 5-class curated ticker universe (D-04), infer_asset_class(ticker), ASSET_CLASS_TICKERS/ASSET_CLASS_SECTORS, MIN_HISTORY_ROWS=20"
  - "src/recommendation/factor_scoring.py: compute_momentum_score/compute_volatility_score/compute_quality_score with within-class normalization (D-03) and degenerate-group fallback"
  - "src/pages/_universe_loader.py: fetch_scorable_row/load_asset_feature_row/load_universe_rows -- shared fetch+assemble+D-08-gate loop"
affects: [03-05-engine, 03-06-recommendations-page, 03-07-search-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zero-I/O pure-pandas module discipline in src/recommendation/ (mirrors src/features/technical.py)"
    - "groupby(\"asset_class\").transform() for within-class cross-sectional normalization (D-03)"
    - "Degenerate-group fallback: groups smaller than MIN_GROUP_SIZE (3) get a fixed DEFAULT_PERCENTILE_FALLBACK (0.5) instead of NaN/inf"
    - "D-07/D-08 status-dict pattern (not_found / insufficient_data / ok) in the I/O loader layer, distinct from the pure scoring layer"

key-files:
  created:
    - src/recommendation/__init__.py
    - src/recommendation/universe.py
    - src/recommendation/factor_scoring.py
    - src/pages/_universe_loader.py
    - tests/test_recommendation_universe.py
    - tests/test_recommendation_factor_scoring.py
    - tests/test_universe_loader.py
  modified: []

key-decisions:
  - "compute_quality_score copies universe_df before assigning the temporary _quality_raw column, rather than mutating the caller's DataFrame in place (matches the immutable-input discipline already used by src/features/)"
  - "fetch_scorable_row's feature_row values come from the last (most recent) row of the dropna'd feature frame, per plan spec"

requirements-completed: [REC-01, REC-02, REC-04]

coverage:
  - id: D1
    description: "Curated, fixed cross-asset-class universe (STOCK/ETF/CRYPTO/GOLD/FOREX_UNIVERSE) with infer_asset_class() ticker classifier"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_universe.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Within-class momentum/volatility/quality factor scoring, isolated per asset class (D-03), with degenerate-group fallback (Pitfall 2)"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_factor_scoring.py"
        status: pass
    human_judgment: false
  - id: D3
    description: "Shared universe loader distinguishing not_found (D-07) from insufficient_data (D-08) for any searched ticker"
    requirement: "REC-04"
    verification:
      - kind: unit
        ref: "tests/test_universe_loader.py"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-04
status: complete
---

# Phase 3 Plan 01: Curated Universe + Factor Scoring + Universe Loader Summary

**Fixed 5-asset-class ticker universe, within-class percentile factor scoring (momentum/volatility/quality) via `groupby().transform()`, and a shared fetch+assemble+minimum-history-gate loader — all zero-network at score time.**

## Performance

- **Duration:** 25 min
- **Started:** 2026-08-05T01:10:21Z
- **Completed:** 2026-08-05T01:26:12Z
- **Tasks:** 2 completed
- **Files modified:** 7 (created)

## Accomplishments
- `src/recommendation/universe.py` defines the fixed, curated 5-class ticker universe (24 stocks across all 10 `profile.py` sectors, 12 ETFs, 12 crypto, 2 gold, 8 forex pairs) plus `infer_asset_class(ticker)`, matching `ASSET_TYPE_OPTIONS`'s exact vocabulary and order
- `src/recommendation/factor_scoring.py` computes momentum/volatility/quality sub-scores strictly within each asset class via `groupby("asset_class").transform()`, with a `MIN_GROUP_SIZE`/`DEFAULT_PERCENTILE_FALLBACK` guard against degenerate small-group percentiles
- `src/pages/_universe_loader.py` is the single shared fetch-and-assemble loop (`fetch_ohlcv` → `assemble_feature_frame` → `MIN_HISTORY_ROWS` gate), distinguishing D-07 "not found" from D-08 "insufficient data" so later pages (recommendations, search) render the correct distinct state
- 24 new unit tests, all synthetic/mocked — zero live network calls; full existing suite (78 tests) still green

## Task Commits

Each task was committed atomically:

1. **Task 1: Curated universe + within-class factor scoring** - `52b4636` (feat)
2. **Task 2: Shared universe data loader (fetch + assemble + D-08 gate)** - `cc7f9f3` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `src/recommendation/__init__.py` - package marker, zero-I/O discipline docstring
- `src/recommendation/universe.py` - STOCK/ETF/CRYPTO/GOLD/FOREX_UNIVERSE, ASSET_CLASSES, ASSET_CLASS_TICKERS, ASSET_CLASS_SECTORS, MIN_HISTORY_ROWS, infer_asset_class(ticker)
- `src/recommendation/factor_scoring.py` - compute_momentum_score, compute_volatility_score, compute_quality_score, MIN_GROUP_SIZE, DEFAULT_PERCENTILE_FALLBACK
- `src/pages/_universe_loader.py` - fetch_scorable_row, load_asset_feature_row, load_universe_rows
- `tests/test_recommendation_universe.py` - 12 tests
- `tests/test_recommendation_factor_scoring.py` - 6 tests
- `tests/test_universe_loader.py` - 7 tests

## Decisions Made
- `compute_quality_score` copies the input `universe_df` before assigning its temporary `_quality_raw` column rather than mutating the caller's frame in place — consistent with `src/features/`'s existing "never mutate input" discipline, a stricter (but compatible) reading of the plan's "assign it as a temporary column" instruction.
- No new composite scoring/engine logic was added in this plan — `factor_scoring.py`'s three functions return independent `pd.Series`, ready for Plan 05's `engine.py` to combine per D-01.

## Deviations from Plan

None - plan executed exactly as written. (`compute_quality_score`'s copy-vs-mutate choice above is an implementation-detail refinement within the plan's own instructions, not a deviation from any `<behavior>`/`<acceptance_criteria>` bullet.)

## Issues Encountered
- The local Supabase CLI Docker stack (required by `tests/conftest.py`'s autouse `supabase_env` session fixture, which every test in `tests/` depends on regardless of whether it touches Supabase) had a crash-looping `supabase_db` container at the start of this session (Docker Desktop had just been restarted). Resolved by running `npx supabase stop` followed by `npx supabase start`, which recreated a healthy stack. This is a pre-existing local-dev-environment characteristic of the test suite (established in Phase 1), not a defect introduced by this plan — none of this plan's own code depends on Supabase.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Plan 05 (`engine.py`) can now import `recommendation.universe`'s ticker lists/`infer_asset_class` and `recommendation.factor_scoring`'s three sub-score functions directly, with no rework.
- Plans 06/07 (recommendations/search pages) can import `src.pages._universe_loader`'s three functions directly for their fetch-and-assemble loops.
- No blockers identified for downstream plans in this phase.

---
*Phase: 03-deterministic-recommendation-engine*
*Completed: 2026-08-04*

## Self-Check: PASSED

All 8 created files verified present on disk; both task commits (`52b4636`, `cc7f9f3`) verified present in git log.
