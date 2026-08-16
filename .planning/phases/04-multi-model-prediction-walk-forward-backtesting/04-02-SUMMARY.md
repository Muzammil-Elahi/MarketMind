---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 02
subsystem: ui
tags: [plotly, streamlit, charts, confidence-interval, forecast]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine
    provides: "src/components/charts.py's pure-builder/thin-renderer split (build_price_history_figure, CHART_MARK_COLOR, render_*_chart st.plotly_chart wrapper pattern)"
provides:
  - "build_forecast_figure(price_df, forecast_index, forecast_values, ci_lower, ci_upper) -> go.Figure: 4-trace historical + shaded-CI-band + dashed-forecast chart"
  - "render_forecast_chart(price_df, forecast_index, forecast_values, ci_lower, ci_upper, key) -> None: thin st.plotly_chart wrapper"
  - "FORECAST_COLOR (#0EA5E9) and CI_FILL_COLOR (rgba(14, 165, 233, 0.2)) module constants"
affects: [04-08, 04-09]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Plotly fill='tonexty' three-trace CI-band idiom (invisible upper line, invisible lower line with fill=tonexty, visible dashed forecast line) extending the existing pure-builder/thin-renderer chart convention"

key-files:
  created: []
  modified:
    - src/components/charts.py
    - tests/test_components.py

key-decisions:
  - "build_forecast_figure calls build_price_history_figure(price_df) and adds 3 traces on top rather than reimplementing the historical line, per the existing reuse convention and this plan's explicit prohibition"

patterns-established: []

requirements-completed: [PRED-03]

coverage:
  - id: D1
    description: "build_forecast_figure returns a 4-trace go.Figure (historical line, invisible CI-upper line, invisible CI-lower line with fill=tonexty, visible dashed forecast line) in the exact order/shape specified by 04-RESEARCH.md Pattern 6 and 04-UI-SPEC.md's Color table"
    requirement: "PRED-03"
    verification:
      - kind: unit
        ref: "tests/test_components.py#test_build_forecast_figure_returns_four_traces_in_order"
        status: unknown
      - kind: unit
        ref: "tests/test_components.py#test_build_forecast_figure_uses_forecast_and_ci_fill_colors"
        status: unknown
      - kind: unit
        ref: "tests/test_components.py#test_forecast_color_and_ci_fill_color_match_ui_spec_exactly"
        status: unknown
      - kind: unit
        ref: "tests/test_components.py#test_build_forecast_figure_preserves_ci_lower_forecast_ci_upper_ordering"
        status: unknown
      - kind: other
        ref: "manual python -c import/exercise of build_forecast_figure (bypasses Docker-gated conftest.py) -- see Issues Encountered"
        status: pass
    human_judgment: false
  - id: D2
    description: "render_forecast_chart thin st.plotly_chart wrapper matching render_price_history_chart's shape"
    requirement: "PRED-03"
    verification: []
    human_judgment: true
    rationale: "st.plotly_chart-calling wrapper requires a running Streamlit script context to test meaningfully; per this file's own test-module docstring convention (see tests/test_components.py header), it is exercised by Plans 08/09's human-check, not an automated test here."

# Metrics
duration: 20min
completed: 2026-08-16
status: complete
---

# Phase 4 Plan 2: Forecast Chart with Shaded Confidence-Interval Band Summary

**`build_forecast_figure`/`render_forecast_chart` added to `src/components/charts.py`, overlaying a dashed forecast line and shaded `fill='tonexty'` CI band on the reused historical price chart, with 4 new unit tests plus a color-constant test in `tests/test_components.py`.**

## Performance

- **Duration:** ~20 min
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- `build_forecast_figure(price_df, forecast_index, forecast_values, ci_lower, ci_upper)` returns a 4-trace `go.Figure`: reused historical line + invisible CI-upper line + invisible CI-lower line (`fill="tonexty"`) + visible dashed forecast line, per 04-RESEARCH.md Pattern 6 verbatim.
- `render_forecast_chart(..., key)` thin `st.plotly_chart` wrapper mirroring `render_price_history_chart`'s exact shape.
- `FORECAST_COLOR = "#0EA5E9"` and `CI_FILL_COLOR = "rgba(14, 165, 233, 0.2)"` module-level constants matching 04-UI-SPEC.md's Color table exactly.
- 4 new tests added to `tests/test_components.py` covering trace order/shape, color usage, exact color-constant values, and CI-lower/forecast/CI-upper ordering preservation.

