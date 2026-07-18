---
phase: 01-foundation-data-layer-caching-auth
plan: 04
subsystem: ui
tags: [streamlit, auth, st.navigation, st.form, supabase]

# Dependency graph
requires:
  - phase: 01-foundation-data-layer-caching-auth (Plan 02)
    provides: src/auth/session.py — sign_up, sign_in, sign_in_with_magic_link, require_auth(), sign_out()
provides:
  - render_login_page() — three-tab (Log In / Create Account / Magic Link) email/password + magic-link UI
  - render_home_page() — require_auth()-gated placeholder home page with Log Out
  - src/app.py entrypoint — conditional st.navigation hiding gated pages until login (D-03)
affects: [phase-2-profile-ui, phase-6-compliance-audit]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "st.form + explicit non-empty-field guard-clause before calling into src.auth.session (Streamlit's own form/text_input widgets do not natively block empty submission the way HTML5 required inputs do)"
    - "Repo-root sys.path insertion at the top of src/app.py so `streamlit run src/app.py` (which sets sys.path[0] to the script's own directory) can still resolve absolute src.* imports"
    - "Scoped CSS injection keyed off st.text_input's key= / the st-key-<key> wrapper class, to apply per-field red-border highlighting without a custom form-widget library"

key-files:
  created:
    - src/pages/login.py
    - src/pages/home.py
    - src/app.py
  modified: []

key-decisions:
  - "UI-SPEC's assumption that native Streamlit form validation blocks empty-field submission does not hold in practice — st.form/st.text_input have no built-in required-field blocking or visual cue. Added an explicit guard-clause plus st.warning plus red-border highlighting to actually deliver the UI-SPEC's intended empty-state behavior."
  - "streamlit run src/app.py needs a repo-root sys.path insertion before the src.* imports, since Streamlit sets sys.path[0] to the script's own directory (src/), not the project root."

patterns-established:
  - "Auth pages guard against empty required fields with an explicit non-empty check before any src.auth.session call, rather than relying on Streamlit's form widgets."

requirements-completed: [AUTH-01, AUTH-03]

coverage:
  - id: D1
    description: "Login/signup/magic-link page (src/pages/login.py) with Log In, Create Account, and Magic Link tabs, wired to src.auth.session, using exact Copywriting Contract button/error strings, no OAuth surface"
    requirement: "AUTH-01"
    verification:
      - kind: manual_procedural
        ref: "Human checkpoint (Task 3): create account, log in, log out, log back in, magic link tab, empty-submit, invalid-password — all confirmed working, approved after 3 rounds of fixes"
        status: pass
    human_judgment: false
  - id: D2
    description: "Placeholder home page (src/pages/home.py), require_auth()-gated as its first statement, exact 'You're in' empty-state copy, Log Out button"
    requirement: "AUTH-03"
    verification:
      - kind: manual_procedural
        ref: "Human checkpoint (Task 3): confirmed Home renders only when logged in, shows You're in heading/body, Log Out returns to login-only nav"
        status: pass
    human_judgment: false
  - id: D3
    description: "src/app.py entrypoint conditionally constructs st.navigation so gated pages are entirely absent from nav (not visible-but-redirecting) until login (D-03)"
    requirement: "AUTH-03"
    verification:
      - kind: manual_procedural
        ref: "Human checkpoint (Task 3): confirmed only the login page is reachable when logged out, no other page appears in sidebar/nav"
        status: pass
    human_judgment: false

# Metrics
duration: 105min
completed: 2026-07-18
status: complete
---

# Phase 1 Plan 4: Login/Signup Page, Placeholder Home Page, App Entrypoint Summary

**Three-tab Streamlit login/signup/magic-link page plus require_auth()-gated placeholder home page, wired through a conditional st.navigation entrypoint that hides gated pages entirely until login (D-03) — human-verified after 3 rounds of empty-field-handling fixes.**

## Performance

