---
phase: 01-foundation-data-layer-caching-auth
plan: 03
subsystem: data
tags: [yfinance, sqlite, tenacity, streamlit-cache, caching]

# Dependency graph
requires:
  - phase: 01-01
    provides: "src/config.py (CACHE_TTL_SECONDS=3600), package scaffolding (src/data/__init__.py)"
provides:
  - "src/data/cache.py: fetch_ohlcv(ticker, period) -> (DataFrame, status), the single yfinance chokepoint (st.cache_data -> SQLite -> tenacity -> yf.download)"
  - "format_stale_cache_message(fetched_at) helper matching the UI-SPEC Copywriting Contract stale-cache sentence"
  - "src/data/prices.py: thin public re-export of fetch_ohlcv for later phases to import instead of touching cache.py/yfinance directly"
affects: [01-04, 01-05, phase-3-recommendation-engine, phase-4-prediction-backtesting]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single yfinance chokepoint: only src/data/cache.py imports yfinance; all other code imports src.data.prices.fetch_ohlcv (RESEARCH.md Pattern 3)"
    - "Cache layering: st.cache_data(ttl=CACHE_TTL_SECONDS) in-memory -> SQLite disk cache (survives cold container) -> tenacity-retried live fetch -> stale-fallback with explicit 'stale' status on failure, hard raise when no cache exists at all"

key-files:
  created:
    - src/data/cache.py
    - src/data/prices.py
    - tests/test_cache.py
  modified: []

key-decisions:
  - "Added reraise=True to the tenacity @retry decorator so a total live-fetch failure with no disk cache propagates the original exception type (e.g. RuntimeError) rather than tenacity's own RetryError wrapper -- matches the plan's 'raises explicitly' requirement and gives later phases a stable exception type to catch"
  - "Used io.StringIO() when reading the payload_json back with pd.read_json() to avoid pandas' FutureWarning about passing a literal JSON string directly"

patterns-established:
  - "SQLite cache table (ticker, period, fetched_at, payload_json) keyed on (ticker, period), all queries parameterized with ? placeholders"

requirements-completed: [AUTH-02]

coverage:
  - id: D1
    description: "fetch_ohlcv() returns cached result on repeated calls within TTL without a second live-fetch invocation"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_repeated_fetch_within_ttl_hits_cache_not_live_fetch"
        status: pass
    human_judgment: false
  - id: D2
    description: "On live-fetch failure with a prior successful fetch already on disk, fetch_ohlcv returns the stale row with status='stale' instead of raising"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_live_fetch_failure_falls_back_to_stale_disk_row"
        status: pass
    human_judgment: false
  - id: D3
    description: "On live-fetch failure with no disk cache at all, fetch_ohlcv raises explicitly rather than returning None/empty silently"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_live_fetch_failure_with_no_cached_row_raises"
        status: pass
    human_judgment: false
  - id: D4
    description: "_fetch_live is tenacity-retried with stop_after_attempt(3), no hardcoded requests-per-minute constant anywhere in the module"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_fetch_live_retry_configured_for_three_attempts"
        status: pass
    human_judgment: false
  - id: D5
    description: "fetch_ohlcv's st.cache_data ttl argument references CACHE_TTL_SECONDS from src.config, not a hardcoded literal"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_fetch_ohlcv_uses_configured_ttl_not_a_literal"
        status: pass
    human_judgment: false
  - id: D6
    description: "format_stale_cache_message() renders the exact UI-SPEC Copywriting Contract stale-cache sentence"
    requirement: "AUTH-02"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_format_stale_cache_message_matches_ui_spec_copywriting_contract"
        status: pass
    human_judgment: false
  - id: D7
    description: "All SQL statements referencing ticker/period use ? placeholders, never f-string/%-formatted interpolation (T-01-03)"
    verification:
      - kind: unit
        ref: "tests/test_cache.py#test_sql_statements_use_parameterized_placeholders_not_string_interpolation"
        status: pass
    human_judgment: false
  - id: D8
    description: "src/data/prices.py re-exports fetch_ohlcv and never imports yfinance directly, preserving the single-chokepoint discipline"
    verification:
      - kind: unit
        ref: "grep -c fetch_ohlcv src/data/prices.py; grep -Eq '^import yfinance|^from yfinance' src/data/prices.py (expect no match)"
        status: pass
    human_judgment: false

duration: 15min
completed: 2026-07-18
status: complete
---

# Phase 1 Plan 3: Cache Chokepoint & Price-Fetch Wrapper Summary

**Single yfinance chokepoint (`src/data/cache.py`) layering `st.cache_data(ttl=3600)` over a SQLite disk cache over a `tenacity`-retried `yf.download()`, with explicit stale-fallback and hard-failure-raises paths, re-exported through a thin `src/data/prices.py` wrapper**

## Performance

