---
phase: 02-investor-profile-feature-engineering-foundation
plan: 03
subsystem: data
tags: [supabase, rls, crud, mass-assignment, ticker-validation, testing]

# Dependency graph
requires:
  - phase: 02-investor-profile-feature-engineering-foundation
    plan: "01"
    provides: public.profiles six new columns + public.holdings owner-scoped child table with 4-policy RLS + GRANTs, live on the local Supabase stack
provides:
  - "src/data/profile.py: fetch_profile, upsert_profile, fetch_holdings, upsert_holdings, validate_ticker — the single chokepoint for all profile/holdings Supabase CRUD and D-08 ticker validation"
affects: [02-04, phase-03-recommendation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Scoped-client-per-call CRUD discipline (fresh create_client() + postgrest.auth(access_token) per function call, never the shared cache_resource client) extended from src/auth/session.py's _touch_last_login to a second module"
    - "Named-keyword-argument payload construction for UPDATE (upsert_profile) and explicit per-row whitelist extraction for INSERT (upsert_holdings) as structural mass-assignment mitigations (T-02-04)"

key-files:
  created:
    - src/data/profile.py
    - tests/test_profile_crud.py
    - tests/test_ticker_validation.py
    - tests/test_holdings_rls.py
  modified: []

key-decisions:
  - "Followed src/auth/session.py's _touch_last_login scoped-client pattern exactly for all four CRUD functions — no new client-lifecycle pattern introduced"
  - "upsert_profile uses .update() exclusively (never .upsert()/.insert()) since public.profiles has no client-facing INSERT policy"
  - "validate_ticker fails open (returns True) on any exception from fetch_ohlcv, and flags invalid only on a genuinely-empty-but-successful DataFrame result (Pitfall 1)"

patterns-established:
  - "Reworded docstring prose in src/data/profile.py to avoid literal substrings (\".upsert(\", \"@st.cache_data\") that would otherwise falsely self-match this plan's own structural inspect.getsource() test assertions — a pattern future structural-check tests in this codebase should watch for"

requirements-completed: [PROFILE-01, PROFILE-02]

coverage:
  - id: T1
    description: "fetch_profile/upsert_profile/fetch_holdings/upsert_holdings/validate_ticker implemented per the scoped-client discipline; upsert_profile UPDATE-only; upsert_holdings whitelists ticker/quantity/cost_basis per row; validate_ticker fails open on exceptions"
    requirement: "PROFILE-01"
    verification:
      - kind: unit
        ref: "python -c import check + grep structural assertions (def upsert_profile, .update(payload).eq(\"user_id\", row[\"ticker\"], create_client( x5) all pass"
        status: pass
    human_judgment: false
  - id: T2
    description: "Profile scalar-field round-trip, UPDATE-only structural check, double-upsert idempotency (row-count proof), no-caching structural check, holdings round-trip with optional cost_basis, and spoofed-user_id mass-assignment resistance — all against the live local Supabase stack; ticker validation fully mocked"
    requirement: "PROFILE-01, PROFILE-02"
    verification:
      - kind: integration
        ref: "pytest tests/test_profile_crud.py -x -q -> 6 passed"
        status: pass
      - kind: unit
        ref: "pytest tests/test_ticker_validation.py -x -q -> 4 passed (zero live network calls)"
        status: pass
    human_judgment: false
  - id: T3
    description: "Cross-user select/insert/delete on holdings blocked by RLS (select/delete return zero rows; insert-with-mismatched-user_id raises), plus a same-user full-CRUD positive control"
    requirement: "PROFILE-01"
    verification:
      - kind: integration
        ref: "pytest tests/test_holdings_rls.py -x -q -> 4 passed"
        status: pass
    human_judgment: false

duration: 25min
completed: 2026-07-21
status: complete
---

# Phase 2 Plan 3: Investor Profile CRUD + Feature Engineering Foundation Summary

**Built `src/data/profile.py` as the single, RLS-safe, mass-assignment-resistant CRUD chokepoint for `profiles`/`holdings` Supabase reads and writes plus D-08 ticker validation, proven correct by 14 passing tests (10 against the live local Supabase stack, 4 fully mocked) covering round-trip persistence, idempotency, two-user RLS isolation, and a real mass-assignment attack scenario.**

## Performance

- **Duration:** 25 min
- **Completed:** 2026-07-21
- **Tasks:** 3 completed
- **Files modified:** 4 (all new)

## Accomplishments

- `src/data/profile.py` implements `fetch_profile`, `upsert_profile`, `fetch_holdings`, `upsert_holdings`, and `validate_ticker`, every CRUD function building a fresh `create_client()` + `.postgrest.auth(access_token)` per call — the exact scoped-client discipline `src/auth/session.py`'s `_touch_last_login` established in Phase 1, applied to a second module for the first time.
- `upsert_profile` issues `.update()` only against `profiles` (never `.upsert()`/`.insert()`), matching the fact that `public.profiles` has no client-facing INSERT policy; named keyword arguments make mass-assignment structurally impossible for this function.
- `upsert_holdings` replaces all of a user's holdings rows on save (delete-then-insert) and builds each inserted row's payload by explicitly extracting `ticker`/`quantity`/`cost_basis` — never forwarding the caller-supplied row dict as-is — so a spoofed extra `user_id` key in an input row can never override the real, server-supplied ownership value (T-02-04), proven by a genuine two-user attack-scenario test.
- `validate_ticker` correctly distinguishes a genuinely-invalid ticker (successful fetch, empty DataFrame — Pitfall 1) from a transient infrastructure failure (exception — fails open, returns `True`), avoiding both silent-accept-of-bad-tickers and blocking saves on flaky network conditions.
- `tests/test_profile_crud.py` (6 tests, real local Supabase stack, no mocking): scalar-field round-trip, UPDATE-only structural check, double-upsert idempotency with a direct row-count proof (via a service-role client), no-caching structural check, holdings round-trip with optional `cost_basis`, and the mass-assignment spoofed-`user_id` resistance test.
- `tests/test_ticker_validation.py` (4 tests, fully mocked, zero live network calls): live-nonempty (valid), live-empty (invalid, Pitfall 1), fail-open-on-exception (Pitfall 4), and correct `period="5d"` call-shape assertion.
- `tests/test_holdings_rls.py` (4 tests, real local Supabase stack, two-user pattern mirroring `test_rls_policy.py`): cross-user select returns zero rows, cross-user insert with a mismatched `user_id` raises (the INSERT policy's `with check` clause — a different RLS failure shape than SELECT/UPDATE's zero-rows behavior), cross-user delete affects zero rows and the row survives, and a same-user full-CRUD positive control proving RLS filters rather than blocks everything.

## Task Commits

Each task was committed atomically:

1. **Task 1: `src/data/profile.py` — profile/holdings CRUD + ticker validation** - `e1904b4` (feat)
2. **Task 2: Profile CRUD + ticker validation tests** - `ecb3a96` (test) — includes a small docstring-wording fix to `src/data/profile.py` (see Deviations)
3. **Task 3: Holdings RLS two-user isolation proof** - `03dd096` (test)

## Files Created/Modified

- `src/data/profile.py` — the CRUD/ticker-validation chokepoint (created in Task 1, docstring reworded in Task 2)
- `tests/test_profile_crud.py` — scalar/holdings CRUD round-trip, idempotency, mass-assignment resistance (real stack)
- `tests/test_ticker_validation.py` — mocked D-08 ticker validation
- `tests/test_holdings_rls.py` — two-user holdings RLS isolation proof (real stack)

## Decisions Made

- Followed `src/auth/session.py`'s `_touch_last_login` scoped-client pattern exactly for all four CRUD functions in `src/data/profile.py` — no new client-lifecycle pattern was introduced, per the plan's explicit instruction.
- `upsert_profile` uses `.update()` exclusively; `upsert_holdings` uses delete-then-insert with an explicit per-row whitelist — both decisions were already locked in the plan, not made during execution.
- Idempotency test proves the double-upsert claim with a direct row-count query via a service-role client (not just value equality), since `profiles.user_id` being the primary key alone doesn't rule out an app-layer bug that could otherwise attempt a second row.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Docstring prose in `src/data/profile.py` accidentally matched this plan's own structural test assertions**
- **Found during:** Task 2 (writing `tests/test_profile_crud.py`)
- **Issue:** `upsert_profile`'s docstring said "never `.upsert()`/`.insert()`" and the module docstring said "wrapped in `@st.cache_data`/`@st.cache_resource`" — both are legitimate prose describing what the code does *not* do, but `inspect.getsource()`-based structural tests (`test_upsert_profile_uses_update_never_insert_for_profiles`, `test_fetch_profile_has_no_cache_data_decorator`) check the whole function/module source text for the literal absence of these substrings, and the docstrings' own explanatory mentions of the forbidden patterns caused false-positive test failures.
- **Fix:** Reworded both docstring passages to describe the same behavior without using the literal `.upsert(`/`@st.cache_data` substrings (e.g. "never an upsert or insert call", "wrapped in a Streamlit caching decorator") — no functional code change, `grep`-verified the actual code still contains `.update(payload).eq("user_id"` and zero `.upsert(`/`.insert(` calls against `"profiles"`.
- **Files modified:** `src/data/profile.py`
- **Commit:** `ecb3a96`

Or in full: two of Task 1's five original files' behavior was unchanged; only prose wording shifted to keep this plan's own structural tests meaningful rather than accidentally-passing/failing on documentation text.

## Known Stubs

None — all five functions are fully wired to the live Supabase schema created in Plan 02-01; no placeholder/mock data paths remain in `src/data/profile.py` itself.

## Threat Flags

None — the threat surface introduced here (`T-02-01` RLS isolation, `T-02-03` parameterized-query tampering resistance, `T-02-04` mass-assignment resistance) was already identified in this plan's own `<threat_model>` and is exactly what Tasks 2/3's tests prove; no new, unplanned security-relevant surface was introduced.

## Issues Encountered

None. The local Supabase CLI stack (started during Plan 02-01) was already running and reachable at session start; all 14 tests in this plan's three new test files passed on the first fully-corrected run.

## User Setup Required

None — no external service configuration required. (Local Supabase CLI stack is dev-only infrastructure already established in Phase 1/Plan 02-01.)

## Next Phase Readiness

`src/data/profile.py` is the proven, RLS-safe, mass-assignment-resistant, idempotent CRUD chokepoint for profile/holdings data — Plan 02-04's `src/pages/profile.py` UI page can now call `fetch_profile`/`upsert_profile`/`fetch_holdings`/`upsert_holdings`/`validate_ticker` directly with no further data-layer work required. No blockers identified.

---
*Phase: 02-investor-profile-feature-engineering-foundation*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: src/data/profile.py
- FOUND: tests/test_profile_crud.py
- FOUND: tests/test_ticker_validation.py
- FOUND: tests/test_holdings_rls.py
- FOUND: commit e1904b4
- FOUND: commit ecb3a96
- FOUND: commit 03dd096