- **Duration:** 105 min (17:59 first commit to 19:42 last fix commit)
- **Started:** 2026-07-18T17:59:07-04:00
- **Completed:** 2026-07-18T19:42:52-04:00
- **Tasks:** 2 planned tasks + 1 checkpoint (approved)
- **Files modified:** 3 (src/pages/login.py, src/pages/home.py, src/app.py)

## Accomplishments
- render_login_page() — Log In / Create Account / Magic Link tabs, each in its own st.form, wired to src.auth.session sign_in/sign_up/sign_in_with_magic_link, rendering the exact Copywriting Contract error strings on failure and no OAuth/social-provider surface
- render_home_page() — require_auth() is the page's first executable statement (per D-04), renders the exact "You're in" empty-state heading/body, and a working Log Out button
- src/app.py — entrypoint that conditionally builds st.navigation off st.session_state.get("logged_in") so the Home page is entirely absent from nav (not visible-but-redirecting) until login, per D-03
- Human checkpoint (Task 3) approved after 3 rounds of fixes to the empty-field submission experience, which the plan's original UI-SPEC assumption did not anticipate

## Task Commits

Each task was committed atomically, with checkpoint-round fixes committed individually as they were found:

1. **Task 1: Login/signup page — email/password + magic link** - `55bb3a7` (feat)
2. **Task 2: Placeholder home page + app entrypoint navigation** - `ca704a0` (feat)
3. **Checkpoint fix 1: ModuleNotFoundError running `streamlit run src/app.py` directly** - `bbcc66a` (fix)
4. **Checkpoint fix 2: Guard against empty-field form submission crashing the app** - `c1d6c44` (fix)
5. **Checkpoint fix 3: Show validation message when required login fields are left blank** - `2254434` (fix)
6. **Checkpoint fix 4: Highlight empty required fields in red on failed form submission** - `40a441d` (fix)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `src/pages/login.py` - render_login_page(): three-tab auth UI, empty-field guard clause, st.warning empty-state copy, red-border highlighting on offending fields
- `src/pages/home.py` - render_home_page(): require_auth()-gated placeholder with "You're in" copy and Log Out
- `src/app.py` - entrypoint: repo-root sys.path insertion, st.Page construction, conditional st.navigation per D-03

## Decisions Made
- UI-SPEC's assumption that native Streamlit form validation blocks empty-field submission does not hold in practice (st.form/st.text_input have no built-in required-field blocking or visual cue) — the plan's own empty-state intent was instead delivered via an explicit guard-clause, a distinct st.warning message, and scoped CSS red-border highlighting, layered across the checkpoint round rather than baked into Task 1.
- `streamlit run src/app.py` sets `sys.path[0]` to the script's own directory (`src/`), not the repo root, breaking the `src.*` absolute imports used throughout the app — fixed by inserting the repo root onto `sys.path` as the first statements in `src/app.py`, mirroring the `pythonpath = ["."]` behavior already configured for pytest.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Resolved ModuleNotFoundError running `streamlit run src/app.py` directly**
- **Found during:** Human checkpoint (Task 3), step 2 (running the app locally)
- **Issue:** `streamlit run` sets `sys.path[0]` to the script's own directory (`src/`), not the repo root, so the `src.*` absolute imports in `app.py` failed with `ModuleNotFoundError: No module named 'src'`.
- **Fix:** Inserted the repo root onto `sys.path` as the first statements in `app.py`, before importing `src.pages.home`/`src.pages.login`, mirroring pytest's `pythonpath = ["."]` behavior. Added `# noqa: E402` on the post-sys.path imports since ruff flags module-level imports after other statements.
- **Files modified:** src/app.py
- **Verification:** Verified with `ruff check`; app launches without the import error.
- **Committed in:** bbcc66a

