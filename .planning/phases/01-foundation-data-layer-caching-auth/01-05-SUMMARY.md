---
phase: 01-foundation-data-layer-caching-auth
plan: 05
subsystem: testing
tags: [supabase, auth, rls, apptest, cache_resource, pytest, postgrest]

# Dependency graph
requires:
  - phase: 01-foundation-data-layer-caching-auth (Plan 01)
    provides: "public.profiles table + RLS policies + handle_new_user() trigger + running local Supabase CLI stack"
  - phase: 01-foundation-data-layer-caching-auth (Plan 02)
    provides: "src/auth/session.py (sign_up, sign_in, require_auth, sign_out, _touch_last_login), src/data/supabase_client.py (get_supabase_client), tests/conftest.py (supabase_env, test_user_factory)"
  - phase: 01-foundation-data-layer-caching-auth (Plan 04)
    provides: "src/pages/home.py (render_home_page(), require_auth()-gated), src/app.py entrypoint"
provides:
  - "tests/test_auth_isolation.py: real cache_resource-leak-vector proof (D-05) via AppTest, not session_state comparison"
  - "tests/apptest_scripts/home_page_target.py: thin AppTest target script exercising the real require_auth()/render_home_page() code path"
  - "tests/test_profile_persistence.py: AUTH-02 cross-session persistence + last_login write proof + insert-idempotency proof"
  - "tests/test_rls_policy.py: AUTH-03 database-level RLS enforcement proof (positive + negative control)"
  - "tests/conftest.py: two_users fixture (two distinct real users)"
  - "Critical bug fix in src/auth/session.py: every authenticating call now routed through a short-lived scoped client, never the shared cache_resource client"
  - "supabase/migrations/20260719001207_grant_profiles_service_role.sql: service_role table grant (bug fix, self-managed local stack gap)"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "AppTest.from_file() against a thin test-only wrapper script for function-based (st.Page) pages that have no top-level script execution of their own"
    - "st.cache_resource default scope='global' backs onto a single process-wide cache (ResourceCaches, keyed with no session id) independent of AppTest's per-run mocked Runtime -- calling the cached function directly from the test process after an AppTest run observes the exact same object the AppTest run resolved"
    - "_scoped_client() helper in src/auth/session.py: every authenticating GoTrue call (sign_up, sign_in_with_password, sign_in_with_otp, refresh_session) must go through a fresh, uncached create_client() -- never the shared get_supabase_client() -- because each of those calls internally persists/removes a session on whatever client instance invokes them"
    - "sign_out() uses the stateless admin.sign_out(access_token, scope) call (explicit token) instead of the stateful auth.sign_out() wrapper, which depends on get_session() finding a token on the calling client"
    - "service-role-keyed client for test-only direct-table operations that must bypass RLS to isolate a specific guarantee (e.g. PK uniqueness) from a different guarantee (RLS filtering) tested elsewhere"

key-files:
  created:
    - tests/test_auth_isolation.py
    - tests/apptest_scripts/home_page_target.py
    - tests/test_profile_persistence.py
    - tests/test_rls_policy.py
    - supabase/migrations/20260719001207_grant_profiles_service_role.sql
  modified:
    - tests/conftest.py
    - src/auth/session.py

key-decisions:
  - "Critical bug found and fixed: sign_up()/sign_in()/sign_in_with_magic_link() and require_auth()'s refresh branch all called authenticating GoTrue methods directly on the shared, st.cache_resource-decorated get_supabase_client() instance. sign_in_with_password()/sign_up()/sign_in_with_otp()/refresh_session() all internally call _save_session()/_remove_session() on whichever client invokes them -- so every sign-in/sign-up was persisting (or wiping another in-flight user's) session onto the supposedly-stateless shared client, in direct violation of supabase_client.py's own documented contract and exactly the T-01-01 leak this phase's threat model exists to prevent. Fixed by routing every authenticating call through a new _scoped_client() helper (a fresh, uncached create_client()), mirroring the already-established _touch_last_login pattern."
  - "sign_out() switched from the stateful auth.sign_out() wrapper (which relies on get_session() finding a token on the client it's called on) to the stateless admin.sign_out(access_token, scope) call, passing the token explicitly from st.session_state -- required once the shared client no longer ever has a session attached, otherwise sign_out() would silently stop revoking sessions server-side."
  - "test_duplicate_insert_for_existing_user_id_raises_unique_violation uses a service-role-keyed PostgREST client for the direct table INSERT, not a raw psycopg2/Postgres connection over SUPABASE_DB_URL, to avoid introducing a new pip dependency (Rule 3's package-install exclusion) while still proving a genuine Postgres-level unique_violation (error code 23505) independent of RLS/app code -- RLS enforcement itself is proven separately in test_rls_policy.py."
  - "AppTest verified (via git stash push/pop) to actually catch the leak: both new isolation tests were run against the pre-fix code and failed as expected, then passed after the fix -- confirming the tests are real proofs, not trivially-passing checks (the exact failure mode D-05/Pitfall 3 warns against)."

