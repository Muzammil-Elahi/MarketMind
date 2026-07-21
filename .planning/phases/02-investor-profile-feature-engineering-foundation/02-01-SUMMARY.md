---
phase: 02-investor-profile-feature-engineering-foundation
plan: 01
subsystem: database
tags: [supabase, postgres, rls, migration, schema]

# Dependency graph
requires:
  - phase: 01-foundation-data-layer-caching-auth
    provides: public.profiles stub table (user_id/created_at/last_login), handle_new_user() signup trigger, RLS+GRANT precedent
provides:
  - Six new nullable investor-profile columns on public.profiles (risk_tolerance, time_horizon, preferred_sectors, excluded_sectors, preferred_asset_types, capital)
  - public.holdings owner-scoped child table with full 4-policy RLS set and GRANTs, applied live to the local Supabase stack
affects: [02-02, 02-03, 02-04, phase-03-recommendation-engine]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "holdings as an owner-scoped child table with its own user_id FK (not a jsonb blob), RLS+GRANTs folded into one migration"
    - "text + CHECK constraint for fixed-value-set columns instead of native Postgres ENUM"

key-files:
  created:
    - supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql
  modified: []

key-decisions:
  - "Followed RESEARCH.md Pattern 1/2 and CONTEXT.md D-01/D-02/D-06/D-07 exactly — no deviations required"
  - "GRANTs for holdings folded into the same migration as table/RLS creation, avoiding Phase 1's two-migration retroactive-fix pattern"

patterns-established:
  - "Pattern: owner-scoped child table (user_id references auth.users(id) directly) reused for any future per-user dynamic-row resource"

requirements-completed: [PROFILE-01]

coverage:
  - id: D1
    description: "public.profiles extended with six nullable investor-profile columns (risk_tolerance, time_horizon with CHECK constraints; preferred_sectors, excluded_sectors, preferred_asset_types, capital), compatible with the existing handle_new_user() signup trigger"
    requirement: "PROFILE-01"
    verification:
      - kind: integration
        ref: "docker exec supabase_db_Popcorn-Pilot psql -tAc \"select count(*) from information_schema.columns where table_name='profiles' and column_name in ('risk_tolerance','time_horizon','preferred_sectors','excluded_sectors','preferred_asset_types','capital')\" -> 6"
        status: pass
    human_judgment: false
  - id: D2
    description: "public.holdings owner-scoped child table created with 4 RLS policies (select/insert/update/delete) and matching GRANTs (authenticated: select/insert/update/delete; service_role: all), applied live to the running local Supabase stack"
    requirement: "PROFILE-01"
    verification:
      - kind: integration
        ref: "docker exec supabase_db_Popcorn-Pilot psql -tAc \"select count(*) from pg_policies where tablename='holdings'\" -> 4; relrowsecurity=true; role_table_grants confirms authenticated+service_role privileges"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-21
status: complete
---

# Phase 2 Plan 1: Investor Profile Schema Foundation Summary

**Extended `public.profiles` with six nullable investor-profile columns and created a new owner-scoped `public.holdings` child table (4-policy RLS + GRANTs), applied live to the local Supabase CLI stack — the schema foundation Plan 02-03's CRUD layer will build on.**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-21T00:46:08Z
- **Completed:** 2026-07-21T00:52:28Z
- **Tasks:** 2 completed
- **Files modified:** 1

## Accomplishments
- `public.profiles` extended with `risk_tolerance` (CHECK: Conservative/Moderate/Aggressive), `time_horizon` (CHECK: <1yr/1-3yr/3-5yr/5-10yr/10+yr), `preferred_sectors`, `excluded_sectors`, `preferred_asset_types` (all `text[]`), and `capital` (`numeric`) — all nullable, no defaults, preserving `handle_new_user()`'s trigger insert.
- `public.holdings` created as a new owner-scoped child table (`id`, `user_id` FK to `auth.users`, `ticker`, `quantity`, `cost_basis`, `created_at`) with RLS enabled and 4 explicit policies (view/insert/update/delete "their own holdings"), plus an index on `user_id`.
- GRANTs for `holdings` (select/insert/update/delete to `authenticated`, all to `service_role`) folded into the same migration file, avoiding Phase 1's retroactive two-migration GRANT-fix pattern.
- Migration applied live to the running local Supabase CLI Docker stack (Docker Desktop was not running at session start — started it, waited for the pre-existing containers to come back up, then confirmed `npx supabase status` reachable) and verified via direct `psql` queries against the live Postgres instance, not just by inspecting the migration file.

## Task Commits

Each task was committed atomically:

1. **Task 1: Migration — extend profiles, create holdings, RLS, GRANTs** - `7545f3d` (feat)
2. **Task 2: Apply migration to the local Supabase stack and verify live schema** - verification-only, no additional file changes; migration applied via `npx supabase migration up` against the already-committed file from Task 1 (no separate commit needed)

**Plan metadata:** (recorded in the final docs commit for this plan)

## Files Created/Modified
- `supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql` - Extends `profiles` with 6 nullable columns (2 CHECK-constrained) and creates `holdings` (table + RLS + GRANTs)

## Decisions Made
None beyond what RESEARCH.md/CONTEXT.md already specified — plan executed exactly as written. The CHECK-constraint choice for `risk_tolerance`/`time_horizon` (over native ENUM) and the owner-scoped `holdings` child-table design (over a `jsonb` blob) were both already locked decisions (RESEARCH.md Pattern 1/2, CONTEXT.md D-01/D-02/D-06/D-07), not made during execution.

## Deviations from Plan

None - plan executed exactly as written. Docker Desktop needed to be started manually before `npx supabase status`/`migration up` would work (it was not running at session start), but this was an environment-startup step, not a code or schema deviation — no plan content changed as a result.

## Issues Encountered
Docker Desktop was not running when the session started, causing `npx supabase status` and `docker exec` calls to fail with a named-pipe connection error. Resolved by launching Docker Desktop directly (`/c/Program Files/Docker/Docker/Docker Desktop.exe`) and polling `docker ps` until ready (~20s); the existing Supabase containers from a prior session then restarted automatically and `npx supabase status` confirmed the stack reachable at `http://127.0.0.1:54321`.

## User Setup Required

None - no external service configuration required. (Local Supabase CLI stack is dev-only infrastructure already established in Phase 1.)

## Next Phase Readiness
Live, RLS-enforced, GRANT-correct schema for both `profiles` (extended) and `holdings` (new) is now available on the running local Supabase stack. Plan 02-02 (feature engineering pipeline) and Plan 02-03 (profile/holdings CRUD helpers + their tests, including `test_holdings_rls.py` and `test_profile_crud.py`) can now be planned/executed against real data. No blockers identified.

---
*Phase: 02-investor-profile-feature-engineering-foundation*
*Completed: 2026-07-21*

## Self-Check: PASSED

- FOUND: supabase/migrations/20260721005033_extend_profiles_and_create_holdings.sql
- FOUND: commit 7545f3d
- FOUND: commit d425857
