# Phase 1: Foundation — Data Layer, Caching & Auth - Pattern Map

**Mapped:** 2026-07-17
**Files analyzed:** 11
**Analogs found:** 0 / 11 (greenfield project — no application code exists in the repo)

## Greenfield Notice

This repository currently contains **only planning docs** (`.planning/`), a `.claude/` config directory, and a placeholder `README.md`. There is no `src/`, no Python application code, and no prior test suite. Confirmed via `Glob("**/*.py")` (zero results) and a directory listing of the repo root.

**Consequence:** There are no existing codebase analogs for any file in this phase. Every pattern below is sourced directly from `01-RESEARCH.md`'s `## Code Examples` / `## Architecture Patterns` sections, which in turn cite official Supabase/Streamlit/tenacity documentation fetched during research (see RESEARCH.md `## Sources`, HIGH-confidence primary citations). **This phase establishes the baseline patterns and module structure that all later phases (2-6) will follow and extend** — the planner should treat the excerpts below as the canonical first-instance implementation, not as "copy from an existing file."

## File Classification

| New File | Role | Data Flow | Closest Analog | Match Quality |
|----------|------|-----------|-----------------|----------------|
| `src/auth/session.py` | middleware | request-response | *(none — greenfield)* | no analog |
| `src/data/supabase_client.py` | service | CRUD | *(none — greenfield)* | no analog |
| `src/data/cache.py` | service | request-response (cache-then-fetch) | *(none — greenfield)* | no analog |
| `src/data/prices.py` | service | request-response | *(none — greenfield)* | no analog |
| `src/pages/login.py` | component (Streamlit page) | request-response | *(none — greenfield)* | no analog |
| `src/pages/home.py` | component (Streamlit page) | request-response | *(none — greenfield)* | no analog |
| `src/app.py` | route/controller (entrypoint) | request-response | *(none — greenfield)* | no analog |
| `src/config.py` | config | — | *(none — greenfield)* | no analog |
| `supabase/migrations/*.sql` (profiles table + trigger + RLS) | migration | CRUD | *(none — greenfield)* | no analog |
| `tests/test_auth_isolation.py` | test | event-driven (session simulation) | *(none — greenfield)* | no analog |
| `tests/test_cache.py` | test | request-response | *(none — greenfield)* | no analog |

## Pattern Assignments

### `src/auth/session.py` (middleware, request-response)

**Analog:** none — first instance of this pattern in the codebase. Source: RESEARCH.md Pattern 1 / Pattern 2, citing `supabase.com/docs/reference/python/auth-getuser` (HIGH confidence, official docs).

**Core pattern — server-verified `require_auth()` gate** (RESEARCH.md lines 199-217, 428-446):
```python
# auth/session.py
import streamlit as st
from supabase_auth.errors import AuthApiError

def require_auth():
    token = st.session_state.get("access_token")
    if not token:
        st.switch_page("pages/login.py")
        st.stop()
    try:
        return get_supabase_client().auth.get_user(token).user
    except AuthApiError:
        st.session_state.clear()  # per-session only — never touches other users
        st.warning("Your session expired — please log in again.")
        st.switch_page("pages/login.py")
        st.stop()
```

**Auth pattern — email/password sign-up, no confirmation required (D-02)** (RESEARCH.md lines 417-426):
```python
response = supabase.auth.sign_up({"email": user_email, "password": user_password})
# With "Confirm email" OFF, response.session is populated immediately.
st.session_state["access_token"] = response.session.access_token
st.session_state["refresh_token"] = response.session.refresh_token
```

**Auth pattern — magic link** (RESEARCH.md lines 406-415):
```python
response = supabase.auth.sign_in_with_otp({
    "email": user_email,
    "options": {"email_redirect_to": "https://<your-deployed-app>.streamlit.app"},
})
# Session established automatically when the user clicks the emailed link.
```

**Error handling:** `AuthApiError` from `supabase_auth.errors` caught around `get_user()`; `st.session_state.clear()` on failure (scoped to the calling session only — never a global/shared object). RESEARCH.md flags the exact import path as `[ASSUMED]` (Open Question 2) — verify against the installed `supabase`/`supabase_auth` package at implementation time.

**Critical constraint (non-discretionary, D-04/D-06):** Never call `get_session()` for authorization — only `get_user()` performs server-side JWT validation (Pitfall 1). Never `st.cache_resource` anything containing a token or user identity (Pitfall 2).

---

### `src/data/supabase_client.py` (service, CRUD)

**Analog:** none — first instance. Source: RESEARCH.md Pattern 2 (lines 219-236).

