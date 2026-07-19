---
phase: 01-foundation-data-layer-caching-auth
reviewed: 2026-07-18T00:00:00Z
depth: standard
files_reviewed: 23
files_reviewed_list:
  - .streamlit/secrets.toml.example
  - src/__init__.py
  - src/app.py
  - src/auth/__init__.py
  - src/auth/session.py
  - src/config.py
  - src/data/__init__.py
  - src/data/cache.py
  - src/data/prices.py
  - src/data/supabase_client.py
  - src/pages/__init__.py
  - src/pages/home.py
  - src/pages/login.py
  - supabase/config.toml
  - supabase/migrations/20260718204703_create_profiles.sql
  - supabase/migrations/20260718211140_grant_profiles_privileges.sql
  - supabase/migrations/20260719001207_grant_profiles_service_role.sql
  - tests/apptest_scripts/home_page_target.py
  - tests/conftest.py
  - tests/test_auth_flow.py
  - tests/test_auth_isolation.py
  - tests/test_cache.py
  - tests/test_profile_persistence.py
  - tests/test_rls_policy.py
findings:
  critical: 1
  warning: 5
  info: 3
  total: 9
status: issues_found
---

# Phase 01: Code Review Report

**Reviewed:** 2026-07-18T00:00:00Z
**Depth:** standard
**Files Reviewed:** 23
**Status:** issues_found

## Summary

Reviewed the foundation data-layer/caching/auth phase: the yfinance-backed SQLite disk-cache
chokepoint (`src/data/cache.py`), the Supabase auth gate and session-isolation discipline
(`src/auth/session.py`, `src/data/supabase_client.py`), the login/home pages, the `profiles`
RLS migrations, and the integration test suite.

The auth/RLS design is careful and well-reasoned (stateless shared client, scoped per-call
clients for every authenticating operation, `get_user()` over `get_session()`, RLS + explicit
GRANTs on `profiles`, SECURITY DEFINER trigger hardened with `search_path = ''`), and the test
suite genuinely exercises the real Supabase stack rather than asserting against mocks.

However, one **BLOCKER** was found and confirmed reproducible: `src/data/cache.py`'s SQLite
disk-cache layer will crash on the very first call in any fresh checkout or fresh deployment,
because the `data/` directory it writes to is never created anywhere in the codebase, and
`sqlite3.connect()` does not create missing parent directories. This defeats the entire
purpose of the disk-cache fallback (D-07/D-08/D-09) — the exact failure mode it was built to
survive. The existing test suite does not catch this because its isolation fixture points
`DB_PATH` at pytest's `tmp_path`, which already exists as a directory.

Several warning-level robustness/consistency gaps were also found in the auth gate's error
handling and the login page's stale-state highlighting, plus a couple of low-severity
quality nits.

## Critical Issues

### CR-01: SQLite disk cache crashes on first use — `data/` directory is never created

**File:** `src/data/cache.py:27, 30-43, 101-122`
**Issue:** `DB_PATH = "data/price_cache.db"` (line 27) is opened via `sqlite3.connect(DB_PATH)`
in `_init_db()` (line 32), `_write_through()` (line 73), and `_read_disk_cache()` (line 87).
`sqlite3.connect()` does **not** create missing parent directories — confirmed by direct
reproduction:

```
$ python -c "import sqlite3; sqlite3.connect('scratch_data/test.db')"
sqlite3.OperationalError: unable to open database file
```

Nothing in the codebase creates the `data/` directory (`grep -r "makedirs\|mkdir"` across
`src/` returns no matches), and the directory itself does not exist in the repo — `.gitignore`
only excludes `data/*.db`/`data/*.db-journal`, it does not ship a `.gitkeep` or otherwise commit
the directory. On a fresh `git clone`, a fresh Streamlit Community Cloud container, or any
container that woke up from sleep on an ephemeral filesystem, `_init_db()` — called
unconditionally at the top of `fetch_ohlcv()` at line 112, **before** the `try`/`except` that
is supposed to provide graceful stale-cache fallback — raises `OperationalError` immediately.
This exception is not caught by anything: it propagates straight out of `fetch_ohlcv()` on the
very first call, before a single live fetch is even attempted. This breaks the entire
price-data pipeline (D-07/D-08/D-09) out of the box, which is precisely the scenario this
disk-cache layer exists to protect against (a cold container after sleep, per its own
docstring at cache.py:2-9).

