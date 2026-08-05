---
phase: 03-deterministic-recommendation-engine
plan: 04
subsystem: recommendation-engine, ui
tags: [numpy, cosine-similarity, plotly, streamlit-components, disclaimer]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine (Plan 03)
    provides: numpy==2.3.4 and plotly==5.24.1 pinned in requirements.txt
provides:
  - "similarity_score(momentum_score, volatility_score, risk_tolerance) — D-02's content-based, structurally cold-start-immune similarity sub-score"
  - "render_disclaimer_banner() — the single shared educational-use disclaimer component for Plans 06/07"
  - "build_breakdown_figure/render_breakdown_bar_chart and build_price_history_figure/render_price_history_chart — the single shared chart-building functions for Plans 06/07"
affects: [03-05-engine, 03-06-recommendations-page, 03-07-search-page, 06-compliance-consolidation]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/components/ is a new package (this phase's introduction) for UI elements shared across pages -- separate from src/recommendation/'s zero-I/O discipline"
    - "Chart-building functions are split pure-figure-builder + thin st.plotly_chart-calling wrapper, so the pure builder is unit-testable without a Streamlit script context"

key-files:
  created:
    - src/recommendation/similarity.py
    - src/components/__init__.py
    - src/components/disclaimer.py
    - src/components/charts.py
    - tests/test_recommendation_similarity.py
    - tests/test_components.py
  modified: []

key-decisions:
  - "RISK_ARCHETYPES target vectors ([0.3,0.9] Conservative / [0.6,0.6] Moderate / [0.9,0.2] Aggressive over [momentum, volatility]) are a tunable v1 design choice per RESEARCH.md Assumptions Log A2, not derived from an external benchmark"
  - "similarity_score falls back to the Moderate archetype for any unrecognized risk_tolerance string, matching Phase 2's nullable-fields defensive-default precedent"
  - "charts.py splits build_*_figure (pure, returns go.Figure) from render_*_chart (thin st.plotly_chart wrapper) so the pure builders are unit-testable without a running Streamlit script context, per the plan's own test-scope note"

patterns-established:
  - "Pattern: shared UI components live in src/components/, imported identically by every page that needs them -- never re-implemented per page"
  - "Pattern: chart-building functions preserve caller-supplied dict/DataFrame order rather than re-sorting, so callers control display order"

requirements-completed: [REC-01, REC-02]

coverage:
  - id: D1
    description: "similarity_score(momentum_score, volatility_score, risk_tolerance) — deterministic, bounded [0,1], structurally cold-start-immune content-based similarity sub-score (D-02)"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_similarity.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Shared disclaimer banner (render_disclaimer_banner) rendering the exact UI-SPEC Copywriting Contract sentence"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "tests/test_components.py::test_disclaimer_text_matches_ui_spec_copywriting_contract_exactly"
        status: pass
    human_judgment: false
  - id: D3
    description: "Shared, reusable Plotly chart builders (build_breakdown_figure, build_price_history_figure) used at both compact and larger render sizes, using CHART_MARK_COLOR for all data ink"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "tests/test_components.py::test_build_breakdown_figure_returns_figure_with_five_bars_in_input_order"
        status: pass
      - kind: unit
        ref: "tests/test_components.py::test_build_price_history_figure_returns_single_line_trace_matching_close"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 4: Similarity Sub-Score and Shared UI Components Summary

**Content-based cosine-similarity function (numpy) completing D-01's third sub-score, plus a shared disclaimer banner and shared Plotly chart-builder functions (bar breakdown + price history) for reuse across the two upcoming pages.**

## Performance

- **Duration:** 25 min
- **Tasks:** 2
- **Files modified:** 6 (all created)

## Accomplishments
- `src/recommendation/similarity.py` implements `RISK_ARCHETYPES`, `cosine_similarity`, and `similarity_score` — a pure numpy content-based similarity function with no user_id/session/history parameter of any kind, proven cold-start-immune by a structural signature assertion test.
- `src/components/disclaimer.py` implements `DISCLAIMER_TEXT` and `render_disclaimer_banner()` — the single shared educational-use disclaimer, matching STATE.md's "introduce the component as early as Phase 3" decision.
- `src/components/charts.py` implements `CHART_MARK_COLOR`, `build_breakdown_figure`/`render_breakdown_bar_chart`, and `build_price_history_figure`/`render_price_history_chart` — single shared, independently-testable chart builders for the sub-factor breakdown and historical price line chart.
- Both `tests/test_recommendation_similarity.py` and `tests/test_components.py` follow the TDD RED/GREEN gate: each test file was committed first in a genuinely failing state (implementation module temporarily absent), then the implementation was added and the same tests were re-run to confirm GREEN before that commit.

## Task Commits

Each task was committed atomically, following the TDD RED/GREEN cycle:

1. **Task 1: Content-based similarity sub-score (D-02)**
   - `d7a8ad1` (test) — add failing test for similarity_score
   - `f9a8f60` (feat) — implement similarity_score content-based sub-score
2. **Task 2: Shared disclaimer banner + Plotly chart builders**
   - `fa64cc6` (test) — add failing test for disclaimer banner and chart builders
   - `920229c` (feat) — implement shared disclaimer banner and Plotly chart builders

**Plan metadata:** committed separately after this SUMMARY (see final commit).

## Files Created/Modified
- `src/recommendation/similarity.py` - RISK_ARCHETYPES, cosine_similarity, similarity_score (D-02 content-based sub-score)
- `src/components/__init__.py` - new shared-UI-components package marker
- `src/components/disclaimer.py` - DISCLAIMER_TEXT, render_disclaimer_banner()
- `src/components/charts.py` - CHART_MARK_COLOR, build_breakdown_figure/render_breakdown_bar_chart, build_price_history_figure/render_price_history_chart
- `tests/test_recommendation_similarity.py` - unit tests for similarity.py, including the cold-start-non-issue structural signature assertion
- `tests/test_components.py` - unit tests for the pure figure-building functions and disclaimer/chart constants

## Decisions Made
- `RISK_ARCHETYPES` vectors are a tunable v1 design choice (RESEARCH.md Pattern 3 / Assumptions Log A2), not an externally-derived benchmark — documented inline in `similarity.py`.
- `similarity_score` defensively falls back to the `"Moderate"` archetype for any unrecognized `risk_tolerance` value, consistent with Phase 2's nullable-fields precedent.
- `charts.py` splits each chart into a pure `build_*_figure` function (returns `go.Figure`, fully unit-testable) and a thin `render_*_chart` wrapper (calls `st.plotly_chart`), so the plan's test suite can exercise the pure builders without a running Streamlit script context.

## Deviations from Plan

None - plan executed exactly as written. Both tasks followed the plan's exact function signatures, constants, and file layout. The `tdd="true"` RED/GREEN gate was formally enforced per task (implementation module temporarily removed to confirm a genuine `ModuleNotFoundError`/collection failure before writing the implementation).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `similarity_score` is ready for Plan 05's `engine.py` to import and blend into the composite score alongside `profile_fit` (Plan 02), factor scores (Plan 01), and the D-06 explanation (`explain.py`).
- `render_disclaimer_banner()`, `render_breakdown_bar_chart()`, and `render_price_history_chart()` are ready for Plans 06/07's `recommendations.py` and `search.py` pages to import directly — no chart-building or disclaimer-copy logic needs to be duplicated or newly written in either page.
- No blockers identified for Plan 05 (engine) or Plans 06/07 (pages).

---
*Phase: 03-deterministic-recommendation-engine*
*Completed: 2026-08-05*

## Self-Check: PASSED

All 6 created files verified present on disk; all 4 commit hashes (d7a8ad1, f9a8f60, fa64cc6, 920229c) verified present in git log.
