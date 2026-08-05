---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
current_phase: 3
current_phase_name: Deterministic Recommendation Engine
status: planning
stopped_at: Phase 3 planned (8 plans, verification passed)
last_updated: "2026-08-05T01:06:25.403Z"
last_activity: 2026-08-03
last_activity_desc: Phase 02 complete, transitioned to Phase 3
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 17
  completed_plans: 9
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-03)

**Core value:** A user gets a ranked, explainable shortlist of assets matching their investor profile, and can drill into any of them to see a price forecast with confidence intervals and backtested accuracy — recommendation and prediction work together as one pipeline, not two disconnected tools.
**Current focus:** Phase 3 — Deterministic Recommendation Engine

## Current Position

Phase: 3 — Deterministic Recommendation Engine
Plan: Not started
Status: Ready to plan
Last activity: 2026-08-03 — Phase 02 complete, transitioned to Phase 3

Progress: [████████████████████] 9/9 plans (100%) · 2/6 phases complete

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: - min
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01 | 5 | - | - |
| 02 | 4 | - | - |

**Recent Trend:**

- Last 5 plans: -
- Trend: -

*Updated after each plan completion*
**Per-Plan Metrics:**

| Plan | Duration | Tasks | Files |
|------|----------|-------|-------|
| Phase 01 P01 | 20min | 3 tasks | 13 files |
| Phase 01 P02 | 30min | 2 tasks | 5 files |
| Phase 01 P03 | 15min | 2 tasks | 3 files |
| Phase 01 P04 | 105min | 2 tasks | 3 files |
| Phase 01 P05 | 40min | 2 tasks | 7 files |
| Phase 02 P01 | 15 | 2 tasks | 1 files |
| Phase 02 P02 | 25min | 3 tasks | 6 files |
| Phase 02 P03 | 25min | 3 tasks | 4 files |
| Phase 02 P04 | 8min | 2 tasks | 2 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Roadmap: Project uses standard (Horizontal Layers) mode — build order is data/caching -> features -> recommendation engine -> prediction/backtesting -> LLM agent -> compliance/watchlist, per architecture research (each layer depends on the correctness of the one before it).
- Roadmap: Phase 1 establishes generic Supabase persistence + session isolation; Phases 2 and 6 exercise that same persistence pattern for profile and watchlist data respectively rather than rebuilding it (covers AUTH-02 across phases).
- Roadmap: Compliance disclaimer/non-directive-copy requirements (COMPLY-01/02) are delivered as a final audit pass in Phase 6, once all recommendation/prediction views exist — but per research, the disclaimer UI component itself should be introduced early (as early as Phase 3) and simply gets audited/consolidated in Phase 6, not built from scratch there.
- [Phase ?]: Local Supabase CLI Docker stack (not mock, not live cloud) is the test backend for Phase 1 automated tests
- [Phase ?]: D-06 resolved: Supabase client is st.cache_resource-shared (stateless), tokens live only in st.session_state
- [Phase ?]: require_auth() explicitly returns None after st.stop() so the gate is unit-testable outside a running Streamlit script context
- [Phase ?]: Cache chokepoint (src/data/cache.py) uses tenacity reraise=True so a total live-fetch failure with no disk cache propagates the original exception type rather than tenacity's RetryError wrapper
- [Phase ?]: UI-SPEC's assumption that native Streamlit form validation blocks empty-field submission does not hold in practice - added explicit guard-clause + warning copy + red-border highlighting in 01-04 to deliver the intended empty-state behavior
- [Phase ?]: streamlit run src/app.py requires a repo-root sys.path insertion since Streamlit sets sys.path[0] to the script's own directory, not the project root
- [Phase ?]: Critical fix (T-01-01): every authenticating Supabase Auth call (sign_up, sign_in, magic-link, refresh_session) must route through a short-lived scoped client, never the shared cache_resource get_supabase_client() -- GoTrue's authenticating methods internally persist a session onto whichever client invokes them
- [Phase ?]: sign_out() uses the stateless admin.sign_out(access_token, scope) call with an explicit token, not the stateful auth.sign_out() wrapper which depends on get_session() finding a token on the calling client
- [Phase ?]: test_auth_isolation.py verified as a real (not trivially-passing) proof by temporarily reverting the session.py fix and confirming both isolation tests fail against the pre-fix code
- [Phase ?]: Owner-scoped holdings child table (own user_id FK) with 4 RLS policies + GRANTs folded into a single migration, matching RESEARCH.md Pattern 1/2
- [Phase 02, Plan 02]: pandas-ta-classic==0.6.52's importable module name is pandas_ta_classic, not pandas_ta as 02-02-PLAN.md/RESEARCH.md assumed (RESEARCH.md had flagged this API shape as [ASSUMED]/unverified) — all src/features/ code and future usages must import pandas_ta_classic
- [Phase 02, Plan 02]: src/features/ mirrors src/data/prices.py's zero-I/O module-boundary discipline — every function takes an already-fetched DataFrame, never fetches its own data; assemble_feature_frame(df) is the single shared entry point for Phase 3/4 to import
- [Phase ?]: [Phase 02, Plan 03] src/data/profile.py CRUD chokepoint mirrors src/auth/session.py's _touch_last_login scoped-client pattern exactly (fresh create_client()+postgrest.auth() per call, never the shared cache_resource client)
- [Phase ?]: [Phase 02, Plan 03] upsert_profile is UPDATE-only (never upsert/insert) since public.profiles has no client-facing INSERT policy; upsert_holdings whitelists ticker/quantity/cost_basis per row to resist mass-assignment (T-02-04), proven by a real spoofed-user_id attack test
- [Phase ?]: [Phase 02, Plan 04] src/pages/profile.py's holdings invalid-ticker highlight is scoped to the whole st.data_editor widget (via its own key=), not per-row/per-cell, since st.data_editor exposes no finer-grained CSS hook -- a deliberate capability-driven adaptation of the UI-SPEC's per-row intent

