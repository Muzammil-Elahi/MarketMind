---
phase: 03-deterministic-recommendation-engine
plan: 06
subsystem: ui
tags: [streamlit, recommendations-page, require-auth, plotly, cross-navigation]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine (Plan 01)
    provides: universe.ASSET_CLASSES/ASSET_CLASS_TICKERS/ASSET_CLASS_SECTORS, _universe_loader.load_universe_rows
  - phase: 03-deterministic-recommendation-engine (Plan 04)
    provides: components.disclaimer.render_disclaimer_banner, components.charts.render_breakdown_bar_chart
  - phase: 03-deterministic-recommendation-engine (Plan 05)
    provides: recommendation.engine.build_recommendations
provides:
  - "render_recommendations_page() -- src/pages/recommendations.py's require_auth()-gated ranked-shortlist page (REC-01/REC-02/REC-03's user-facing surface)"
affects: [03-08-app-registration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "src/pages/recommendations.py is render-only over build_recommendations' output -- no page-local scoring/normalization logic, mirroring src/pages/profile.py's page-thin/module-thick split"
    - "Deferred (call-time, not module-level) import of src.pages.search.render_search_page inside the View Details button handler, since search.py ships in the next plan (03-07) -- keeps this page importable in the interim without affecting runtime navigation behavior once both pages exist"

key-files:
  created:
    - src/pages/recommendations.py
  modified: []

key-decisions:
  - "View Details cross-navigation imports src.pages.search.render_search_page lazily inside the button's on-click branch rather than at module top level, since src/pages/search.py does not exist until Plan 07 executes immediately after this one -- avoids a transient ImportError on this module without changing any must-have behavior"
  - "Ticker (Heading-role element) is rendered via st.subheader(card['ticker']) per card, consistent with the asset-class section headers' own st.subheader usage and the UI-SPEC's Heading typography role"

requirements-completed: [REC-01, REC-02, REC-03]

coverage:
  - id: D1
    description: "render_recommendations_page() gated by require_auth() first-and-only, renders per-asset-class ranked shortlist (Stocks/ETFs/Crypto/Gold/Forex in order) sourced entirely from build_recommendations(profile, universe_df)"
    requirement: "REC-01"
    verification:
      - kind: unit
        ref: "grep -c 'def render_recommendations_page' / 'require_auth' / 'build_recommendations(' / 'load_universe_rows(' -- all present"
        status: pass
      - kind: other
        ref: "python -c \"import ast; ast.parse(open('src/pages/recommendations.py').read())\""
        status: pass
    human_judgment: true
    rationale: "End-to-end rendered-page verification (card layout, live navigation, empty/error states) happens in Plan 08's end-of-phase human-check once app.py registers both pages -- this plan's own verification is structural/static only."
  - id: D2
    description: "Each card shows composite_score_display as '{score}/100', sub-factor breakdown via render_breakdown_bar_chart, and the verbatim explanation sentence -- all from the same engine dict entry, never recomputed on the page"
    requirement: "REC-02"
    verification:
      - kind: other
        ref: "manual code review -- card fields (composite_score_display, sub_scores_display, explanation) read directly from build_recommendations' output dict with no page-local computation"
        status: pass
    human_judgment: true
    rationale: "Visual fidelity of the breakdown chart and card layout requires a running app to confirm -- deferred to Plan 08's human-check."
  - id: D3
    description: "Disclaimer banner renders once near the top of the page, before the ranked list; zero-scoreable-universe path renders the exact UI-SPEC error copy instead of a crash"
    requirement: "REC-03"
    verification:
      - kind: unit
        ref: "grep -c \"We couldn't generate recommendations\" src/pages/recommendations.py"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-08-05
status: complete
---

# Phase 3 Plan 06: Recommendations Page Summary

Built `src/pages/recommendations.py`'s `render_recommendations_page()` -- the `require_auth()`-gated, per-asset-class ranked shortlist that renders `build_recommendations`' scored output (composite score, sub-factor breakdown chart, one-sentence explanation) with zero page-local scoring logic.

## Performance

- **Duration:** 15 min
- **Started:** 2026-08-05T02:10:00Z
- **Completed:** 2026-08-05T02:25:00Z
- **Tasks:** 1
- **Files modified:** 1

## Accomplishments
- `render_recommendations_page()` -- `require_auth()`-first page, fetches profile fresh every render via `src.data.profile.fetch_profile`, treats an incomplete profile as a non-blocking `st.info` nudge (never a hard error)
- Builds `tickers_with_metadata` across all 5 asset classes from `universe.ASSET_CLASS_TICKERS`/`ASSET_CLASS_SECTORS`, loads them via `_universe_loader.load_universe_rows`, and scores via `engine.build_recommendations` as the page's entire scoring implementation
- Renders every asset-class section (Stocks/ETFs/Crypto/Gold/Forex) unconditionally with its header even when empty (D-04/D-05 zero-one-many)
- Renders the disclaimer banner near the top, before the ranked list, and the exact UI-SPEC error copy when zero assets are scorable across the entire universe
- "View Details" button per card cross-navigates to the Search page (`st.switch_page` with `query_params={"ticker": ...}`), with a deferred import to tolerate `src/pages/search.py` not yet existing at this point in the build order

## Task Commits

Each task was committed atomically:

1. **Task 1: Recommendations page -- fetch, score, render ranked shortlist** - `48800ee` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `src/pages/recommendations.py` - `render_recommendations_page()`, the require_auth()-gated ranked-shortlist page

## Decisions Made
- View Details' `from src.pages.search import render_search_page` is a call-time (lazy) import inside the button's on-click branch, not a module-level import, since `src/pages/search.py` ships in Plan 07 (the very next plan in this wave) -- this keeps `src/pages/recommendations.py` importable on its own in the interim, with no change to the actual navigation behavior once both pages exist and are registered in Plan 08.
- The per-card ticker (Heading-role element per UI-SPEC Typography) is rendered via `st.subheader(card["ticker"])`, matching the same `st.subheader` call used for asset-class section headers elsewhere on this page.

## Deviations from Plan

None (structural) -- plan executed as written. One implementation-detail clarification not fully specified by the plan text: the plan's action paragraph instructs importing `render_search_page` from `src.pages.search` without specifying import timing; since that module doesn't exist until Plan 07 runs (this plan and 03-07 are both wave 4, with 03-07 executing immediately after per the orchestrator's stated sequencing), a call-time import was used instead of a module-level import to avoid a transient `ImportError` on this file. This is a Rule 3 (auto-fix blocking issue) judgment call -- no architectural change, no behavior change once both pages exist, and it does not affect any of the plan's must-have truths, key-links, or prohibitions (none of which specify import location).

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- `src/pages/recommendations.py` is complete and ready for `src/app.py` registration (Plan 08), pending `src/pages/search.py` (Plan 07) for the View Details cross-navigation to be exercisable end-to-end.
- No blockers identified for Plan 07 (Search page) or Plan 08 (app registration).

---
*Phase: 03-deterministic-recommendation-engine*
*Completed: 2026-08-05*