patterns-established:
  - "Any function that performs an authenticating Supabase Auth call must route through a short-lived, uncached client -- never the shared get_supabase_client() cache_resource instance -- documented now at the top of src/auth/session.py for future auth-related modules (e.g. OAuth, if ever added) to follow."

requirements-completed: [AUTH-02, AUTH-03]

coverage:
  - id: D1
    description: "tests/test_auth_isolation.py exercises the real require_auth()/get_supabase_client() code path via AppTest for two distinct real users and asserts on the shared cache_resource client object itself (get_session() is None, same instance across runs) rather than session_state comparison -- covers both the normal get_user() path and the refresh_session() path"
    requirement: "AUTH-03"
    verification:
      - kind: integration
        ref: "tests/test_auth_isolation.py::test_shared_client_carries_no_identity_across_two_real_user_sessions, ::test_shared_client_carries_no_identity_after_refresh_token_path"
        status: pass
    human_judgment: false
  - id: D2
    description: "Critical fix: sign_up/sign_in/sign_in_with_magic_link/require_auth's refresh branch route every authenticating call through a short-lived scoped client, never the shared cache_resource client; sign_out() uses the stateless admin.sign_out(access_token, scope) call"
    requirement: "AUTH-03"
    verification:
      - kind: integration
        ref: "tests/test_auth_isolation.py (both tests fail against the pre-fix code, pass after the fix, per manual git-stash verification); tests/test_auth_flow.py (all 14 pre-existing tests still pass)"
        status: pass
    human_judgment: false
  - id: D3
    description: "tests/test_profile_persistence.py proves profiles row auto-provisioned by trigger with last_login null post-signup, last_login persists across a simulated new-session re-authentication and advances strictly on each sign_in(), and a duplicate INSERT for an existing user_id raises a Postgres unique_violation"
    requirement: "AUTH-02"
    verification:
      - kind: integration
        ref: "tests/test_profile_persistence.py::test_profile_row_auto_provisioned_by_trigger_with_last_login_null, ::test_last_login_persists_across_new_session_and_advances_on_each_sign_in, ::test_duplicate_insert_for_existing_user_id_raises_unique_violation"
        status: pass
    human_judgment: false
  - id: D4
    description: "tests/test_rls_policy.py proves cross-user SELECT/UPDATE against another user's profiles row return/affect zero rows, and same-user SELECT/UPDATE succeed (positive control)"
    requirement: "AUTH-03"
    verification:
      - kind: integration
        ref: "tests/test_rls_policy.py::test_cross_user_select_returns_zero_rows, ::test_cross_user_update_affects_zero_rows, ::test_same_user_select_and_update_succeed_positive_control"
        status: pass
    human_judgment: false
  - id: D5
    description: "Full phase test suite (Plans 02, 03, 05 combined) passes in one run"
    verification:
      - kind: integration
        ref: "pytest tests/ -v -- 29 passed"
        status: pass
    human_judgment: false

duration: 40min
completed: 2026-07-19
status: complete
---

# Phase 1 Plan 5: Session Isolation, Persistence & RLS Proof Summary

**Real AppTest-driven cache_resource leak-vector proof (D-05) uncovered and fixed a critical bug where every sign-up/sign-in persisted one user's session onto the shared, supposedly-stateless Supabase client; plus AUTH-02 cross-session/last_login/idempotency proofs and AUTH-03 database-level RLS proofs -- full 29-test phase suite green.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-07-18T23:50:00-04:00 (approx.)
- **Completed:** 2026-07-19T00:15:16-04:00
- **Tasks:** 2
- **Files modified:** 7 (5 created, 2 modified)

