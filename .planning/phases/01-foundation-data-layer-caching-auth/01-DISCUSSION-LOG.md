# Phase 1: Foundation — Data Layer, Caching & Auth - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-17
**Phase:** 1-Foundation — Data Layer, Caching & Auth
**Areas discussed:** Auth method & signup flow, Session isolation pattern, Caching strategy — TTLs & disk persistence, Minimal persisted-data proof for AUTH-02

---

## Auth method & signup flow

| Option | Description | Selected |
|--------|-------------|----------|
| Email/password only | Simplest to build with supabase-py; no extra provider config | |
| Email/password + magic link | Passwordless login via Supabase's built-in magic-link email flow | ✓ |
| Email/password + Google OAuth | Social login; requires OAuth app registration, more setup | |

**User's choice:** Email/password + magic link

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, required (email verification) | Confirmation email required before login; Supabase default | |
| No, skip verification | Log in immediately after signup; lower friction | ✓ |

**User's choice:** No, skip verification

| Option | Description | Selected |
|--------|-------------|----------|
| Single login/signup page, gated pages hidden | st.navigation shows only login page in sidebar until authenticated | ✓ |
| Gated pages visible but redirect to login | All pages show in nav; clicking while logged out redirects | |

**User's choice:** Single login/signup page, gated pages hidden
**Notes:** User chose to move to next area after these three questions without further follow-up.

---

## Session isolation pattern

| Option | Description | Selected |
|--------|-------------|----------|
| Central require_auth() helper, called at top of every page | Research's recommended pattern; re-verifies token server-side, halts rendering if invalid | ✓ |
| Per-page manual checks | Each page writes its own inline check; risk of inconsistency | |

**User's choice:** Central require_auth() helper

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add a two-session isolation test | PITFALLS.md recommends a lightweight integration test with two sessions | ✓ |
| No — rely on code review / manual QA only | Skip automated test, verify manually | |

**User's choice:** Yes — add a two-session isolation test

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — shared stateless client, per-session token/identity | Research's recommended split | |
| Let Claude decide at planning/implementation time | Mechanical detail once require_auth() pattern is locked | ✓ |

**User's choice:** Let Claude decide at planning/implementation time
**Notes:** Recorded as Claude's Discretion (D-06) in CONTEXT.md, with the non-discretionary constraint (token never in a global/cached object) preserved.

---

## Caching strategy — TTLs & disk persistence

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — add disk-persisted cache now | Research-recommended foundational pattern for cold-start resilience | ✓ |
| No — st.cache_data only for v1, revisit later | Simpler Phase 1 scope | |

**User's choice:** Yes — add disk-persisted cache now

| Option | Description | Selected |
|--------|-------------|----------|
| 15 minutes | Tighter freshness for active users | |
| 1 hour | Research's example TTL (ARCHITECTURE.md shows ttl=3600); acceptable staleness for an educational tool | ✓ |

**User's choice:** 1 hour

---

## Minimal persisted-data proof for AUTH-02

| Option | Description | Selected |
|--------|-------------|----------|
| A users/profiles stub table with just user_id + created_at + last_login | Minimal schema that Phase 2 will extend with real profile fields | ✓ |
| A throwaway test value (e.g. a demo settings toggle) | Fully decoupled from future schema, but pure scaffolding | |

**User's choice:** A users/profiles stub table with just user_id + created_at + last_login

| Option | Description | Selected |
|--------|-------------|----------|
| Yes — explicit RLS policy + test, required in this phase | Directly satisfies AUTH-03 at the database level; research warns RLS is easy to skip | ✓ |
| Let Claude decide at planning/implementation time | Standard Supabase pattern once schema is fixed | |

**User's choice:** Yes — explicit RLS policy + test, required in this phase

---

## Claude's Discretion

- Whether the Supabase client object is `st.cache_resource`-shared vs. constructed per-call (D-06) — constrained by: token/identity must never live in a cached/global object.
- Exact degraded/stale-cache fallback UI copy and disk-cache implementation format (SQLite vs. parquet, file layout) (D-09).
- Base app shell / navigation page inventory beyond "login page + hidden gated pages" — likely just login + a minimal placeholder/home page, since later phases' pages don't exist yet.

## Deferred Ideas

None outside phase scope — all four discussed areas stayed within Phase 1's boundary (AUTH-01/02/03, caching foundation). User declined to explore additional gray areas beyond the four selected.
