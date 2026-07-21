---
phase: 02-investor-profile-feature-engineering-foundation
fixed_at: 2026-07-21T02:10:16Z
review_path: .planning/phases/02-investor-profile-feature-engineering-foundation/02-REVIEW.md
iteration: 1
findings_in_scope: 4
fixed: 4
skipped: 0
status: all_fixed
---

# Phase 02: Code Review Fix Report

**Fixed at:** 2026-07-21T02:10:16Z
**Source review:** .planning/phases/02-investor-profile-feature-engineering-foundation/02-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 4 (Critical + Warning; Info findings IN-01/IN-02/IN-03 out of scope per `fix_scope: critical_warning`)
- Fixed: 4
- Skipped: 0

## Fixed Issues

### CR-01: Holdings save can silently delete a user's holdings with no rollback and no error shown

**Files modified:** `src/pages/profile.py`, `src/data/profile.py`
**Commit:** 9a8a50c
**Applied fix:** Two layers of defense, matching the review's "Fix" guidance:
1. `src/pages/profile.py` — the row-building loop that already skipped blank-ticker rows now also detects a blank `quantity` on a row with a non-blank ticker, collects those tickers, and surfaces a field-level `st.error` (`Quantity is required for "{ticker}".`) plus the existing red-border highlight, returning *before* either `upsert_profile` or `upsert_holdings` is called — mirroring the existing invalid-ticker validation pattern exactly.
2. `src/data/profile.py`'s `upsert_holdings` now builds and validates every insert payload (`quantity is not None`) *before* issuing the `delete()`, raising `ValueError` on a bad row. This is deliberate defense-in-depth: even if a future caller bypasses the new UI-level check, the CRUD chokepoint itself can no longer delete a user's rows and then crash on the subsequent insert.

Verified via full 3-tier check: re-read both files (fix present, surrounding code intact), `python -c "import ast; ast.parse(...)"` passed on both files, and per the task's explicit instruction, the live-Supabase-stack integration suites were run (`tests/test_profile_crud.py`, `tests/test_holdings_rls.py`, `tests/test_ticker_validation.py` — 14 passed) plus the full project suite afterward (54 passed, 0 failed).

### WR-01: Scalar profile-form widgets have no `key=`, so unsaved edits are silently discarded on a validation-failure rerun

**Files modified:** `src/pages/profile.py`
**Commit:** ac9eb2a
**Applied fix:** Gave every scalar widget (`risk_tolerance`, `time_horizon`, `preferred_sectors`, `excluded_sectors`, each asset-type checkbox, `capital`) a stable, distinct `st.session_state` key, seeded from the DB-fetched `profile` dict only the first time each key is seen (`if "profile_x" not in st.session_state: st.session_state["profile_x"] = ...`). This matches the already-keyed `holdings_editor` widget's behavior: on a rerun triggered by a validation failure elsewhere on the page (invalid ticker or, after the CR-01 fix, missing quantity), every field now retains whatever the user had just entered instead of resetting to stale DB-persisted values.

**Note — flagged for human verification:** per the verifier's logic-bug guidance, this fix changes multi-widget state-management behavior across a Streamlit rerun, which cannot be exercised by a syntax check or by the existing pytest suite (none of which drive the Streamlit widget tree). Tier 1 (re-read, fix present, code intact) and Tier 2 (`ast.parse` syntax check) both passed, and the full test suite (54 passed) shows no regression in anything currently under test, but the actual rerun-preservation behavior should be manually confirmed in a running app session before this phase proceeds to verification.

### WR-02: Repeated Supabase client-scoping boilerplate is a latent RLS-bypass risk

**Files modified:** `src/data/profile.py`
**Commit:** 9a73a0c
**Applied fix:** Extracted the repeated `create_client(...)` + `.postgrest.auth(access_token)` pair into a single `_scoped_client(access_token)` helper (mirroring `tests/test_holdings_rls.py`'s own helper of the same name/shape) and updated `fetch_profile`, `upsert_profile`, `fetch_holdings`, and `upsert_holdings` to call it instead of repeating the boilerplate inline. A future function added to this module now has a single, obvious call to make for RLS-scoped access instead of four independent copy-paste sites that could drift.

Verified: re-read file (all four call sites now use the helper, docstrings intact), `ast.parse` passed, and `tests/test_profile_crud.py` + `tests/test_holdings_rls.py` + `tests/test_ticker_validation.py` (14 passed) plus the full suite (54 passed) confirm no behavioral change.

### WR-03: Synthetic future-signal leakage test can never fail, regardless of implementation

**Files modified:** `tests/test_features_leakage.py`
**Commit:** 428293b
**Applied fix:** Took the review's second suggested option — rewrote `test_synthetic_future_signal_never_appears_before_its_source_date` to actually exercise the leakage-guard computation path instead of checking column membership (which was vacuously true for any implementation of `assemble_feature_frame`, since it never passes through arbitrary input columns). The rewritten test perturbs the real `Close` value at a single future date (`*= 1000`, an unmistakable change) and asserts every feature row dated before that date is byte-for-byte identical (`pd.testing.assert_frame_equal`) between the baseline and perturbed frames — a genuine second, independent angle on D-11 alongside the existing truncation-invariance test (which varies frame *length*, not a single future value).

Verified: re-read file, `ast.parse` passed, `tests/test_features_leakage.py` + `tests/test_features_technical.py` (10 passed) and the full suite (54 passed) confirm the rewritten test passes against the current, correct implementation.

## Skipped Issues

None — all four in-scope findings (CR-01, WR-01, WR-02, WR-03) were fixed. IN-01, IN-02, and IN-03 were out of scope for this run (`fix_scope: critical_warning`) and were not attempted.

---

_Fixed: 2026-07-21T02:10:16Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
