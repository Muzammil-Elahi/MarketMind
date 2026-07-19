# Phase 2: Investor Profile + Feature Engineering Foundation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-07-19
**Phase:** 2-Investor Profile + Feature Engineering Foundation
**Areas discussed:** Profile field design, Existing holdings format, Feature pipeline scope, Profile edit UX

---

## Profile field design

| Question | Option | Selected |
|----------|--------|----------|
| Risk tolerance capture | 3-level categorical (Conservative/Moderate/Aggressive) | ✓ |
| | 5-level categorical | |
| | 1-10 slider | |
| Time horizon capture | Bucketed categories (<1yr, 1-3yr, 3-5yr, 5-10yr, 10+yr) | ✓ |
| | Free numeric years input | |
| Sector taxonomy | Simplified list (~10 categories) | ✓ |
| | Full GICS 11-sector standard | |
| Asset-type selection | Multi-select checkboxes, include-only | ✓ |
| | Checkboxes + exclude toggle | |

**User's choice:** 3-level risk tolerance, bucketed time horizon, simplified ~10-sector list, include-only asset-type checkboxes.
**Notes:** Capital input format was not deep-dived — user moved to next area, leaving it (numeric dollar field) to Claude's discretion.

---

## Existing holdings format

| Question | Option | Selected |
|----------|--------|----------|
| Entry format | Structured rows (ticker + quantity) | ✓ |
| | Free-text ticker list | |
| Cost basis | No — ticker + quantity only | |
| | Yes — optional cost-basis field | ✓ |
| Ticker validation | No live validation | |
| | Validate on submit | ✓ |

**User's choice:** Structured ticker+quantity rows, optional cost-basis field, validate tickers against yfinance on submit.
**Notes:** Cost basis isn't consumed by anything currently in the roadmap, but user wants it captured now to avoid a later schema change.

---

## Feature pipeline scope

| Question | Option | Selected |
|----------|--------|----------|
| Indicator set | Core set: returns, volatility, SMA, RSI | |
| | Full technical set now (+MACD, Bollinger) | |
| | You decide | ✓ |
| Asset-class coverage | Equities + ETFs first | |
| | All 5 asset classes now | ✓ |
| Leakage smoke test | Injected future-signal test | |
| | You decide | ✓ |

**User's choice:** All 5 asset classes now; indicator set and leakage-test mechanism left to Claude's discretion.
**Notes:** User explicitly chose to front-load cross-asset-calendar complexity (crypto 24/7 vs. equities) now rather than defer to Phase 3, even though STATE.md flags factor-weight normalization across asset classes as still-unresearched.

---

## Profile edit UX

| Question | Option | Selected |
|----------|--------|----------|
| Create vs. edit handling | Single always-editable form | ✓ |
| | View screen + separate edit mode | |
| Cache/staleness enforcement | No st.cache_data on profile reads | ✓ |
| | Cached with explicit invalidation on save | |

**User's choice:** Single always-editable form; no caching on profile reads (fetch fresh every load).
**Notes:** Profile reads are a cheap single-row Supabase query, unlike rate-limited yfinance calls, so skipping caching entirely was judged simpler than cache+invalidate.

---

## Claude's Discretion

- Capital input format (D-05): numeric dollar field assumed as default, not challenged.
- Feature pipeline exact indicator set (D-10): core ARCHITECTURE.md set (returns, volatility, SMA, RSI) as floor; MACD/Bollinger added only if cheap.
- Leakage smoke test mechanism (D-11): injected future-signal test per ARCHITECTURE.md Anti-Pattern 3, unless research surfaces something stronger.

## Deferred Ideas

None — discussion stayed within phase scope; no scope-creep suggestions arose.