**Core pattern — stateless cached client**:
```python
# data/supabase_client.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    # Safe to share: stateless connection using the anon/publishable key.
    # NEVER call .auth.sign_in_* on this cached instance.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
```

**Security constraint:** Client must be constructed with the anon/publishable key only. The service-role/secret key must never be loaded into the deployed Streamlit process (Pitfall 5, RESEARCH.md lines 392-396).

---

### `src/data/cache.py` (service, request-response / cache-then-fetch chokepoint)

**Analog:** none — first instance. Source: RESEARCH.md Pattern 3 (lines 238-284).

**Imports pattern**:
```python
import sqlite3, time
import streamlit as st
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
```

**Core pattern — cache chokepoint (st.cache_data → SQLite → tenacity → yfinance)**:
```python
DB_PATH = "data/price_cache.db"

def _init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT, period TEXT, fetched_at REAL, payload_json TEXT,
                PRIMARY KEY (ticker, period)
            )
        """)

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(Exception),  # narrow to requests.HTTPError/YFRateLimitError in impl
)
def _fetch_live(ticker: str, period: str):
    return yf.download(ticker, period=period, progress=False)  # bulk download, not per-ticker loop

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_ohlcv(ticker: str, period: str = "1y"):
    _init_db()
    try:
        df = _fetch_live(ticker, period)
        _write_through(ticker, period, df)
        return df, "live"
    except Exception:
        stale = _read_disk_cache(ticker, period)
        if stale is not None:
            return stale, "stale"  # UI renders degraded-state message using this flag
        raise
```

**Error handling:** try live fetch → on any exception fall back to stale SQLite row + degraded-state flag → if no cache at all, re-raise for an explicit failure UI state (never crash unhandled — Pitfall 4, Security Domain "DoS" row).

**Security note:** all SQLite queries must be parameterized (`?` placeholders) — never string-interpolate ticker/user input (ASVS V5, Security Domain table).

---

### `src/data/prices.py` (service, request-response)

**Analog:** none. This is a thin domain wrapper around `data/cache.py::fetch_ohlcv` per the Recommended Project Structure (RESEARCH.md lines 172-191): `fetch_ohlcv(ticker, period) -> DataFrame`. No separate excerpt beyond Pattern 3 above — `prices.py` is the public-facing function signature layer; `cache.py` is the only module that imports `yfinance` directly.

---

### `src/pages/login.py` / `src/pages/home.py` (component — Streamlit pages, request-response)

**Analog:** none. Source: RESEARCH.md Pattern 5 (lines 332-347) for the navigation-gating shell these pages plug into.

**Core pattern — conditional `st.navigation` hide-not-redirect gating** (this lives in `app.py` but directly determines how `login.py`/`home.py` are wired):
```python
# app.py
import streamlit as st

if st.session_state.get("logged_in"):
    pg = st.navigation({"Account": [logout_page], "Home": [home_page]})
else:
    pg = st.navigation([login_page])

pg.run()
```

`home.py` and every other gated page must call `require_auth()` (from `auth/session.py`) at the top of the page — per D-04, no per-page inline auth checks, always route through the central helper.

---

### `src/app.py` (route/controller, entrypoint)

**Analog:** none. Same Pattern 5 excerpt as above — this file owns the conditional `st.navigation()` construction and is the single place that decides page visibility based on `st.session_state.get("logged_in")`.

---

### `src/config.py` (config)

**Analog:** none. No RESEARCH.md code excerpt is prescriptive here beyond usage conventions already documented in project CLAUDE.md (`st.secrets` in production, `python-dotenv` locally — never hardcode either). Cache TTL constant: `ttl=3600` (1 hour, D-08).

---

### `supabase/migrations/*.sql` — `profiles` table + trigger + RLS (migration, CRUD)

**Analog:** none. Source: RESEARCH.md Pattern 4 (lines 286-328), cited from official Supabase docs (`supabase.com/docs/guides/auth/managing-user-data`, HIGH confidence).

**Core pattern — schema, RLS policies, and auto-provisioning trigger**:
```sql
create table public.profiles (
  user_id uuid not null references auth.users(id) on delete cascade,
  created_at timestamptz not null default now(),
  last_login timestamptz,
  primary key (user_id)
);

alter table public.profiles enable row level security;

create policy "Users can view their own profile"
  on public.profiles for select
  using ( (select auth.uid()) = user_id );

create policy "Users can update their own profile"
  on public.profiles for update
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );
-- INSERT is handled by the SECURITY DEFINER trigger below, not client inserts.

create function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.profiles (user_id, created_at)
  values (new.id, now());
  return new;
end;
$$;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();
```

