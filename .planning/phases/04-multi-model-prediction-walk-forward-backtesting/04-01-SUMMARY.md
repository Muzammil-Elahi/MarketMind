---
phase: 04-multi-model-prediction-walk-forward-backtesting
plan: 01
subsystem: infra
tags: [xgboost, prophet, scikit-learn, cmdstanpy, dependencies, package-skeleton]

# Dependency graph
requires:
  - phase: 03-deterministic-recommendation-engine
    provides: "src/recommendation/ package-marker docstring convention this plan replicates for src/prediction/"
provides:
  - "xgboost==3.3.0, prophet==1.2.1, scikit-learn==1.9.0 pinned in requirements.txt"
  - "src/prediction/ package skeleton (zero-I/O contract) every later Phase 4 plan builds under"
affects: [04-02, 04-03, 04-04, 04-05, 04-06, 04-07, 04-08, 04-09]

# Tech tracking
tech-stack:
  added: [xgboost==3.3.0, prophet==1.2.1, scikit-learn==1.9.0]
  patterns:
    - "src/prediction/ mirrors src/recommendation/'s zero-I/O, no-streamlit/yfinance/sqlite3 module-boundary discipline"

key-files:
  created: [src/prediction/__init__.py]
  modified: [requirements.txt]

key-decisions:
  - "Task 1's blocking-human-verify checkpoint (package legitimacy for xgboost/prophet/scikit-learn) was explicitly approved by the human before any install ran -- never auto-approved despite workflow.mode=yolo"
  - "cmdstanpy (Prophet's transitive Stan backend) is not added as its own requirements.txt line -- remains an auto-installed transitive dependency of prophet, per CLAUDE.md's framing"

patterns-established:
  - "Pattern: new phase-level ML dependencies get a dedicated blocking-human-verify Task 1 (Package Legitimacy Gate) before any pip install runs, mirroring 03-03-PLAN.md's numpy/plotly precedent"

requirements-completed: [PRED-02]

coverage:
  - id: D1
    description: "xgboost==3.3.0, prophet==1.2.1, scikit-learn==1.9.0 installed and pinned in requirements.txt, all nine pre-existing lines unchanged/unreordered"
    requirement: "PRED-02"
    verification:
      - kind: other
        ref: "grep -c xgboost==3.3.0/prophet==1.2.1/scikit-learn==1.9.0/streamlit==1.59.2 requirements.txt (all exit 0/count 1)"
        status: pass
    human_judgment: false
  - id: D2
    description: "All three packages import successfully, including sklearn.model_selection.TimeSeriesSplit"
    requirement: "PRED-02"
    verification:
      - kind: other
        ref: "python -c \"import xgboost; import prophet; import sklearn; from sklearn.model_selection import TimeSeriesSplit\" (exit 0)"
        status: pass
    human_judgment: false
  - id: D3
    description: "src/prediction/__init__.py exists documenting the package's zero-I/O contract"
    requirement: "PRED-02"
    verification:
      - kind: other
        ref: "test -f src/prediction/__init__.py"
        status: pass
    human_judgment: false

duration: 12min
completed: 2026-08-17
status: complete
---

# Phase 4 Plan 01: Pin ML/Backtest Dependencies + Prediction Package Skeleton Summary

**xgboost/prophet/scikit-learn pinned in requirements.txt after human-approved package-legitimacy checkpoint, plus the src/prediction/ zero-I/O package skeleton every later Phase 4 plan builds under**

## Performance

- **Duration:** 12 min
- **Started:** 2026-08-17T00:05:00Z
- **Completed:** 2026-08-17T00:17:16Z
- **Tasks:** 2 (Task 1 checkpoint + Task 2 auto)
- **Files modified:** 2

