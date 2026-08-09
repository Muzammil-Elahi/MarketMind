---
phase: 03-deterministic-recommendation-engine
reviewed: 2026-08-09T00:00:00Z
depth: standard
files_reviewed: 22
files_reviewed_list:
  - src/app.py
  - src/components/__init__.py
  - src/components/charts.py
  - src/components/disclaimer.py
  - src/pages/_universe_loader.py
  - src/pages/recommendations.py
  - src/pages/search.py
  - src/recommendation/__init__.py
  - src/recommendation/engine.py
  - src/recommendation/explain.py
  - src/recommendation/factor_scoring.py
  - src/recommendation/profile_fit.py
  - src/recommendation/similarity.py
  - src/recommendation/universe.py
  - tests/test_components.py
  - tests/test_recommendation_engine.py
  - tests/test_recommendation_explain.py
  - tests/test_recommendation_factor_scoring.py
  - tests/test_recommendation_profile_fit.py
  - tests/test_recommendation_search.py
  - tests/test_recommendation_similarity.py
  - tests/test_recommendation_universe.py
  - tests/test_universe_loader.py
findings:
  critical: 2
  warning: 3
  info: 2
  total: 7
status: issues_found
---

# Phase 03: Code Review Report

**Reviewed:** 2026-08-09T00:00:00Z
**Depth:** standard
**Files Reviewed:** 22
**Status:** issues_found

## Summary

Reviewed the deterministic recommendation engine (scoring, factor/profile-fit/similarity/explain modules, curated universe, shared UI components) plus the Recommendations and Search pages that consume it, and their test suites. The scoring math itself is well-covered by unit tests and the zero-I/O module boundaries are respected. Two reachable correctness defects were found: (1) the explanation-sentence generator emits the literal string `"None"` into user-facing copy whenever `risk_tolerance` is unset — a state the Recommendations page's own personalization nudge explicitly anticipates as common (every brand-new user), and (2) any ETF ticker searched on the Search page (e.g. `SPY`, `QQQ`) is silently misclassified as a "Stocks" asset and scored against a random-stocks peer group instead of its real ETF peers, breaking the engine's own within-asset-class normalization invariant for one of the five core, advertised asset classes. Three further warnings and two info-level items are documented below.

## Critical Issues

### CR-01: Explanation sentence renders literal "None" when risk_tolerance is unset

**File:** `src/recommendation/explain.py:29-56` (caller: `src/recommendation/engine.py:113`)
**Issue:** `explain(sub_scores, risk_tolerance)` interpolates `risk_tolerance` directly into `ONE_FACTOR_TEMPLATE`/`TWO_FACTOR_TEMPLATE` with no `None` guard:
```python
ONE_FACTOR_TEMPLATE = "Strong {factor_a} matches your {risk_tolerance} risk profile."
...
return ONE_FACTOR_TEMPLATE.format(factor_a=FACTOR_LABELS[ordered[0][0]], risk_tolerance=risk_tolerance)
```
`engine.py:113` calls this with `profile.get("risk_tolerance")` unmodified — no fallback. `risk_tolerance` is a nullable profile field (Phase 2), and `src/pages/recommendations.py:99` explicitly detects and nudges users who haven't set it yet (`PROFILE_PERSONALIZATION_FIELDS` includes `"risk_tolerance"`). So the very users the nudge message is designed for will see cards reading: `"Strong momentum matches your None risk profile."` on their first visit to Recommendations or Search. Note that the two sibling scoring functions that also take `risk_tolerance` (`similarity.similarity_score` and, implicitly, `profile_fit`) both defensively fall back to a sane default (`similarity.py:43`, `RISK_ARCHETYPES.get(risk_tolerance, RISK_ARCHETYPES["Moderate"])`) — `explain.py` is the one call site that was never given the same treatment, and no test exercises `explain()` with `risk_tolerance=None` (`tests/test_recommendation_explain.py` only passes `"Moderate"`/`"Aggressive"`/`"Conservative"`).
**Fix:**
```python
# explain.py
def explain(sub_scores: dict, risk_tolerance: str | None) -> str:
    risk_tolerance = risk_tolerance or "your"  # or a dedicated default label
    ...
```
or, more robustly, use a template that doesn't degrade when the value is missing, e.g. `"Strong {factor_a} matches your risk profile."` when `risk_tolerance` is falsy, and the current templates otherwise.

### CR-02: Searching an ETF ticker scores it against the wrong peer universe