## Accomplishments
- Discovered and fixed a critical, real cross-user session leak in `src/auth/session.py`: `sign_up()`, `sign_in()`, `sign_in_with_magic_link()`, and `require_auth()`'s refresh branch all called authenticating GoTrue methods (`sign_up`, `sign_in_with_password`, `sign_in_with_otp`, `refresh_session`) directly on the shared, `st.cache_resource`-decorated `get_supabase_client()` instance -- each of those calls internally persists (or wipes another user's) session on whatever client invokes them, in direct violation of `supabase_client.py`'s own documented "never call an authenticating method on the shared client" contract. Fixed by introducing `_scoped_client()` and routing every authenticating call through it; `sign_out()` switched to the stateless `admin.sign_out(access_token, scope)` call.
- `tests/test_auth_isolation.py`: proves D-05 for real -- two distinct real users driven through the actual `require_auth()`/`get_supabase_client()` code path via `AppTest.from_file()` (against a thin wrapper script, `tests/apptest_scripts/home_page_target.py`, since `render_home_page()` is a function-based page with no top-level script execution). Asserts on the shared client object itself (`get_session()` returns `None`, same instance across runs) rather than `session_state` comparison -- exactly the distinction RESEARCH.md's Pitfall 3 requires. Verified (via temporary `git stash` of the fix) that both tests genuinely fail against the pre-fix buggy code and pass after the fix.
- `tests/test_profile_persistence.py`: proves the `profiles` row is auto-provisioned by the `handle_new_user()` trigger (not app code) with `last_login` null post-signup, that the row persists and `last_login` populates/advances across a simulated new-session re-authentication, and that a direct duplicate INSERT for an existing `user_id` raises a genuine Postgres `unique_violation` (23505) via a service-role-keyed client.
- `tests/test_rls_policy.py`: proves cross-user SELECT/UPDATE against another user's `profiles` row return/affect zero rows via an anon-key client scoped to the querying user's own token, with a same-user positive control proving the policy filters rather than blocks everything.
- Full phase test suite: `pytest tests/ -v` -- 29 tests passing in one run across Plans 02 (`test_auth_flow.py`), 03 (`test_cache.py`), and 05 (this plan's four new test files).

## Task Commits

Each task was committed atomically:

1. **Task 1: Two-concurrent-session isolation test (the real leak vector)** - `519bf15` (test) -- includes the `src/auth/session.py` bug fix, found while implementing this task's isolation test
2. **Task 2: Cross-session persistence, insert idempotency, and RLS enforcement** - `05cab98` (test) -- includes the `service_role` grant migration bug fix, found while implementing the idempotency test

**Plan metadata:** pending (docs: complete plan, this commit)

## Files Created/Modified
- `tests/test_auth_isolation.py` - real cache_resource leak-vector proof (D-05), two tests covering the normal `get_user()` path and the `refresh_session()` path
- `tests/apptest_scripts/home_page_target.py` - thin AppTest target script wrapping `require_auth()`/`render_home_page()`
- `tests/test_profile_persistence.py` - AUTH-02 cross-session persistence, last_login write, and insert-idempotency proofs
- `tests/test_rls_policy.py` - AUTH-03 database-level RLS enforcement proof (positive + negative control)
- `tests/conftest.py` - added `two_users` fixture (two distinct real users)
- `src/auth/session.py` - critical fix: `_scoped_client()` helper; every authenticating call routed through it; `sign_out()` uses stateless `admin.sign_out()`
- `supabase/migrations/20260719001207_grant_profiles_service_role.sql` - `grant all on public.profiles to service_role` (bug fix)

## Decisions Made
- Every authenticating Supabase Auth call (sign-up, sign-in, magic-link, refresh) must go through a short-lived, uncached client -- never the shared `get_supabase_client()` -- because GoTrue's `sign_in_with_password`/`sign_up`/`sign_in_with_otp`/`refresh_session` all internally call `_save_session()`/`_remove_session()` on whichever client instance invokes them. This is now documented at the top of `src/auth/session.py` as a hard constraint for any future auth-related code (e.g. OAuth, if ever added).
- `test_duplicate_insert_for_existing_user_id_raises_unique_violation` uses a service-role-keyed PostgREST client instead of a raw `psycopg2` connection over `SUPABASE_DB_URL`, avoiding a new pip dependency (Rule 3's package-install exclusion) while still proving a genuine Postgres-level `unique_violation` independent of RLS.
- Verified both new isolation tests are real proofs, not trivially-passing checks, by temporarily reverting the `src/auth/session.py` fix (`git stash push`/`git stash pop` on that single file, not a worktree operation) and confirming both tests failed against the pre-fix code before restoring the fix and confirming they pass.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Critical Bug, T-01-01] Every authenticating Supabase Auth call was made on the shared, cache_resource client**
- **Found during:** Task 1, while designing `test_auth_isolation.py`'s assertions on the shared client object
- **Issue:** `sign_up()`, `sign_in()`, and `sign_in_with_magic_link()` called `get_supabase_client().auth.sign_up(...)` / `.sign_in_with_password(...)` / `.sign_in_with_otp(...)` directly on the shared, process-wide `st.cache_resource` client. `require_auth()`'s refresh branch similarly called `get_supabase_client().auth.refresh_session(...)`. Inspecting the installed `supabase-auth==2.31.0` source confirmed all four of these GoTrue methods internally call `self._save_session(...)` (or `self._remove_session()` first) on the client instance they're invoked on -- meaning every sign-in/sign-up/magic-link/refresh call persisted that user's session onto the shared client (or wiped whatever was there from a different in-flight user), directly contradicting `src/data/supabase_client.py`'s own documented contract ("Do NOT invoke any authenticating auth-module method ... on the client returned by this module") and the exact leak class T-01-01/D-05 exist to prevent.
- **Fix:** Added `_scoped_client()` to `src/auth/session.py` (a fresh, uncached `create_client()` per call), and routed `sign_up`, `sign_in`, `sign_in_with_magic_link`, and `require_auth`'s refresh branch through it. `sign_out()` was updated to call the stateless `get_supabase_client().auth.admin.sign_out(access_token, scope)` (passing the token explicitly from `st.session_state`) instead of the stateful `auth.sign_out()` wrapper, which depends on `get_session()` finding a token on the client it's called on -- a dependency that silently breaks once the shared client never has a session attached.
- **Files modified:** `src/auth/session.py`
- **Verification:** All 14 pre-existing `tests/test_auth_flow.py` tests still pass unchanged; both new `tests/test_auth_isolation.py` tests pass after the fix and were confirmed (via temporary `git stash` of the fix) to fail against the pre-fix code, proving the tests genuinely catch this exact leak class.
- **Committed in:** `519bf15` (Task 1 commit)

**2. [Rule 1 - Bug] `service_role` had zero table grants on `public.profiles` on this self-managed local stack**
- **Found during:** Task 2, first run of `test_duplicate_insert_for_existing_user_id_raises_unique_violation`
- **Issue:** A service-role-keyed client's INSERT (needed to isolate the PK unique-violation proof from RLS/grant questions) failed with `permission denied for table profiles` (42501) rather than reaching the constraint check -- the local Supabase CLI stack, unlike hosted Supabase Cloud, does not auto-grant `service_role` any table privileges (the same gap class Plan 02 found and fixed for the `authenticated` role).
- **Fix:** Added `supabase/migrations/20260719001207_grant_profiles_service_role.sql` (`grant all on public.profiles to service_role;`), generated via `npx supabase migration new` and applied via `npx supabase migration up`. `service_role` is never loaded into the deployed app (Pitfall 5) -- this grant only affects test-only direct-table access.
- **Files modified:** `supabase/migrations/20260719001207_grant_profiles_service_role.sql`
- **Verification:** `pytest tests/test_profile_persistence.py -x -q` -- all 3 tests pass after applying the grant.
- **Committed in:** `05cab98` (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 critical security bug fix, 1 environment/grant bug fix)
**Impact on plan:** The session-leak fix was necessary for AUTH-03's isolation guarantee to hold at all -- without it, this phase's central security proof would have been false (the isolation test would have failed, correctly). The service_role grant fix was necessary for the insert-idempotency test to isolate the PK constraint from RLS/grants. No scope creep -- no functionality was added beyond what the plan's own acceptance criteria required.

## Issues Encountered
- None beyond the two deviations documented above.

## User Setup Required
None - no external service configuration required. All tests run against the local Supabase CLI Docker stack already running from Plan 01.

## Next Phase Readiness
- Phase 1's five ROADMAP success criteria (AUTH-01 through AUTH-03, cache resilience) are now proven end-to-end by 29 passing automated tests against the live local Supabase stack -- no mocking anywhere in the suite.
- The critical session-leak fix in `src/auth/session.py` is the single most important outcome of this plan: had it shipped as originally written (from Plan 02), every concurrent user session in production would have silently corrupted the shared client's internal auth state. This is now structurally prevented and proven by a real (not trivially-passing) test.
- `_scoped_client()`'s pattern (fresh, uncached client for every authenticating call) is now the established template any future auth-related module (e.g. Phase 2's investor-profile writes, or any OAuth addition) must follow.
- No blockers for Phase 2.

---
*Phase: 01-foundation-data-layer-caching-auth*
*Completed: 2026-07-19*

## Self-Check: PASSED

All created/modified files verified present on disk (`tests/test_auth_isolation.py`, `tests/apptest_scripts/home_page_target.py`, `tests/test_profile_persistence.py`, `tests/test_rls_policy.py`, `supabase/migrations/20260719001207_grant_profiles_service_role.sql`, `tests/conftest.py`, `src/auth/session.py`); commits `519bf15` and `05cab98` verified present in `git log`.