## Accomplishments
- Task 1's blocking-human-verify checkpoint (package legitimacy for xgboost==3.3.0/prophet==1.2.1/scikit-learn==1.9.0, all three flagged SUS by 04-RESEARCH.md's automated audit due to a known PyPI-metadata-gap tool limitation) was resolved by explicit human approval ("approved") before this continuation agent proceeded to install anything.
- `pip install xgboost==3.3.0 prophet==1.2.1 scikit-learn==1.9.0` completed cleanly against Python 3.13.7 on Windows -- all three (plus prophet's transitive deps: cmdstanpy, matplotlib, holidays, scipy, joblib, threadpoolctl) resolved to **prebuilt wheels** (`win_amd64`/`py3-none-any`), no source compilation or C-toolchain step was triggered during `pip install` itself.
- `requirements.txt` now has `xgboost==3.3.0`, `prophet==1.2.1`, `scikit-learn==1.9.0` appended after the nine pre-existing Phase 1/2/3 lines, in that exact order, with all nine prior lines byte-identical and unreordered.
- `src/prediction/__init__.py` created as a package marker with a docstring documenting the zero-I/O contract (no `streamlit`/`yfinance`/`sqlite3` imports anywhere under `src/prediction/`), mirroring `src/recommendation/__init__.py`'s exact convention.
- `python -c "import xgboost; import prophet; import sklearn; from sklearn.model_selection import TimeSeriesSplit"` exits 0.

## Task Commits

Each task was committed atomically:

1. **Task 1: [BLOCKING] Verify xgboost, prophet, and scikit-learn package legitimacy before install** - checkpoint only, no commit (resolved via human "approved" response in the resume instructions; no code/file changes are associated with a pure verification gate).
2. **Task 2: Install and pin xgboost/prophet/scikit-learn, create the prediction package skeleton** - `b189cb2` (feat)

**Plan metadata:** SUMMARY.md commit (this file) follows immediately after.

## Files Created/Modified
- `requirements.txt` - Appended `xgboost==3.3.0`, `prophet==1.2.1`, `scikit-learn==1.9.0` after the nine pre-existing Phase 1/2/3 lines
- `src/prediction/__init__.py` - New package marker, zero-I/O contract docstring mirroring `src/recommendation/__init__.py`

## Decisions Made
- cmdstanpy (Prophet's transitive Stan backend dependency) was **not** added as its own line in `requirements.txt` -- it remains an auto-installed transitive dependency of `prophet`, matching `CLAUDE.md`'s "auto-installed dep" framing and the plan's explicit instruction.
- Package legitimacy for all three flagged-SUS packages was verified and approved by the human before Task 2 ran, per the Package Legitimacy Gate (never auto-approvable even under `workflow.mode=yolo`).

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Prophet import time (local Windows dev-machine measurement):** `import prophet` alone took **1.575s** on this machine (Python 3.13.7, Windows 11). This is a local dev-machine data point only, per the plan's explicit caveat -- it does **not** prove Streamlit Community Cloud's Debian build-image behavior. The actual Streamlit Cloud deploy validation (confirming the build log shows a wheel install rather than a CmdStan source compile step) remains an outstanding STATE.md-flagged item to check at actual deploy time, not resolvable from local execution.

**CmdStan backend binary not yet installed (informational, out of scope for this plan):** `prophet`'s Python package imports successfully, but its Stan backend (`cmdstanpy.cmdstan_path()`) reports "No CmdStan installation found" -- this is expected: `pip install prophet` installs the Python wrapper only, and the compiled CmdStan binary is a separate install step (`cmdstanpy.install_cmdstan()` or equivalent) needed only when a model is actually *fit*, not at import time. This plan's acceptance criteria only required the import statement to succeed (it does), so no action was taken here. Flagging explicitly for whichever later plan (05, per 04-RESEARCH.md) first calls `Prophet().fit(...)` -- that plan will need to either bundle/trigger the CmdStan install or handle the resulting runtime error via the import-guard pattern already anticipated in `src/prediction/__init__.py`'s docstring and the threat model's T-04-02 mitigation.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All three Phase 4 model-layer dependencies (`xgboost`, `prophet`, `scikit-learn`) are installed, pinned, and import-verified; `src/prediction/` package skeleton exists.
- Plans 03-09 of this phase (SMA baseline, XGBoost model, Prophet model, walk-forward backtesting via `TimeSeriesSplit`, prediction UI, etc.) can now import from `src/prediction/` or these three packages with no further gating.
- Outstanding, not-yet-actioned concern for Plan 05 (or whichever plan first fits a Prophet model): CmdStan backend binary installation is a separate step from `pip install prophet` and needs its own handling (install trigger or graceful runtime degradation) before Prophet can actually produce a forecast.

---
*Phase: 04-multi-model-prediction-walk-forward-backtesting*
*Completed: 2026-08-17*

## Self-Check: PASSED

- FOUND: requirements.txt
- FOUND: src/prediction/__init__.py
- FOUND: b189cb2 (Task 2 commit)
- FOUND: 6fee958 (SUMMARY.md commit)
