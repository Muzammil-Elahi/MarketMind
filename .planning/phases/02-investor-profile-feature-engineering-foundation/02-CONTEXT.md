# Phase 2: Investor Profile + Feature Engineering Foundation - Context

**Gathered:** 2026-07-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Two deliverables that share a phase because both are foundational inputs the recommendation engine (Phase 3) depends on, but neither has any UI/model surface of its own yet:

1. **Investor profile builder** — a Streamlit form where a user builds/edits risk tolerance, time horizon, preferred/excluded sectors, preferred asset types, capital, and existing holdings, persisted to Supabase (extending the `profiles` stub table created in Phase 1).
2. **Feature engineering pipeline** — a pure-Python, no-I/O module (`src/features/`) that computes point-in-time technical/factor features from cached price data, with an automated leakage smoke test. No UI surface — this is infrastructure Phase 3 (recommendation) and Phase 4 (prediction/backtest) will import, not render.

Explicitly NOT this phase: recommendation scoring/ranking logic (Phase 3), any model training or prediction (Phase 4), news/sentiment features (deferred to v2 SENT-01).

</domain>

<decisions>
## Implementation Decisions

### Profile field design
- **D-01:** Risk tolerance is a 3-level categorical field: Conservative / Moderate / Aggressive. Maps directly and unambiguously to Phase 3's factor-weight buckets — no intermediate bucketing logic needed downstream.
- **D-02:** Time horizon is captured as bucketed categories: `<1yr`, `1-3yr`, `3-5yr`, `5-10yr`, `10+yr` (not a free numeric year input) — same rationale as D-01, ready to consume as weight-bucket keys in Phase 3.
- **D-03:** Preferred/excluded sectors use a simplified ~10-category list (Tech, Healthcare, Financials, Energy, Consumer, Industrials, Real Estate, Utilities, Materials, Communication), not the full GICS 11-sector standard. Close enough to yfinance's own sector field for later matching; full GICS was judged unnecessary complexity at this scale.
- **D-04:** Preferred asset types use multi-select checkboxes across the 5 supported classes (stocks/ETFs/crypto/gold/forex), include-only (no separate "exclude asset type" toggle — asymmetric with sectors, which do get preferred/excluded, by design; user only selects what they want more of).
- **D-05 (Claude's discretion):** Capital input format (numeric dollar field vs. bucketed ranges) — not deep-dived, left to implementation. A single numeric dollar input is the obvious default given no counter-signal was raised.

### Existing holdings format
- **D-06:** Holdings are captured as structured rows: ticker + quantity (shares/units), via a dynamic add-row UI — not a free-text ticker list. Sets up future gain/loss or exposure-overlap features without a schema migration later.
- **D-07:** Each holding row has an *optional* cost-basis (purchase price) field. Nothing in the current roadmap (through Phase 6) consumes this yet, but the user wants it captured now rather than added later as a schema change.
- **D-08:** Entered ticker symbols are validated against yfinance on form submit (not on every keystroke, not deferred to first-use) — flag unrecognized tickers back to the user at save time.

### Feature pipeline scope
- **D-09:** The feature module must handle all 5 asset classes (stocks, ETFs, crypto, gold, forex) now, not equities-only first — even though STATE.md flags cross-asset-class factor-weight *normalization* as unresearched until Phase 3. This phase's scope is point-in-time feature computation (returns/volatility/indicators), not weighting, so building calendar-agnostic logic now (crypto trades 24/7, equities/ETFs don't) avoids a later rework of `features/feature_frame.py`.
- **D-10 (Claude's discretion):** Exact technical indicator set for this phase (returns, volatility, SMA, RSI at minimum per ARCHITECTURE.md; MACD/Bollinger optional) — user deferred to implementation time. Guidance: prefer the ARCHITECTURE.md-cited core set (returns, volatility, SMA, RSI, moving averages) as the floor; add MACD/Bollinger only if cheap to do point-in-time-safely in the same pass, since no model consumes any of it until Phase 3/4.
- **D-11 (Claude's discretion):** Exact leakage-smoke-test mechanism — user deferred to implementation time. Strong default per ARCHITECTURE.md Anti-Pattern 3: inject a synthetic future-only signal into test data and assert the feature/backtest pipeline does NOT show improved accuracy from it. Use this pattern unless research surfaces something stronger.

### Profile edit UX
- **D-12:** Single always-editable form serves both first-time creation and later edits — pre-filled with existing values if a profile row exists, empty otherwise. No separate view-then-edit-mode toggle.
- **D-13:** Profile reads are NOT wrapped in `st.cache_data` — fetch fresh from Supabase on every page load. This is a cheap single-row query (unlike yfinance), so the simplest way to satisfy success criterion #2 ("updated values reflected immediately... no stale cache") is to just not cache it, rather than caching with explicit invalidation on save.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope & requirements
- `.planning/PROJECT.md` — core value, constraints ($0 budget, free-tier-only), Key Decisions table
- `.planning/REQUIREMENTS.md` — PROFILE-01, PROFILE-02 requirement definitions and traceability
- `.planning/ROADMAP.md` §"Phase 2: Investor Profile + Feature Engineering Foundation" — goal, success criteria, dependencies

### Architecture & research (directly informed this discussion)
- `.planning/research/ARCHITECTURE.md` — see especially: `features/` module structure (`technical.py`, `sentiment.py`, `feature_frame.py`), Pattern 3 "Shared feature frame (no train/serve skew, no lookahead)", Anti-Pattern 3 "Feature computation that leaks future data" (leakage-test guidance for D-11), `data/` ↔ `features/` boundary rules (no Streamlit imports, no I/O in `features/`)
- `.planning/research/FEATURES.md` — see especially: "Investor profile / risk questionnaire" table-stakes entry (profile must visibly change rec output), MVP definition confirming profile builder scope
- `.planning/research/PITFALLS.md` — general free-tier/caching pitfalls carried forward from Phase 1
- `.planning/research/STACK.md` — approved dependency versions (pandas-ta-classic for indicators, per "What NOT to Use" — not TA-Lib or original pandas-ta)

### Prior phase artifacts (schema this phase extends)
- `supabase/migrations/20260718204703_create_profiles.sql` — the `profiles` stub table (user_id, created_at, last_login) this phase's migration must extend with real profile columns, plus its RLS policies (select/update scoped to owning user) and the `handle_new_user()` auto-provisioning trigger — new columns must remain compatible with this trigger's INSERT
- `.planning/phases/01-foundation-data-layer-caching-auth/01-CONTEXT.md` — D-10/D-11 there record that the `profiles` table was deliberately built as this phase's seed, not throwaway scaffolding

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/auth/session.py` `require_auth()` — call this first (and only) on the new profile page, per Phase 1's D-04 pattern; no inline auth logic.
- `src/data/supabase_client.py` `get_supabase_client()` — the shared, stateless `st.cache_resource` client. Profile CRUD should go through this, passing the user's token explicitly where row-level auth context is needed (same pattern as `src/auth/session.py`).
- `src/data/cache.py` / `src/data/prices.py` — existing chokepoint for cached OHLCV fetches (`fetch_ohlcv`). The feature pipeline's raw-data input should call `fetch_ohlcv` from `src/data/prices.py`, never `yfinance` directly or `src/data/cache.py` internals.

### Established Patterns
- Single-chokepoint pattern: all yfinance access routes through `src/data/cache.py` → `src/data/prices.py`. The new `src/features/` module must consume prices only via `fetch_ohlcv`, keeping it I/O-free and independently testable (per ARCHITECTURE.md).
- RLS-per-table pattern established in Phase 1 (`profiles` table): new profile columns added by this phase's migration inherit the existing owner-scoped select/update policies — no new RLS policy needed unless a new table is introduced.
- `require_auth()`-first pattern: every page (including the new profile page) calls this exactly once at the top, per Phase 1 D-04.

### Integration Points
- New profile page (e.g. `src/pages/profile.py`) registered in `src/app.py`'s `st.navigation`, following the same pattern as the existing `home.py`/`login.py` pages.
- New migration file under `supabase/migrations/` extending `public.profiles` with the fields from D-01–D-08 (risk tolerance, time horizon, sectors, asset types, capital, holdings — holdings likely need their own child table or JSON column given the structured ticker+quantity+cost-basis rows from D-06/D-07).
- New `src/features/` package (`technical.py`, `feature_frame.py` at minimum, per ARCHITECTURE.md's proposed structure) with zero Streamlit/I/O imports, consuming `src/data/prices.py`.

</code_context>

<specifics>
## Specific Ideas

- Holdings should be structured (ticker + quantity, optional cost basis) specifically so a later phase can compute gain/loss or portfolio-overlap features without a schema migration — this was an explicit forward-looking choice, not just "what's easiest now."
- The asymmetry between sectors (preferred AND excluded) and asset types (preferred only, D-04) is intentional — asset-type exclusion wasn't asked for and shouldn't be added speculatively.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope. No scope-creep suggestions came up during this session.

### Reviewed Todos (not folded)
None — `todo.match-phase` returned zero matches for Phase 2.

</deferred>

---

*Phase: 2-Investor Profile + Feature Engineering Foundation*
*Context gathered: 2026-07-19*
