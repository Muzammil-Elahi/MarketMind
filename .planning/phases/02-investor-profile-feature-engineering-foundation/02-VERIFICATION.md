---
phase: 02-investor-profile-feature-engineering-foundation
verified: 2026-08-03T00:00:00Z
status: passed
score: 14/14 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 2: Investor Profile & Feature Engineering Foundation Verification Report

**Phase Goal:** Extend the Supabase schema with investor-profile and holdings data, build a pure zero-I/O feature engineering module with a proven no-lookahead-bias guarantee, build the profile/holdings CRUD chokepoint, and ship the investor profile builder UI page.
**Verified:** 2026-08-03T00:00:00Z
**Status:** passed
**Re-verification:** Yes — canonicalized after `02-UAT.md` human verification pass (4/4 tests passed, 0 issues) closed out the 2 previously behavior-unverified truths (Truth #2 PROFILE-02 reload, Truth #13 CR-01). The 2026-08-03 project rename commit (`a326d13`) touched only a cosmetic Docker container-name string inside `02-01-SUMMARY.md`'s verification ref (`supabase_db_Popcorn-Pilot` → `supabase_db_MarketMind`); no functional or test-content change, confirmed via `git show a326d13 -- 02-01-SUMMARY.md`.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can complete a profile form (risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, holdings) that saves to Supabase (ROADMAP SC1) | ✓ VERIFIED | `src/pages/profile.py` renders all fields via `st.form`; `src/data/profile.py`'s `upsert_profile`/`upsert_holdings` persist to live schema; `tests/test_profile_crud.py::test_upsert_profile_and_fetch_profile_round_trip_all_scalar_fields` + `test_upsert_holdings_round_trip_...` pass against the live local Supabase stack (confirmed via full-suite run below) |
| 2 | User can edit their profile and see updated values reflected immediately on reload, no stale cache (ROADMAP SC2 / PROFILE-02) | ✓ VERIFIED | Structural: no `@st.cache_data`/`@st.cache_resource` anywhere in `src/data/profile.py` (`test_fetch_profile_has_no_cache_data_decorator` passes); `fetch_profile`/`fetch_holdings` called fresh at top of every `render_profile_page()` render. Runtime reload/rerun behavior confirmed by human UAT — `02-UAT.md` Test 1 (2026-08-03), passed |
| 3 | Feature engineering module computes technical/factor features using only point-in-time data; automated leakage smoke test fails if any feature uses future information (ROADMAP SC3) | ✓ VERIFIED | `tests/test_features_leakage.py` — `test_truncation_invariance_no_future_data_changes_past_features` and the WR-03-rewritten `test_synthetic_future_signal_never_appears_before_its_source_date` (perturbs a real future `Close` value and asserts pre-perturbation rows are byte-identical) both pass |
| 4 | The same feature-computation functions serve both a future backtest harness and live inference with no duplicated logic (ROADMAP SC4) | ✓ VERIFIED | `src/features/feature_frame.py`'s `assemble_feature_frame()` is the only place that assembles features, calling only `technical.py` functions; no other file in the repo reimplements rolling-window logic |
| 5 | `public.holdings` exists as an owner-scoped child table (not jsonb) with 4-policy RLS + GRANTs, live on Postgres | ✓ VERIFIED | Live `psql` query: `relrowsecurity=true`, `pg_policies` count=4, `role_table_grants` shows `authenticated` has SELECT/INSERT/UPDATE/DELETE and `service_role` has full grants on `holdings`; migration file matches |
| 6 | All 6 new `profiles` columns are nullable, no DEFAULT — `handle_new_user()`'s trigger insert still succeeds | ✓ VERIFIED | Live `psql` query confirms all 6 columns exist; migration file has no `not null`/`default` on any of them; full test suite (including Phase 1's auth/signup tests) still passes |
| 7 | `src/data/profile.py` CRUD functions use a fresh scoped client per call (never the shared cache_resource client) | ✓ VERIFIED | `_scoped_client()` helper (post WR-02 fix) used by all 4 CRUD functions; code read confirms `create_client(...)` + `.postgrest.auth(access_token)` pattern matching `_touch_last_login` |
| 8 | `upsert_profile` always issues UPDATE, never INSERT/upsert; idempotent under double-submit | ✓ VERIFIED | Code contains only `.update(payload).eq("user_id", ...)`, no `.upsert(`/`.insert(` on `profiles`; `test_upsert_profile_uses_update_never_insert_for_profiles` (structural) and `test_double_upsert_profile_is_idempotent` (row-count proof via service-role client) both pass |
| 9 | `upsert_holdings` resists mass-assignment (spoofed `user_id` in row payload can't override real ownership) | ✓ VERIFIED | Code explicitly extracts `ticker`/`quantity`/`cost_basis` per row; `test_upsert_holdings_ignores_spoofed_user_id_in_row_payload` passes (a genuine attack-scenario test, not just a structural check) |
| 10 | `validate_ticker` flags genuinely-invalid tickers, fails open on transient exceptions | ✓ VERIFIED | 4 mocked tests in `tests/test_ticker_validation.py` all pass, covering live-nonempty/live-empty/exception/period="5d" call-shape |
| 11 | Cross-user access to another user's holdings is blocked at the Postgres RLS layer (not app-layer), proven by a real 2-user test | ✓ VERIFIED | `tests/test_holdings_rls.py` (4 tests: cross-select zero rows, cross-insert raises, cross-delete zero-affected, same-user positive control) all pass against the live stack |
| 12 | Investor Profile page is entirely absent from nav for a logged-out user, only reachable after `require_auth()` | ✓ VERIFIED | `src/app.py`: `profile_page` only appears inside the `if st.session_state.get("logged_in")` branch; the `else` branch (`st.navigation([login_page])`) is untouched; `render_profile_page()`'s first statement is `require_auth()` |
| 13 | CR-01 fix: a holdings row with missing `quantity` can never wipe existing holdings via delete-then-crash | ✓ VERIFIED | Code read confirms two layers: (a) `src/pages/profile.py` returns before any CRUD call if a row has a ticker but blank quantity; (b) `src/data/profile.py`'s `upsert_holdings` validates every payload's `quantity is not None` and raises `ValueError` *before* calling `delete()`. Runtime scenario confirmed by human UAT — `02-UAT.md` Test 2 (2026-08-03), passed |
| 14 | WR-01 fix: unsaved scalar-field edits survive a validation-failure rerun (don't reset to stale DB values) | ✓ VERIFIED | Code confirms every scalar widget now has a stable `key=` seeded into `st.session_state` only once. Runtime rerun behavior confirmed by human UAT — `02-UAT.md` Test 3 (2026-08-03), passed |

**Score:** 14/14 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql` | profiles extension (6 nullable cols) + holdings table + RLS (4 policies) + GRANTs | ✓ VERIFIED | Exists, applied live, confirmed via direct `psql` query (not just file inspection) |
| `src/features/technical.py` | `compute_returns`/`compute_volatility`/`compute_sma`/`compute_rsi` — pure, zero-I/O | ✓ VERIFIED | All 4 functions present with correct signatures; no `center=True`/`.shift(-`/`import streamlit` |
| `src/features/feature_frame.py` | `assemble_feature_frame(df)` single shared entry point | ✓ VERIFIED | Present, calls only `technical.py` functions, returns exactly 4 named columns |
| `src/features/__init__.py` | package marker documenting zero-I/O boundary | ✓ VERIFIED | Present, docstring + re-export of `assemble_feature_frame` |
| `src/data/profile.py` | `fetch_profile`/`upsert_profile`/`fetch_holdings`/`upsert_holdings`/`validate_ticker` chokepoint | ✓ VERIFIED | All 5 functions present, importable, scoped-client discipline confirmed |
| `src/pages/profile.py` | `render_profile_page()` — auth-gated builder UI | ✓ VERIFIED | Present, calls `require_auth()` first, renders all required fields + holdings grid, exact Copywriting Contract strings present |
| `src/app.py` (modified) | `profile_page` registered in logged-in nav branch only | ✓ VERIFIED | Confirmed by direct read |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| migration file | live local Postgres | `npx supabase migration up` | ✓ WIRED | Confirmed via direct `psql` queries against `information_schema.columns`, `pg_class`, `pg_policies`, `role_table_grants` |
| `feature_frame.py` | `technical.py` | `assemble_feature_frame()` calls `compute_returns`/`compute_volatility`/`compute_sma`/`compute_rsi` | ✓ WIRED | Code confirms all 4 calls, no reimplementation |
| `src/data/profile.py` | `src/data/prices.py` | `validate_ticker()` calls `fetch_ohlcv(ticker, period="5d")` | ✓ WIRED | Import + call confirmed; mocked tests assert exact call shape |
| `src/data/profile.py` | Supabase Postgres | `_scoped_client()` builds `create_client()` + `.postgrest.auth(access_token)` per call | ✓ WIRED | Confirmed in all 4 CRUD functions |
| `src/app.py` | `src/pages/profile.py` | `st.navigation(...)` includes `profile_page` only in logged-in branch | ✓ WIRED | Confirmed by direct read |
| `src/pages/profile.py` | `src/data/profile.py` | Direct function calls with `access_token`/`user_id` | ✓ WIRED | Confirmed; also verified `src.features` is never imported in `src/pages/profile.py` (prohibition honored) |
| `src/pages/profile.py` | `src/auth/session.py` | `require_auth()` called first | ✓ WIRED | Confirmed |

### Behavioral Spot-Checks / Test Execution

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full project test suite (single run, not per-truth) | `python -m pytest tests/ -q` | `54 passed, 96 warnings in 125.28s` | ✓ PASS |
| `pandas_ta_classic` importable | `python -c "import pandas_ta_classic"` | exit 0 | ✓ PASS |
| `src.data.profile` importable with all 5 functions | `python -c "from src.data.profile import ..."` | exit 0 | ✓ PASS |
| Live schema: 6 profiles columns | `docker exec ... psql ... information_schema.columns` | `6` | ✓ PASS |
| Live schema: holdings RLS enabled | `psql ... pg_class.relrowsecurity` | `t` | ✓ PASS |
| Live schema: holdings 4 policies | `psql ... pg_policies` count | `4` | ✓ PASS |
| Live schema: holdings GRANTs | `psql ... role_table_grants` | authenticated: SELECT/INSERT/UPDATE/DELETE; service_role: full | ✓ PASS |
| No debt markers (TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER) in phase-modified files | `grep -niE "..." <files>` | no matches | ✓ PASS |
| No gain/loss/portfolio-performance computation (prohibition) | `grep -rniE "gain.?loss\|portfolio.?performance\|exposure.?overlap" src/data/profile.py src/pages/profile.py src/features/` | no matches | ✓ PASS |
| No `src.features` import in `src/pages/profile.py` (prohibition) | `grep -n "src.features" src/pages/profile.py` | no matches | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|---|---|---|---|---|
| PROFILE-01 | 02-01, 02-02, 02-03, 02-04 | User can build an investor profile (risk tolerance, time horizon, sectors, asset types, capital, holdings) | ✓ SATISFIED | Schema + CRUD + UI page all present and wired; 54/54 tests pass including live-stack round-trip tests |
| PROFILE-02 | 02-03, 02-04 | User can edit profile after creation, see updates reflected (recommendations-update clause deferred to Phase 3 per ROADMAP scoping) | ✓ SATISFIED | Idempotency/no-duplicate-row proven by test; "reflected immediately, no stale cache" on an actual browser reload confirmed by human UAT — `02-UAT.md` Test 1 (2026-08-03), passed |

No orphaned requirements found — REQUIREMENTS.md maps only PROFILE-01/PROFILE-02 to Phase 2, and both appear in plan frontmatter `requirements` fields.

### Anti-Patterns Found

None found. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no stub return patterns, no hardcoded-empty-data patterns in any phase-modified file.

### Human Verification Required

None outstanding. All 4 items below were carried forward from the initial verification pass (2026-07-20) and closed out by `02-UAT.md`'s human UAT session (2026-08-03, 4/4 tests passed, 0 issues):

1. **PROFILE-02 end-to-end save/reload walkthrough** — `02-UAT.md` Test 1, passed.
2. **CR-01 fix confirmation** (missing-quantity row must not delete existing holdings) — `02-UAT.md` Test 2, passed.
3. **WR-01 fix confirmation** (unsaved scalar-field edits survive a validation-failure rerun) — `02-UAT.md` Test 3, passed.
4. **Minor visual/UX backstop items** (near-instant loads, malformed-ticker cell display, last-write-wins concurrent edits explicitly out of scope for v1) — `02-UAT.md` Test 4, passed.

### Gaps Summary

No gaps found. All ROADMAP Phase 2 success criteria and PLAN must-haves have verified automated evidence (schema live-queried, 54/54 tests passing, structural code confirmation) plus human UAT confirmation for the 4 runtime/UI behaviors this codebase has no automated harness to exercise (no Streamlit AppTest usage). The phase's one Critical code-review finding (CR-01) and all 3 Warning findings (WR-01/02/03) were fixed and re-verified by the review-fix pass, with commits confirmed present in git history (9a8a50c, ac9eb2a, 9a73a0c, 428293b), and CR-01/WR-01's runtime behavior is now human-confirmed via UAT. Phase security threat register (6/6 threats, `02-SECURITY.md`) is fully closed at ASVS L1.

---

_Verified: 2026-08-03T00:00:00Z_
_Verifier: Claude (gsd-verifier, canonicalized post-UAT per verify-work workflow)_
