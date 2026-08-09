---
phase: 03-deterministic-recommendation-engine
fixed_at: 2026-08-09T16:06:14Z
review_path: .planning/phases/03-deterministic-recommendation-engine/03-REVIEW.md
iteration: 1
findings_in_scope: 5
fixed: 5
skipped: 0
status: all_fixed
---

# Phase 03: Code Review Fix Report

**Fixed at:** 2026-08-09T16:06:14Z
**Source review:** .planning/phases/03-deterministic-recommendation-engine/03-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 5 (critical_warning scope — CR-01, CR-02, WR-01, WR-02, WR-03; IN-01/IN-02 out of scope)
- Fixed: 5
- Skipped: 0

## Fixed Issues

### CR-01: Explanation sentence renders literal "None" when risk_tolerance is unset

**Files modified:** `src/recommendation/explain.py`
**Commit:** f7ef37d
**Applied fix:** Added `ONE_FACTOR_TEMPLATE_NO_RISK` / `TWO_FACTOR_TEMPLATE_NO_RISK` fallback templates that omit the risk-profile clause entirely, and branched `explain()` to use them whenever `risk_tolerance` is falsy (`None` or unset), instead of interpolating a missing value into the existing templates. Manually verified both branches (with and without `risk_tolerance`) produce correct, non-"None" output while preserving the exact existing sentences when `risk_tolerance` is set.

### CR-02: Searching an ETF ticker scores it against the wrong peer universe

**Files modified:** `src/recommendation/universe.py`
**Commit:** 7abd356
**Applied fix:** Added an `ETF_UNIVERSE` membership check to `infer_asset_class`, ordered after the Forex/Crypto/Gold checks and before the Stocks fallback, so curated ETF tickers (`SPY`, `QQQ`, `VTI`, etc.) now classify as `"ETFs"` instead of falling through to `"Stocks"`. Manually verified `SPY`/`QQQ` -> `ETFs`, `AAPL` -> `Stocks`, `GLD` -> `Gold`, `BTC-USD` -> `Crypto`, `EURUSD=X` -> `Forex`. No changes needed in `src/pages/search.py` — it already consumes `infer_asset_class`'s return value to build the peer group via `ASSET_CLASS_TICKERS[asset_class]`, so the corrected classification flows through automatically.

### WR-01: Bare `except Exception` silently swallows all errors as "not found," with no logging

**Files modified:** `src/pages/_universe_loader.py`
**Commit:** 702de4e
**Applied fix:** Added a module-level `logger = logging.getLogger(__name__)` and a `logger.exception("fetch_scorable_row failed for %s", ticker)` call inside the `except Exception:` block in `fetch_scorable_row`, before returning `{"status": "not_found"}`. Genuine bugs in the fetch/feature pipeline are now distinguishable from ordinary lookup misses in logs, without changing the returned status contract.

### WR-02: Breakdown bar chart's visual order is not guaranteed to match the documented fixed order

**Files modified:** `src/components/charts.py`
**Commit:** 911f458
**Applied fix:** Added `fig.update_yaxes(autorange="reversed")` in `build_breakdown_figure` after constructing the figure, so the rendered chart reads top-to-bottom in the same order as `sub_scores_display` (matching `SUB_SCORE_ORDER`). Verified via manual exercise that `fig.layout.yaxis.autorange == "reversed"` while `bar.y`/`bar.x` trace-data order is unchanged (existing `tests/test_components.py` assertions on trace order remain valid).

### WR-03: Tickers that fail to fetch are silently dropped with no user-facing signal

**Files modified:** `src/pages/recommendations.py`
**Commit:** 21dcc53
**Applied fix:** Captured the previously-discarded `_unscorable` return value from `load_universe_rows` (renamed to `unscorable`) and added an `st.caption(...)` notice via a new `UNSCORABLE_NOTICE_TEMPLATE` constant when the list is non-empty, with correct singular/plural grammar ("1 asset was" / "N assets were ... temporarily unavailable and excluded from these results"). Users can now distinguish "the engine ran and found nothing" from "some tickers temporarily failed to load."

## Skipped Issues

None — all in-scope findings were fixed.

---

_Fixed: 2026-08-09T16:06:14Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