This is masked by the test suite: `tests/test_cache.py`'s `isolated_cache` fixture
(`conftest`-style fixture at test_cache.py:18-27) does
`monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "price_cache.db"))` — and `tmp_path`
is a directory pytest creates for you, so the "parent directory doesn't exist" case is never
exercised by any existing test.

**Fix:**
```python
def _init_db() -> None:
    """Create the price_cache table (and its parent directory) if needed."""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_cache (
                ticker TEXT,
                period TEXT,
                fetched_at REAL,
                payload_json TEXT,
                PRIMARY KEY (ticker, period)
            )
            """
        )
```
(add `from pathlib import Path` to the imports), and add a regression test that points
`DB_PATH` at a path whose parent directory does not yet exist (e.g.
`tmp_path / "nested" / "price_cache.db"`) to prevent this from regressing silently again.

## Warnings

### WR-01: `require_auth()`'s failure path clears *all* of `st.session_state`, not just auth keys

**File:** `src/auth/session.py:112-130, 151`
**Issue:** The docstring says on total failure this function "clears the auth keys from
`st.session_state`" (lines 122-123), but the implementation at line 151 calls
`st.session_state.clear()` — wiping every key in session state, not just `access_token`/
`refresh_token`/`logged_in`. Compare with `sign_out()` (lines 156-177), which surgically pops
only the three auth keys. This mismatch is currently invisible because `require_auth()` is
always immediately followed by `st.stop()` on the same call, and the only page that exists yet
(`home.py`) has no other session state to lose. It becomes a real landmine once later phases
add home-page state (selected filters, in-progress recommendation/prediction runs, etc.):
an expired-token edge case would silently wipe all of that, not just the auth keys, mid-session.
**Fix:**
```python
for key in ("access_token", "refresh_token", "logged_in"):
    st.session_state.pop(key, None)
```
in place of `st.session_state.clear()`.

### WR-02: `require_auth()` only catches `AuthApiError` — any other exception crashes the page

**File:** `src/auth/session.py:136-149`
**Issue:** Both the initial `get_user(token)` call (line 137, guarded by `except AuthApiError`
at line 138) and the refresh-then-retry path (lines 144-147, guarded by `except AuthApiError`
at line 148) only catch `AuthApiError`. A transient network failure, timeout, or any other
exception raised by the underlying `httpx`/`supabase-py` stack while calling out to Supabase
Auth is not caught, and will propagate uncaught out of `require_auth()`, crashing the whole
page with a raw traceback instead of the intended graceful "not authenticated, please log in
again" halt. The project's own stated free-tier reliability constraints (documented rate-limit/
outage risk for yfinance/Gemini/NewsAPI, mitigated with `tenacity` + fallbacks elsewhere in this
same phase) apply equally to Supabase Auth calls, which currently get no equivalent treatment.
**Fix:** widen the except clauses (e.g. `except (AuthApiError, Exception)` narrowed to the
specific network/HTTP exception types the supabase client can raise, or a bare
`except Exception` with a log line), so a transient Auth-service hiccup degrades to the
existing "not authenticated" halt rather than an unhandled crash.

### WR-03: SQLite connections opened in `src/data/cache.py` are never closed

**File:** `src/data/cache.py:32-43, 65-78, 81-98`
**Issue:** `_init_db()`, `_write_through()`, and `_read_disk_cache()` all do
`with sqlite3.connect(DB_PATH) as conn:`. Per Python's `sqlite3` documentation, the connection
context manager only commits or rolls back the current transaction on exit — it does **not**
close the connection. Every cache-miss call to `fetch_ohlcv()` therefore opens a new
`sqlite3.Connection` (and underlying OS file handle) that is only ever reclaimed when CPython
happens to garbage-collect the object. Given Streamlit reruns the whole script on every user
interaction, this can accumulate open file handles over a long-running session/container
lifetime.
**Fix:** use `contextlib.closing(sqlite3.connect(DB_PATH))` or add an explicit `conn.close()`
in each of these three functions.

### WR-04: A successful-but-empty `yf.download()` result is cached and served as `"live"`