**Note:** column name is `user_id` (matching D-10 literally) referencing `auth.users(id)` as the PK — same semantics as the official `id`-named example (RESEARCH.md lines 330).

---

### `tests/test_auth_isolation.py` (test, event-driven / session-simulation)

**Analog:** none — no prior test suite exists. Source: RESEARCH.md Pitfall 3 (lines 380-384) and Validation Architecture table.

**Core pattern requirement (critical — do not build a test that only proves the testing framework works):**
The test must exercise the real leak vector, not just `session_state` equality:
1. Run user A's session through the real `require_auth()` / `get_supabase_client()` code path.
2. Capture whatever object is behind the `st.cache_resource`-decorated `get_supabase_client()`.
3. Run user B's session.
4. Assert: (a) the cached client object is the *same instance* across both (expected — stateless), (b) it contains no trace of user A's token/identity, (c) user B's `require_auth()` returns user B's identity, not user A's.

Uses `st.testing.v1.AppTest` (`docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest`, HIGH confidence, official docs) — but per Pitfall 3, a naive two-`AppTest` `session_state`-only comparison **always passes even with a real leak**, so it must not be the sole assertion.

---

### `tests/test_cache.py` (test, request-response)

**Analog:** none. Source: Validation Architecture table (RESEARCH.md lines 505-523) — unit test, mock `yf.download`/tenacity retry paths, no live network. Assert: (1) repeated fetch within TTL hits `st.cache_data` without a new network call, (2) simulated `yf.download` failure falls back to stale SQLite row + degraded flag (Pattern 3's `except Exception` branch), (3) SQLite queries use parameterized placeholders.

## Shared Patterns

### Identity confinement (auth token / user id)
**Source:** RESEARCH.md Pattern 2, Pitfall 2, Security Domain table.
**Apply to:** `auth/session.py`, `data/supabase_client.py`, every gated page.
**Rule:** Token/user-identity lives only in `st.session_state`. Anything wrapped in `st.cache_resource` (e.g., the Supabase client) must remain stateless and identical for every user — never cache the result of a sign-in call.

### Server-verified auth check, never client-trusted
**Source:** RESEARCH.md Pattern 1, Pitfall 1.
**Apply to:** `auth/session.py::require_auth()`, called at the top of every gated page (no per-page inline checks per D-04).
```python
get_supabase_client().auth.get_user(token)  # NOT get_session()
```

### Cache-first chokepoint for all external data
**Source:** RESEARCH.md Pattern 3.
**Apply to:** `data/cache.py` is the only module permitted to `import yfinance`. All other modules call `data/prices.py`/`data/cache.py` wrappers. Same chokepoint discipline should be reused by later phases for NewsAPI/Gemini calls (per project CLAUDE.md's mandated `tenacity` + `st.cache_data(ttl=...)` convention at every external-call boundary).

### Parameterized SQL / no string-interpolated queries
**Source:** RESEARCH.md Security Domain (ASVS V5), Pitfall discussion of SQL injection via SQLite ticker cache.
**Apply to:** `data/cache.py` and any future SQLite access.

### RLS as the sole enforcement point for per-user data access
**Source:** RESEARCH.md "Don't Hand-Roll" table, Pattern 4.
**Apply to:** `profiles` table (this phase) and every future user-scoped table — never re-implement access control as an app-layer `if row.user_id == current_user_id` filter; that is a documented anti-pattern ("second, weaker enforcement point").

## No Analog Found

All 11 files listed above have no analog — this is a greenfield repository with zero prior application code. Every pattern is sourced from `01-RESEARCH.md`'s official-docs-derived code examples rather than from codebase precedent. Later phases (2-6) should treat the module structure and patterns established here (`auth/session.py`, `data/cache.py`, `data/supabase_client.py`, the `require_auth()` gate, the single-chokepoint external-call pattern) as the analogs to copy from going forward.

## Metadata

**Analog search scope:** Entire repository root (`Glob("**/*.py")`, directory listing of repo root) — confirmed zero existing Python/application files.
**Files scanned:** 0 application files (repo contains only `.planning/`, `.claude/`, `.git/`, `README.md`)
**Pattern extraction date:** 2026-07-17
**Pattern source:** `01-RESEARCH.md` (`## Architecture Patterns`, `## Code Examples`, `## Common Pitfalls`), which itself cites official Supabase (`supabase.com/docs`) and Streamlit (`docs.streamlit.io`) documentation as primary/HIGH-confidence sources.