**File:** `src/recommendation/universe.py:70-85` (`infer_asset_class`), consumed by `src/pages/search.py:73-87`
**Issue:** `infer_asset_class` only special-cases Forex (`=X`), Crypto (`-USD`), and Gold (`GOLD_UNIVERSE` membership or `=F`); every other ticker — including every real ETF such as `SPY`, `QQQ`, `VTI` — falls through to the `"Stocks"` default:
```python
if ticker in GOLD_UNIVERSE or ticker.endswith("=F"):
    return "Gold"
return "Stocks"
```
`resolve_search_result` (`search.py:73-87`) then builds the peer group from `ASSET_CLASS_TICKERS["Stocks"]` (24 real single-name equities) and scores the searched ETF's momentum/volatility/quality against that peer group via `score_universe`, which is explicitly designed to compute percentile ranks **within each asset class's own universe** (`factor_scoring.py`'s whole "Pitfall 1" design point). An ETF's raw returns/volatility profile is not comparable to individual equities', so this produces a materially misleading composite score with no indication to the user that peer-group assignment is wrong. ETFs are one of the five asset classes the app explicitly advertises ("stock, ETF, crypto, gold, or forex pair" — `search.py:34-36`), and the Search page's own placeholder text conspicuously omits an ETF example, suggesting this gap was known but left unhandled. No test covers searching a real ETF ticker (`tests/test_recommendation_universe.py` only checks `GLD`, which is explicitly listed in `GOLD_UNIVERSE`).
**Fix:** Check ETF membership before falling back to Stocks:
```python
from src.recommendation.universe import ETF_UNIVERSE
...
if ticker in ETF_UNIVERSE:
    return "ETFs"
return "Stocks"
```
This still won't classify *arbitrary* off-universe ETF tickers correctly, but at minimum every ETF in the curated universe (the only tickers `search.py` can otherwise resolve for scoring, since peer data only exists for curated tickers) will land in the correct peer group.

## Warnings

### WR-01: Bare `except Exception` silently swallows all errors as "not found," with no logging

**File:** `src/pages/_universe_loader.py:34-37`
**Issue:**
```python
try:
    df, _source = fetch_ohlcv(ticker)
except Exception:
    return {"status": "not_found"}
```
This catches *every* exception type — a genuine bug in `assemble_feature_frame`, a malformed cache row, an unexpected type error, anything — and reports it to the user identically to "ticker doesn't exist," with zero logging. A real defect introduced elsewhere in the fetch/feature pipeline would silently manifest in production as `NOT_FOUND_TEMPLATE` ("We couldn't find ... check the symbol") rather than surfacing anywhere a developer could diagnose it.
**Fix:** At minimum log the exception before returning the not-found status, e.g. `logging.getLogger(__name__).exception("fetch_scorable_row failed for %s", ticker)`, so real bugs are distinguishable from genuine lookup misses in logs/telemetry.

### WR-02: Breakdown bar chart's visual order is not guaranteed to match the documented fixed order

**File:** `src/components/charts.py:18-31`
**Issue:** `build_breakdown_figure` preserves `sub_scores_display`'s dict order in the underlying trace data (`bar.y`), which is correctly unit-tested in `tests/test_components.py`. However, for a Plotly horizontal bar chart (`orientation="h"`), the y-axis is not reversed by default — Plotly renders the *first* category in `y=[...]` at the **bottom** of the chart and later categories going upward, unless `yaxis.autorange="reversed"` is set. The function never sets this, so the rendered chart will visually read bottom-to-top as `profile_fit, momentum, volatility, quality, similarity` — i.e. `similarity` appears at the top and `profile_fit` (explicitly the highest-weighted factor, `WEIGHTS["profile_fit"] = 0.30`) appears at the bottom. This contradicts the module's stated intent ("REC-02's fixed sub-factor display order... is respected") if that order was meant to read top-to-bottom, and no test checks rendered axis order (only trace data order).
**Fix:**
```python
def build_breakdown_figure(sub_scores_display: dict) -> go.Figure:
    ...
    fig = go.Figure(data=[bar])
    fig.update_yaxes(autorange="reversed")
    return fig
```

### WR-03: Tickers that fail to fetch are silently dropped with no user-facing signal

**File:** `src/pages/recommendations.py:103`
**Issue:** `scorable_rows, _unscorable = load_universe_rows(tickers_with_metadata)` discards `_unscorable` entirely. If yfinance/the disk cache fails for a subset of the curated universe (a documented, real risk per CLAUDE.md: "yfinance's undocumented rate limits are the single largest reliability risk in this stack"), the affected asset-class section(s) simply render with fewer (or zero) cards and no distinction from "there are genuinely no assets that scored well here." A user has no way to tell "the engine ran and found nothing" apart from "some tickers temporarily failed to load."
**Fix:** Surface a lightweight notice when `_unscorable` is non-empty, e.g. `st.caption(f"{len(_unscorable)} assets were temporarily unavailable and excluded from these results.")`.

## Info

### IN-01: `capital == 0` is treated as a missing profile field for the personalization nudge

**File:** `src/pages/recommendations.py:99`
**Issue:** `if any(not profile.get(field) for field in PROFILE_PERSONALIZATION_FIELDS):` — for `"capital"`, a user who has legitimately entered `0` will still trigger `PROFILE_NUDGE_MESSAGE` since `not 0` is `True`, even though they've answered the field.
**Fix:** Check for `None` explicitly for numeric fields, e.g. `profile.get("capital") is None`, rather than relying on falsiness.

### IN-02: Search page's query-param prefill is never cleared, so a later manual search can be silently reverted on refresh

**File:** `src/pages/search.py:114-125`
**Issue:** `query_ticker = st.query_params.get("ticker", "")` stays in the URL indefinitely (it's set once by `recommendations.py`'s "View Details" `st.switch_page(..., query_params=...)` call and never cleared by `search.py`). If a user arrives via that link, then types and submits a *different* ticker, the URL still shows `?ticker=<original>`; a subsequent page refresh (or any rerun that doesn't go through the form submit branch) will re-prefill and re-run the search for the original ticker, discarding the user's later manual search.
**Fix:** Clear the query param after consuming it once, e.g. `st.query_params.pop("ticker", None)` after reading `query_ticker`, or track "has the user manually searched since arriving" in `st.session_state`.

---

_Reviewed: 2026-08-09T00:00:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