**File:** `src/data/cache.py:52-62, 101-122`
**Issue:** `_fetch_live()` (lines 52-62) only retries/fails on a raised exception; it does not
validate that the returned DataFrame is non-empty. `yfinance` is documented to return an
**empty** DataFrame (not raise) for a delisted, mistyped, or rate-limited ticker in a number of
cases. If that happens, `fetch_ohlcv()` (line 114-116) treats it as a successful `"live"` fetch,
write-throughs the empty payload to the SQLite disk cache (`_write_through`, line 115) —
silently overwriting any previously-good stale row — and returns `(empty_df, "live")` to the
caller, indistinguishable from a genuinely-empty trading calendar day.
**Fix:** after `_fetch_live()` returns, check `if df.empty: raise ValueError(f"No data returned
for {ticker}/{period}")` before treating the result as a live success, so the existing
stale-cache fallback path in `fetch_ohlcv()`'s `except` block engages instead of caching an
empty result as authoritative.

### WR-05: Login page's per-field "empty" red-border highlight is never reset on logout/re-visit

**File:** `src/pages/login.py:91-105, 114-132, 138-150`; `src/auth/session.py:156-177`
**Issue:** `st.session_state["log_in_email_error"]`/`"log_in_password_error"`/
`"create_account_email_error"`/`"create_account_password_error"`/`"magic_link_email_error"`
are only ever written inside each tab's `if submitted:` block (e.g. login.py:92-93). On any
rerun where the user has *not* just pressed that tab's submit button — including the very
first render after `sign_out()` (session.py:156-177) navigates back to the login page, or a
page rerun triggered by switching tabs — whatever value was last written to these keys persists
unchanged, since nothing ever clears them. `sign_out()` only pops `access_token`/
`refresh_token`/`logged_in` (session.py:174-176), not any of the five `*_error` keys. Net
effect: a user who left a field flagged as empty in a previous session, later signs in
successfully (e.g. via a different tab or a fresh login attempt with valid data), and then
eventually logs out, will see the previous session's red-border highlight reappear on an
untouched, freshly-rendered empty form — a stale visual artifact with no corresponding
just-submitted action to justify it.
**Fix:** either clear the five `*_error` keys in `sign_out()`, or scope the check to also
require `submitted` on the current rerun (e.g. store a monotonically increasing "last
submitted tab" token alongside the boolean and only render the highlight when it matches the
current rerun's submit), so the highlight cannot outlive the submit that produced it.

## Info

### IN-01: `get_config()`'s broad `except Exception: pass` also swallows genuine misconfiguration

**File:** `src/config.py:31-40`
**Issue:** The `try`/`except Exception: pass` around `st.secrets` access is documented as
intentionally covering "no secrets.toml exists" / "not running inside a Streamlit context" —
but it will just as silently swallow a genuinely malformed `secrets.toml` (TOML parse error) as
"not found," falling through to `os.environ` with no diagnostic signal at all. Low severity
since it's a deliberate, documented tradeoff, but worth at least a debug-level log if
misconfiguration turns out to be a support burden in practice.
**Fix:** narrow the except to the specific exception `st.secrets` raises for "no secrets file"
(`streamlit.errors.StreamlitSecretNotFoundError` in recent Streamlit versions), or add a log
line before falling through, so a malformed secrets file doesn't fail silently.

### IN-02: Duplicate-signup error reuses invalid-credentials copy (self-acknowledged in-code)

**File:** `src/pages/login.py:118-126`
**Issue:** A duplicate-email signup attempt surfaces `INVALID_CREDENTIALS_ERROR`
("We couldn't verify that email and password. Double-check them and try again.") — misleading
for a user whose credentials are in fact correct but who already has an account. The in-code
comment (lines 122-126) already flags this as a deliberate compromise given no distinct copy
exists in the Copywriting Contract, so this is recorded here as a UX debt item rather than a
defect, for whoever owns copy in a later phase.
**Fix:** add a distinct "an account with this email already exists" message to the Copywriting
Contract and use it here instead of reusing the invalid-credentials string.

### IN-03: Function-local `import json` instead of a module-level import

**File:** `tests/test_auth_flow.py:24`
**Issue:** `import json` is nested inside `_mailpit_messages_to()` rather than declared at the
top of the file with the other imports. Harmless but inconsistent with the rest of the file's
import style.
**Fix:** move `import json` to the top-level import block.

---

_Reviewed: 2026-07-18T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
