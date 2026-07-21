---
phase: 02-investor-profile-feature-engineering-foundation
plan: 04
subsystem: ui
tags: [streamlit, forms, data-editor, ticker-validation, navigation]

# Dependency graph
requires:
  - phase: 02-investor-profile-feature-engineering-foundation
    plan: "03"
    provides: "src/data/profile.py: fetch_profile, upsert_profile, fetch_holdings, upsert_holdings, validate_ticker — the CRUD/ticker-validation chokepoint this page calls exclusively"
provides:
  - "src/pages/profile.py: render_profile_page() — the require_auth()-gated investor profile builder UI (scalar form + dynamic holdings grid + D-08 validation + save)"
  - "src/app.py: profile_page registered in the logged-in st.navigation branch only"
affects: [phase-03-recommendation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.data_editor(num_rows=\"dynamic\") as the first dynamic add/remove-row grid in the codebase, following RESEARCH.md's Code Examples shape"
    - "Widget-level (not per-cell/per-row) CSS-injection highlight for a data_editor, adapting login.py's _highlight_empty_fields technique to a widget that exposes only one key= — documented as a deliberate capability-driven narrowing of the UI-SPEC's per-row intent"

key-files:
  created:
    - src/pages/profile.py
  modified:
    - src/app.py

key-decisions:
  - "Followed login.py's copy-constants-not-inline-strings and CSS-injection patterns verbatim rather than introducing a new styling approach"
  - "st.rerun() called immediately after st.success() on save, per the plan's explicit instruction, even though this means the success message is visually replaced by the rerun almost immediately — matches login.py's existing rerun-after-mutate precedent, not a new tradeoff introduced here"
  - "Blank ticker rows (unfilled newly-added grid rows) are silently skipped before validation and before save — not treated as an error — since an empty row is not a submission attempt"
  - "NaN/blank numeric cells (quantity, cost_basis) are converted to Python None before being passed to upsert_holdings, since pandas' NaN is truthy and would otherwise defeat a naive `or \"\"` blank-check on the ticker column too — pd.isna() is used explicitly instead"

requirements-completed: [PROFILE-01, PROFILE-02]

coverage:
  - id: T1
    description: "render_profile_page() renders the scalar-fields form + holdings grid with exact Copywriting Contract strings, validates every ticker via validate_ticker() before saving anything, and never imports src.features or wraps any read in a caching decorator"
    requirement: "PROFILE-01"
    verification:
      - kind: unit
        ref: "grep structural assertions (def render_profile_page, require_auth, Save Profile, Existing Holdings, No holdings added yet, Profile saved, num_rows=\"dynamic\", absence of st.cache_data / from src.features) all pass; python -c ast.parse succeeds"
        status: pass
    human_judgment: false
  - id: T2
    description: "profile_page registered in st.app.py's logged-in st.navigation branch only; logged-out branch unchanged"
    requirement: "PROFILE-01, PROFILE-02"
    verification:
      - kind: unit
        ref: "grep structural assertions (import line, profile_page occurrences) pass; python -c ast.parse succeeds; full pytest suite (54 tests, including test_profile_crud.py/test_holdings_rls.py/test_rls_policy.py against the live local Supabase stack) passes unaffected"
        status: pass
    human_judgment: true
    human_judgment_note: "Task 2's <human-check> block (sign-in, fill/save/reload/edit/delete a holdings row end-to-end) is deferred to this project's end-of-phase human-verify mode per workflow.human_verify_mode: end-of-phase — not exercised as a blocking checkpoint during this plan's execution."

duration: 8min
completed: 2026-07-20
status: complete
---

# Phase 2 Plan 4: Investor Profile Builder Page Summary

**Built `src/pages/profile.py` — the single always-editable Streamlit form (D-12) for the six scalar profile fields plus a dynamic `st.data_editor` holdings grid with D-08 submit-time ticker validation and a scoped invalid-ticker highlight — and registered it in `src/app.py`'s auth-gated navigation, delivering PROFILE-01/PROFILE-02's actual user-facing surface.**

## Performance

- **Duration:** 8 min
- **Completed:** 2026-07-20
- **Tasks:** 2 completed
- **Files modified:** 2 (1 created, 1 modified)

## Accomplishments

- `render_profile_page()` calls `require_auth()` first (D-04), then fetches `existing_profile`/`existing_holdings` fresh on every render (D-13, no caching decorator anywhere in the file) to pre-fill every widget.
- One `st.form("profile_form")` covers Risk Tolerance / Time Horizon (`st.selectbox`, `index=None` when unset), Preferred/Excluded Sectors (`st.multiselect`), Preferred Asset Types (five `st.checkbox` widgets laid out via `st.columns(5)`), and Capital (`st.number_input`) — identical rendering path for a first-time user (empty/default values) and an existing edit (pre-filled values), per D-12.
- The holdings grid renders `HOLDINGS_EMPTY_STATE` caption above an empty `st.data_editor` when there are zero rows, and otherwise pre-fills `ticker`/`quantity`/`cost_basis` from `fetch_holdings()`; `st.data_editor(..., num_rows="dynamic", key="holdings_editor")` handles add/remove-row UX natively.
- On submit, blank (unfilled) ticker rows are skipped, every remaining ticker is checked via `validate_ticker()`; any invalid ticker renders the exact Copywriting Contract error string per bad ticker, applies `_highlight_holdings_editor()`'s widget-scoped red border (`div.st-key-holdings_editor`), and blocks the save entirely — neither scalar fields nor holdings are written.
- On an all-valid submit, `upsert_profile(...)` and `upsert_holdings(...)` run inside a `try`/`except`; success renders `"Profile saved."` then `st.rerun()`; any exception renders `"We couldn't save your profile. Please try again."` with no partial write left inconsistent from the page's perspective (the underlying CRUD functions were already proven atomic-per-call in Plan 02-03).
- `src/app.py` now imports `render_profile_page`, builds `profile_page = st.Page(render_profile_page, title="Investor Profile", url_path="profile")`, and adds it to `st.navigation({"Home": [home_page], "Profile": [profile_page]})` — the logged-out `st.navigation([login_page])` branch is untouched, so the page is entirely absent from nav (not visible-but-redirecting) until login, per D-03/Pattern 5.

## Task Commits

Each task was committed atomically:

1. **Task 1: Investor profile page — scalar form + holdings grid + validation + save** — `7649a89` (feat)
2. **Task 2: Register the profile page in app navigation** — `883eb34` (feat)

## Files Created/Modified

- `src/pages/profile.py` — the profile builder page (created)
- `src/app.py` — registers `profile_page` in the logged-in navigation branch (modified)

## Decisions Made

- Reused `login.py`'s copy-constants-not-inline-strings and CSS-injection (`_highlight_empty_fields`-style) patterns verbatim rather than introducing a new styling approach for this page.
- Widget-level (not per-row) CSS highlight for the holdings editor: `st.data_editor` exposes only its own `key=` as a CSS hook, not a per-cell/per-row one — this is a deliberate, capability-driven adaptation of the UI-SPEC's per-row intent, called out explicitly in the plan's `must_haves` rather than silently narrowed.
- `pd.isna()` is used (not a truthy `or ""` check) to detect blank ticker/quantity/cost-basis cells, since pandas' `NaN` is a truthy Python value and a naive `value or ""` check would incorrectly turn a blank numeric cell into the literal string `"nan"`.

## Deviations from Plan

None — plan executed exactly as written. The `pd.isna()` handling above is an implementation detail within Task 1's own `<action>` instructions (which specify "skipping any row with a blank/empty ticker") rather than a deviation from what was planned.

## Known Stubs

None — every field in the scalar form and every column in the holdings grid is wired directly to `src/data/profile.py`'s live CRUD functions; no placeholder/mock data path exists on this page.

## Threat Flags

None — the one new surface this plan introduces (the CSS-injection highlight, T-02-05 in the plan's own threat model) only ever interpolates the static, developer-controlled string `"holdings_editor"` into `unsafe_allow_html`, never a raw ticker or other user-entered value, matching `login.py`'s existing discipline exactly. No other new network endpoint, auth path, or schema change is introduced by this plan.

## Issues Encountered

None. The local Supabase CLI stack was already running from Plan 02-03; the full test suite (54 tests across `tests/`) passed unaffected after this plan's changes, since this plan added no new test files (it is a UI plan consuming Plan 02-03's already-proven CRUD chokepoint) — automated verification here is the grep/AST structural checks specified in the plan itself plus a full-suite regression run.

## User Setup Required

None for automated verification. Task 2's `<human-check>` block (manual sign-in → fill → save → validate-rejection → reload → edit → delete-row walkthrough) is intentionally deferred to this project's end-of-phase UAT pass, per `workflow.human_verify_mode: end-of-phase` — not exercised as a blocking mid-phase checkpoint during this plan's execution.

## Next Phase Readiness

Phase 2's only UI surface (PROFILE-01/PROFILE-02) is now fully wired end-to-end: schema (02-01) → CRUD (02-03) → page (02-04). Combined with the feature-engineering pipeline from 02-02, Phase 2 is functionally complete pending the end-of-phase human-verify UAT pass on this page. No blockers identified for Phase 3 (recommendation engine), which can now assume both a persisted investor profile and a point-in-time feature pipeline exist.

---
*Phase: 02-investor-profile-feature-engineering-foundation*
*Completed: 2026-07-20*

## Self-Check: PASSED

- FOUND: src/pages/profile.py
- FOUND: src/app.py (modified)
- FOUND: commit 7649a89
- FOUND: commit 883eb34
