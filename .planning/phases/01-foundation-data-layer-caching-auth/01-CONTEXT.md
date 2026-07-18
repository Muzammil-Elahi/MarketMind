# Phase 1: Foundation — Data Layer, Caching & Auth - Context

**Gathered:** 2026-07-17
**Status:** Ready for planning

<domain>
## Phase Boundary

A secure, cache-first foundation: users can sign up and log in with strictly isolated sessions (Supabase auth), and all market-data fetches are cached and resilient to rate limits. This phase covers AUTH-01, AUTH-02, AUTH-03 only — no investor profile UI (Phase 2), no recommendation/prediction logic (Phases 3–4). The "profile" persisted here is a minimal stub table, not the real profile builder.

</domain>

<decisions>
## Implementation Decisions

### Auth method & signup flow
- **D-01:** Auth methods: email/password **and** Supabase magic-link (passwordless) login. No OAuth/social login in this phase.
- **D-02:** Email verification is **not** required — users can log in immediately after signup (lower friction, favors quick demoing of a portfolio project over combating throwaway signups).
- **D-03:** Unauthenticated users see a single login/signup page; auth-gated pages are hidden from `st.navigation` entirely until logged in (not visible-but-redirecting).

### Session isolation pattern
- **D-04:** Use a central `require_auth()` helper called at the top of every page — it reads the token from `st.session_state`, re-verifies server-side with Supabase, and halts rendering if invalid. No per-page inline auth checks (research/PITFALLS.md ties inconsistent per-page checks directly to real reported cross-user session leaks on Streamlit).
- **D-05:** Add an automated two-concurrent-session isolation test (simulate two sessions with different logged-in users, assert no `st.session_state` or cached data cross-contaminates). This directly verifies Phase 1 success criterion #2.
- **D-06 (Claude's discretion):** Whether the Supabase client object itself is `st.cache_resource`-shared (stateless connection) vs. constructed per-call — user deferred to implementation time. Constraint that is NOT discretionary: the auth token/user identity must never live in a cached/global object, only in `st.session_state` (per PITFALLS.md Anti-Pattern 4 / Pitfall 7).

### Caching strategy — TTLs & disk persistence
- **D-07:** Build a disk-persisted price cache (SQLite or parquet) in addition to `st.cache_data`, so a cold Streamlit Community Cloud container (post-sleep) doesn't immediately re-hammer yfinance. This is foundational — later phases' data calls should inherit this cold-start resilience rather than each reimplementing it.
- **D-08:** Live price data TTL: **1 hour** (`st.cache_data(ttl=3600)`), matching the research-documented pattern. This is an educational/research tool, not a live-trading terminal — hours of staleness is acceptable per PITFALLS.md.
- **D-09 (Claude's discretion):** Exact degraded/stale-cache fallback UI copy and disk-cache implementation details (SQLite vs. parquet, file layout) — not locked by the user, follow research's guidance (`data/cache.py` single chokepoint, all yfinance/NewsAPI/Gemini calls route through it).

### Minimal persisted-data proof for AUTH-02
- **D-10:** Persist a `profiles` stub table (or equivalently named) with just `user_id`, `created_at`, `last_login` — NOT a throwaway test value. This is deliberately the same table Phase 2 will extend with real profile fields (risk tolerance, time horizon, etc.), so this phase's schema work isn't discarded.
- **D-11:** Explicit Supabase Row Level Security (RLS) policy on the `profiles` table (a user can only read/write their own row) is **required** in this phase, with a test verifying it — not deferred. Research (PITFALLS.md) explicitly warns RLS is not "on by default" and that skipping this is a common, easy-to-miss gap; this directly satisfies AUTH-03 at the database level, not just the app layer.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — core value, constraints ($0 budget, free-tier-only), Key Decisions table
- `.planning/REQUIREMENTS.md` — AUTH-01, AUTH-02, AUTH-03 requirement definitions and traceability
- `.planning/ROADMAP.md` §"Phase 1: Foundation — Data Layer, Caching & Auth" — goal, success criteria, dependencies

### Architecture & pitfalls research (directly informed this discussion)
- `.planning/research/ARCHITECTURE.md` — see especially: UI/session-state layer patterns, `require_auth()` central-check recommendation, `data/cache.py` single-chokepoint pattern, module structure (`auth/session.py`, `data/cache.py`, `data/supabase_client.py`), Anti-Pattern 4 (global/module-level auth state), Streamlit/Supabase multi-session-leak citations
- `.planning/research/PITFALLS.md` — see especially: Pitfall 7 (`st.cache_resource`/`st.cache_data` misuse causing cross-user leakage), yfinance rate-limit pitfall + disk-cache mitigation, Supabase RLS-not-on-by-default warning, two-concurrent-session test recommendation, Supabase free-tier 7-day inactivity pause note
- `.planning/research/STACK.md` — approved dependency versions (Streamlit 1.59.x, supabase-py 2.31.0, tenacity, `st.cache_data`/`st.cache_resource` usage conventions)

</canonical_refs>

<code_context>
## Existing Code Insights

Greenfield project — no application code exists yet (repo contains only planning docs and a placeholder README). Nothing to reuse or integrate with; this phase establishes the foundational module structure (`auth/`, `data/cache.py`, `data/supabase_client.py`) that all later phases build on.

</code_context>

<specifics>
## Specific Ideas

- The `profiles` stub table created in this phase (user_id, created_at, last_login) is intentionally the seed of the real profile table Phase 2 will extend — not throwaway scaffolding.
- Session isolation is treated as the highest-risk area of this phase, per explicit real-incident citations in research (Streamlit Community discussion threads on Supabase-auth session leakage).

</specifics>

<deferred>
## Deferred Ideas

- Base app shell / navigation page inventory beyond "login page + auth-gated pages hidden until logged in" was not deep-dived — user was satisfied with the four discussed areas and did not want to explore further gray areas this session. Planner should use judgment (likely: login page + a minimal placeholder/home page for now, since Profile/Recommendation/Prediction pages don't exist until later phases).
- Exact Supabase client caching mechanics (D-06) and disk-cache file format (D-09) left to Claude's discretion at planning/implementation time.

### Reviewed Todos (not folded)
None — `todo.match-phase` returned zero matches for Phase 1.

</deferred>

---

*Phase: 1-Foundation — Data Layer, Caching & Auth*
*Context gathered: 2026-07-17*