- **Duration:** 15 min
- **Started:** 2026-07-18T21:39:00Z (approx.)
- **Completed:** 2026-07-18T21:55:04Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `src/data/cache.py` implements the full D-07/D-08/D-09 resilience chain: `st.cache_data(ttl=CACHE_TTL_SECONDS)` (in-memory, TTL-bound) → SQLite disk cache (`price_cache` table, survives cold container restarts) → `tenacity`-wrapped `_fetch_live()` (3 attempts, exponential backoff, `reraise=True`) → single bulk `yf.download()` call
- On any live-fetch failure, falls back to the SQLite stale row and returns `(stale_df, "stale")`; when no cached row exists at all, re-raises the original exception rather than silently returning `None`/empty (Pitfall 4)
- `format_stale_cache_message(fetched_at)` renders the exact UI-SPEC Copywriting Contract sentence ("Showing saved data from {timestamp} — live prices are temporarily unavailable.") for a later phase's price-display page
- All SQL statements in the cache module use `?` placeholders exclusively — no ticker/period value is ever interpolated into a SQL string (T-01-03)
- `src/data/prices.py` re-exports `fetch_ohlcv` as the only cross-module import point for price data; it never imports `yfinance`, preserving the single-chokepoint discipline for all later phases (recommendation engine, prediction/backtesting)
- `tests/test_cache.py` proves every behavior with mocked `yf.download()` — zero live network calls — using a per-test `tmp_path`-isolated SQLite file

## Task Commits

Each task was committed atomically:

1. **Task 1: Cache chokepoint — st.cache_data / SQLite / tenacity / yfinance** - `f903e5f` (feat)
2. **Task 2: Thin public price-fetch wrapper** - `e20dcda` (feat)

**Plan metadata:** pending (docs: complete plan, this commit)

## Files Created/Modified
- `src/data/cache.py` - `fetch_ohlcv()` chokepoint, `_init_db()`, `_fetch_live()` (tenacity-retried), `_write_through()`/`_read_disk_cache()` (parameterized SQLite), `format_stale_cache_message()`
- `src/data/prices.py` - thin public re-export of `fetch_ohlcv`, no yfinance import
- `tests/test_cache.py` - TTL-hit, stale-fallback, hard-failure-raises, retry-config, ttl-config, copywriting-contract, and SQL-parameterization tests, all mocking `yf.download`

## Decisions Made
- Added `reraise=True` to the `tenacity.@retry` decorator on `_fetch_live` so a total failure (live fetch fails, no disk cache exists) propagates the original exception type instead of tenacity's own `RetryError` wrapper — matches the plan's "re-raise the original exception" requirement literally and gives later-phase callers a stable, predictable exception type to catch
- Used `io.StringIO(payload_json)` when reading the cached JSON payload back via `pd.read_json()`, avoiding a pandas `FutureWarning` about passing a literal JSON string directly (a forward-compat correctness fix, not a scope change)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] tenacity's default RetryError wrapping would have broken the "raises explicitly" requirement**
- **Found during:** Task 1 (writing `tests/test_cache.py`'s hard-failure test)
- **Issue:** Without `reraise=True`, tenacity's `@retry` decorator wraps the final exception in its own `tenacity.RetryError` rather than propagating the original exception (e.g. `RuntimeError` from a simulated network failure). The plan's behavior spec says fetch_ohlcv "raises (does not return None or an empty DataFrame silently)" and the `<action>` text says "re-raise the original exception" — a caller catching a specific exception type (or a later phase's own error-handling code) would see an opaque `RetryError` instead.
- **Fix:** Added `reraise=True` to the `@retry(...)` decorator on `_fetch_live`.
- **Files modified:** `src/data/cache.py`
- **Verification:** `tests/test_cache.py::test_live_fetch_failure_with_no_cached_row_raises` asserts `pytest.raises(RuntimeError)` specifically (not a generic `Exception`), and passes.
- **Committed in:** `f903e5f` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Correctness fix only — no scope creep, no architectural change. The plan's own behavior spec already implied this exact requirement; the fix just makes tenacity's actual default behavior match it.

## Issues Encountered
- None beyond the auto-fixed tenacity `reraise` issue above. `pytest tests/test_cache.py -x -q` passes cleanly (7 tests, ~13s — the two retry-exhaustion tests each incur tenacity's real exponential-backoff sleep, ~4s each, which is expected and not mocked away since the plan's behavior spec calls for asserting the actual retry configuration).

## User Setup Required

None - no external service configuration required. This plan's test suite mocks `yfinance` entirely and does not depend on the local Supabase stack (per this plan's environment note).

## Next Phase Readiness
- `src/data/prices.py::fetch_ohlcv` is ready for Plan 04 (app shell) and any later phase (3: recommendation engine, 4: prediction/backtesting) to import for price data without touching yfinance or SQLite directly.
- `format_stale_cache_message()` is ready for a later phase's price-display page to import and render against the UI-SPEC's stale-cache Copywriting Contract row.
- No blockers. `data/price_cache.db` is gitignored (`data/*.db` in `.gitignore` from Plan 01) and does not exist yet on a fresh checkout — by design, since the cache is a disposable performance optimization, not durable storage (Pitfall 4).

---
*Phase: 01-foundation-data-layer-caching-auth*
*Completed: 2026-07-18*

## Self-Check: PASSED

All created files verified present on disk; commits `f903e5f` and `e20dcda` verified present in `git log`.
