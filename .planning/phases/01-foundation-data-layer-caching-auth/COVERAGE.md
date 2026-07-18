# Phase 1 — Supabase Auth/Postgres API Coverage Matrix

**Generated:** 2026-07-18 (plan-phase, API Coverage Decision Checkpoint)
**Detector:** fired — this phase integrates the Supabase Auth/Postgres API via `supabase-py` 2.31.0.

Default posture: every capability starts as `INTEGRATE`. This table is the subtraction record — each `OPT-OUT` carries a one-line reason.

| capability | decision | reason |
|---|---|---|
| `sign_up` (email/password) | INTEGRATE | AUTH-01, D-01 — core signup path |
| `sign_in_with_password` | INTEGRATE | AUTH-01, D-01 — core login path |
| `sign_in_with_otp` (magic link) | INTEGRATE | AUTH-01, D-01 — passwordless login path, explicitly locked |
| `sign_out` | INTEGRATE | Needed for the "Log Out" CTA on the home page (UI-SPEC Copywriting Contract) |
| `get_user` | INTEGRATE | D-04 — the only server-verified identity check `require_auth()` may use |
| `get_session` | OPT-OUT | D-04/Pitfall 1 forbid using it as a trust source; tokens are sourced directly from sign-in/sign-up responses and `st.session_state`, never re-read via `get_session()` |
| refresh session/token (`refresh_session`) | INTEGRATE | Needed so `require_auth()` can silently renew an expired access token via the refresh token before forcing re-login — required for ROADMAP success criterion #1 ("stays logged in across a page reload / new browser session") |
| password reset/recovery | OPT-OUT | Not needed — D-01 scopes Phase 1 auth to email/password + magic link only; magic link already gives a passwordless recovery path (a user who forgets their password can always log in via magic link), so no separate reset flow is required for AUTH-01/02/03 |
| `update_user` (change email/password) | OPT-OUT | Not needed — CONTEXT.md's Phase Boundary states the persisted `profiles` row is a minimal stub, not the real profile builder; no account-settings UI exists in Phase 1 |
| OAuth providers | OPT-OUT | Explicitly out of scope — D-01: "No OAuth/social login in this phase." |
| admin/service-role operations | OPT-OUT | Explicitly forbidden — RESEARCH.md Pitfall 5 / Security Domain: the service-role/secret key must never be loaded into the deployed Streamlit process; the app's client uses the anon/publishable key only |
| RLS policy enforcement | INTEGRATE | D-11 (required, not deferred) — the sole enforcement point for per-user `profiles` access |
| Postgres CRUD on the `profiles` table | INTEGRATE | D-10, AUTH-02 — trigger-based INSERT at signup, SELECT/UPDATE for `last_login` persistence proof |
| realtime subscriptions | OPT-OUT | Not needed — Phase 1 has no live-updating UI surface; no requirement calls for realtime sync |
| storage (file/object storage) | OPT-OUT | Not needed — no file/avatar upload feature exists in AUTH-01/02/03 or CONTEXT.md's Phase 1 scope |

**Coverage:** 8 INTEGRATE / 7 OPT-OUT of 15 capabilities. Every OPT-OUT carries a reason above; none are silent.
