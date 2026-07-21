---
phase: 02-investor-profile-feature-engineering-foundation
verified: 2026-07-20T22:30:00Z
status: human_needed
score: 12/14 must-haves verified
behavior_unverified: 2
overrides_applied: 0
behavior_unverified_items:
  - truth: "User can edit their existing profile and see updated values reflected immediately on return to the profile screen (no stale cache) — ROADMAP Phase 2 SC #2 / PROFILE-02."
    test: "Sign in, save a profile with distinct scalar values, hard-reload the browser (or open the profile page in a fresh session), confirm the reloaded form pre-fills exactly the just-saved values (not a stale/empty state)."
    expected: "Every scalar field and holdings row reflects the persisted DB state on the next page load, with no visible staleness."
    why_human: "src/pages/profile.py fetches fresh (no caching decorator — confirmed structurally) and st.session_state widget-seeding-once logic (WR-01 fix) is a multi-render Streamlit session_state interaction; no Streamlit AppTest/UI test exists in this codebase to exercise a real rerun/reload cycle, so this is provable only by running the app."
  - truth: "CR-01 fix: a holdings row with a blank/missing quantity can never trigger delete()-then-crash data loss — src/pages/profile.py's pre-save guard and src/data/profile.py's upsert_holdings pre-delete validation."
    test: "As a signed-in user with existing saved holdings, add a new holdings row with only a ticker (no quantity) and click Save Profile."
    expected: "An error ('Quantity is required for \"{ticker}\".') is shown, the save is aborted before either upsert_profile or upsert_holdings runs, and reloading the page shows all pre-existing holdings intact (nothing deleted)."
    why_human: "Code inspection confirms the ordering (UI-level skip-and-return happens before any CRUD call; upsert_holdings's own validate-before-delete is a second layer) is structurally correct, but no automated test exercises this specific ordering/state-invariant end-to-end — it is exactly the scenario the Critical review finding (CR-01) was about, and no regression test was added for it."
---

# Phase 2: Investor Profile & Feature Engineering Foundation Verification Report

