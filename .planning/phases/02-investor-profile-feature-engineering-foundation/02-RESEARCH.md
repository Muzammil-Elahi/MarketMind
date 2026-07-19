# Phase 2: Investor Profile + Feature Engineering Foundation - Research

**Researched:** 2026-07-19
**Domain:** Supabase Postgres schema/RLS design for a multi-field user profile + child resource, Streamlit dynamic-row forms, and a leakage-safe point-in-time technical-feature pipeline (pandas-ta-classic)
**Confidence:** MEDIUM (Supabase RLS and Streamlit patterns confirmed against official docs and cross-corroborated community sources; pandas-ta-classic itself carries a legitimacy warning — see Package Legitimacy Audit)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Profile field design**
- **D-01:** Risk tolerance is a 3-level categorical field: Conservative / Moderate / Aggressive. Maps directly and unambiguously to Phase 3's factor-weight buckets — no intermediate bucketing logic needed downstream.
- **D-02:** Time horizon is captured as bucketed categories: `<1yr`, `1-3yr`, `3-5yr`, `5-10yr`, `10+yr` (not a free numeric year input) — same rationale as D-01, ready to consume as weight-bucket keys in Phase 3.
- **D-03:** Preferred/excluded sectors use a simplified ~10-category list (Tech, Healthcare, Financials, Energy, Consumer, Industrials, Real Estate, Utilities, Materials, Communication), not the full GICS 11-sector standard. Close enough to yfinance's own sector field for later matching; full GICS was judged unnecessary complexity at this scale.
- **D-04:** Preferred asset types use multi-select checkboxes across the 5 supported classes (stocks/ETFs/crypto/gold/forex), include-only (no separate "exclude asset type" toggle — asymmetric with sectors, which do get preferred/excluded, by design; user only selects what they want more of).
- **D-05 (Claude's discretion):** Capital input format (numeric dollar field vs. bucketed ranges) — not deep-dived, left to implementation. A single numeric dollar input is the obvious default given no counter-signal was raised.

**Existing holdings format**
- **D-06:** Holdings are captured as structured rows: ticker + quantity (shares/units), via a dynamic add-row UI — not a free-text ticker list. Sets up future gain/loss or exposure-overlap features without a schema migration later.
- **D-07:** Each holding row has an *optional* cost-basis (purchase price) field. Nothing in the current roadmap (through Phase 6) consumes this yet, but the user wants it captured now rather than added later as a schema change.
- **D-08:** Entered ticker symbols are validated against yfinance on form submit (not on every keystroke, not deferred to first-use) — flag unrecognized tickers back to the user at save time.

**Feature pipeline scope**
- **D-09:** The feature module must handle all 5 asset classes (stocks, ETFs, crypto, gold, forex) now, not equities-only first — even though STATE.md flags cross-asset-class factor-weight *normalization* as unresearched until Phase 3. This phase's scope is point-in-time feature computation (returns/volatility/indicators), not weighting, so building calendar-agnostic logic now (crypto trades 24/7, equities/ETFs don't) avoids a later rework of `features/feature_frame.py`.
- **D-10 (Claude's discretion):** Exact technical indicator set for this phase (returns, volatility, SMA, RSI at minimum per ARCHITECTURE.md; MACD/Bollinger optional) — user deferred to implementation time. Guidance: prefer the ARCHITECTURE.md-cited core set (returns, volatility, SMA, RSI, moving averages) as the floor; add MACD/Bollinger only if cheap to do point-in-time-safely in the same pass, since no model consumes any of it until Phase 3/4.
- **D-11 (Claude's discretion):** Exact leakage-smoke-test mechanism — user deferred to implementation time. Strong default per ARCHITECTURE.md Anti-Pattern 3: inject a synthetic future-only signal into test data and assert the feature/backtest pipeline does NOT show improved accuracy from it. Use this pattern unless research surfaces something stronger.

**Profile edit UX**
- **D-12:** Single always-editable form serves both first-time creation and later edits — pre-filled with existing values if a profile row exists, empty otherwise. No separate view-then-edit-mode toggle.
- **D-13:** Profile reads are NOT wrapped in `st.cache_data` — fetch fresh from Supabase on every page load. This is a cheap single-row query (unlike yfinance), so the simplest way to satisfy success criterion #2 ("updated values reflected immediately... no stale cache") is to just not cache it, rather than caching with explicit invalidation on save.

### Claude's Discretion
- D-05: Capital input format — numeric dollar field chosen as default.
- D-10: Exact technical indicator set — core set (returns, volatility, SMA, RSI) is the floor; MACD/Bollinger optional if cheap.
- D-11: Exact leakage-smoke-test mechanism — synthetic future-signal injection is the strong default.

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope. No scope-creep suggestions came up during the CONTEXT.md session.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROFILE-01 | User can build an investor profile (risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, existing holdings) | Standard Stack + Architecture Patterns (profile schema, `holdings` child table + RLS, `st.data_editor` dynamic-row pattern, D-08 ticker-validation finding) |
| PROFILE-02 | User can edit their profile after creation and see recommendations update accordingly | D-12/D-13 always-editable, uncached-read pattern; Architecture Patterns (single-form load/save cycle); note the "recommendations update" half of this requirement's wording is Phase 3's responsibility — this phase only guarantees the profile data itself is freshly persisted and freshly re-read (Success Criterion #2) |
</phase_requirements>

## Summary

This phase has two independent deliverables sharing a phase boundary, and the research splits cleanly along that line. For the **profile builder**, the existing `profiles` table (Phase 1) gets extended with nullable columns for the six scalar/array fields (risk tolerance, time horizon, sectors ×2, asset types, capital) — the existing RLS policies already cover new columns on the same table, so no RLS changes are needed there. **Holdings**, however, must be a separate child table (`holdings`) with its own `user_id` column and its own RLS policies, because it's a dynamic set of rows, not scalar fields on one row; Supabase's documented pattern for this is to carry the owning `user_id` directly on the child table (not join through the parent) and reuse the same `(select auth.uid()) = user_id` policy shape already established in `20260718204703_create_profiles.sql`. The dynamic add/remove-row UI is a solved problem in Streamlit 1.59.x via `st.data_editor(df, num_rows="dynamic")`.

For the **feature pipeline**, the key research finding is that D-09's "all 5 asset classes now, no special-casing" requirement is actually *easy* to satisfy correctly: because this phase's rolling-window indicators (SMA, RSI, returns, volatility) operate on row-order windows within a single asset's own OHLCV history, no cross-asset calendar alignment is needed yet — that only becomes a problem when *comparing* assets side-by-side, which is explicitly Phase 3's job. `pandas-ta-classic`'s `df.ta.*` accessor API computes all of these as standard trailing rolling windows, which are point-in-time safe by construction as long as `center=False` (the default) and no `.shift(-n)` is used. The leakage smoke test (D-11) has a well-established two-part pattern: (1) truncation invariance — features computed on data through date T must be identical whether the raw frame extends to T or to T+30; (2) synthetic future-signal injection — a column deterministically derived from a future price must never appear, even indirectly, in any feature value dated before that future date.

One package-legitimacy concern surfaced: `pandas-ta-classic` — already the project's approved STACK.md choice, replacing the abandoned `pandas-ta` and the build-hostile `TA-Lib` — is flagged `SUS` by the automated legitimacy gate (published 2026-06-24, unknown download count). This does not override the prior STACK.md research decision (it remains the right choice versus the alternatives), but the planner must add a `checkpoint:human-verify` task before the `pip install` step, per the Package Legitimacy Gate protocol.

**Primary recommendation:** Extend `profiles` with nullable scalar/array columns (CHECK constraints, not native Postgres ENUMs, for the two fixed-value fields); add a new `holdings` child table with its own `user_id` FK + matching RLS policy set; build `features/technical.py` as a single-asset, pure-pandas module using `pandas-ta-classic`'s `df.ta` accessor with `center=False` rolling windows exclusively, deferring all cross-asset calendar alignment to Phase 3.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Profile form rendering + validation | Frontend Server (SSR — Streamlit page) | — | Streamlit renders and re-executes server-side per session; no separate browser-JS tier exists in this stack |
| Profile persistence (scalar fields CRUD) | API / Backend (`src/data/` profile CRUD helpers) | Database / Storage (Supabase Postgres, RLS) | Business logic (field validation, save orchestration) lives in a thin Python module; the database enforces final authorization via RLS regardless of app-layer checks |
| Holdings dynamic sub-resource (add/remove rows) | Frontend Server (SSR — `st.data_editor`) | Database / Storage (`holdings` table + RLS) | UI owns the editable grid state per session; persistence + per-user isolation is enforced at the DB tier, not trusted from the client |
| Ticker validation on submit (D-08) | API / Backend (`src/data/prices.py` chokepoint) | — | Reuses the existing single chokepoint for all yfinance access; must not be duplicated in page code (Anti-Pattern 1, ARCHITECTURE.md) |
| Point-in-time technical/factor feature computation | API / Backend (`src/features/`, pure Python, zero I/O) | — | Explicitly designed to have no Streamlit/DB dependency so it is importable/testable from both this phase's tests and Phase 3/4's model code (Pattern 3, ARCHITECTURE.md) |
| Leakage smoke test | API / Backend (pytest suite over `src/features/`) | — | Pure-function testability is the entire point of keeping `features/` I/O-free |
| Row-level access control (profile + holdings) | Database / Storage (Postgres RLS policies) | API / Backend (auth token passed through per-request) | RLS is the actual enforcement boundary (per Phase 1's `test_rls_policy.py` precedent) — app code never re-implements authorization checks in Python |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|---------------|
| `pandas-ta-classic` | 0.6.52 [VERIFIED: PyPI registry — `pip index versions pandas-ta-classic`] | Technical indicators (SMA, RSI, MACD, Bollinger, returns/volatility) via the `df.ta` DataFrame accessor | Already the project's STACK.md-approved choice (replaces abandoned `pandas-ta` and build-hostile `TA-Lib` on Streamlit Cloud); see Package Legitimacy Audit below — flagged `SUS` by the legitimacy gate, install must be gated behind human verification, but no better-legitimacy alternative exists that meets the "don't hand-roll 224 indicators" bar. `[ASSUMED]` — package identity/API shape sourced from WebSearch + PyPI, not Context7/official docs (no context7 MCP available in this research session). |
| `pandas` | 2.3.3 (currently installed; not yet pinned in `requirements.txt`) [VERIFIED: local `pip show`/PyPI registry] | DataFrame engine `features/` and `pandas-ta-classic` both depend on directly | Already a transitive dependency (via `yfinance`) and already imported directly in `tests/test_cache.py`, but never pinned explicitly in `requirements.txt` — this phase is the first to import `pandas` directly from `src/` code, so pin it now rather than relying on whatever version `yfinance` happens to pull. PyPI's newest is 3.0.3; recommend pinning to the already-installed/tested 2.3.x line (`pandas>=2.3,<3`) rather than jumping to an unvalidated pandas 3.x mid-project. `[ASSUMED]` — pandas 3.x compatibility with `pandas-ta-classic` 0.6.52 was not verified this session. |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|--------------|
| `supabase-py` | 2.31.0 (already installed, per `requirements.txt`) | `holdings` table CRUD, extended `profiles` CRUD | Reuse the existing `get_supabase_client()` / scoped-client patterns from Phase 1 — no new client code needed |
| `streamlit` | 1.59.2 (already installed) | `st.data_editor(num_rows="dynamic")` for the holdings grid; `st.form` for the rest of the profile fields | Already the project's pinned frontend version; `st.data_editor` dynamic rows is a built-in 1.5x+ feature, no extra dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|-------------|-----------|-----------|
| `holdings` as a child table with FK + own RLS | Store holdings as a `jsonb` column on `profiles` | Rejected in CONTEXT.md discussion (D-06) — a JSON blob can't cleanly support later per-holding features (gain/loss, exposure-overlap) without a schema migration, and RLS on `jsonb` contents is not queryable/enforceable at row level the way a real column is |
| `st.data_editor(num_rows="dynamic")` | Manual `st.session_state` list + `st.columns()` per-row layout with explicit add/remove buttons | More code, more state-management surface area, no built-in delete/undo UX — only worth it if `st.data_editor`'s validation/typing model (fixed dtypes per column) proves too rigid for the ticker/quantity/cost-basis shape, which it should not be here |
| Postgres `text` + `CHECK (col IN (...))` for risk_tolerance/time_horizon | Native Postgres `ENUM` type | `ENUM` requires `ALTER TYPE ... ADD VALUE` (acquires `ACCESS EXCLUSIVE` lock, cannot run inside some transaction contexts) if the value set ever changes, and values can never be removed once added — `CHECK` constraints are trivially alterable and this project's value sets (3 risk levels, 5 horizon buckets) are exactly the kind of "might tweak wording later" fields `CHECK` handles better |

**Installation:**
```bash
pip install pandas-ta-classic==0.6.52
# recommend also pinning the already-present transitive dependency explicitly:
pip install "pandas>=2.3,<3"
```
Add both to `requirements.txt` (not just installed ad hoc) — Streamlit Community Cloud's build step reads `requirements.txt` directly (per project CLAUDE.md/STACK.md).

**Version verification:** `pip index versions pandas-ta-classic` confirmed `0.6.52` as latest on PyPI at research time; `pip index versions pandas` confirmed `3.0.3` as latest with `2.3.3` (the version already installed in this dev environment, matching what `tests/test_cache.py` already exercises) as the most recent 2.x release.

## Package Legitimacy Audit

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|--------------|---------|--------------|
| `pandas-ta-classic` | PyPI | ~26 days old at research time (published 2026-06-24) | Unknown (not reported by registry metadata) | `github.com/xgboosted/pandas-ta-classic` | **SUS** (`too-new`, `unknown-downloads`) | **Flagged** — keep per prior STACK.md decision (best available replacement for abandoned `pandas-ta`/build-hostile `TA-Lib`), but planner **must** add a `checkpoint:human-verify` task before the `pip install pandas-ta-classic` step |

**Packages removed due to SLOP verdict:** none.
**Packages flagged as suspicious [SUS]:** `pandas-ta-classic` — planner must insert `checkpoint:human-verify` before this install. Suggested verification for the human: confirm the GitHub repo (`xgboosted/pandas-ta-classic`) has actual commit history / is a genuine fork-continuation of the well-known `twopirllc/pandas-ta`, not a fresh namesquat, before installing. This package name and its rationale were already present in the project's STACK.md from prior research (2026-07-14) — the `SUS` verdict here reflects the automated gate's registry-age heuristic on a genuinely new package release, not a newly-discovered hallucination risk.

*This package name was carried forward from `.planning/research/STACK.md` (an earlier research pass), not freshly discovered via WebSearch this session — but it has not previously been run through the `package-legitimacy check` seam, so it is tagged `[ASSUMED]` here pending the human-verify checkpoint.*

## Architecture Patterns

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                    STREAMLIT PAGE: profile.py (new)                   │
│                                                                         │
│  require_auth() ─────► [scalar fields form: risk/horizon/sectors/     │
│                          asset types/capital, st.form]                 │
│                    └──► [holdings grid: st.data_editor(num_rows=      │
│                          "dynamic"), ticker/quantity/cost_basis]       │
│                                                                         │
│  On page load (D-13, no cache):                                        │
│    fetch existing profile row + existing holdings rows ──► pre-fill    │
│                                                                         │
│  On submit:                                                            │
│    for each holdings row: ticker ──► fetch_ohlcv(ticker) ──► empty?    │
│         │                                  │                           │
│         │                          yes ──► flag row invalid,           │
│         │                                  block save, show warning    │
│         │                          no  ──► proceed                     │
│         └──► profile CRUD: upsert profiles row (scalar fields)         │
│         └──► holdings CRUD: replace/upsert holdings rows for user_id   │
└───────────────────────────┬─────────────────────────────────────────┘
                             │ (via src/data/supabase_client.get_supabase_client(),
                             │  scoped with the caller's access token)
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     SUPABASE POSTGRES (existing project)               │
│  profiles (extended: risk_tolerance, time_horizon, preferred_sectors,  │
│            excluded_sectors, preferred_asset_types, capital)           │
│    RLS: (select auth.uid()) = user_id  [unchanged from Phase 1]        │
│  holdings (new: id, user_id FK, ticker, quantity, cost_basis)          │
│    RLS: (select auth.uid()) = user_id  [new policy, same shape]        │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                 FEATURE PIPELINE (src/features/, no I/O, no UI)        │
│                                                                         │
│  caller (this phase's tests now; Phase 3/4 models later) passes in a   │
│  DataFrame obtained from fetch_ohlcv() ── never fetches its own data   │
│                    │                                                    │
│                    ▼                                                   │
│  technical.py: compute_returns(df), compute_volatility(df),            │
│    compute_sma(df, window), compute_rsi(df, window)                    │
│    [+ optional: compute_macd(df), compute_bbands(df)]                  │
│    — each function: single-asset input, rolling(center=False) only,    │
│      no cross-asset joins, no .shift(-n)                               │
│                    │                                                    │
│                    ▼                                                   │
│  feature_frame.py: assemble_feature_frame(df) → single DataFrame,      │
│    same aligned index as input, calling technical.py functions only    │
│    — this is the one function both backtest harness (future phase)     │
│      and live inference will call                                      │
│                    │                                                    │
│                    ▼                                                   │
│  leakage smoke test (pytest): truncation-invariance + synthetic-       │
│    future-signal-injection assertions against assemble_feature_frame() │
└─────────────────────────────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/
├── features/
│   ├── __init__.py
│   ├── technical.py          # compute_returns, compute_volatility, compute_sma,
│   │                          # compute_rsi (+ optional macd/bbands) — pure functions,
│   │                          # DataFrame in, DataFrame/Series out, no I/O
│   └── feature_frame.py      # assemble_feature_frame(df) -> DataFrame; the single
│                              # shared entry point per ARCHITECTURE.md Pattern 3
├── data/
│   └── profile.py            # NEW: profile + holdings CRUD helpers (upsert_profile,
│                              # fetch_profile, upsert_holdings, fetch_holdings, all
│                              # taking an access_token explicitly, same pattern as
│                              # src/auth/session.py's _touch_last_login)
└── pages/
    └── profile.py             # NEW: the investor-profile Streamlit page

supabase/migrations/
└── <timestamp>_extend_profiles_and_create_holdings.sql   # NEW migration

tests/
├── test_features_technical.py       # unit tests per indicator function
├── test_features_leakage.py          # D-11 leakage smoke test
├── test_profile_crud.py              # profile field save/edit round-trip (real local
│                                      # Supabase stack, same pattern as
│                                      # test_profile_persistence.py)
└── test_holdings_rls.py              # RLS isolation proof for the new holdings table,
                                       # same two-user pattern as test_rls_policy.py
```

### Structure Rationale
- **`src/features/` stays exactly as ARCHITECTURE.md specified** (`technical.py` + `feature_frame.py`, zero Streamlit/I/O imports) — this phase does not need `sentiment.py` (deferred, SENT-01 is v2 scope).
- **`src/data/profile.py` is new but follows the existing chokepoint discipline**: profile/holdings Supabase calls go through this module, never inline in `src/pages/profile.py`, mirroring how `src/data/prices.py`/`cache.py` centralize yfinance access. Every write takes the caller's `access_token` explicitly (same pattern as `_touch_last_login` in `src/auth/session.py`) — never routed through the shared `get_supabase_client()` cache_resource object without a scoped/attached token, so RLS is enforced as the signed-in user, not bypassed.
- **One migration file, not two**: since both `profiles` column additions and the new `holdings` table are part of the same phase/feature, a single migration keeps them atomic — matches the existing pattern of one migration per Phase-1 concern (`create_profiles.sql`, then separate *fix* migrations only for genuine follow-up bugs discovered after the fact).

### Pattern 1: `holdings` as an owner-scoped child table (not a JSON blob)

**What:** `holdings` gets its own `user_id uuid not null references auth.users(id) on delete cascade` column — directly, not only via a `profile_id` FK to `profiles.user_id` — so its RLS policy can use the exact same `(select auth.uid()) = user_id` shape already proven in `create_profiles.sql`, with no cross-table subquery needed.
**When to use:** Any time a user-owned child resource needs its own RLS-enforced row-level isolation and the parent's primary key is already the user's own id (which it is here: `profiles.user_id` *is* the `auth.users.id`).
**Trade-offs:** Slight denormalization (both `profiles.user_id` and `holdings.user_id` ultimately reference the same `auth.users.id`, rather than `holdings` referencing `profiles.user_id` and relying on a join) — but this is the documented Supabase-recommended pattern specifically because it avoids a slower join-based RLS check and lets Postgres use a direct index on `holdings.user_id`. [CITED: supabase.com/docs/guides/database/postgres/row-level-security]

**Example:**
```sql
-- Source: pattern adapted from supabase.com/docs/guides/database/postgres/row-level-security
-- and this project's own create_profiles.sql precedent.
create table public.holdings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  ticker text not null,
  quantity numeric not null,
  cost_basis numeric,
  created_at timestamptz not null default now()
);

alter table public.holdings enable row level security;

create policy "Users can view their own holdings"
  on public.holdings for select
  using ( (select auth.uid()) = user_id );

create policy "Users can insert their own holdings"
  on public.holdings for insert
  with check ( (select auth.uid()) = user_id );

create policy "Users can update their own holdings"
  on public.holdings for update
  using ( (select auth.uid()) = user_id )
  with check ( (select auth.uid()) = user_id );

create policy "Users can delete their own holdings"
  on public.holdings for delete
  using ( (select auth.uid()) = user_id );

create index holdings_user_id_idx on public.holdings (user_id);

-- Same two GRANT migrations Phase 1 needed for profiles will be needed here too
-- (grant select/insert/update/delete on public.holdings to authenticated;
--  grant all on public.holdings to service_role;) — RLS alone does not grant
-- table privileges on a self-managed local Supabase CLI stack, per the
-- 20260718211140_grant_profiles_privileges.sql precedent.
```

**Important divergence from `profiles`:** `profiles` has no client-facing INSERT policy because `handle_new_user()`'s `SECURITY DEFINER` trigger is the only INSERT path. `holdings` has no equivalent trigger — the app itself inserts/replaces holdings rows on every profile save — so `holdings` **needs an explicit INSERT policy** (and DELETE, for row removal on edit), unlike `profiles`.

### Pattern 2: CHECK constraint, not native ENUM, for fixed-value-set columns

**What:** `risk_tolerance` and `time_horizon` are `text` columns with a `CHECK (col IN (...))` constraint, not a Postgres `CREATE TYPE ... AS ENUM`.
**When to use:** Any small, plausibly-will-change-wording-later value set — exactly D-01/D-02's shape.
**Trade-offs:** `ENUM` types read slightly cleaner in SQL and have a small performance edge in extreme high-volume scenarios, but adding/removing a value later requires `ALTER TYPE ... ADD VALUE` (an `ACCESS EXCLUSIVE` lock, and in Postgres, new enum values can't be used in the same transaction they're added in) — a real friction cost for a schema still evolving through Phase 2-6. `CHECK` constraints are trivially alterable via `ALTER TABLE ... DROP CONSTRAINT` / `ADD CONSTRAINT`. [CITED: supabase.com/docs/guides/database/postgres/enums; crunchydata.com/blog/enums-vs-check-constraints-in-postgres]

**Example:**
```sql
-- Source: pattern per crunchydata.com/blog/enums-vs-check-constraints-in-postgres
alter table public.profiles
  add column risk_tolerance text
    check (risk_tolerance in ('Conservative', 'Moderate', 'Aggressive')),
  add column time_horizon text
    check (time_horizon in ('<1yr', '1-3yr', '3-5yr', '5-10yr', '10+yr')),
  add column preferred_sectors text[],
  add column excluded_sectors text[],
  add column preferred_asset_types text[],
  add column capital numeric;
```
All six new columns must be nullable with no `NOT NULL` (and no `default`) — `handle_new_user()`'s trigger INSERT only supplies `user_id`/`created_at`, and that trigger is not being modified this phase, so any `NOT NULL` column added here would break every new signup until the profile form is completed. This is a hard compatibility constraint carried forward from the existing `create_profiles.sql` trigger, not a new decision.

### Pattern 3: Single-asset, row-order rolling windows — no cross-asset calendar handling needed this phase

**What:** Every function in `technical.py` takes one asset's OHLCV `DataFrame` (already time-sorted ascending, as returned by `fetch_ohlcv`) and computes rolling statistics using `.rolling(window)` (never `.rolling(window, center=True)`) keyed on row position, not calendar dates. A 20-period SMA is "the mean of the 20 most recent available bars for this asset," full stop — it does not matter that crypto has weekend bars and equities/forex don't, because no function ever compares across assets or requires two assets to share an index.
**When to use:** This phase, for exactly the reason D-09 states: point-in-time feature computation (this phase) is a different problem from cross-asset weight normalization (Phase 3, explicitly deferred/unresearched per STATE.md). Building calendar-alignment logic now would be solving a problem this phase doesn't have yet.
**Trade-offs:** `feature_frame.py`'s output for two different assets will have different-length/different-dated indexes (e.g., `BTC-USD` has ~365 rows/year, `AAPL` has ~252) — any code that eventually needs to compare them side-by-side (Phase 3's recommendation engine) will need its own alignment step at that point, but that's explicitly out of this phase's scope and was flagged as an open research item for Phase 3 already.

**Example:**
```python
# Source: pandas-ta-classic df.ta accessor pattern, cross-checked against
# pypi.org/project/pandas-ta-classic and github.com/xgboosted/pandas-ta-classic
# [ASSUMED — not verified against Context7/official docs this session]
import pandas as pd

def compute_sma(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """Point-in-time SMA: trailing window only, never centered."""
    return df.ta.sma(length=window, append=False)  # center=False is pandas-ta-classic's default

def compute_rsi(df: pd.DataFrame, window: int = 14) -> pd.Series:
    return df.ta.rsi(length=window, append=False)

def compute_returns(df: pd.DataFrame) -> pd.Series:
    # simple pct-change return, no .shift(-1) — this is a feature (today's
    # realized return given yesterday's close), not a future-looking label
    return df["close"].pct_change()

def compute_volatility(df: pd.DataFrame, window: int = 20) -> pd.Series:
    return compute_returns(df).rolling(window, center=False).std()
```

### Pattern 4: `pandas.DataFrame.rolling(center=False)` is the load-bearing safety property

**What:** `pandas.rolling()` defaults to `center=False` (window ends at the current row), which is point-in-time safe. `center=True` explicitly includes rows *after* the current one in the window average — a direct, easy-to-miss lookahead bug.
**When to use:** Enforce as a code-review/lint-level rule for every rolling call in `technical.py`.
**Trade-offs:** None — there is no legitimate reason to use `center=True` anywhere in a point-in-time feature pipeline; it exists in pandas for signal-smoothing/visualization use cases, not predictive features.

### Anti-Patterns to Avoid

- **Using `pandas.rolling(window, center=True)` anywhere in `features/`:** silently pulls future rows into "today's" indicator value — the exact Anti-Pattern 3 failure mode from ARCHITECTURE.md, just via a different mechanism than `.shift(-1)`.
- **Joining/aligning multiple assets' OHLCV frames into one calendar-unified DataFrame in this phase:** not needed for point-in-time computation (Pattern 3 above) and pre-empts unresearched Phase 3 work — avoid building it speculatively.
- **Storing holdings as a `jsonb` blob on `profiles`:** explicitly rejected in CONTEXT.md (D-06) — blocks future per-holding features and can't be RLS-scoped at the row level.
- **Trusting `yf.download()`'s return value alone for ticker validation:** see Common Pitfalls below — `yf.download()` does not raise for an invalid ticker, it returns an empty DataFrame. Checking only for an exception (the existing `fetch_ohlcv` retry/exception path) will silently accept invalid tickers.
- **Giving `holdings` the same "no INSERT policy" shape as `profiles`:** `profiles`' lack of a client INSERT policy relies on `handle_new_user()`'s trigger being the only insert path — `holdings` has no such trigger, so omitting the INSERT (and DELETE) policy would make the table entirely read-only to the app.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|--------------|-----|
| Row-level per-user data isolation for `holdings` | A Python-layer `if row.user_id == current_user.id` filter | Postgres RLS policies (Pattern 1 above) | App-layer filtering can be bypassed by any code path that forgets the check (or a future refactor); RLS is enforced at the database engine regardless of which code path queries it — Phase 1's `test_rls_policy.py` already establishes this is the project's chosen enforcement layer |
| Technical indicators (SMA/RSI/MACD/Bollinger) | Hand-rolled `.rolling().mean()`/Wilder's-smoothing RSI implementations | `pandas-ta-classic`'s `df.ta` accessor | Correctly implementing RSI's Wilder smoothing, MACD's EMA crossover, and Bollinger's rolling-std bands from scratch is a well-known source of off-by-one and edge-case bugs (first-N-rows NaN handling, EMA seed value); `pandas-ta-classic` provides 193+ pre-tested indicators |
| Dynamic add/remove-row form UI | Manual `st.session_state` list + per-row `st.columns()` widgets with custom add/delete button logic | `st.data_editor(df, num_rows="dynamic")` | Streamlit's built-in dynamic data editor handles add/delete/undo UX, keyboard interaction, and per-column dtype validation natively — hand-rolling this reproduces a worse version of a feature Streamlit already ships |

**Key insight:** every "don't hand-roll" item above maps to a documented pitfall category from `.planning/research/PITFALLS.md` (Pitfall 1 lookahead bias for indicators; Security Mistakes table for RLS) — this phase's job is to apply those already-researched guardrails to the specific profile/holdings/features shapes, not to re-derive them.

## Common Pitfalls

### Pitfall 1: `yf.download()` returns an empty DataFrame for an invalid ticker — it does not raise

**What goes wrong:** D-08 requires flagging unrecognized tickers on holdings-form submit. The natural implementation is "call `fetch_ohlcv(ticker)`, catch the exception, flag if it raises." But `yf.download()` (the function `_fetch_live` in `src/data/cache.py` wraps) does not raise for a bad/delisted ticker — it logs a "possibly delisted"/"No data found" message and returns an **empty** DataFrame with the expected columns but zero rows. `fetch_ohlcv()`'s existing exception-based retry/fallback logic will treat this as a **successful** live fetch (status `"live"`) since no exception was thrown.
**Why it happens:** `yfinance`'s `download()` API aggregates per-ticker errors into a log line rather than raising per-ticker, by design (documented in multiple `ranaroussi/yfinance` GitHub issues/discussions) — it's optimized for bulk multi-ticker calls where one bad ticker shouldn't abort the whole batch.
**How to avoid:** Ticker validation must check `df.empty` (or `len(df) == 0`) after a successful `fetch_ohlcv()` call, in addition to (not instead of) handling a raised exception for genuine network/API failures. Implement as: `df, status = fetch_ohlcv(ticker, period="5d"); is_valid = status == "live" and not df.empty` (a short period like `"5d"` is enough to prove the ticker resolves, and keeps the validation call cheap).
**Warning signs:** Holdings rows saving successfully with obviously-invalid tickers (e.g. a typo); D-08's "flag unrecognized tickers" success criterion silently not firing in manual testing.

### Pitfall 2: `NOT NULL`/`DEFAULT` on new `profiles` columns breaks the existing signup trigger

**What goes wrong:** `handle_new_user()` (the `SECURITY DEFINER` trigger from Phase 1) inserts a `profiles` row with only `user_id` and `created_at` populated. If this phase's migration adds any of the six new columns as `NOT NULL` (with no `DEFAULT`), every new signup will start failing at the trigger's `INSERT` the moment the migration lands — a regression Phase 1's existing auth tests (`test_profile_persistence.py`) would immediately catch, but only if this phase's migration is tested against the same local Supabase stack before merging.
**Why it happens:** It's a natural instinct to make "required" profile fields `NOT NULL` at the schema level, but here "required to complete the profile" (an app-level UX concern) and "required to exist at all" (a schema constraint) are different things — the row must be insertable *before* the user has filled in any profile data.
**How to avoid:** Every new column this phase adds must be nullable with no default. Enforce "user must fill this in before recommendations work" as an app-level check in Phase 3, not a database constraint here.
**Warning signs:** `test_profile_row_auto_provisioned_by_trigger_with_last_login_null` (existing Phase 1 test) or a fresh signup starting to fail with a Postgres `not-null-violation` after this phase's migration.

### Pitfall 3: RLS policies alone are not sufficient on a self-managed local Supabase CLI stack — GRANTs are also required

**What goes wrong:** This exact pitfall already bit Phase 1 twice (`20260718211140_grant_profiles_privileges.sql`, `20260719001207_grant_profiles_service_role.sql`) — a self-managed local Supabase CLI stack does not auto-grant table privileges to the `authenticated`/`service_role` Postgres roles the way the hosted Supabase dashboard does. Defining RLS policies on `holdings` without also `GRANT`ing `select, insert, update, delete` to `authenticated` (and `all` to `service_role` for tests) will produce `permission denied for table holdings` (42501) regardless of correct RLS logic.
**Why it happens:** RLS and GRANTs are two independent Postgres authorization layers; the hosted Supabase product's dashboard/CLI-provisioning path grants these automatically, but a bare `create table` + `create policy` migration on a self-managed stack does not.
**How to avoid:** Include the `GRANT` statements for `holdings` in the same migration (or an immediate follow-up migration, matching the Phase 1 pattern) that creates the table and its RLS policies — do not treat this as a separate later fix.
**Warning signs:** `test_holdings_rls.py`-style tests failing with a 42501 permission error rather than an RLS-filtering assertion failure.

### Pitfall 4: `pandas.rolling(center=True)` is a silent lookahead bug, not an obvious one

**What goes wrong:** Unlike `.shift(-1)` (which reads as suspicious on sight), `df.rolling(window, center=True)` looks like an innocuous formatting choice (it's genuinely useful for smoothing a chart for *display*) but pulls `window // 2` future rows into every computed value — a real, silent instance of ARCHITECTURE.md's Anti-Pattern 3 in a form a reviewer might not immediately recognize as a lookahead bug.
**Why it happens:** `center=True` is a legitimate, documented pandas parameter with real non-predictive use cases (visualization smoothing), so it doesn't trigger the same "this looks wrong" instinct that `.shift(-1)` does.
**How to avoid:** Never pass `center=True` anywhere in `technical.py`/`feature_frame.py`; the D-11 leakage smoke test (below) should include at least one assertion that would fail if `center=True` were accidentally introduced.
**Warning signs:** A feature value at row `t` changing when the underlying raw DataFrame is truncated to end exactly at row `t` vs. extended further — this is precisely what the leakage smoke test's truncation-invariance check (Code Examples, below) is designed to catch.

## Code Examples

### D-11 leakage smoke test (truncation-invariance + synthetic future-signal injection)

```python
# Source: pattern synthesized from ARCHITECTURE.md Anti-Pattern 3 guidance +
# general smoke-testing practice for ML feature pipelines
# [CITED: pattern cross-corroborated across multiple lookahead-bias sources,
#  no single canonical library implements this — it is a hand-written pytest
#  pattern by design, per D-11's "no special leakage-testing library exists"]
import pandas as pd
import pytest

from src.features.feature_frame import assemble_feature_frame


def _sample_ohlcv(n_rows: int) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    close = pd.Series(range(100, 100 + n_rows), index=dates, dtype=float)
    return pd.DataFrame({"close": close, "high": close, "low": close, "open": close})


def test_truncation_invariance_no_future_data_changes_past_features():
    """Features for dates <= T must be identical whether the raw frame ends
    at T or extends 30 rows further into the future."""
    full_df = _sample_ohlcv(100)
    truncated_df = full_df.iloc[:70]  # ends at "T"

    features_from_truncated = assemble_feature_frame(truncated_df)
    features_from_full = assemble_feature_frame(full_df).iloc[:70]

    pd.testing.assert_frame_equal(features_from_truncated, features_from_full)


def test_synthetic_future_signal_never_appears_before_its_source_date():
    """A column deterministically derived from a *future* close price must
    not leak into any feature value dated before that future date."""
    df = _sample_ohlcv(100)
    future_date = df.index[80]
    # "cheat" signal: literally the future close price, injected as if it
    # were available from day 1 — a bug would leak this into early rows'
    # features (e.g. via an unguarded merge/join or center=True rolling).
    df["cheat_future_close"] = df.loc[future_date, "close"]

    features = assemble_feature_frame(df)

    assert "cheat_future_close" not in features.columns.tolist() or (
        features.loc[: df.index[79], "cheat_future_close"].isna().all()
    )
```

### Point-in-time technical features (`src/features/technical.py`)

```python
# Source: pandas-ta-classic df.ta accessor, per pypi.org/project/pandas-ta-classic
# [ASSUMED — WebSearch-sourced API shape, not Context7-verified this session;
#  verify exact column-naming output (e.g. "SMA_20", "RSI_14") against the
#  installed 0.6.52 package during implementation, not just this research]
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

### `holdings` CRUD via a scoped client (`src/data/profile.py`)

```python
# Source: pattern matches src/auth/session.py's _touch_last_login — a
# short-lived client with the caller's access_token attached, never the
# shared cache_resource client used for authenticating calls.
from supabase import create_client

from src.config import get_config


def upsert_holdings(access_token: str, user_id: str, rows: list[dict]) -> None:
    scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    scoped_client.postgrest.auth(access_token)
    # Replace-all-on-save semantics (simplest correct behavior for a
    # dynamic add/remove-row grid): delete existing rows for this user,
    # then insert the current grid state.
    scoped_client.table("holdings").delete().eq("user_id", user_id).execute()
    if rows:
        scoped_client.table("holdings").insert(
            [{**row, "user_id": user_id} for row in rows]
        ).execute()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|-------------------|---------------|--------|
| `pandas-ta` (original) for technical indicators | `pandas-ta-classic` (community-maintained fork) | Project's own STACK.md research (2026-07-14) already made this switch — not a new finding this session | Avoids depending on an unmaintained package; carries forward the `[SUS]` legitimacy caveat documented above |
| Native Postgres `ENUM` for fixed-choice fields | `text` + `CHECK` constraint | No version-dated "change" — this is a longstanding tradeoff, but increasingly the recommended default for schemas expected to evolve (Supabase's own 2026 docs and community guidance both lean `CHECK` for anything not truly immutable) | Avoids `ACCESS EXCLUSIVE`-lock migration friction later in this project's active development |

**Deprecated/outdated:** None specific to this phase beyond what STACK.md already flagged project-wide (`google-generativeai`, Gemini 2.0 Flash, original `pandas-ta`, `TA-Lib` on Streamlit Cloud) — not relevant to this phase's scope.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|-----------------|
| A1 | `pandas-ta-classic`'s `df.ta.sma/.rsi/.macd/.bbands` accessor API and default `center=False` rolling behavior, as described in Standard Stack / Code Examples | Standard Stack, Architecture Patterns, Code Examples | If the actual installed 0.6.52 API differs (e.g. different method names, different default column-naming), `technical.py`'s implementation would need adjustment during Wave 0/1 of execution — low risk since this is a widely-documented library shape, but not Context7-verified this session (no context7 MCP tool was available) |
| A2 | `pandas-ta-classic` is a legitimate, non-malicious continuation of the `pandas-ta` lineage (not a namesquat) | Package Legitimacy Audit | If wrong, a `SUS`-flagged, unverified package would be installed into the project's dependency tree — mitigated by the required `checkpoint:human-verify` task before install |
| A3 | `pandas` 2.3.x is compatible with `pandas-ta-classic` 0.6.52; pandas 3.0.x compatibility unverified | Standard Stack | If pandas 3.x has breaking changes `pandas-ta-classic` hasn't adapted to yet, pinning to 2.3.x (as recommended) avoids the risk entirely — but if a future phase needs pandas 3.x for another dependency, this pin may need revisiting |
| A4 | `yf.download()` returns an empty DataFrame (not an exception) for an invalid/delisted ticker, as described in Pitfall 1 | Common Pitfalls, Anti-Patterns | Sourced from multiple `ranaroussi/yfinance` GitHub issues/discussions (community, not official docs) — behavior is well-corroborated across sources but should be confirmed with a quick manual check against a known-bad ticker string during implementation before relying on `df.empty` as the sole validation signal |

**If this table is empty:** N/A — see entries above; none of these are project-compliance-critical, all are implementation-detail risks with clear mitigations already built into the recommended approach.

## Open Questions

1. **Exact `pandas-ta-classic` column-naming convention for MACD/Bollinger output**
   - What we know: `df.ta.macd()`/`df.ta.bbands()` append multiple columns (e.g. MACD line, signal line, histogram; upper/mid/lower bands) per standard TA-library convention.
   - What's unclear: The exact column name strings (e.g. `MACD_12_26_9` vs. some other naming) were not verified against the installed 0.6.52 package this session.
   - Recommendation: If MACD/Bollinger are implemented (D-10 marks them optional), inspect `df.ta.macd().columns` directly against the installed package during Wave 0/1 rather than hardcoding assumed column names from this research.

2. **Whether `holdings` needs a uniqueness constraint on `(user_id, ticker)`**
   - What we know: D-06/D-07 describe holdings as dynamic rows a user adds/edits/removes; nothing in CONTEXT.md explicitly says duplicate ticker rows are disallowed or should be merged.
   - What's unclear: If a user adds "AAPL" twice with different quantities, should that be two separate lots (valid, since cost-basis differs per purchase) or a data-entry error to block?
   - Recommendation: Do not add a uniqueness constraint — multiple rows for the same ticker are a legitimate "multiple purchase lots" pattern (this also more naturally supports the future gain/loss feature D-07 was captured for). Leave as an explicit non-constraint, not an oversight.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|--------------|-----------|---------|----------|
| Local Supabase CLI stack | `holdings`/`profiles` migration testing (same pattern as Phase 1's `test_rls_policy.py`) | ✓ | Running at `http://127.0.0.1:54321` (`npx supabase status` confirmed reachable; `imgproxy`/`pooler` sub-services reported stopped but not required for Postgres/Auth/PostgREST) | — |
| Python | Feature pipeline, all tests | ✓ | 3.13.7 (dev machine) | STACK.md recommends 3.11/3.12 for prebuilt ML-library wheels (Prophet/XGBoost, Phase 4 concern) — not a blocker for this phase's pure-Python/`pandas-ta-classic` scope, but worth confirming the deployment target (Streamlit Community Cloud) pins 3.11/3.12 per STACK.md before Phase 4, not this phase |
| `pandas-ta-classic` | `features/technical.py` | ✗ (not yet installed) | latest available: 0.6.52 | None needed — installation is part of this phase's own task list, gated by the `checkpoint:human-verify` step (Package Legitimacy Audit) |
| Network access to Yahoo Finance (yfinance) | D-08 ticker validation | Not directly probed this session (existing `fetch_ohlcv` chokepoint already exercises this in Phase 1) | — | Existing `fetch_ohlcv` stale-cache fallback applies; a first-time never-before-fetched ticker with no network access would need to surface as a validation failure, not a silent pass — worth an explicit test case |

**Missing dependencies with no fallback:** none blocking.
**Missing dependencies with fallback:** `pandas-ta-classic` — install is itself an in-scope task this phase, not a true "missing" dependency.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (per `pyproject.toml`'s `[tool.pytest.ini_options]`, already established in Phase 1) |
| Config file | `pyproject.toml` (`testpaths = ["tests"]`, `pythonpath = ["."]`) |
| Quick run command | `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` |
| Full suite command | `pytest` (runs the entire `tests/` directory, including the live-local-Supabase-stack tests inherited from Phase 1 — requires `npx supabase start` running first, per `tests/conftest.py`'s `supabase_env` fixture) |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|---------------------|---------------|
| PROFILE-01 | Profile form saves all scalar fields to Supabase | integration (real local stack, no mocking — matches `test_profile_persistence.py` precedent) | `pytest tests/test_profile_crud.py -x` | ❌ Wave 0 |
| PROFILE-01 | Holdings dynamic rows save/read back correctly, RLS-scoped per user | integration (real local stack, two-user isolation, matches `test_rls_policy.py` precedent) | `pytest tests/test_holdings_rls.py -x` | ❌ Wave 0 |
| PROFILE-01 | Invalid ticker on holdings form submit is flagged, not silently saved | unit (mocked `fetch_ohlcv`, matches `test_cache.py`'s mocking pattern) | `pytest tests/test_ticker_validation.py -x` | ❌ Wave 0 |
| PROFILE-02 | Editing an existing profile and reloading shows updated values immediately (no stale cache) | integration (real local stack; assert D-13's uncached-read behavior explicitly, e.g. by asserting no `st.cache_data` decorator wraps the read function) | `pytest tests/test_profile_crud.py::test_edit_reflects_immediately -x` | ❌ Wave 0 |
| (infrastructure, supports Phase 3/4) | Feature functions are point-in-time safe | unit + smoke test | `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_features_technical.py tests/test_features_leakage.py -x` (fast, no live-stack dependency)
- **Per wave merge:** `pytest` (full suite, requires `npx supabase start`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `tests/test_features_technical.py` — covers each `technical.py` function's basic correctness (known-input/known-output for SMA/RSI/returns/volatility)
- [ ] `tests/test_features_leakage.py` — covers D-11 (truncation-invariance + synthetic-future-signal-injection)
- [ ] `tests/test_profile_crud.py` — covers PROFILE-01/PROFILE-02 scalar-field save/edit round-trip against the real local Supabase stack
- [ ] `tests/test_holdings_rls.py` — covers holdings RLS isolation (two-user pattern, same shape as `test_rls_policy.py`)
- [ ] `tests/test_ticker_validation.py` — covers D-08 (mocked `fetch_ohlcv`, including the empty-DataFrame invalid-ticker case from Pitfall 1)
- [ ] New migration: `supabase/migrations/<timestamp>_extend_profiles_and_create_holdings.sql` (plus a same-phase GRANT migration per Pitfall 3, matching the Phase 1 precedent — do not defer to a follow-up "fix" migration)

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|-----------------|---------|---------------------|
| V2 Authentication | Yes (inherited, not new) | `require_auth()` — every new page (`src/pages/profile.py`) calls it first, per the established Phase 1 D-04 pattern; no new auth logic this phase |
| V3 Session Management | Yes (inherited, not new) | Access token stays in `st.session_state`; profile/holdings CRUD helpers take the token explicitly (matches `_touch_last_login`'s scoped-client pattern) — never persisted onto the shared `get_supabase_client()` object |
| V4 Access Control | Yes (new surface area) | Postgres RLS on both `profiles` (existing policies extend automatically to new columns) and the new `holdings` table (Pattern 1 above) — this is the primary new security surface this phase introduces |
| V5 Input Validation | Yes | Ticker validation via `fetch_ohlcv` + `df.empty` check (D-08, Pitfall 1); numeric fields (`quantity`, `cost_basis`, `capital`) should be validated as non-negative numbers at the Streamlit-form layer before ever reaching Supabase; `CHECK` constraints (Pattern 2) provide defense-in-depth at the database layer for the two fixed-value-set fields |
| V6 Cryptography | No | No new cryptographic operations introduced this phase |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|------------------------|
| IDOR on `holdings` (a user reading/editing another user's holdings by guessing/manipulating a row id) | Elevation of Privilege / Information Disclosure | RLS policy set (Pattern 1) enforced at the Postgres engine, not app-layer filtering — verified by a `test_holdings_rls.py` two-user test, same shape as Phase 1's `test_rls_policy.py` |
| Missing GRANTs silently blocking legitimate access, then "fixed" by over-broadly granting to the wrong role | Denial of Service (accidental) / Elevation of Privilege (if over-corrected) | Grant exactly `select, insert, update, delete` to `authenticated` and `all` to `service_role` only — mirrors the exact scope of Phase 1's `20260718211140_grant_profiles_privileges.sql`, do not grant to `anon` |
| SQL injection via ticker/sector/free-text fields | Tampering | All Supabase writes in this phase go through `supabase-py`'s query builder (`.insert()`/`.update()` with a dict payload), which parameterizes values — never build raw SQL strings with interpolated user input (matches the existing `src/data/cache.py` `?`-placeholder discipline, T-01-03 precedent) |
| Mass assignment / over-posting on profile update (a form handler blindly passing `st.session_state` or raw form dict into `.update()`) | Tampering | Explicitly construct the update payload as a whitelisted dict of only the expected profile/holdings columns in `src/data/profile.py` — never pass a raw widget-state dict straight through to Supabase |
| Stored injection via `unsafe_allow_html` fed by user input | Tampering (XSS-adjacent, though Streamlit is server-rendered not browser-JS) | The existing `_highlight_empty_fields` pattern in `src/pages/login.py` only ever interpolates static, developer-controlled `key=` strings into `unsafe_allow_html`, never raw user input — replicate that same discipline if any CSS-injection helper is reused/extended for the profile page; never interpolate a ticker/sector string or any other user-entered value into `unsafe_allow_html` |

## Sources

### Primary (HIGH confidence)
None — no official Context7 MCP tool was available in this research session; all findings below are WebSearch-derived and cross-checked against official docs URLs where cited.

### Secondary (MEDIUM confidence)
- [Row Level Security | Supabase Docs](https://supabase.com/docs/guides/database/postgres/row-level-security) — RLS policy shape, `(select auth.uid())` performance pattern
- [Managing Enums in Postgres | Supabase Docs](https://supabase.com/docs/guides/database/postgres/enums) — CHECK vs. ENUM tradeoffs
- [Enums vs Check Constraints in Postgres | Crunchy Data Blog](https://www.crunchydata.com/blog/enums-vs-check-constraints-in-postgres) — ACCESS EXCLUSIVE lock / ALTER TYPE friction detail
- [st.data_editor - Streamlit Docs](https://docs.streamlit.io/develop/api-reference/data/st.data_editor) — `num_rows="dynamic"` behavior
- [pandas-ta-classic · PyPI](https://pypi.org/project/pandas-ta-classic/) — package version/identity (0.6.52)
- [GitHub - xgboosted/pandas-ta-classic](https://github.com/xgboosted/pandas-ta-classic) — source repo referenced in Package Legitimacy Audit
- `pip index versions pandas-ta-classic` / `pip index versions pandas` — local registry verification, this session
- `gsd-tools query package-legitimacy check --ecosystem pypi pandas-ta-classic` — automated legitimacy gate result (SUS verdict)

### Tertiary (LOW confidence)
- [No data found, symbol may be delisted · Issue #359 · ranaroussi/yfinance](https://github.com/ranaroussi/yfinance/issues/359) and related `ranaroussi/yfinance` GitHub issues/discussions — `yf.download()` empty-DataFrame-not-exception behavior for invalid tickers (Pitfall 1); community-sourced, not official docs, but corroborated across multiple independent issue threads
- [Look-Ahead Bias / lookahead-bias smoke-testing sources] — general pytest leakage-smoke-test pattern (no single canonical source; synthesized from cross-corroborated community/ML-engineering writeups per the research protocol)
- yfinance ticker-convention and calendar-difference community sources (blog posts, Medium writeups) — cross-checked against this project's own existing `src/data/cache.py`/`prices.py` code, which already encodes the `BTC-USD`/`EURUSD=X`/`GC=F` ticker conventions from Phase 1's own (separately-cited) research

## Metadata

**Confidence breakdown:**
- Standard stack: MEDIUM — `pandas-ta-classic` API shape and versions verified against PyPI registry directly, but not against Context7/official docs (unavailable this session); package legitimacy gate flagged `SUS`, requiring a human-verify checkpoint
- Architecture (RLS/schema patterns): MEDIUM-HIGH — RLS/GRANT patterns directly extend an already-proven, already-tested precedent in this exact codebase (Phase 1's `profiles` table + its two follow-up GRANT migrations), not a novel pattern being introduced cold
- Pitfalls: MEDIUM — Pitfall 1 (yfinance empty-DataFrame behavior) and Pitfall 3 (RLS+GRANT on self-managed stacks) are both either directly corroborated by multiple independent sources or already proven true in this exact codebase's git history

**Research date:** 2026-07-19
**Valid until:** 2026-08-18 (30 days — no fast-moving/deprecation-risk dependencies introduced this phase; re-verify `pandas-ta-classic`'s legitimacy signals, e.g. download counts, if this research is reused after that date)