### Pending Todos

None yet.

### Blockers/Concerns

- Research flagged: re-verify current free-tier rate limits (Gemini RPM/RPD, yfinance undocumented thresholds) at the start of Phase 1 and Phase 5 — research-time numbers move fast and should not be hardcoded into rate-limit logic.
- Research flagged: Prophet/cmdstanpy cold-start behavior on Streamlit Community Cloud's ephemeral build environment needs empirical validation in Phase 4, not just documentation research.
- Research flagged: Phase 3 needs its own research pass on cross-asset-class factor-weight normalization (stocks/24-7 crypto/forex/gold behave very differently) — no authoritative pattern found during initial research.
- Research flagged: Phase 5 (LangGraph 1.0 LTS + Gemini) is a newer, less-established combination — verify exact free-tier model list and rate limits at build time.
- [Phase 2] Recommendation-update-on-profile-edit clause of PROFILE-02 is explicitly deferred to Phase 3 per ROADMAP scoping — Phase 3's recommendation engine must actually pick up edited profiles, not just persist them.

## Deferred Items

Items acknowledged and carried forward from previous milestone close:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| v2 Requirement | SENT-01 — FinBERT news-sentiment scoring as optional prediction input | Deferred | Roadmap creation (2026-07-14) |
| v2 Requirement | AGENT-03 — Multi-turn conversational follow-up Q&A | Deferred | Roadmap creation (2026-07-14) |
| v2 Requirement | MODEL-01 — Additional prediction models (LSTM, ARIMA, Linear Regression) | Deferred | Roadmap creation (2026-07-14) |

## Session Continuity

Last session: 2026-08-05T01:06:25.387Z
Stopped at: Phase 3 planned (8 plans, verification passed)
Resume file: .planning/phases/03-deterministic-recommendation-engine/03-08-PLAN.md
