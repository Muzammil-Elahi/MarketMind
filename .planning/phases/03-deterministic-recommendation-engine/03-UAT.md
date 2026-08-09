---
status: resolved
phase: 03-deterministic-recommendation-engine
source: [03-08-PLAN.md Task 1 human-check, deferred by verifier per workflow.human_verify_mode: end-of-phase]
started: 2026-08-09T16:00:00Z
updated: 2026-08-09T20:00:00Z
---

## Current Test

None — user approved phase 3 as done after the blocking bug (test 2) was found and fixed.

## Tests

### 1. Nav visibility — Recommendations and Search appear only when logged in
expected: "Recommendations" and "Search" appear in the sidebar nav alongside Home/Profile after logging in; neither appears before logging in.
result: Not individually re-confirmed with a screenshot; user approved phase 3 overall (see closure note).

### 2. Recommendations page — disclaimer, all 5 asset-class sections, card contents
expected: Disclaimer banner renders near the top. All 5 asset-class section headers (Stocks/ETFs/Crypto/Gold/Forex) render in that order even if a class has few/no cards. Each card shows a "{score}/100" composite score, an expandable "Score Breakdown" bar chart with 5 bars in Profile Fit/Momentum/Volatility/Quality/Similarity order (Profile Fit at top after the WR-02 fix), and a one-sentence explanation that plausibly matches the highest bar(s).
result: RESOLVED — initially FAILED (page showed "We couldn't generate recommendations right now" for a fully-filled profile; screenshot evidence: risk_tolerance=Moderate, time_horizon=10+yr, sectors=Tech/Financials, all asset types checked, capital=1000, holdings SPY/QQQ). Root cause: `yf.download()` in `src/data/cache.py::_fetch_live` returned MultiIndex columns (`[('Close','AAPL'),...]`); `df["Close"]` yielded a 1-column DataFrame instead of a Series, so `pandas_ta_classic`'s `ta.sma()`/`ta.rsi()` silently produced all-NaN `sma_20`/`rsi_14` for every ticker; `dropna()` removed every row → 0 scorable rows across the entire 58-ticker universe. Cross-phase bug in Phase 1's `fetch_ohlcv` chokepoint (masked by all phases' tests using mocked flat-column DataFrames). Fixed via quick task `260809-j0k` (commit `4a15535`, merged `b98e9f2`): MultiIndex columns are now flattened at the yfinance chokepoint. Verified: live `fetch_ohlcv('AAPL')` returns flat columns, `assemble_feature_frame(df).dropna()` retains 231 rows (was 0); new regression test `tests/test_cache.py::test_multiindex_columns_from_live_fetch_are_flattened`; full suite 130/130 passing. App restarted with the fix; page was not re-screenshotted after restart, but user approved phase 3 as done afterward.

### 3. View Details cross-navigation
expected: Clicking "View Details" on any card navigates to the Search page with that ticker pre-filled and its score/chart already showing.
result: Not individually re-confirmed after the fix; user approved phase 3 overall (see closure note).

### 4. Search — valid ticker outside curated universe
expected: A valid, well-known ticker not in the recommended list (e.g. a large-cap stock) scores correctly.
result: Not individually re-confirmed after the fix; user approved phase 3 overall (see closure note).

### 5. Search — invalid ticker
expected: An obviously-invalid ticker (e.g. "ZZZZZZINVALID") shows the "We couldn't find..." error, no crash.
result: Not individually re-confirmed after the fix; user approved phase 3 overall (see closure note).

### 6. Search — empty submit
expected: Leaving the search box empty and submitting shows the "Search for any asset..." empty-state copy, no fetch attempted.
result: Not individually re-confirmed after the fix; user approved phase 3 overall (see closure note).

### 7. Disclaimer on Search page
expected: The disclaimer banner also renders on the Search page.
result: Not individually re-confirmed after the fix; user approved phase 3 overall (see closure note).

### 8. Search — ETF ticker (CR-02 regression)
expected: Searching an ETF ticker (e.g. SPY or QQQ) now scores against the ETF peer group, not Stocks (this was the critical bug fixed by CR-02).
result: Not individually re-confirmed via the UI after the fix, but `infer_asset_class("SPY")`/`("QQQ")` → `"ETFs"` was independently verified live during phase verification (03-VERIFICATION.md). User approved phase 3 overall (see closure note).

## Summary

total: 8
passed: 1
issues: 0
pending: 0
skipped: 0
blocked: 0
user_approved_without_individual_walkthrough: 7

## Gaps

- status: resolved
  test: 2 (Recommendations page)
  description: Zero scorable rows across the entire universe because yfinance's MultiIndex-column DataFrame broke pandas_ta_classic's sma/rsi computation. Fixed via quick task 260809-j0k (commit 4a15535, merged b98e9f2). Full test suite passing (130/130) after fix.

## Closure Note

User explicitly approved Phase 3 as done (2026-08-09), conditional on two follow-up ideas raised during this UAT session being captured for later rather than blocking now — both logged as backlog Phase 999.1 (scoring explanation depth, portfolio-aware recommendations). Tests 1 and 3–7 were not individually re-walked with screenshot evidence after the test-2 fix; closure relies on the user's explicit sign-off plus the automated test suite (130/130) rather than a full re-walkthrough. If issues in the untested areas surface later, they are not gaps in this UAT — they were knowingly left unverified at user's direction.