## Task Commits

Each task was committed atomically (TDD RED/GREEN cycle):

1. **Task 1: Forecast chart builder with shaded CI band (RED)** - `eba4ea0` (test)
2. **Task 1: Forecast chart builder with shaded CI band (GREEN)** - `3cd5ce7` (feat)

**Deviation commit:** `adec194` (docs: log pre-existing Docker/Supabase pytest environment gap)

_Note: this task had `tdd="true"` -- no REFACTOR commit was needed; the GREEN implementation matched 04-RESEARCH.md Pattern 6's code verbatim with no cleanup pass required._

## TDD Gate Compliance

- RED gate: `eba4ea0` (`test(04-02): add failing tests for forecast chart builder`) -- confirmed failing via `ImportError: cannot import name 'CI_FILL_COLOR'` before any implementation existed.
- GREEN gate: `3cd5ce7` (`feat(04-02): implement forecast chart builder with shaded CI band`) -- implementation added after RED commit.
- REFACTOR gate: not applicable -- implementation matched the plan's specified code verbatim, no cleanup needed.

Both gates present in git log in the correct order. Gate sequence is compliant.

## Files Created/Modified
- `src/components/charts.py` - Added `FORECAST_COLOR`, `CI_FILL_COLOR` constants and `build_forecast_figure`/`render_forecast_chart` functions
- `tests/test_components.py` - Added `test_forecast_color_and_ci_fill_color_match_ui_spec_exactly`, `test_build_forecast_figure_returns_four_traces_in_order`, `test_build_forecast_figure_uses_forecast_and_ci_fill_colors`, `test_build_forecast_figure_preserves_ci_lower_forecast_ci_upper_ordering`

## Decisions Made
- None beyond the plan's own explicit instructions - implemented 04-RESEARCH.md Pattern 6's code verbatim as directed, reusing `build_price_history_figure` per the plan's prohibition against reimplementing the historical-line trace.

## Deviations from Plan

None affecting the shipped code - `build_forecast_figure`/`render_forecast_chart`/constants were implemented exactly as specified in the plan's `<action>` block.

### Auto-fixed Issues

None.

## Issues Encountered

**Pre-existing environment gap (not caused by this plan, logged to `deferred-items.md`, out of scope per SCOPE BOUNDARY):** `pytest tests/test_components.py -x -q` could not be run in this sandboxed worktree because `tests/conftest.py`'s `supabase_env` fixture is `scope="session", autouse=True` and requires a running local Supabase CLI Docker stack (`npx supabase status -o env`). This fixture fires for the whole test session regardless of which file is targeted, and Docker Desktop's daemon is unreachable in this environment (`docker ps` fails with `failed to connect to the docker API at npipe:////./pipe/dockerDesktopLinuxEngine`).

As a workaround, `build_forecast_figure`'s full behavior (4-trace order, colors, `fill="tonexty"`, historical-trace byte-identity to `build_price_history_figure`, CI-lower/forecast/CI-upper ordering preservation) was verified via a direct `python -c "..."` script that imports and exercises the function outside pytest (bypassing the Docker-gated `conftest.py`, since `src.components.charts` has no Supabase import chain). All assertions passed. See `.planning/phases/04-multi-model-prediction-walk-forward-backtesting/deferred-items.md` for the full writeup. The equivalent assertions are encoded as real pytest tests and will pass once run in an environment with the local Supabase Docker stack running (standard dev/CI environment, per PROJECT.md's Key Decisions).

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- `build_forecast_figure`/`render_forecast_chart` are ready for Plans 08/09 (search-page UI extension) to call directly with real forecast/CI arrays from Plans 03-07's model/backtest code, with no rework needed.
- Recommend re-running `pytest tests/test_components.py -x -q` in an environment with the local Supabase Docker stack running (or after conftest.py's Supabase fixture is scoped down to only the test modules that need it) to get a fully green automated pytest confirmation on top of this plan's manual verification.

## Self-Check

- FOUND: src/components/charts.py contains `build_forecast_figure`, `render_forecast_chart`, `FORECAST_COLOR`, `CI_FILL_COLOR`
- FOUND: tests/test_components.py contains the 4 new tests
- FOUND: commit eba4ea0 (test)
- FOUND: commit 3cd5ce7 (feat)
- FOUND: commit adec194 (docs)

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-16*