**Phase Goal:** Extend the Supabase schema with investor-profile and holdings data, build a pure zero-I/O feature engineering module with a proven no-lookahead-bias guarantee, build the profile/holdings CRUD chokepoint, and ship the investor profile builder UI page.
**Verified:** 2026-07-20T22:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can complete a profile form (risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, holdings) that saves to Supabase (ROADMAP SC1) | ✓ VERIFIED | `src/pages/profile.py` renders all fields via `st.form`; `src/data/profile.py`'s `upsert_profile`/`upsert_holdings` persist to live schema; `tests/test_profile_crud.py::test_upsert_profile_and_fetch_profile_round_trip_all_scalar_fields` + `test_upsert_holdings_round_trip_...` pass against the live local Supabase stack (confirmed via full-suite run below) |
| 2 | User can edit their profile and see updated values reflected immediately on reload, no stale cache (ROADMAP SC2 / PROFILE-02) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Structural: no `@st.cache_data`/`@st.cache_resource` anywhere in `src/data/profile.py` (`test_fetch_profile_has_no_cache_data_decorator` passes); `fetch_profile`/`fetch_holdings` called fresh at top of every `render_profile_page()` render. But the actual reload/rerun UI behavior is not exercised by any test — routed to Human Verification |
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
| 13 | CR-01 fix: a holdings row with missing `quantity` can never wipe existing holdings via delete-then-crash | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Code read confirms two layers: (a) `src/pages/profile.py` returns before any CRUD call if a row has a ticker but blank quantity; (b) `src/data/profile.py`'s `upsert_holdings` validates every payload's `quantity is not None` and raises `ValueError` *before* calling `delete()`. Ordering is correct on inspection, but no automated regression test exercises this specific ordering/data-loss scenario (this was the phase's one Critical review finding) — routed to Human Verification |
| 14 | WR-01 fix: unsaved scalar-field edits survive a validation-failure rerun (don't reset to stale DB values) | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Code confirms every scalar widget now has a stable `key=` seeded into `st.session_state` only once; `02-REVIEW-FIX.md` itself explicitly flags this as "cannot be exercised by pytest ... should be manually confirmed in a running app session" — routed to Human Verification per that explicit flag |

**Score:** 12/14 truths verified (2 present + wired, behavior-unverified)

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
| PROFILE-02 | 02-03, 02-04 | User can edit profile after creation, see updates reflected (recommendations-update clause deferred to Phase 3 per ROADMAP scoping) | ? NEEDS HUMAN | Idempotency/no-duplicate-row proven by test; but "reflected immediately, no stale cache" on an actual browser reload is not exercised by any automated test — see Truth #2 |

No orphaned requirements found — REQUIREMENTS.md maps only PROFILE-01/PROFILE-02 to Phase 2, and both appear in plan frontmatter `requirements` fields.

### Anti-Patterns Found

None found. No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER` markers, no stub return patterns, no hardcoded-empty-data patterns in any phase-modified file.

### Human Verification Required

### 1. PROFILE-02 end-to-end save/reload walkthrough (deferred from 02-04-PLAN Task 2's `<human-check>` block, per `workflow.human_verify_mode: end-of-phase`)

**Test:** Run `streamlit run src/app.py` with the local Supabase stack up. Log in with an existing test account. Confirm "Investor Profile" appears in nav only after login. Fill every scalar field, add two holdings rows (one valid ticker like AAPL, one invalid like ZZZZZZINVALID), click Save. Confirm the invalid-ticker error + red-border highlight appear and nothing was saved (reload — fields at prior state). Fix the ticker, save again; confirm "Profile saved." appears, page reloads with just-saved values pre-filled. Reload again (fresh visit) and confirm the same values persist. Remove a holdings row, save, confirm it's gone after reload.
**Expected:** Every step behaves as described above — this is PROFILE-02's actual "no stale cache" success criterion.
**Why human:** No Streamlit UI/AppTest framework is used in this codebase; the rerun/session_state/reload interaction cannot be exercised by pytest.

### 2. CR-01 fix confirmation — missing-quantity row must not delete existing holdings

**Test:** As a signed-in user with previously-saved holdings, add a new holdings row with only a ticker filled in (leave quantity blank), click Save Profile.
**Expected:** An error `Quantity is required for "{ticker}".` appears with the red-border highlight; nothing is saved; reloading the page shows all pre-existing holdings still present.
**Why human:** This is the exact scenario the phase's one Critical review finding (CR-01, data loss) was about. Code inspection shows the fix's ordering is correct (validate before delete, at two layers), but no automated regression test exists for this specific scenario — recommend adding one in a follow-up, but for this phase's UAT pass it should be manually confirmed.

### 3. WR-01 fix confirmation — unsaved scalar-field edits survive a validation-failure rerun

**Test:** Change risk tolerance, time horizon, and capital to new values, then also add an invalid-ticker holdings row, and click Save Profile (triggering the invalid-ticker rejection path).
**Expected:** The error appears and nothing saves, but the risk tolerance/time horizon/capital fields you just changed remain showing your new (unsaved) selections — not reset to the prior DB-persisted values.
**Why human:** `02-REVIEW-FIX.md` itself explicitly flags this fix as unable to be exercised by the pytest suite and recommends manual confirmation in a running app session before the phase proceeds to verification.

### 4. Minor visual/UX backstop items (lower priority, from 02-03/02-04 plans' own `verification: backstop` must-haves)

- Profile and holdings reads on page load are near-instant with no custom skeleton/spinner (native Streamlit rerun behavior).
- A holdings ticker cell with an unusually long or malformed entry displays acceptably via `st.data_editor`'s native fixed-width cell behavior.
- Concurrent edits to the same profile from two browser tabs are not merged/conflict-checked (last-write-wins) — explicitly accepted as out of scope for v1.

**Why human:** These were declared `verification: backstop` in the plans themselves (non-inferable from code, intended for visual/implementation-time QA), not automated-test targets.

### Gaps Summary

No gaps found. All ROADMAP Phase 2 success criteria and PLAN must-haves have either verified automated evidence (schema live-queried, 54/54 tests passing, structural code confirmation) or are explicitly routed to human verification because they are runtime/UI behaviors this codebase has no automated harness to exercise (no Streamlit AppTest usage). The phase's one Critical code-review finding (CR-01) and all 3 Warning findings (WR-01/02/03) were fixed and re-verified by the review-fix pass, with commits confirmed present in git history (9a8a50c, ac9eb2a, 9a73a0c, 428293b). Two of those fixes (CR-01's ordering guarantee and WR-01's session_state behavior) remain behavior-unverified by automated tests and are carried forward as human-verification items rather than being silently marked passed.

---

_Verified: 2026-07-20T22:30:00Z_
_Verifier: Claude (gsd-verifier)_
