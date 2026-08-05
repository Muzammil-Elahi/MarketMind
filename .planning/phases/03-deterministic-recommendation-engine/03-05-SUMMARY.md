---
phase: 03-deterministic-recommendation-engine
plan: 05
subsystem: recommendation-engine
tags: [scoring, orchestration, composite-score, top-n-grouping]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine (Plan 01)
    provides: universe.ASSET_CLASSES/MIN_HISTORY_ROWS, factor_scoring.compute_momentum_score/compute_volatility_score/compute_quality_score
  - phase: 03-deterministic-recommendation-engine (Plan 02)
    provides: profile_fit.is_excluded/compute_profile_fit, explain.SUB_SCORE_ORDER/explain
  - phase: 03-deterministic-recommendation-engine (Plan 04)
    provides: similarity.similarity_score
provides:
  - "WEIGHTS, TOP_N_PER_CLASS — src/recommendation/engine.py's tunable v1 scoring constants"
  - "score_universe(profile, universe_df, apply_hard_exclude=True) -> pd.DataFrame — the single scoring pipeline (REC-01/REC-02/REC-03), reused unmodified by both the ranked-list and search pages (REC-04)"
  - "build_recommendations(profile, universe_df, top_n=TOP_N_PER_CLASS) -> dict[str, list[dict]] — D-05's top-N-per-asset-class grouping on top of score_universe"
affects: [03-06-recommendations-page, 03-07-search-page]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/recommendation/engine.py orchestrates all five sibling modules (universe, factor_scoring, profile_fit, similarity, explain) without reimplementing any of their math inline -- mirrors src/features/feature_frame.py's assembly pattern"
    - "_round_half_up (math.floor(value + 0.5)) is used everywhere a display-rounded integer is needed, never Python's built-in round(), to avoid silently violating REC-02's round-half-up precision requirement via banker's-rounding"

key-files:
  created:
    - src/recommendation/engine.py
    - tests/test_recommendation_engine.py
  modified: []

key-decisions:
  - "WEIGHTS = {profile_fit: 0.30, momentum: 0.20, volatility: 0.15, quality: 0.10, similarity: 0.25} is a documented, tunable v1 choice (RESEARCH.md Assumptions A3) summing to exactly 1.0, not a locked decision"
  - "score_universe accepts apply_hard_exclude (default True) as the single lever distinguishing the ranked-list page's curated-universe filtering from the search page's bypass path (REC-04) -- there is exactly one scoring implementation, never two"
  - "The hard-exclude filter runs via a boolean mask on the full universe_df BEFORE any factor/profile_fit/similarity column is computed, so an excluded row never enters any later groupby/apply and can never influence another asset's within-class percentile (T-03-04)"

patterns-established:
  - "Pattern: any future orchestrator combining src/recommendation/ sub-modules should read SUB_SCORE_ORDER from explain.py rather than redefining a literal key-order list, keeping ordering single-source-of-truth"

# Metrics
duration: 20min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 05: Deterministic Recommendation Engine Orchestrator Summary

Built `src/recommendation/engine.py`'s `score_universe`/`build_recommendations` pair — the zero-I/O orchestrator that composes profile_fit, factor_scoring, and similarity sub-scores into a single [0,100]-bounded, round-half-up-precise, deterministically-ordered, top-N-per-class recommendation set.

## What Was Built

- **`score_universe(profile, universe_df, apply_hard_exclude=True)`**: the single scoring pipeline. Applies the hard-exclude pre-filter (via `profile_fit.is_excluded`) before any scoring math runs when `apply_hard_exclude=True`; computes `momentum`/`volatility`/`quality` via `factor_scoring`, `profile_fit` via `profile_fit.compute_profile_fit` (fed the just-computed momentum as `momentum_pct`), and `similarity` via `similarity.similarity_score`; composes all five into a weighted `composite_score` via a private `_compose_score`; attaches `composite_score_display`/`sub_scores_display` via a private `_round_half_up` (round-half-up, not banker's-rounding); attaches `explanation` from `explain.explain` called with the row's own `sub_scores` dict; sorts by `(composite_score desc, ticker asc)`.
- **`build_recommendations(profile, universe_df, top_n=TOP_N_PER_CLASS)`**: groups `score_universe`'s output by `asset_class`, always returning all 5 `ASSET_CLASSES` as dict keys (absent classes map to `[]`), truncating each group to `top_n` rows without re-sorting or recomputing any score.
- **`WEIGHTS`** (sums to 1.0) and **`TOP_N_PER_CLASS = 3`** module-level constants.

## Deviations from Plan

None — plan executed exactly as written. One internal test-authoring correction: the module's own docstring originally used the literal word "LangGraph" while describing what it does *not* import, which tripped both the plan's own case-insensitive `langgraph` grep check and this plan's own zero-network-import unit test (a documentation string, not an actual import, was matching). Reworded the docstring to describe the exclusion without using the forbidden literal tokens — no functional change, verification commands and the added unit test both pass cleanly.

## Verification

- `pytest tests/test_recommendation_engine.py -x -q` — 19/19 passed.
- Full repo suite: `pytest -q` — 121/121 passed (no regressions in Phase 1/2/3 prior work).
- `sum(WEIGHTS.values()) == 1.0` — confirmed via direct assertion and a dedicated test.
- Negative grep for `streamlit`/`yfinance`/`langgraph`/`google.genai`/`google_genai` imports in `src/recommendation/engine.py` — zero matches.

## TDD Gate Compliance

RED commit `65e85f4` (`test(03-05): add failing test for score_universe and build_recommendations`) confirmed failing via `ImportError` (module did not yet exist) before any implementation was written. GREEN commit `8d1749f` (`feat(03-05): implement score_universe and build_recommendations orchestrator`) makes all 19 tests in the file pass. No REFACTOR commit was needed — the implementation matched the plan's `<action>` block directly on first pass.

## Self-Check: PASSED

- FOUND: `src/recommendation/engine.py`
- FOUND: `tests/test_recommendation_engine.py`
- FOUND commit `65e85f4`
- FOUND commit `8d1749f`
