---
phase: 01-foundation-data-layer-caching-auth
plan: 02
subsystem: auth
tags: [supabase, auth, gotrue, streamlit, session-state, rls, pytest]

# Dependency graph
requires:
  - phase: 01-foundation-data-layer-caching-auth (Plan 01)
    provides: "src/config.py get_config()/CACHE_TTL_SECONDS, package scaffolding, public.profiles table + RLS + auto-provisioning trigger on a running local Supabase CLI stack"
provides:
  - "get_supabase_client() — st.cache_resource-shared stateless Supabase client (src/data/supabase_client.py)"
  - "sign_up, sign_in, sign_in_with_magic_link, require_auth, sign_out — src/auth/session.py"
  - "_touch_last_login(access_token, user_id) — private helper wired into sign_in(), proves AUTH-02 Postgres CRUD via a short-lived per-call client"
  - "tests/conftest.py: supabase_env (parses `npx supabase status -o env`), test_user_factory (creates distinct real users) — reusable by Plan 05"
  - "tests/test_auth_flow.py: 14 passing tests proving AUTH-01 signup/login/duplicate-signup/magic-link/token-refresh/sign-out behavior against the live local Supabase stack"
  - "supabase/migrations/20260718211140_grant_profiles_privileges.sql: GRANT SELECT, UPDATE ON public.profiles TO authenticated (bug fix, see Deviations)"
