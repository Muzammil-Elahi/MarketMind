# Phase 2: Investor Profile + Feature Engineering Foundation - Pattern Map

**Mapped:** 2026-07-19
**Files analyzed:** 12
**Analogs found:** 10 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/pages/profile.py` | component (Streamlit page) | request-response (form load/save) | `src/pages/login.py` (form pattern) + `src/pages/home.py` (auth-gate pattern) | role-match |
| `src/data/profile.py` | service (CRUD helpers) | CRUD | `src/auth/session.py` (`_touch_last_login`) | exact |
| `supabase/migrations/<ts>_extend_profiles_and_create_holdings.sql` | migration | CRUD (schema) | `supabase/migrations/20260718204703_create_profiles.sql` | exact |
| `supabase/migrations/<ts>_grant_holdings_privileges.sql` | migration | CRUD (schema) | `supabase/migrations/20260718211140_grant_profiles_privileges.sql` | exact |
| `src/features/__init__.py` | utility (package init) | transform | `src/data/prices.py` (thin re-export module) | partial |
| `src/features/technical.py` | utility (pure transform) | transform | *(no direct analog — new pure-compute module)* | none |
| `src/features/feature_frame.py` | utility (pure transform, aggregator) | transform | `src/data/prices.py` (single public entry-point re-export pattern) | partial |
| `src/app.py` (modified) | config (page registration) | request-response | existing `src/app.py` itself | exact |
| `tests/test_profile_crud.py` | test | CRUD | `tests/test_profile_persistence.py` | exact |
| `tests/test_holdings_rls.py` | test | CRUD (RLS) | `tests/test_rls_policy.py` | exact |
| `tests/test_ticker_validation.py` | test | request-response (mocked I/O) | `tests/test_cache.py` | exact |
| `tests/test_features_technical.py` / `tests/test_features_leakage.py` | test | transform | `tests/test_cache.py` (structural/behavioral pytest style) | role-match |

## Pattern Assignments

### `src/pages/profile.py` (component, request-response)

**Analog 1 (auth gate + page shape):** `src/pages/home.py`

**Auth-gate pattern** (lines 14-16):
```python
def render_home_page() -> None:
    """Render the require_auth()-gated placeholder home page."""
    require_auth()
```
Apply verbatim as the first line of `render_profile_page()` — no inline auth logic, per D-04.

**Analog 2 (form + validation + highlight pattern):** `src/pages/login.py`

**Imports pattern** (lines 32-35):
```python
import streamlit as st
from supabase_auth.errors import AuthApiError

from src.auth.session import sign_in, sign_in_with_magic_link, sign_up
```
For `profile.py`, swap in: `from src.auth.session import require_auth`, `from src.data.profile import fetch_profile, upsert_profile, fetch_holdings, upsert_holdings`, `from src.data.prices import fetch_ohlcv`.

**Form + submit-button pattern** (lines 86-105):
```python
with log_in_tab:
    with st.form("log_in_form"):
        email = st.text_input("Email", key="log_in_email")
        password = st.text_input("Password", type="password", key="log_in_password")
        submitted = st.form_submit_button("Log In")
    if submitted:
        st.session_state["log_in_email_error"] = not email.strip()
        ...
```
Copy this `st.form(...)` + `st.form_submit_button(...)` + post-submit session_state error-flag shape for the scalar-fields form. Note per D-12 there is no separate create/edit branch — pre-fill `st.selectbox`/`st.multiselect`/`st.number_input` `value=`/`default=` args from `fetch_profile()`'s result (or field defaults if none exists).

**Red-border invalid-field highlight pattern** (lines 55-75, D-08 reuse target per UI-SPEC):
```python
def _highlight_empty_fields(*keys: str | None) -> None:
    active_keys = [key for key in keys if key]
    if not active_keys:
        return
    selector = ", ".join(f'div.st-key-{key} input' for key in active_keys)
    st.markdown(
        f"<style>{selector} {{ border: 1px solid {FIELD_ERROR_BORDER_COLOR} "
        "!important; border-radius: 0.5rem; }}</style>",
        unsafe_allow_html=True,
    )
