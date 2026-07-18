---
phase: 01-foundation-data-layer-caching-auth
plan: 01
subsystem: infra
tags: [supabase, postgres, rls, streamlit, config, dependency-manifest]

# Dependency graph
requires: []
provides:
  - "requirements.txt/requirements-dev.txt pinning the 7 RESEARCH.md-approved package versions"
  - "pyproject.toml with pytest testpaths/pythonpath and ruff config"
  - "src/config.py: get_config(key, default) (st.secrets-first, os.environ fallback) and CACHE_TTL_SECONDS=3600"
  - "src, src.auth, src.data, src.pages importable package scaffolding"
  - ".streamlit/secrets.toml.example template (SUPABASE_URL, SUPABASE_ANON_KEY)"
  - ".gitignore covering secrets, disk cache, Supabase CLI local state, Python artifacts"
  - "public.profiles table (user_id/created_at/last_login) + RLS (SELECT/UPDATE policies) + handle_new_user() trigger, applied to a running local Supabase CLI stack"
affects: [01-02, 01-03, 01-04, 01-05]

# Tech tracking
tech-stack:
  added: [streamlit==1.59.2, supabase==2.31.0, yfinance==1.5.1, tenacity==9.1.4, python-dotenv==1.2.2, pytest==9.1.1, ruff==0.15.22, "Supabase CLI (via npx, local Docker stack)"]
  patterns:
    - "get_config() single chokepoint for secrets/env resolution (st.secrets try/except, then os.environ)"
    - "profiles auto-provisioned via SECURITY DEFINER Postgres trigger, not application code (RESEARCH.md Pattern 4)"

key-files:
  created:
    - requirements.txt
    - requirements-dev.txt
    - pyproject.toml
    - src/config.py
    - src/__init__.py
    - src/auth/__init__.py
    - src/data/__init__.py
    - src/pages/__init__.py
    - .streamlit/secrets.toml.example
    - .gitignore
    - supabase/config.toml
    - supabase/migrations/20260718204703_create_profiles.sql
  modified: []

key-decisions:
  - "Migration timestamp 20260718204703 generated via `npx supabase migration new create_profiles` (not hand-picked), per plan instruction"
  - "Local Supabase CLI Docker stack (not a mock, not live cloud) is the test backend for this phase's automated tests, resolved by 01-CONTEXT.md/01-RESEARCH.md Wave 0 gap"

patterns-established:
  - "Pattern 4 (RESEARCH.md): profiles auto-provisioning via AFTER INSERT trigger on auth.users, SECURITY DEFINER function — no client-facing INSERT policy needed"

requirements-completed: [AUTH-02, AUTH-03]

coverage:
  - id: D1
    description: "requirements.txt/requirements-dev.txt pin exactly the 7 RESEARCH.md-approved package versions; pyproject.toml configures pytest/ruff"
    verification:
      - kind: unit
        ref: "grep -c streamlit==1.59.2 requirements.txt; test -f pyproject.toml"
        status: pass
    human_judgment: false
  - id: D2
    description: "src/config.py exports get_config(key, default) and CACHE_TTL_SECONDS=3600, importable with no ImportError"
    verification:
      - kind: unit
        ref: "python -c \"from src.config import get_config, CACHE_TTL_SECONDS; assert CACHE_TTL_SECONDS == 3600\""
        status: pass
    human_judgment: false
  - id: D3
    description: "supabase/migrations/20260718204703_create_profiles.sql creates public.profiles (user_id/created_at/last_login only), enables RLS, defines SELECT/UPDATE policies, and a SECURITY DEFINER handle_new_user() + on_auth_user_created trigger"
    requirement: "AUTH-02"
    verification:
      - kind: unit
        ref: "grep -c 'create table public.profiles' / 'enable row level security' / 'on_auth_user_created' / 'security definer' supabase/migrations/20260718204703_create_profiles.sql"
        status: pass
    human_judgment: false
  - id: D4
    description: "Local Supabase CLI stack (Docker: Postgres, GoTrue, Inbucket, Studio, Kong) running with the migration applied; profiles table exists with relrowsecurity=true and 2 policies (SELECT, UPDATE) confirmed via direct psql query, not just the migration file"
    requirement: "AUTH-03"
    verification:
      - kind: integration
        ref: "npx supabase status -o env (API_URL/ANON_KEY/DB_URL/INBUCKET_URL present); docker exec supabase_db_Popcorn-Pilot psql -c \"select relrowsecurity from pg_class where relname='profiles'\" -> t; psql -c \"select policyname,cmd from pg_policies where tablename='profiles'\" -> 2 rows"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-18
status: complete
---

# Phase 1 Plan 1: Foundation Scaffolding & Supabase Schema Summary

**Dependency manifest, `src/config.py` (st.secrets/os.environ resolver + 1hr cache TTL), and a `public.profiles` table with RLS + auto-provisioning trigger, live-applied to a local Supabase CLI Docker stack**

## Performance