affects: [01-04, 01-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "require_auth() as the single central server-verified auth gate (D-04): calls .auth.get_user(token), never .auth.get_session(); refresh_session() attempted once before halting"
    - "Stateless st.cache_resource client (data/supabase_client.py) vs. per-user tokens confined to st.session_state (D-06) — no authenticating call ever made on the shared client"
    - "Short-lived, uncached per-call Supabase client for authenticated writes (_touch_last_login) — never reuses the shared cache_resource client for a token-bearing request"

key-files:
  created:
    - src/data/supabase_client.py
    - src/auth/session.py
    - tests/conftest.py
    - tests/test_auth_flow.py
    - supabase/migrations/20260718211140_grant_profiles_privileges.sql
  modified: []

key-decisions:
  - "D-06 resolved: Supabase client object is st.cache_resource-shared (stateless connection); tokens live exclusively in st.session_state"
  - "require_auth() returns None (after calling st.stop()) rather than relying solely on st.stop() to halt, so the gate is unit-testable outside a running Streamlit script context (where st.stop() is a documented no-op in bare mode) while still halting real page renders"
  - "AuthApiError import path confirmed at implementation time: `from supabase_auth.errors import AuthApiError` is stable in the installed supabase-auth==2.31.0 package (RESEARCH.md Open Question 2 resolved)"

patterns-established:
  - "Pattern: any grep-based acceptance check on `.auth.sign_(in|up)` or `.auth.get_session(` must be written with prose that avoids the literal substring (e.g. 'get_session() accessor' not '.auth.get_session()') — module/function docstrings describing what NOT to call will otherwise self-trigger the very acceptance grep they document"

requirements-completed: [AUTH-01, AUTH-03]

coverage:
  - id: D1
    description: "get_supabase_client() is st.cache_resource-decorated, built from SUPABASE_URL/SUPABASE_ANON_KEY only, with no authenticating call anywhere in the module"
    requirement: "AUTH-03"
    verification:
      - kind: unit
        ref: "grep -c st.cache_resource / SUPABASE_ANON_KEY src/data/supabase_client.py; grep -Ev auth.sign_(in|up) check"
        status: pass
      - kind: integration
        ref: "python -c get_supabase_client() called twice, asserts identical object"
        status: pass
    human_judgment: false
  - id: D2
    description: "sign_up()/sign_in()/sign_in_with_magic_link()/require_auth()/sign_out() implemented per behavior spec; require_auth() calls .auth.get_user(), never .auth.get_session()"
    requirement: "AUTH-01"
    verification:
      - kind: unit
        ref: "tests/test_auth_flow.py::test_require_auth_uses_get_user_never_get_session"
        status: pass
      - kind: integration
        ref: "pytest tests/test_auth_flow.py -x -q (14 tests) against the live local Supabase stack"
        status: pass
    human_judgment: false
  - id: D3
    description: "Duplicate sign_up() with the same email does not crash and does not create a second profiles row/silently succeed as a new account"
    requirement: "AUTH-01"
    verification:
      - kind: integration
        ref: "tests/test_auth_flow.py::test_duplicate_sign_up_does_not_crash_or_create_second_account"
        status: pass
    human_judgment: false
  - id: D4
    description: "sign_in() persists profiles.last_login via a short-lived per-call authenticated client (never the shared cache_resource client) — AUTH-02's Postgres CRUD persistence proof; last_login is null after sign_up and populated/changes across sequential sign_in() calls"
    requirement: "AUTH-03"
    verification:
      - kind: integration
        ref: "tests/test_auth_flow.py::test_sign_in_updates_last_login_across_two_calls, ::test_signup_does_not_call_touch_last_login_leaving_it_null_until_first_sign_in"
        status: pass
    human_judgment: false
  - id: D5
    description: "require_auth() attempts refresh_session() before giving up on an expired/invalid access token, and clears st.session_state + halts when both tokens are invalid"
    requirement: "AUTH-01"
    verification:
      - kind: integration
        ref: "tests/test_auth_flow.py::test_require_auth_expired_token_refreshes_before_giving_up, ::test_require_auth_both_tokens_invalid_clears_session_and_halts"
        status: pass
    human_judgment: false
  - id: D6
    description: "Magic-link sign-in actually delivers an email end-to-end via the local Inbucket/Mailpit instance, no mocking"
    requirement: "AUTH-01"
    verification:
      - kind: integration
        ref: "tests/test_auth_flow.py::test_magic_link_sign_in_sends_email_via_local_inbucket"
        status: pass
    human_judgment: false

duration: 30min
completed: 2026-07-18
status: complete
---

# Phase 1 Plan 2: Auth Module — Stateless Client & require_auth() Gate Summary

**Stateless `st.cache_resource`-shared Supabase client plus a `require_auth()` central gate (server-verified via `get_user()`, never `get_session()`) and sign_up/sign_in/magic-link/sign_out wrappers, proven by 14 tests against the live local Supabase stack**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-07-18T21:04:00Z
- **Completed:** 2026-07-18T21:14:42Z
- **Tasks:** 2 (Task 2 followed TDD: test → feat)
- **Files modified:** 5 created (0 modified)

## Accomplishments
- `src/data/supabase_client.py`: `get_supabase_client()`, `st.cache_resource`-decorated, built only from `SUPABASE_URL`/`SUPABASE_ANON_KEY` — verified to return the identical object across calls, with zero authenticating calls anywhere in the module (D-06, T-01-01)
- `src/auth/session.py`: `sign_up`, `sign_in`, `sign_in_with_magic_link`, `require_auth`, `sign_out`, plus the private `_touch_last_login` helper — `require_auth()` is now the single, central, server-verified auth gate every later page will call (D-04), and it demonstrably calls `.auth.get_user(token)` and never `.auth.get_session()`
- `tests/conftest.py` + `tests/test_auth_flow.py`: 14 integration tests against the real local Supabase CLI stack (no mocking of `supabase-py`) proving signup/login/duplicate-signup/no-confirmation-gate/token-refresh/sign-out/magic-link-delivery/`last_login` persistence — all pass
- Discovered and fixed a real gap in Plan 01's migration: RLS policies existed but the `authenticated` role was never `GRANT`ed table privileges, so every authenticated request failed with `permission denied for table profiles` regardless of RLS — added `supabase/migrations/20260718211140_grant_profiles_privileges.sql`

## Task Commits

Each task was committed atomically (Task 2 followed TDD: RED → GREEN):

1. **Task 1: Stateless cached Supabase client** - `684c66d` (feat)
2. **Task 2 (RED): failing tests for require_auth() gate and auth wrappers** - `8418b93` (test)
2. **Task 2 (GREEN): require_auth() gate + sign-up/sign-in/magic-link/sign-out wrappers** - `c7d594a` (feat)

**Plan metadata:** pending (docs: complete plan, this commit)

## Files Created/Modified
- `src/data/supabase_client.py` - `get_supabase_client()`, `st.cache_resource`-shared stateless client
- `src/auth/session.py` - `sign_up`/`sign_in`/`sign_in_with_magic_link`/`require_auth`/`sign_out`/`_touch_last_login`
- `tests/conftest.py` - `supabase_env` (parses `npx supabase status -o env`), `test_user_factory`
- `tests/test_auth_flow.py` - 14 tests covering every behavior bullet in the plan's Task 2 spec
- `supabase/migrations/20260718211140_grant_profiles_privileges.sql` - grants `SELECT, UPDATE` on `public.profiles` to `authenticated` (bug fix)

## Decisions Made
- D-06 resolved as planned: the Supabase client is `st.cache_resource`-shared (stateless connection); tokens live exclusively in `st.session_state`
- `require_auth()` explicitly `return`s `None` after each `st.stop()` call rather than relying only on `st.stop()` to halt — `st.stop()` is a documented no-op outside a running Streamlit script context (confirmed empirically: `st.stop()` printed a warning but did not halt a bare `python -c` script), so the explicit `None` return makes the gate's "does not return a user" behavior verifiable by a plain pytest assertion while still halting real page renders (where `st.stop()` does raise/halt)
- Confirmed `AuthApiError` import path (`from supabase_auth.errors import AuthApiError`) against the installed `supabase-auth==2.31.0` package before use, resolving RESEARCH.md's Open Question 2 rather than trusting the research doc's `[ASSUMED]` tag

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed missing GRANT on public.profiles for the authenticated role**
- **Found during:** Task 2, first `pytest` run (`test_sign_in_after_sign_up_succeeds_with_no_confirmation_gate` failed with `permission denied for table profiles`, code `42501`)
- **Issue:** Plan 01's migration (`20260718204703_create_profiles.sql`) enabled RLS and defined SELECT/UPDATE policies on `public.profiles`, but never `GRANT`ed the underlying table privileges to the `authenticated` role. On a self-managed local Supabase CLI stack (no dashboard auto-grant step), Postgres requires both a `GRANT` and a passing RLS policy for a role to touch a table at all — RLS alone is not sufficient, and without the grant every authenticated client request against `profiles` failed regardless of RLS correctness.
- **Fix:** Added `supabase/migrations/20260718211140_grant_profiles_privileges.sql` (`grant select, update on public.profiles to authenticated;`), generated via `npx supabase migration new` and applied via `npx supabase migration up` against the running local stack. Verified via direct `psql` query that `authenticated` now has `SELECT`/`UPDATE` in `information_schema.role_table_grants`. RLS scoping (`auth.uid() = user_id`) is unaffected — each row is still filtered per-user.
- **Files modified:** `supabase/migrations/20260718211140_grant_profiles_privileges.sql`
- **Verification:** `pytest tests/test_auth_flow.py -x -q` — all 14 tests pass after applying the grant
- **Committed in:** `c7d594a` (part of Task 2's GREEN commit)

**2. [Test-authoring correction, not a plan deviation] Docstring prose self-triggered literal grep acceptance checks**
- **Found during:** Task 1 and Task 2 verification (`grep -Eq "\.auth\.sign_(in|up)"` and `grep -Eq "\.auth\.get_session\("` both initially matched inside module/function docstrings describing what NOT to call)
- **Issue:** Explanatory prose like "Do NOT call `.auth.sign_up`" or "never `.auth.get_session()`" contains the exact literal substring the acceptance grep searches for, causing a false-positive match against documentation rather than code
- **Fix:** Rephrased the docstrings to describe the same constraint without the literal dotted-call substring (e.g. "never the client-trusted, locally-cached `get_session()` accessor"), preserving the documentation's meaning
- **Files modified:** `src/data/supabase_client.py`, `src/auth/session.py`
- **Verification:** All plan-specified `grep`/`grep -Eq` acceptance commands pass exactly as written in the plan
- **Committed in:** `684c66d`, `c7d594a`

---

**Total deviations:** 2 (1 Rule 1 bug fix, 1 test-authoring self-correction)
**Impact on plan:** The migration fix was necessary for AUTH-02/AUTH-03's persistence proof to function at all under the local Supabase CLI stack; no scope creep. The docstring rephrasing changed no behavior.

## Issues Encountered
- `pip list` initially showed `streamlit==1.51.0` and no `supabase`/`yfinance`/`pytest`/`ruff` installed at all, despite Plan 01 pinning exact versions in `requirements-dev.txt` — ran `pip install -r requirements-dev.txt` to bring the environment in line with the pinned versions before writing any code; this is routine environment setup, not a plan deviation.
- `npx supabase status -o env` prints `Stopped services: [supabase_imgproxy_..., supabase_pooler_...]` — these two optional services (image proxy, connection pooler) are not required by this plan's auth flow and their absence did not affect any test.

## User Setup Required

None - no external service configuration required. All tests run against the local Supabase CLI Docker stack already running from Plan 01.

## Next Phase Readiness
- `require_auth()`, `sign_up`, `sign_in`, `sign_in_with_magic_link`, `sign_out` are all implemented and proven — Plan 04 (pages) can call `require_auth()` directly with no further auth-module work, and Plan 05 (isolation/RLS tests) can build on `test_user_factory`/`supabase_env` from `tests/conftest.py`.
- `_touch_last_login`'s short-lived, per-call authenticated client pattern is now the established template for any future write that must be scoped to one user's JWT without touching the shared `get_supabase_client()` instance.
- The migration fix (`20260718211140_grant_profiles_privileges.sql`) is applied to the running local stack; if a later plan/session starts a fresh local stack from scratch (`npx supabase start` after a full reset), this migration will apply automatically along with Plan 01's, since both live in `supabase/migrations/`.
- No blockers.

---
*Phase: 01-foundation-data-layer-caching-auth*
*Completed: 2026-07-18*

## Self-Check: PASSED

All created files verified present on disk (`src/data/supabase_client.py`, `src/auth/session.py`, `tests/conftest.py`, `tests/test_auth_flow.py`, `supabase/migrations/20260718211140_grant_profiles_privileges.sql`); commits `684c66d`, `8418b93`, and `c7d594a` verified present in `git log`.