```
UI-SPEC explicitly directs reusing this exact CSS-injection pattern (keyed off the invalid-ticker row/cell) for D-08's red-border highlight. `FIELD_ERROR_BORDER_COLOR = "#DC2626"` constant should be reused or re-declared identically (UI-SPEC Destructive token).

**Copy constants pattern** (lines 37-52): declare module-level string constants for each Copywriting Contract entry (`"We couldn't recognize \"{ticker}\" — check the symbol and try again."`, `"We couldn't save your profile. Please try again."`, `"Profile saved."`), exactly as `login.py` declares `INVALID_CREDENTIALS_ERROR`/`EMPTY_EMAIL_AND_PASSWORD_WARNING` — never inline the copy string at the call site.

**Holdings grid (no direct analog):** use `st.data_editor(df, num_rows="dynamic")` directly per RESEARCH.md Pattern/UI-SPEC — no existing codebase file uses `st.data_editor` yet; follow RESEARCH.md's Code Examples section for shape, and D-08's post-submit validation loop (call `fetch_ohlcv(ticker, period="5d")` per row, check `status == "live" and not df.empty`).

---

### `src/data/profile.py` (service, CRUD)

**Analog:** `src/auth/session.py`, specifically `_touch_last_login` (lines 179-197)

**Scoped-client CRUD pattern** (lines 179-197):
```python
def _touch_last_login(access_token: str, user_id: str) -> None:
    scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    scoped_client.postgrest.auth(access_token)
    scoped_client.table("profiles").update(
        {"last_login": datetime.now(timezone.utc).isoformat()}
    ).eq("user_id", user_id).execute()
```
Every function in `src/data/profile.py` (`fetch_profile`, `upsert_profile`, `fetch_holdings`, `upsert_holdings`) must follow this exact shape: build a fresh `create_client(...)` (never the shared `get_supabase_client()`), attach `.postgrest.auth(access_token)`, execute one scoped query. Never persist the scoped client — matches RESEARCH.md's own `upsert_holdings` example (RESEARCH.md Code Examples section), which is this same pattern applied to `holdings`.

**Imports pattern** (lines 34-39, `session.py` module-level):
```python
from supabase import Client, create_client
from src.config import get_config
from src.data.supabase_client import get_supabase_client
```
`profile.py` needs `create_client`/`get_config` for the scoped-write pattern; it does NOT need `get_supabase_client` unless a read-only, non-auth-scoped path is added (it should not be — every profile/holdings read/write needs the caller's token per RLS, matching `_touch_last_login`, not the shared client's anon-only context).

**Whitelisted-payload discipline (Security):** construct each CRUD payload as an explicit dict of only the expected columns (RESEARCH.md's "mass assignment" mitigation) — never pass raw `st.session_state`/widget dicts straight through, mirroring how `_touch_last_login` builds `{"last_login": ...}` explicitly rather than forwarding an arbitrary dict.

---

### `supabase/migrations/<ts>_extend_profiles_and_create_holdings.sql` (migration, CRUD/schema)

**Analog:** `supabase/migrations/20260718204703_create_profiles.sql`

**RLS policy shape** (lines 18-27):
```sql
alter table public.profiles enable row level security;

create policy "Users can view their own profile"
  on public.profiles for select
  using ( (select auth.uid()) = user_id );

create policy "Users can update their own profile"
  on public.profiles for update
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );
```
Reuse this exact `(select auth.uid()) = user_id` shape for all four `holdings` policies (select/insert/update/delete) — RESEARCH.md Pattern 1 already gives the full `create table public.holdings (...)` + policy block to copy verbatim (RESEARCH.md lines 226-260).

**Critical divergence to apply:** `profiles` has NO client-facing INSERT policy (trigger-only); `holdings` MUST have explicit INSERT and DELETE policies (RESEARCH.md "Important divergence" callout) — do not copy the `profiles` INSERT omission onto `holdings`.

**Nullable-columns constraint (Pitfall 2):** every new `profiles` column added by this migration must be nullable, no `NOT NULL`, no `default` — `handle_new_user()`'s trigger (same file, lines 32-42) only inserts `user_id`/`created_at`, and must not be modified this phase.

---

### `supabase/migrations/<ts>_grant_holdings_privileges.sql` (migration)

**Analog:** `supabase/migrations/20260718211140_grant_profiles_privileges.sql`

**Full file to mirror** (lines 1-15):
```sql
-- Deviation (Rule 1 - bug fix, found during 01-02 Task 2): ...
-- On a self-managed local Supabase CLI stack (no dashboard auto-grant step),
-- Postgres requires both a GRANT *and* a passing RLS policy ...