**2. [Rule 1 - Bug] Guarded against empty-field form submission crashing the app**
- **Found during:** Human checkpoint (Task 3), step 9 (submitting the login form with both fields empty)
- **Issue:** Streamlit's `st.form`/`st.text_input` have no built-in required-field blocking (unlike HTML5 `required` inputs) — an empty `form_submit_button` press still submitted blank strings, which `supabase_auth` raised as `AuthInvalidCredentialsError`, a client-side guard-clause exception (subclass of `AuthError`, not `AuthApiError`) that the existing `except AuthApiError` clause could never catch, crashing the app.
- **Fix:** Added an explicit non-empty check before calling `sign_in`/`sign_up`/`sign_in_with_magic_link` on all three tabs (Log In, Create Account, Magic Link), so no auth call is ever attempted with blank required fields.
- **Files modified:** src/pages/login.py
- **Verification:** Verified headlessly via `streamlit.testing.v1.AppTest`: all three empty-submit cases no longer crash and no longer call into `src.auth.session`; non-empty submit still calls through correctly.
- **Committed in:** c1d6c44

**3. [Rule 2 - Missing Critical] Added validation message when required login fields are left blank**
- **Found during:** Human checkpoint (Task 3), step 9 (re-verification after fix #2)
- **Issue:** Fix #2 silently guarded against the crash but gave the user no feedback at all when submitting with required fields blank — a missing-critical usability gap on the plan's own "form does not submit" empty-state requirement. The plan's underlying UI-SPEC assumption that native validation would supply this feedback did not hold (see Decisions Made).
- **Fix:** Added a plain `st.warning` on each tab telling the user to fill in the missing field(s), kept distinct from the invalid-credentials/magic-link-failure Copywriting Contract error strings (those remain reserved for actual failed auth attempts against non-empty credentials).
- **Files modified:** src/pages/login.py
- **Verification:** Verified via `streamlit.testing.v1.AppTest`: all three tabs now render a visible warning on empty submit and still make no auth call; non-empty submit unaffected.
- **Committed in:** 2254434

**4. [Rule 2 - Missing Critical] Highlighted empty required fields in red on failed form submission**
- **Found during:** Human checkpoint (Task 3), final re-verification round
- **Issue:** The `st.warning` text alone did not visually indicate *which* field(s) were empty, falling short of the UI-SPEC's "partial row" backstop expectation of per-field required-state highlighting.
- **Fix:** Added a `_highlight_empty_fields()` helper injecting scoped CSS keyed off each `st.text_input`'s `key=` (Streamlit renders an `st-key-<key>` class on the widget wrapper), reusing the UI-SPEC Destructive token (`#DC2626`). Tracks which field(s) were left blank at the most recent submit per tab in `st.session_state`, so only the offending field(s) get the red border, clearing once filled in and resubmitted. Additive to the `st.warning` copy from fix #3, not a replacement.
- **Files modified:** src/pages/login.py
- **Verification:** Manually confirmed during the human checkpoint's final approval pass.
- **Committed in:** 40a441d

---

**Total deviations:** 4 auto-fixed (1 blocking, 3 missing-critical/bug found during checkpoint verification)
**Impact on plan:** All four fixes were necessary to deliver the plan's own stated empty-field-validation intent, which the UI-SPEC had assumed (incorrectly) would come for free from Streamlit's native form widgets. No scope creep — no functionality was added beyond what Task 1's acceptance criteria already required.

## Issues Encountered
- UI-SPEC line 109 assumed native Streamlit form validation blocks empty submission with no custom copy needed; this did not hold in practice and required 3 rounds of checkpoint fixes (guard-clause, warning copy, red-border highlight) to deliver the intended behavior. See Deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The full Phase 1 login-to-home flow is built, human-verified, and matches D-01 through D-04 and the UI-SPEC Copywriting Contract exactly.
- AUTH-01 and AUTH-03 are satisfied end-to-end by this plan (session module from Plan 02 + this plan's UI wiring).
- Remaining Phase 1 work is Plan 05 (two-session isolation, cross-session persistence, and RLS enforcement tests) — no blockers identified for it.

---
*Phase: 01-foundation-data-layer-caching-auth*
*Completed: 2026-07-18*

## Self-Check: PASSED