- **Duration:** 20 min
- **Started:** 2026-07-18T20:43:18Z
- **Completed:** 2026-07-18T20:58:07Z
- **Tasks:** 3
- **Files modified:** 13

## Accomplishments
- Pinned the exact 7 RESEARCH.md Package-Legitimacy-Audit-approved dependency versions across `requirements.txt`/`requirements-dev.txt`, with `pyproject.toml` wiring pytest (`testpaths=["tests"]`, `pythonpath=["."]`) and ruff (`line-length=100`)
- `src/config.py` provides the single `get_config()` chokepoint (st.secrets-first, os.environ/`.env` fallback) and the `CACHE_TTL_SECONDS=3600` constant (D-08) that all later data-layer/auth plans will import
- `public.profiles` (user_id/created_at/last_login only, per D-10) created via a Supabase-CLI-generated migration, with RLS enabled and SELECT/UPDATE policies keyed on `auth.uid() = user_id` (D-11), plus a `SECURITY DEFINER` `handle_new_user()` trigger auto-provisioning the row on `auth.users` insert (RESEARCH.md Pattern 4) — covers both password and magic-link signup paths with one mechanism
- Stood up a local Supabase CLI stack via Docker (`npx supabase start`) and confirmed, by direct `psql` query against the running Postgres instance (not just inspecting the SQL file), that `profiles` has `relrowsecurity = true` and exactly 2 policies (SELECT, UPDATE) — this is the live backend later plans' AUTH-02/AUTH-03 tests will run against

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependency manifest, config module, and package scaffolding** - `45ac7c4` (feat)
2. **Task 2: Supabase migration — profiles table, RLS, auto-provisioning trigger** - `2a9c122` (feat)
3. **Task 3: [BLOCKING] Start local Supabase stack and apply the migration** - no commit (verification-only task; no tracked files changed — `supabase/config.toml` was unchanged by `npx supabase start`)

**Plan metadata:** pending (docs: complete plan, this commit)

## Files Created/Modified
- `requirements.txt` - Pins streamlit/supabase/yfinance/tenacity/python-dotenv at exact approved versions
- `requirements-dev.txt` - `-r requirements.txt` plus pytest/ruff
- `pyproject.toml` - `[tool.pytest.ini_options]` and `[tool.ruff]` config
- `src/config.py` - `get_config()` and `CACHE_TTL_SECONDS`
- `src/__init__.py`, `src/auth/__init__.py`, `src/data/__init__.py`, `src/pages/__init__.py` - package markers
- `.streamlit/secrets.toml.example` - SUPABASE_URL/SUPABASE_ANON_KEY placeholder template
- `.gitignore` - secrets, disk cache, Supabase CLI local state, Python artifacts
- `supabase/config.toml`, `supabase/.gitignore` - generated by `npx supabase init`
- `supabase/migrations/20260718204703_create_profiles.sql` - profiles table + RLS + trigger

## Decisions Made
- Used the Supabase-CLI-generated timestamp (`20260718204703`) for the migration filename rather than hand-picking one, per the plan's explicit instruction to avoid drift from what the CLI itself would produce
- No `requirements.txt` changes beyond the 7 audited packages — no ad hoc additions

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- `npx supabase start` hit transient Docker Hub rate-limit errors (`Error error from registry: Rate exceeded`) while pulling `logflare` and `postgres-meta` images; these were retried automatically by the underlying pull and all images ultimately downloaded successfully — no action needed.
- A non-blocking warning appeared during migration apply: `failed to cache migrations catalog: ... Failed loading https://registry.npmjs.org/@supabase%2fpg-delta` (Studio's schema-diff helper trying to reach the public npm registry with no network path in this sandbox). This does not affect migration application, RLS, or the trigger — confirmed via direct `psql` query that `profiles`, RLS, and both policies exist correctly. Not in scope to fix (Studio schema-diff tooling, unrelated to this plan's deliverables).
- `python-dotenv` was upgraded locally from an already-installed 1.2.1 to the pinned 1.2.2 to match `requirements.txt` exactly.

## User Setup Required

None - no external service configuration required. The local Supabase CLI Docker stack started by this plan is used by subsequent plans' automated tests; a live cloud Supabase project is only needed at actual deployment time (`.streamlit/secrets.toml` filled from `.example`).

## Next Phase Readiness
- `src/config.py`, the package scaffolding, and the live local Supabase stack (profiles table + RLS + trigger) are all in place for Plan 02 (auth module), Plan 03 (cache module), Plan 04 (app shell), and Plan 05 (verification tests) to build and test against.
- No blockers. The local stack remains running (`npx supabase start` was not stopped) so later plans in this phase can connect immediately; if a later plan's session starts fresh, remember `npx supabase status -o env` re-prints connection details without restarting.

---
*Phase: 01-foundation-data-layer-caching-auth*
*Completed: 2026-07-18*

## Self-Check: PASSED

All created files verified present on disk; commits `45ac7c4`, `2a9c122`, and `1e1498f` verified present in `git log`.