grant select, update on public.profiles to authenticated;
```
For `holdings`, grant all four verbs (`select, insert, update, delete on public.holdings to authenticated`) plus `grant all on public.holdings to service_role` (per RESEARCH.md Pitfall 3 and the second grant migration precedent below). Per RESEARCH.md guidance, fold this into the SAME migration as the table/policy creation (not a separate follow-up file) — the two-migration split above is only how Phase 1 happened to discover the bug retroactively, not the recommended forward pattern.

**Service-role grant analog:** `supabase/migrations/20260719001207_grant_profiles_service_role.sql` (not read in full — same one-line `grant all on public.profiles to service_role;` shape, needed for `tests/test_holdings_rls.py`'s service-role-keyed setup calls, mirroring `test_profile_persistence.py`'s use of `SERVICE_ROLE_KEY`).

---

### `src/features/technical.py` + `feature_frame.py` (utility, transform)

**No direct in-repo analog** — this is the first pure-compute, zero-I/O module in the codebase. Follow RESEARCH.md's Code Examples section directly (already vetted against project conventions):

```python
import pandas as pd

def compute_returns(df: pd.DataFrame) -> pd.Series:
    return df["close"].pct_change()

def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return compute_returns(df).rolling(window, center=False).std()

def compute_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return df.ta.sma(length=window)

def compute_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return df.ta.rsi(length=window)
```

**Module-boundary discipline analog:** `src/data/prices.py` (full file, 12 lines) — the thin, single-purpose re-export/docstring-enforced-boundary style:
```python
"""Public price-data entry point for the rest of the codebase.
...this module never imports ``yfinance`` -- ``src/data/cache.py`` remains
the single chokepoint permitted to do so...
"""
from src.data.cache import fetch_ohlcv
__all__ = ["fetch_ohlcv"]
```
Apply the same discipline to `src/features/__init__.py` and to `feature_frame.py`'s docstring: state explicitly that `technical.py`/`feature_frame.py` have zero Streamlit/I/O imports and that callers must pass in a DataFrame already obtained from `fetch_ohlcv()` — never fetch their own data.

**Critical rule carried from Pitfall 4 / Anti-Patterns:** never pass `center=True` to any `.rolling()` call in this module — enforce via the D-11 leakage test itself.

---

### `src/app.py` (modified, config)

**Analog:** the file's own existing shape (lines 25-36):
```python
from src.pages.home import render_home_page
from src.pages.login import render_login_page

login_page = st.Page(render_login_page, title="Log In", url_path="login")
home_page = st.Page(render_home_page, title="Home", url_path="home", default=True)

if st.session_state.get("logged_in"):
    pg = st.navigation({"Home": [home_page]})
else:
    pg = st.navigation([login_page])
```
Add `from src.pages.profile import render_profile_page`, a `profile_page = st.Page(render_profile_page, title="Investor Profile", url_path="profile")`, and add it to the `{"Home": [home_page]}` dict's auth-gated branch only (never the logged-out `st.navigation([login_page])` list) — matches the conditional-nav pattern already established (D-03/Pattern 5).

---

### Test files

**`tests/test_profile_crud.py`** — Analog: `tests/test_profile_persistence.py` (full file). Copy its `_fetch_profile_row`-style scoped-client helper (lines 17-30) and `test_user_factory` fixture usage; add scalar-field round-trip assertions plus a `test_edit_reflects_immediately` test asserting no `st.cache_data` decorator wraps the profile-read function (structural check, same style as `test_cache.py`'s `test_fetch_ohlcv_uses_configured_ttl_not_a_literal`, lines 87-94, which uses `inspect.getsource()` for a structural assertion).

**`tests/test_holdings_rls.py`** — Analog: `tests/test_rls_policy.py` (full file, 82 lines). Copy the two-user (`two_users` fixture) cross-user-select/cross-user-update/positive-control three-test shape verbatim, retargeted at `holdings` (insert via one user, assert a second user's scoped client gets zero rows; also add insert/delete RLS tests since `holdings` — unlike `profiles` — has client-facing INSERT/DELETE policies to verify, per the Pattern 1 divergence above).

**`tests/test_ticker_validation.py`** — Analog: `tests/test_cache.py`, specifically the mocking style (lines 9-16, 34-44):
```python
from unittest.mock import patch
...
with patch("src.data.cache.yf.download", return_value=_sample_df()) as mock_download:
    first_df, first_status = cache.fetch_ohlcv("AAPL", "1y")
