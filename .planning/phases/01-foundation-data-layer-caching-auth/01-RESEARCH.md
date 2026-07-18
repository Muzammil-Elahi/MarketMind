# Phase 1: Foundation — Data Layer, Caching & Auth - Research

**Researched:** 2026-07-17
**Domain:** Multi-user Streamlit auth (Supabase) + resilient, cache-first market-data layer
**Confidence:** MEDIUM (official Supabase/Streamlit docs fetched directly for API signatures and RLS/navigation patterns — HIGH-tier content; yfinance rate-limit behavior and Streamlit Cloud disk-persistence behavior remain community-sourced/undocumented by the vendor — MEDIUM/LOW-tier content, flagged inline)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Auth method & signup flow**
- **D-01:** Auth methods: email/password **and** Supabase magic-link (passwordless) login. No OAuth/social login in this phase.
- **D-02:** Email verification is **not** required — users can log in immediately after signup (lower friction, favors quick demoing of a portfolio project over combating throwaway signups).
- **D-03:** Unauthenticated users see a single login/signup page; auth-gated pages are hidden from `st.navigation` entirely until logged in (not visible-but-redirecting).

**Session isolation pattern**
- **D-04:** Use a central `require_auth()` helper called at the top of every page — it reads the token from `st.session_state`, re-verifies server-side with Supabase, and halts rendering if invalid. No per-page inline auth checks.
- **D-05:** Add an automated two-concurrent-session isolation test (simulate two sessions with different logged-in users, assert no `st.session_state` or cached data cross-contaminates). This directly verifies Phase 1 success criterion #2.
- **D-06 (Claude's discretion):** Whether the Supabase client object itself is `st.cache_resource`-shared (stateless connection) vs. constructed per-call — deferred to implementation time. Constraint that is NOT discretionary: the auth token/user identity must never live in a cached/global object, only in `st.session_state`.

**Caching strategy — TTLs & disk persistence**
- **D-07:** Build a disk-persisted price cache (SQLite or parquet) in addition to `st.cache_data`, so a cold Streamlit Community Cloud container (post-sleep) doesn't immediately re-hammer yfinance. Foundational — later phases inherit this cold-start resilience.
- **D-08:** Live price data TTL: **1 hour** (`st.cache_data(ttl=3600)`).
- **D-09 (Claude's discretion):** Exact degraded/stale-cache fallback UI copy and disk-cache implementation details (SQLite vs. parquet, file layout) — follow research's guidance (`data/cache.py` single chokepoint).

**Minimal persisted-data proof for AUTH-02**
- **D-10:** Persist a `profiles` stub table with `user_id`, `created_at`, `last_login` — the same table Phase 2 will extend with real profile fields.
- **D-11:** Explicit Supabase Row Level Security (RLS) policy on `profiles` (a user can only read/write their own row) is **required** in this phase, with a test verifying it — not deferred.

### Claude's Discretion
- D-06: Supabase client caching mechanics (`st.cache_resource` vs. per-call construction) — see this research's recommendation below.
- D-09: Disk-cache file format and fallback UI copy — this research recommends SQLite (see Standard Stack / Architecture Patterns).
- Base app shell / page inventory beyond "login page + auth-gated pages hidden until logged in" — planner should use judgment (likely: login page + a minimal placeholder/home page, since Profile/Recommendation/Prediction pages don't exist until later phases).

### Deferred Ideas (OUT OF SCOPE)
- Base app shell / navigation page inventory beyond the four discussed decision areas was not deep-dived by the user this session.
- Exact Supabase client caching mechanics (D-06) and disk-cache file format (D-09) — left to Claude's discretion at planning/implementation time (addressed below).
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AUTH-01 | User can sign up and log in (Supabase auth) | Official `supabase-py` auth API confirmed (sign_up / sign_in_with_password / sign_in_with_otp) — see Standard Stack, Code Examples |
| AUTH-02 | User's profile, watchlist, and history persist across sessions and devices | `profiles` stub table + official Supabase trigger pattern (`handle_new_user()` on `auth.users` insert) confirmed via official docs — see Code Examples, Architecture Patterns |
| AUTH-03 | Auth/session state is strictly scoped per user (no session or cached-object leakage across concurrent users) | `require_auth()` pattern using `get_user()` (server-verified) not `get_session()` (client-trusted); RLS policy pattern confirmed via official docs; AppTest two-instance isolation test pattern researched — see Common Pitfalls, Code Examples, Validation Architecture |
</phase_requirements>

## Summary

This phase has two largely independent halves that share one architectural discipline: **never let anything user-specific live in a process-wide object.** The auth half wires `supabase-py` 2.31.0's email/password and magic-link flows to a Streamlit `require_auth()` gate that re-verifies the JWT server-side (`get_user()`, not the client-trusted `get_session()`) on every page load, backed by a Postgres RLS policy on a minimal `profiles` table populated automatically via a `handle_new_user()` trigger on `auth.users` — this is the officially documented Supabase pattern, not a custom design. The caching half wraps every `yfinance` call in a single chokepoint (`data/cache.py`) that layers `st.cache_data(ttl=3600)` over a stdlib-`sqlite3` disk cache, with `tenacity` backoff around the network call itself — yfinance is an unofficial scraper with no published rate limits, so resilience has to be assumed, not looked up.

The single highest-leverage finding from this research is the concrete mechanism for testing D-05 (two-concurrent-session isolation): `st.testing.v1.AppTest` instances are isolated by construction (each has its own `session_state`), so a naive two-`AppTest` test would pass even with a real leak. The thing that actually needs testing is whether an `st.cache_resource`-wrapped object or module-level global accidentally carries a user identity — because `cache_resource` storage is process-wide and genuinely **is** shared across two `AppTest` instances running in the same pytest process, this is exactly the mechanism that reproduces the real-world Streamlit multi-user leak class documented in the project's own PITFALLS.md. The test must assert on that shared surface, not just on `session_state` equality.

**Primary recommendation:** Build `auth/session.py` (`require_auth()`, `get_user()`-based server verification, sign_up/sign_in/magic-link wrappers), `data/cache.py` (single yfinance chokepoint: `st.cache_data(ttl=3600)` → SQLite disk cache → `tenacity`-wrapped `yf.download()`), and a `profiles` table with the official Supabase trigger + RLS pattern — then verify isolation with a two-`AppTest` test that specifically asserts no identity leaks through any `cache_resource`-wrapped object, not just through `session_state`.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| User signup / login (email+password, magic link) | API / Backend (Supabase Auth/GoTrue) | Frontend Server (Streamlit renders forms, holds token) | Supabase owns credential storage, password hashing, and JWT issuance — Streamlit never touches raw credentials beyond passing them to the SDK call |
| Session token storage & per-request verification | Frontend Server (Streamlit `st.session_state`, per-connection) | API / Backend (`get_user()` server-side JWT validation) | Token must live only in the per-session Streamlit object; but trust in that token is only as good as the server-side re-verification call each page makes |
| Multipage navigation gating (hide pages until logged in) | Frontend Server (Streamlit `st.navigation`) | — | Pure Streamlit routing concern, no backend involvement |
| Market data fetch (yfinance) | API / Backend (external, unofficial Yahoo endpoints) | Database / Storage (disk cache absorbs repeat load) | Yahoo is the system of record for prices; the disk cache exists specifically to reduce load on that unreliable external tier |
| In-memory request-scoped caching (`st.cache_data`) | Frontend Server (Streamlit process) | — | Lives entirely inside the Streamlit process's cache machinery, resets on cold start |
| Disk-persisted price cache (SQLite) | Database / Storage | Frontend Server (read/write via `data/cache.py`) | Survives sleep/wake within one container's lifetime; the Streamlit process is just a client of this local store |
| `profiles` table persistence | Database / Storage (Supabase Postgres) | API / Backend (Supabase Auth trigger writes the row) | The `handle_new_user()` trigger fires inside Postgres, not in application code — persistence and provisioning both live in the database tier |
| RLS policy enforcement | Database / Storage (Postgres RLS) | — | Enforced at the database engine level; must not be re-implemented as an app-layer permission check (that would be a second, weaker enforcement point) |

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| streamlit | 1.59.2 `[VERIFIED: PyPI]` | Frontend + app framework, `st.navigation`/`st.Page`, `st.cache_data`/`st.cache_resource` | Confirmed current via `pip index versions streamlit` (2026-07-17); matches project STACK.md pin |
| supabase (`supabase-py`) | 2.31.0 `[VERIFIED: PyPI]` | Auth (GoTrue) + Postgres client | Confirmed current via `pip index versions supabase`; exact match to project STACK.md pin |
| yfinance | 1.5.1 `[VERIFIED: PyPI]` | Market data fetch (equities/ETFs/crypto/forex/gold) | Confirmed current via `pip index versions yfinance`; STACK.md's "~1.5.x" estimate confirmed exact |
| tenacity | 9.1.4 `[VERIFIED: PyPI]` | Retry/backoff decorator around yfinance calls | Confirmed current via `pip index versions tenacity`; STACK.md left this unpinned ("latest") — now pinnable |
| python-dotenv | 1.2.2 `[VERIFIED: PyPI]` | Local env var loading (Gemini/Supabase keys) in dev | Confirmed current via `pip index versions python-dotenv` |
| `sqlite3` (Python stdlib) | n/a — stdlib | Disk-persisted price cache backing `data/cache.py` | Resolves D-09: zero new dependency, trivial ticker+timestamp keyed queries, sufficient for this scale — see Architecture Patterns for why SQLite over parquet |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | 9.1.1 `[VERIFIED: PyPI]` | Test framework — `AppTest`-based isolation test, RLS test, cache/backoff unit tests | Every automated test this phase adds (D-05, D-11) |
| ruff | 0.15.22 `[VERIFIED: PyPI]` | Lint/format | Project convention per STACK.md |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Hand-rolled SQLite disk cache | `yfinance-cache` (community wrapper) `[ASSUMED — package existence from WebSearch, not independently verified against PyPI/registry this session]` | The yfinance maintainer team explicitly points frustrated users at this wrapper (`ValueRaider/yfinance-cache`) to "fetch smarter" — worth a spike if the hand-rolled cache in `data/cache.py` proves insufficient, but building it in-house first keeps the dependency surface minimal for a $0-budget foundation phase and avoids taking on an unverified package this early. Not recommended for this phase; flagged as a future escape hatch only. |
| SQLite for the disk cache | Parquet (`pyarrow`) | Parquet is better suited to large columnar batch writes/reads; SQLite is the lower-friction choice for a small, incrementally-updated, single-key-lookup ticker cache and adds zero new dependencies (stdlib `sqlite3`) — recommended for this phase (resolves D-09) |
| Legacy Supabase `anon`/`service_role` JWT keys | New `sb_publishable_*` / `sb_secret_*` key format | Both work today — Supabase added the new format as "an improvement over the old JWT-based `service_role` key" but legacy keys "remain valid until you explicitly disable them." New Supabase projects show the new key names by default in the dashboard; document whichever the project's actual dashboard shows rather than assuming — see State of the Art |

**Installation:**
```bash
pip install streamlit==1.59.2 supabase==2.31.0 yfinance==1.5.1 tenacity==9.1.4 python-dotenv==1.2.2
pip install pytest==9.1.1 ruff==0.15.22  # dev
# sqlite3 is Python stdlib — no install needed
```

**Version verification:** All versions above verified against the live PyPI index on 2026-07-17 via `pip index versions <package>` (not training-data recall) — see per-row `[VERIFIED: PyPI]` tags.

## Package Legitimacy Audit

| Package | Registry | Age (evidence) | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----------------|-----------|-------------|---------|-------------|
| streamlit | PyPI | Version history to `0.1` (pip index) — mature, ~7+ yr project | tool: unavailable for PyPI | github.com/streamlit/streamlit | SUS (tool) → **Approved** | Tool flags "too-new"/"unknown-downloads" — see note below |
| supabase | PyPI | Version history to `0.0.3` (pip index) — mature project | tool: unavailable for PyPI | github.com/supabase/supabase-py (tool returned `repoUrl: null`, verified independently) | SUS (tool) → **Approved** | Same tool limitation; repo independently confirmed via official docs during this research |
| yfinance | PyPI | Version history to `0.1.36` (pip index) — mature, ~9+ yr project | tool: unavailable for PyPI | github.com/ranaroussi/yfinance | SUS (tool) → **Approved** | Same tool limitation; also directly cited throughout project-level STACK.md/PITFALLS.md research |
| tenacity | PyPI | Version history to `2.0.0` (pip index) — mature project | tool: unavailable for PyPI | github.com/jd/tenacity | SUS (tool) → **Approved** | Same tool limitation |
| python-dotenv | PyPI | Version history to `0.1.0` (pip index) — mature, ~10+ yr project | tool: unavailable for PyPI | github.com/theskumar/python-dotenv | SUS (tool) → **Approved** | Same tool limitation |
| pytest | PyPI | Version history to `2.0.0` (pip index) — mature, ~20+ yr project | tool: unavailable for PyPI | github.com/pytest-dev/pytest | SUS (tool) → **Approved** | Same tool limitation |
| ruff | PyPI | Version history to `0.0.13` (pip index) — mature project | tool: unavailable for PyPI | docs.astral.sh/ruff | SUS (tool) → **Approved** | Same tool limitation |

**Note on uniform SUS verdicts:** `gsd-tools query package-legitimacy check` returned `SUS` for every package in this batch with reasons `"too-new"` and/or `"unknown-downloads"`. Inspecting the raw signals shows `publishedAt` reflects each package's **latest release date** (all recent, since these are actively maintained projects), not first-publish date, and `weeklyDownloads` is `null` for every PyPI package checked — indicating the legitimacy checker's download/age heuristics are tuned for the npm ecosystem and do not have reliable PyPI-specific signals. This was cross-checked against `pip index versions` for every package (showing 20–260+ historical releases each, i.e., years of continuous maintenance) and against official GitHub repos / docs cited throughout this research. All seven packages are approved. **Packages removed due to `[SLOP]` verdict:** none. **Packages flagged as suspicious `[SUS]`:** none after cross-verification (see note above) — no `checkpoint:human-verify` gate is warranted for this specific batch, but the planner should be aware the legitimacy-check tool is currently unreliable for PyPI packages and should not skip its own judgment for future phases' PyPI installs either.

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────┐
                         │   Browser (per-session)  │
                         └────────────┬─────────────┘
                                      │ HTTP (Streamlit session)
                                      ▼
┌──────────────────────────────────────────────────────────────────────┐
│                     STREAMLIT PROCESS (single, shared)                 │
│                                                                          │
│  entrypoint (app.py)                                                    │
│    │                                                                     │
│    ├─▶ st.session_state.logged_in? ──No──▶ st.navigation([login_page])  │
│    │                                                                     │
│    └─▶ Yes ──▶ require_auth() [auth/session.py]                         │
│                    │                                                     │
│                    ├─▶ read token from st.session_state (per-session)   │
│                    ├─▶ supabase.auth.get_user(token)  ◀── SERVER-VERIFIED│
│                    │        (never trust get_session() for authz)       │
│                    └─▶ invalid? halt render : continue                  │
│                                      │                                   │
│                         st.navigation({gated pages...})                 │
│                                      │                                   │
│                    ┌─────────────────┴──────────────────┐               │
│                    ▼                                     ▼               │
│         data/cache.py (single chokepoint)      data/supabase_client.py  │
│                    │                                     │               │
│         st.cache_data(ttl=3600)?                 st.cache_resource      │
│           hit ──▶ return cached df               (stateless client only,│
│           miss ─┐                                 NEVER token/identity) │
│                  ▼                                                       │
│         SQLite disk cache (data/price_cache.db)                         │
│           hit + fresh ──▶ return                                        │
│           miss/stale ──┐                                                │
│                         ▼                                                │
│         tenacity-wrapped yf.download() ──▶ Yahoo (unofficial, 429-prone)│
│           success ──▶ write-through to SQLite + st.cache_data           │
│           failure ──▶ fall back to stale SQLite row + degraded-UI flag  │
└──────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │  Supabase (Auth + Postgres) │
                         │  auth.users ──trigger──▶ public.profiles │
                         │  RLS: auth.uid() = user_id  │
                         └─────────────────────────┘
```

### Recommended Project Structure
```
src/
├── auth/
│   └── session.py          # sign_up/sign_in_with_password/sign_in_with_otp wrappers,
│                            # require_auth() central gate, get_user()-based verification
├── data/
│   ├── prices.py            # yfinance wrapper: fetch_ohlcv(ticker, period) -> DataFrame
│   ├── cache.py              # single chokepoint: st.cache_data -> SQLite -> tenacity(yfinance)
│   └── supabase_client.py    # st.cache_resource-shared stateless client; profiles CRUD
├── pages/
│   ├── login.py               # single unauthenticated entry page (D-03)
│   └── home.py                 # minimal placeholder landing page post-login
├── app.py                      # entrypoint: conditional st.navigation router
└── config.py                    # env vars (st.secrets/dotenv), cache TTL constants
tests/
├── conftest.py                  # shared fixtures
├── test_auth_isolation.py       # D-05: two-AppTest concurrent-session test
├── test_cache.py                 # TTL + backoff + stale-fallback behavior
└── test_rls.sql (or pgTAP)       # D-11: RLS policy verification
```

### Pattern 1: `require_auth()` with server-verified token, never client-trusted session

**What:** A single function, called at the top of every gated page, that (1) reads the access token out of `st.session_state`, (2) calls `supabase.auth.get_user(token)` — which validates the JWT against the Supabase server, not just reading the locally cached session — and (3) halts rendering (`st.stop()`) if invalid/expired, after attempting a `refresh_session()` if a refresh token is available.
**When to use:** Every gated page, always — this is D-04's non-discretionary requirement.
**Why `get_user()` and not `get_session()`:** Official Supabase docs are explicit that `get_session()` returns "locally cached session data [that] should not be relied upon as a source of trusted data on the server as it could be tampered with," while `get_user()` "validates the user's access token JWT on the server" `[CITED: supabase.com/docs/reference/python/auth-getuser]`.

**Example:**
```python
# auth/session.py
# Source: pattern derived from official docs.supabase.com/reference/python (auth-getuser, auth-signinwithpassword)
import streamlit as st
from supabase_auth.errors import AuthApiError

def require_auth():
    token = st.session_state.get("access_token")
    if not token:
        st.stop()
    try:
        user_response = get_supabase_client().auth.get_user(token)
    except AuthApiError:
        st.session_state.clear()  # per-session only — never touches other users
        st.error("Session expired — please log in again.")
        st.stop()
    return user_response.user
```

### Pattern 2: Stateless client via `st.cache_resource`, identity always in `st.session_state`

**What:** The Supabase client object itself (URL + anon key, no per-user state) is safe to `st.cache_resource`-share across the process — it's a connection object, not a session. The access token, refresh token, and user id are never stored on that client or in any `cache_resource`-wrapped object; they live only in `st.session_state`.
**When to use:** Resolves D-06. This is the standard "resource vs. data" distinction from the project's own PITFALLS.md Pitfall 7, applied concretely to the Supabase client.
**Trade-offs:** Slightly more plumbing (token must be passed explicitly into every `get_user()`/query call rather than living on a shared client instance already logged in), but this is precisely what prevents the documented Streamlit multi-user session-leak class.

```python
# data/supabase_client.py
import streamlit as st
from supabase import create_client, Client

@st.cache_resource
def get_supabase_client() -> Client:
    # Safe to share: stateless connection using the anon/publishable key.
    # NEVER call .auth.sign_in_* on this cached instance and expect the
    # resulting session to be scoped to one user — pass tokens explicitly.
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
```

### Pattern 3: Cache-first data access with disk fallback (single chokepoint)

**What:** `data/cache.py` is the only place that imports `yfinance`. Every call goes: `st.cache_data(ttl=3600)` → SQLite disk cache (survives cold start within a container's lifetime) → `tenacity`-wrapped live fetch → write-through to both layers on success, fall back to stale SQLite row + a degraded-UI flag on failure.
**When to use:** Always — resolves D-07/D-08/D-09.
**Why SQLite over parquet for this specific cache:** a ticker+timestamp keyed, incrementally-updated, small-row-count cache is a natural fit for SQLite's indexed point lookups; parquet is optimized for large columnar batch scans and pulls in `pyarrow` as an extra dependency for no benefit at this scale `[CITED: general Python data-engineering practice, cross-checked via WebSearch, MEDIUM confidence]`.

```python
# data/cache.py
# Source: pattern combining official st.cache_data docs + tenacity retry docs +
# community-reported yfinance 429 mitigation (see Common Pitfalls)
import sqlite3, time
import streamlit as st
import yfinance as yf
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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
        raise  # no cache at all — let the page show an explicit failure state
```

### Pattern 4: Auto-provisioned `profiles` row via database trigger, not application code

**What:** A `handle_new_user()` Postgres function + `AFTER INSERT ON auth.users` trigger inserts the `profiles` stub row automatically at signup — this is the **official** Supabase pattern, not a custom design, and means `AUTH-02`'s persistence proof doesn't depend on application code remembering to write the row after every signup path (password AND magic link both go through `auth.users` insert, so both are covered by one trigger).
**When to use:** Resolves D-10. `[CITED: supabase.com/docs/guides/auth/managing-user-data]`

```sql
-- Source: official Supabase docs — supabase.com/docs/guides/auth/managing-user-data
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
-- Note: INSERT is handled by the SECURITY DEFINER trigger below, not by client
-- inserts — so no client-facing INSERT policy is needed for the stub row itself.

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

> **Naming note:** CONTEXT.md's D-10 specifies a `user_id` column; the official Supabase example uses `id` as the PK directly referencing `auth.users(id)`. Both are the same concept (1:1 with the auth user) — the SQL above uses `user_id` as the column name to match D-10 literally while keeping it as the PK referencing `auth.users(id)`, so RLS/trigger semantics are identical to the official pattern.

### Pattern 5: Conditional `st.navigation` for hide-not-redirect gating

**What:** Construct the pages list/dict passed to `st.navigation()` conditionally on `st.session_state`. Pages excluded from that structure are **not just hidden from the menu** — direct URL access to an excluded page renders Streamlit's "Page not found" state, which is exactly D-03's requirement (hidden, not visible-but-redirecting). `[CITED: docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation]`

```python
# app.py
# Source: official Streamlit docs pattern (login/logout example)
import streamlit as st

if st.session_state.get("logged_in"):
    pg = st.navigation({"Account": [logout_page], "Home": [home_page]})
else:
    pg = st.navigation([login_page])

pg.run()
```

### Anti-Patterns to Avoid
- **Trusting `get_session()` for authorization:** it's locally cached client data that "could be tampered with" per official docs — only `get_user()` is server-verified. Using `get_session()` inside `require_auth()` would silently defeat AUTH-03.
- **Caching the Supabase client *after* calling `sign_in_with_password` on it:** if the signed-in client itself gets `st.cache_resource`-wrapped, the next user to hit that cached function gets the *previous* user's authenticated client — a textbook version of the leak this phase exists to prevent. Sign-in calls must be made fresh per request using tokens routed through `st.session_state`, never baked into the cached client.
- **Looping single-ticker `yf.Ticker(x).history()` calls:** community reports consistently link per-ticker loops (vs. bulk `yf.download(tickers=[...])`) to faster 429 onset under any multi-asset/multi-user load.
- **Treating a local disk cache as durable storage:** local filesystem writes on Streamlit Community Cloud survive a sleep→wake resume (same container) but are lost on redeploy (a `git push` triggers a full rebuild) — never treat the SQLite cache as anything but disposable, rebuildable state.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Password hashing, JWT issuance, session/refresh-token lifecycle | Custom auth backend | Supabase Auth (GoTrue) via `supabase-py` | This is exactly what Supabase Auth exists for; a hand-rolled version is a large, security-critical surface area for zero product differentiation |
| Per-row access control ("user can only see their own profile") | App-layer `if row.user_id == current_user_id` filtering in Python | Postgres Row Level Security policies | RLS is enforced at the database engine regardless of which code path queries it; an app-layer-only check is a single point of failure that a future bug/new query path can silently bypass — this is the exact gap PITFALLS.md flags as "RLS not on by default" |
| Retry/backoff around flaky network calls | Bespoke `try/except` + manual `time.sleep()` loops | `tenacity` (`@retry`, `stop_after_attempt`, `wait_exponential`) | Declarative, testable, and the project's own STACK.md already mandates this — bare retry loops given documented rate-limit volatility risk worsening IP-level blocking |
| Auto-provisioning a user's first-party data row at signup | An application-code "after signup, call insert profile" step that must be remembered on every signup code path (password + magic link) | A `SECURITY DEFINER` trigger on `auth.users` | One trigger covers every way a row can land in `auth.users`, including flows added later (OAuth, if ever added) — application code can't forget to call it because it never has to |

**Key insight:** Every "don't hand-roll" item above maps to a single officially-documented Supabase/Streamlit/tenacity mechanism. The temptation in this phase specifically is to solve session isolation and RLS with more application code (more `if` checks, more manual re-fetching) — the correct answer in both cases is to push the guarantee down to a layer that enforces it structurally (the database engine for RLS, the framework's testing/caching primitives for isolation) rather than layering more Python logic that can drift out of sync.

## Common Pitfalls

### Pitfall 1: `get_session()` used where `get_user()` is required
**What goes wrong:** `require_auth()` reads a cached session object and treats its presence as proof of a valid, current login.
**Why it happens:** `get_session()` is the more obvious/discoverable method name and returns something that *looks* like enough information (it has a `user` field).
**How to avoid:** `require_auth()` must call `get_user(token)` specifically — official docs state this is the one that "validates the user's access token JWT on the server" `[CITED: supabase.com/docs/reference/python/auth-getuser]`.
**Warning signs:** A `require_auth()` implementation with no network call to Supabase inside it — if there's no actual round-trip on the auth-check path, it's trusting local state.

### Pitfall 2: `st.cache_resource` misused for anything post-authentication
**What goes wrong:** A developer caches the *result* of a sign-in call (a logged-in client, or a dict containing the token) via `st.cache_resource` to "avoid re-authenticating on every rerun" — a real, documented pain point in the Streamlit community (a Streamlit Community thread on exactly this problem was found with no resolved answer, underscoring how easy this mistake is to reach for).
**Why it happens:** `st.cache_resource` genuinely does solve the "don't reload the client every rerun" problem for the *client itself* — the bug is scope creep from "cache the connection" to "cache the authenticated session."
**How to avoid:** Cache only the unauthenticated client (Pattern 2 above); persist per-user tokens exclusively in `st.session_state`, and accept that re-verifying via `get_user()` on each gated page load is the cost of correctness, not a bug to optimize away.
**Warning signs:** Any `st.cache_resource`-decorated function whose return value differs based on *which user* called it.

### Pitfall 3: Two-`AppTest`-instance test passes without actually proving isolation
**What goes wrong:** A test creates two `AppTest.from_file(...)` instances, sets different `session_state` values on each, runs both, and asserts `session_state` differs — and this **always passes**, even in the presence of a real leak, because each `AppTest` instance owns its own `session_state` object by construction. This gives false confidence that D-05 is verified.
**Why it happens:** `session_state` isolation between `AppTest` instances is guaranteed by the testing framework's design, not by anything the application code did correctly — so testing only `session_state` tests the framework, not the app.
**How to avoid:** The test must specifically exercise the actual leak vector: run user A's session through `require_auth()`/`get_supabase_client()`, capture whatever object is behind any `st.cache_resource`-decorated function, run user B's session, and assert (a) that shared object is the *same instance* (expected — it's a stateless client, that's fine) but (b) it contains no trace of user A's token/identity, and (c) user B's `require_auth()` call returns user B's identity, not user A's. This is the concrete difference between a test that looks right and a test that actually verifies D-05.
**Warning signs:** A passing isolation test that never actually calls the real `require_auth()`/cached-client code path — i.e., it tests `session_state` directly rather than exercising the auth module.

### Pitfall 4: Local disk cache assumed durable across redeploys
**What goes wrong:** The SQLite disk cache is built to survive Streamlit Cloud's sleep/wake cycle (the stated goal, D-07) but the team also comes to rely on it surviving indefinitely — then a code push (redeploy) wipes it and the app briefly re-hammers yfinance on the next cold start, exactly the scenario the cache was meant to prevent.
**Why it happens:** "Sleep" and "redeploy" are easy to conflate; community reports confirm waking a sleeping app resumes the existing container, but a `git push`-triggered redeploy rebuilds from scratch and loses local files `[CITED: Streamlit Community discussion threads, cross-corroborated, MEDIUM confidence — not an official Streamlit doc guarantee]`.
**How to avoid:** Design the disk cache purely as a performance optimization with no durability guarantee — on a fully empty cache (post-redeploy), the app must still degrade gracefully (first-fetch latency + possible transient rate-limit risk) rather than assume a warm cache always exists.
**Warning signs:** Code that errors (rather than falls back) when `data/price_cache.db` doesn't exist yet.

### Pitfall 5: RLS policy technically present but bypassed by using the `service_role`/`sb_secret_*` key in application code
**What goes wrong:** A Supabase client constructed with the service-role (or new-format secret) key bypasses RLS entirely — "RLS provides zero protection because the service_role key explicitly bypasses it" — so even a correctly-written policy provides no actual protection if the app's Supabase client uses that key instead of the anon/publishable key.
**Why it happens:** Some Supabase tutorials/dashboards surface the service-role key prominently, and it's tempting to use it during development because it "just works" without fighting RLS policies while iterating.
**How to avoid:** The Streamlit app's client (`data/supabase_client.py`) must be constructed with the anon/publishable key only; the service-role/secret key should never be loaded into the deployed Streamlit process at all.
**Warning signs:** `SUPABASE_SERVICE_ROLE_KEY` (or `SUPABASE_SECRET_KEY`) present anywhere in `.streamlit/secrets.toml` or app-facing env vars.

### Pitfall 6: yfinance looped per-ticker without backoff, treated as if it had a documented rate limit
**What goes wrong:** Code assumes there's a specific numeric threshold (e.g., "N requests per minute") to engineer around, when in fact Yahoo publishes no rate-limit numbers for the unofficial endpoints yfinance scrapes — behavior is empirically variable (one community report found ~100 requests before needing a 30s pause, but noted even that pattern eventually stopped working).
**Why it happens:** Developers want a concrete number to code a rate limiter against, and community posts sometimes state numbers confidently despite them being anecdotal, not documented limits.
**How to avoid:** Don't hardcode a specific req/min threshold into the backoff logic; use `tenacity`'s exponential backoff (retry on failure, not a fixed pre-emptive throttle) plus the cache-first architecture (Pattern 3) so the *steady-state* request volume against Yahoo stays low regardless of the exact undocumented threshold. Re-verify this assumption periodically — it was explicitly flagged in STATE.md as needing re-verification at the start of this phase, and this research confirms no vendor-published number exists to lock in.
**Warning signs:** A constant like `MAX_REQUESTS_PER_MINUTE = 60` hardcoded anywhere in `data/`.

## Code Examples

### Magic-link (passwordless) sign-in
```python
# Source: official docs.supabase.com/reference/python/auth-signinwithotp
response = supabase.auth.sign_in_with_otp({
    "email": user_email,
    "options": {"email_redirect_to": "https://<your-deployed-app>.streamlit.app"},
})
# Session is established automatically when the user clicks the emailed link —
# no separate client-side verify_otp() call needed for the magic-link (vs. numeric-code) flow.
```

### Email/password sign-up (no email confirmation required, per D-02)
```python
# Source: official docs.supabase.com/reference/python/auth-signup
response = supabase.auth.sign_up({"email": user_email, "password": user_password})
# With "Confirm email" OFF in the Supabase project's auth settings, response.session
# is populated immediately (not null) — this is what makes D-02's "log in immediately
# after signup" behavior possible without extra app-side logic.
st.session_state["access_token"] = response.session.access_token
st.session_state["refresh_token"] = response.session.refresh_token
```

### Server-verified auth check with error handling
```python
# Source: pattern derived from official docs.supabase.com/reference/python/auth-getuser
# + auth-error-codes; AuthApiError import path per supabase-py's auth-py subpackage
from supabase_auth.errors import AuthApiError

def require_auth():
    token = st.session_state.get("access_token")
    if not token:
        st.switch_page("pages/login.py")
        st.stop()
    try:
        return get_supabase_client().auth.get_user(token).user
    except AuthApiError:
        st.session_state.clear()
        st.warning("Your session expired — please log in again.")
        st.switch_page("pages/login.py")
        st.stop()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `anon` / `service_role` JWT-based Supabase API keys | `sb_publishable_*` (client-safe) / `sb_secret_*` (server-only) key format | Rolled out ahead of 2026 per official docs; legacy keys explicitly still supported ("remain valid until you explicitly disable them") | Whichever key format the project's actual Supabase dashboard shows should be used consistently in `.streamlit/secrets.toml` — don't assume `anon`/`service_role` naming from older tutorials matches what a newly-created project's dashboard displays `[CITED: supabase.com/docs/guides/getting-started/api-keys]` |
| Single train/test-style ad hoc auth smoke test | `st.testing.v1.AppTest`-based automated isolation test (D-05) | `AppTest` is Streamlit's own supported testing framework, not a third-party pattern | Enables a genuinely automated, CI-runnable version of the "two concurrent browser sessions" manual test PITFALLS.md originally described only as a manual verification step |

**Deprecated/outdated:** None identified specific to this phase's stack beyond the key-naming shift above; the project-level STACK.md's broader deprecation notes (legacy `google-generativeai`, Gemini 2.0 Flash) are out of scope for Phase 1.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|----------------|
| A1 | `yfinance-cache` (`ValueRaider/yfinance-cache`) exists as a maintainer-recommended wrapper package | Standard Stack / Alternatives Considered | Low — explicitly flagged as a future escape hatch, not adopted this phase; if the package name is wrong or the project is abandoned, no code in this phase depends on it |
| A2 | SQLite is the better choice over parquet for this specific cache shape | Architecture Patterns, Pattern 3 | Low-medium — this is a reasoned judgment (indexed point lookups vs. columnar batch scans) cross-checked against general Python data-engineering practice via WebSearch, not an authoritative source; if wrong, the fix is a contained swap inside `data/cache.py` since D-09 already scoped this as Claude's discretion |
| A3 | Streamlit Community Cloud "waking from sleep resumes the existing container" (vs. "redeploy rebuilds from scratch, wiping local disk") | Architecture Patterns anti-patterns, Pitfall 4 | Medium — sourced from Streamlit Community discussion threads, not an official Streamlit docs guarantee; if the actual behavior differs (e.g., sleep/wake also sometimes rebuilds), the SQLite disk cache's assumed benefit (surviving cold starts) would need re-validation empirically once deployed |
| A4 | yfinance's ~100-requests-then-30s-pause anecdote is not a reliable, current numeric limit | Common Pitfalls, Pitfall 6 | Low — explicitly treated as unreliable/anecdotal in this research and not hardcoded into any recommended code; the recommendation (don't hardcode a threshold, rely on backoff + cache) is robust to this being wrong in either direction |

**If this table is empty:** N/A — see entries above; all are LOW-to-MEDIUM risk and none block planning, but A3 in particular should be spot-checked once the app is actually deployed to Streamlit Community Cloud (the phase's own success criteria don't require deployment-time verification, but a later hardening phase should confirm it).

## Open Questions

1. **Exact current Supabase free-tier project-pause behavior (7-day inactivity)** (RESOLVED — non-blocking for Phase 1, revisit at deployment/hardening phase)
   - What we know: Project-level PITFALLS.md documents a 7-day database-inactivity pause on the free tier as a known constraint (not re-verified in this research pass, since it's not specific to Phase 1's implementation questions).
   - What's unclear: Whether a scheduled lightweight query/ping is needed starting this phase, or can wait until closer to deployment.
   - Recommendation: Not blocking for Phase 1 planning (no live deployment happens in this phase); flag for the deployment/hardening phase as project-level research already does.

2. **`AuthApiError` import path stability across `supabase-py` minor versions** (RESOLVED — deferred to implementation time, see 01-02 Task 2)
   - What we know: The current pattern is `from supabase_auth.errors import AuthApiError` (confirmed via WebSearch-sourced community example, not an official docs page fetched directly in this session).
   - What's unclear: Whether this import path is guaranteed stable/public API vs. an internal path that could move between `supabase-py` releases.
   - Recommendation: Planner/implementer should confirm the exact exception import at implementation time by inspecting the installed `supabase`/`supabase_auth` package's `__init__.py`, rather than trusting this path as authoritative — treat as `[ASSUMED]`. 01-02-PLAN.md Task 2's action explicitly requires verifying this import path against the installed package before use.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|-------------|-----------|---------|----------|
| Python | Runtime | ✓ | 3.13.7 | STACK.md recommends 3.11/3.12 (Prophet/cmdstanpy wheel lag) — **not a blocker for Phase 1** since this phase's dependencies (streamlit/supabase-py/yfinance/tenacity) all have 3.13 wheels; flag for Phase 4 (Prophet) planning, not this phase |
| pip | Package installs | ✓ | 26.0.1 | — |
| git | Version control | ✓ | 2.52.0 | — |
| Docker | Optional: local Supabase CLI dev stack for offline RLS/pgTAP testing | ✓ | 29.1.3 | — |
| Node.js / npm | Optional: `npx supabase` CLI invocation | ✓ | node 22.19.0 / npm 11.16.0 | — |
| Supabase CLI | Local Postgres/Auth stack for testing RLS without hitting the live free-tier project | ✗ | — | Install via `npx supabase` (no global install needed, uses available Node/npm) — see Validation Architecture |

**Missing dependencies with no fallback:** None — Supabase CLI has a viable `npx`-based fallback given Node/npm are present.

**Missing dependencies with fallback:** Supabase CLI (use `npx supabase start` — Docker confirmed available, no separate binary install required).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (none installed yet — greenfield project) |
| Config file | none — see Wave 0 |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|--------------|
| AUTH-01 | Signup + login succeeds, session persists across reload | integration (mocked Supabase client or local `supabase start` stack) | `pytest tests/test_auth_flow.py -x` | ❌ Wave 0 |
| AUTH-02 | Signed-in user's `profiles` row is written and re-readable in a new session | integration (requires a live or local-CLI Supabase Postgres) | `pytest tests/test_profile_persistence.py -x` | ❌ Wave 0 |
| AUTH-03 | Two concurrent sessions never cross-contaminate `session_state` or any `cache_resource`-wrapped object | integration, `st.testing.v1.AppTest`-based (see Pattern/Pitfall 3 above) | `pytest tests/test_auth_isolation.py -x` | ❌ Wave 0 |
| AUTH-03 (RLS) | A user cannot read/write another user's `profiles` row at the database level | integration, pgTAP against local Supabase CLI stack (`supabase start` via Docker — confirmed available) OR a Python integration test using two distinct authenticated clients against a real/local Supabase project | `supabase test db` (pgTAP) or `pytest tests/test_rls_policy.py -x` | ❌ Wave 0 |
| Cache/backoff behavior (success criterion #3) | Repeated fetch within TTL hits cache; simulated failure degrades gracefully | unit (mock `yf.download`/`tenacity` retry paths, no live network) | `pytest tests/test_cache.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `requirements-dev.txt` or dev extras — `pytest` install
- [ ] `tests/conftest.py` — shared fixtures: a `mock_supabase_client` fixture for unit-level auth tests, and (if the local CLI route is chosen) a `supabase start`/`stop` session fixture for integration-level RLS tests
- [ ] `pytest.ini` or `pyproject.toml` `[tool.pytest.ini_options]` — test discovery config
- [ ] Decide (at planning time, not research time): mock Supabase entirely for AUTH-01/02 tests vs. stand up the local Supabase CLI Docker stack for real integration tests. Docker is confirmed available on this machine (see Environment Availability), making the local-stack route viable, but it adds test-suite runtime and a Docker dependency for CI — the planner should make this call explicitly rather than leave it implicit.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|----------------|---------|-------------------|
| V2 Authentication | yes | Supabase Auth (GoTrue) — email/password + magic link; never hand-roll credential storage/hashing |
| V3 Session Management | yes | Token in `st.session_state` only (never `cache_resource`/global); `get_user()` server-side re-verification per request, not client-trusted `get_session()` |
| V4 Access Control | yes | Postgres RLS policy (`auth.uid() = user_id`) as the enforcement point, not app-layer filtering alone |
| V5 Input Validation | yes | Email/password fields via Streamlit form widgets — rely on Supabase Auth's own server-side validation for credential format/strength rather than reimplementing; sanitize any ticker/text inputs before use in SQLite queries (parameterized queries, never string-interpolated SQL) |
| V6 Cryptography | yes | Never hand-roll — password hashing and JWT signing are entirely owned by Supabase Auth; the app never sees or stores a raw password beyond passing it to `sign_up`/`sign_in_with_password` |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Cross-user session/token leakage via `st.cache_resource` or module-level globals | Information Disclosure | Token/identity confined to `st.session_state`; `cache_resource` reserved for stateless objects only (Pattern 2) |
| RLS bypass via `service_role`/secret key used in client-facing app code | Elevation of Privilege | App's Supabase client constructed with anon/publishable key only; service-role/secret key never loaded into the deployed Streamlit process (Pitfall 5) |
| SQL injection via unparameterized ticker/user input into the SQLite disk cache | Tampering | Always use parameterized `sqlite3` queries (`?` placeholders), never f-string/format SQL with user-controlled ticker strings |
| Forged/stale client-side session accepted as valid | Spoofing | Every gated page re-verifies via `get_user()` (server round-trip), never trusts a cached client-side session object as sufficient proof of identity |
| Yahoo/yfinance response tampering or unexpected payload shape causing a crash | Denial of Service | `tenacity`-wrapped fetch + explicit fallback to stale cache on any exception, never an unhandled crash on a malformed/failed response |

## Sources

### Primary (HIGH confidence — official docs, fetched directly this session)
- https://supabase.com/docs/reference/python/auth-signup — sign_up() signature, session-null-on-unconfirmed-email behavior
- https://supabase.com/docs/reference/python/auth-signinwithpassword — sign_in_with_password() signature
- https://supabase.com/docs/reference/python/auth-signinwithotp — magic-link sign-in flow, `email_redirect_to`
- https://supabase.com/docs/reference/python/auth-getuser — get_user() server-side JWT validation, contrast with get_session()
- https://supabase.com/docs/guides/auth/row-level-security — RLS enable/policy SQL syntax, `auth.uid()` null behavior
- https://supabase.com/docs/guides/auth/managing-user-data — official `profiles` table + `handle_new_user()` trigger pattern
- https://supabase.com/docs/guides/getting-started/api-keys — `sb_publishable_*`/`sb_secret_*` vs. legacy anon/service_role key status
- https://docs.streamlit.io/develop/concepts/multipage-apps/page-and-navigation — conditional `st.navigation` hide-pages pattern
- https://docs.streamlit.io/develop/api-reference/app-testing/st.testing.v1.apptest — AppTest.from_file, session_state manipulation
- `pip index versions <package>` (live PyPI registry queries, 2026-07-17) — streamlit 1.59.2, supabase 2.31.0, yfinance 1.5.1, tenacity 9.1.4, python-dotenv 1.2.2, pytest 9.1.1, ruff 0.15.22

### Secondary (MEDIUM confidence — WebSearch cross-corroborated across multiple independent sources)
- yfinance rate-limit/backoff community reports (GitHub issues #2125, discussion #2431; Medium/Slingacademy writeups) — no official numeric limit exists; bulk-download + backoff + caching is the consistent community mitigation
- Streamlit Community Cloud sleep-vs-redeploy filesystem persistence (Streamlit Community discussion threads, docs.streamlit.io/deploy pages)
- Supabase local CLI / Docker dev stack + pgTAP testing (docs.supabase.com/guides/local-development)
- `AuthApiError` exception handling pattern (community example, not an official docs page fetched directly)

### Tertiary (LOW confidence — single-source or reasoning-based, flagged for validation)
- SQLite vs. parquet tradeoff for this specific cache shape — general practice reasoning, not a directly-cited authoritative source
- `yfinance-cache` package existence/maintainer endorsement — surfaced via WebSearch only, not independently verified against the PyPI registry this session (tagged `[ASSUMED]`, not adopted this phase)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — every version number verified live against PyPI registry this session, not training-data recall
- Architecture (auth/RLS/navigation patterns): HIGH — sourced directly from official Supabase/Streamlit documentation pages fetched this session
- Architecture (caching/disk persistence): MEDIUM — yfinance and Streamlit Cloud filesystem behavior are vendor-undocumented; community-sourced and cross-corroborated but not authoritative
- Pitfalls: MEDIUM-HIGH — the auth/session pitfalls (1, 2, 3, 5) are grounded in official docs + the project's own prior PITFALLS.md incident citations; the yfinance/disk-cache pitfalls (4, 6) are community-sourced

**Research date:** 2026-07-17
**Valid until:** 2026-08-16 (30 days) — re-verify yfinance rate-limit behavior and Supabase key-format status sooner if either area causes implementation friction, since both are explicitly volatile/vendor-in-flux areas per this research

---
*Phase: 1-Foundation — Data Layer, Caching & Auth*
*Research completed: 2026-07-17*
