---
phase: 03-deterministic-recommendation-engine
plan: 02
subsystem: recommendation-engine
tags: [python, pure-functions, rule-engine, template-nlg, zero-io]

# Dependency graph
requires:
  - phase: 02-investor-profile-feature-engineering-foundation
    provides: "Investor profile field design (excluded_sectors, preferred_asset_types, preferred_sectors, time_horizon) that profile_fit.py consumes directly"
provides:
  - "is_excluded(asset_row, profile) -> bool -- single authoritative hard-exclude decision for the recommendation engine's profile-fit sub-score (T-03-04)"
  - "compute_profile_fit(asset_row, profile) -> float -- [0,1]-bounded rule-based profile-fit sub-score"
  - "SUB_SCORE_ORDER, FACTOR_LABELS, ONE_FACTOR_TEMPLATE, TWO_FACTOR_TEMPLATE, explain(sub_scores, risk_tolerance) -> str -- deterministic REC-03 explanation generator"
affects: ["03-05 (engine.py orchestration)", "03-06/03-07 (recommendations/search pages rendering the breakdown + explanation)"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Zero-I/O plain-dict pure functions (no pandas/DataFrame dependency) for rule-based scoring, mirroring src/features/technical.py's zero-I/O module discipline"
    - "Fixed SUB_SCORE_ORDER list as the single source of truth for both display order and tie-break order -- consumers must import it, never redefine it"

key-files:
  created:
    - src/recommendation/profile_fit.py
    - src/recommendation/explain.py
    - tests/test_recommendation_profile_fit.py
    - tests/test_recommendation_explain.py
  modified: []

key-decisions:
  - "compute_profile_fit assumes is_excluded has already been called and returned False -- it never re-implements the exclusion check, avoiding two independently-computed exclusion paths that could drift"
  - "explain() ties are broken via sorted(sub_scores.items(), key=lambda kv: (-kv[1], SUB_SCORE_ORDER.index(kv[0]))) -- exactly two-way ties get the two-factor template, all other cases (clear winner or 3+ way tie) fall back to the one-factor template on the SUB_SCORE_ORDER-first tied factor"

patterns-established:
  - "Pattern: rule-based [0,1]-bounded scoring functions operate on plain dicts, not DataFrames, when the input is a single asset row plus a profile dict (contrasts with factor_scoring.py's DataFrame-based within-class normalization from 03-01)"

requirements-completed: [REC-02, REC-03]

coverage:
  - id: D1
    description: "is_excluded(asset_row, profile) is the single authoritative hard-exclude decision -- sector exclusion, preferred_asset_types hard filter, and None-sector non-match are all correctly implemented"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_is_excluded_true_when_sector_in_excluded_sectors"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_is_excluded_true_when_asset_class_not_in_preferred_asset_types"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_is_excluded_false_when_preferred_asset_types_empty"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_is_excluded_false_when_sector_none_never_matches_exclusion"
        status: pass
    human_judgment: false
  - id: D2
    description: "compute_profile_fit returns a [0,1]-bounded score that responds visibly to preferred_sectors/time_horizon inputs, never raising or going out of range on missing profile fields"
    requirement: "REC-02"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_compute_profile_fit_responds_to_preferred_sector_and_time_horizon"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_profile_fit.py::test_compute_profile_fit_always_bounded_zero_to_one_with_missing_fields"
        status: pass
    human_judgment: false
  - id: D3
    description: "explain(sub_scores, risk_tolerance) generates the exact one-factor/two-factor UI-SPEC Copywriting Contract sentences, deriving its top factor(s) from the caller's own sub_scores dict with a fixed SUB_SCORE_ORDER tie-break, deterministically, with no directive financial-advice language"
    requirement: "REC-03"
    verification:
      - kind: unit
        ref: "tests/test_recommendation_explain.py::test_explain_one_factor_template_for_clear_single_winner"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_explain.py::test_explain_two_factor_template_for_exact_two_way_tie_in_sub_score_order"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_explain.py::test_explain_falls_back_to_one_factor_template_on_five_way_tie"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_explain.py::test_explain_is_deterministic_across_repeated_calls"
        status: pass
      - kind: unit
        ref: "tests/test_recommendation_explain.py::test_no_directive_financial_advice_language_in_labels_or_templates"
        status: pass
    human_judgment: false

# Metrics
duration: 15min
completed: 2026-08-04
status: complete
---

# Phase 3 Plan 2: Profile-Fit Rule Engine + Deterministic Explanation Summary

**Rule-based [0,1]-bounded profile-fit hard-exclude/scoring engine plus a deterministic template-based one-sentence explanation generator, both pure zero-I/O dict functions with no LLM/network calls.**

## Performance

- **Duration:** ~15 min
- **Tasks:** 2 completed
- **Files modified:** 4 (2 source, 2 test)

## Accomplishments

- `src/recommendation/profile_fit.py`: `is_excluded(asset_row, profile)` is now the single authoritative hard-exclude decision (T-03-04) — sector-based exclusion and a non-empty `preferred_asset_types` hard filter, with `None` sectors never matching exclusion. `compute_profile_fit(asset_row, profile)` returns a `[0,1]`-bounded rule-based fit score (neutral 0.5 baseline, +0.3 preferred-sector bonus, +0.2 long-horizon/high-momentum bonus) that assumes exclusion has already been checked.
- `src/recommendation/explain.py`: `SUB_SCORE_ORDER`, `FACTOR_LABELS`, `ONE_FACTOR_TEMPLATE`, `TWO_FACTOR_TEMPLATE`, and `explain(sub_scores, risk_tolerance)` implement REC-03/D-06's deterministic explanation generator, selecting the top factor(s) directly from the caller's own `sub_scores` dict with a fixed tie-break order, exactly matching the UI-SPEC Copywriting Contract's two sentence templates.
- Both modules verified free of directive financial-advice language (`buy`/`sell`/`you should`) and free of `streamlit`/`yfinance` imports, per the plan's negative-grep acceptance criteria.

## Task Commits

Each task followed the TDD RED -> GREEN cycle:

1. **RED (both tasks):** `test(03-02): add failing tests for profile-fit and explain modules` - `11e5818`
2. **Task 1: Profile-fit rule engine (GREEN)** - `406be11` (feat)
3. **Task 2: Deterministic template-based explanation (GREEN)** - `fe9cd6d` (feat)

No REFACTOR commit was needed — both implementations matched the plan's exact prescribed logic on the first pass with no cleanup required.

**Plan metadata:** committed alongside this SUMMARY (see final commit below).

## Files Created/Modified

- `src/recommendation/profile_fit.py` - `is_excluded`/`compute_profile_fit` pure-dict rule engine
- `src/recommendation/explain.py` - `SUB_SCORE_ORDER`/`FACTOR_LABELS`/templates/`explain()` deterministic NLG
- `tests/test_recommendation_profile_fit.py` - covers every `<behavior>` bullet for Task 1
- `tests/test_recommendation_explain.py` - covers every `<behavior>` bullet for Task 2, exact-string assertions

## Decisions Made

- `compute_profile_fit` never re-implements `is_excluded`'s exclusion check — it is documented as assuming exclusion has already been checked by the caller, per the plan's must_haves.
- `explain()`'s tie-break sort key is `(-value, SUB_SCORE_ORDER.index(key))`, matching the plan's exact prescribed action — verified via the five-way-tie test (falls back to `profile_fit`, the first entry in `SUB_SCORE_ORDER`) and the two-way-tie test (momentum before volatility).

## Deviations from Plan

None — plan executed exactly as written. Both modules match the plan's `<action>` prescriptions verbatim (signatures, constants, scoring logic, template strings).

## Issues Encountered

None. Both TDD cycles went RED (ModuleNotFoundError, confirmed before implementation existed) then GREEN (11/11 new tests passing) on the first implementation pass. Full existing suite (89 tests) still passes with no regressions.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

`profile_fit.py` and `explain.py` are ready for Plan 05 (`engine.py`) to import with no rework: `engine.py` must call `is_excluded` on every asset row before any factor/similarity/composite math runs (dropping excluded rows entirely, per T-03-04's mitigation contract), and must call `explain()` with the exact same `sub_scores` dict it stores/displays for REC-02's breakdown so the explanation sentence never drifts from the visible numbers. No blockers.

---
*Phase: 03-deterministic-recommendation-engine*
*Completed: 2026-08-04*

## Self-Check: PASSED

All created files found on disk; all task commit hashes (`11e5818`, `406be11`, `fe9cd6d`) found in git history.