```
Mock `src.data.prices.fetch_ohlcv` (or patch `src.data.cache.yf.download` directly) to return an empty DataFrame for the invalid-ticker case (Pitfall 1) and assert the validation helper flags it — same `unittest.mock.patch` style, no live network call.

**`tests/test_features_technical.py` / `tests/test_features_leakage.py`** — No direct in-repo analog (first pure-pandas test module); use the exact leakage-test code already fully specified in RESEARCH.md's Code Examples section (`_sample_ohlcv`, `test_truncation_invariance_no_future_data_changes_past_features`, `test_synthetic_future_signal_never_appears_before_its_source_date`) — copy verbatim, it is planner-ready.

## Shared Patterns

### Auth gate (`require_auth()` first-and-only)
**Source:** `src/pages/home.py` lines 14-16, `src/auth/session.py` lines 112-153
**Apply to:** `src/pages/profile.py` — call `require_auth()` as the very first line of `render_profile_page()`, no inline auth logic.

### Scoped-client writes (never the shared `cache_resource` client for user-scoped ops)
**Source:** `src/auth/session.py` `_touch_last_login` (lines 179-197), module docstring (lines 1-29)
**Apply to:** All of `src/data/profile.py`'s CRUD functions — always `create_client(...)` + `.postgrest.auth(access_token)` per call, never `get_supabase_client()` for anything that must be RLS-scoped as a specific user.

### Copy-constants-not-inline-strings
**Source:** `src/pages/login.py` lines 37-52
**Apply to:** `src/pages/profile.py` — declare each UI-SPEC Copywriting Contract string as a module-level constant.

### CSS-injection field-highlight (D-08 invalid ticker)
**Source:** `src/pages/login.py` `_highlight_empty_fields` (lines 55-75) + `FIELD_ERROR_BORDER_COLOR` (line 52)
**Apply to:** `src/pages/profile.py`'s holdings-grid invalid-ticker highlight — UI-SPEC explicitly calls for reusing this exact pattern.

### RLS policy shape `(select auth.uid()) = user_id`
**Source:** `supabase/migrations/20260718204703_create_profiles.sql` lines 20-27
**Apply to:** All four `holdings` table policies in the new migration — plus remembering `holdings` needs INSERT/DELETE policies that `profiles` does not have.

### Migration GRANT-alongside-RLS (self-managed stack requirement)
**Source:** `supabase/migrations/20260718211140_grant_profiles_privileges.sql`
**Apply to:** The `holdings` migration — include GRANT statements for `authenticated`/`service_role` in the same or immediately-following migration, not deferred.

### Structural/behavioral pytest style, no live network calls for unit-level tests
**Source:** `tests/test_cache.py` (`unittest.mock.patch`, `inspect.getsource()` structural checks)
**Apply to:** `tests/test_ticker_validation.py`, and the structural "no `st.cache_data`" assertion in `tests/test_profile_crud.py`.

### Real-local-stack, two-user RLS proof style
**Source:** `tests/test_rls_policy.py`, `tests/test_profile_persistence.py`
**Apply to:** `tests/test_holdings_rls.py`, `tests/test_profile_crud.py` — no mocking, real `npx supabase start` stack, `test_user_factory`/`two_users` fixtures from `tests/conftest.py`.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/features/technical.py` | utility | transform | First pure-pandas, zero-I/O module in the codebase — no prior file has this shape. Use RESEARCH.md's Code Examples directly (already vetted); apply `src/data/prices.py`'s "thin boundary module" discipline for `__init__.py`/`feature_frame.py` docstrings only. |
| `tests/test_features_technical.py` / `tests/test_features_leakage.py` | test | transform | No prior pure-pandas test file exists; RESEARCH.md's Code Examples section is planner-ready and should be copied near-verbatim rather than adapted from an existing test. |

## Metadata

**Analog search scope:** `src/`, `tests/`, `supabase/migrations/`
**Files scanned:** `src/auth/session.py`, `src/pages/login.py`, `src/pages/home.py`, `src/data/prices.py`, `src/data/cache.py`, `src/data/supabase_client.py`, `src/app.py`, `src/config.py`, `supabase/migrations/20260718204703_create_profiles.sql`, `supabase/migrations/20260718211140_grant_profiles_privileges.sql`, `tests/test_rls_policy.py`, `tests/test_profile_persistence.py`, `tests/test_cache.py`
**Pattern extraction date:** 2026-07-19
