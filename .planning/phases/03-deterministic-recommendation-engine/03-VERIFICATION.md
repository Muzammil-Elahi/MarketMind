---
phase: 03-deterministic-recommendation-engine
verified: 2026-08-09T00:00:00Z
status: passed
score: 4/4 must-haves verified
behavior_unverified: 0
overrides_applied: 0
---

# Phase 3: Deterministic Recommendation Engine Verification Report

**Phase Goal:** Users get a fully deterministic, ranked, explainable shortlist of assets across all supported asset classes, scored against their profile with zero LLM dependency.
**Verified:** 2026-08-09
**Status:** passed
**Re-verification:** No — initial verification (post code-review-fix pass)

## Goal Achievement

### Observable Truths (Roadmap Success Criteria REC-01..04)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can view a ranked list of recommended assets spanning stocks, ETFs, crypto, gold, and forex, from a zero-network/LLM hybrid scorer | ✓ VERIFIED | `src/recommendation/universe.py` defines 5 static ticker lists (24 stocks, 12 ETFs, 12 crypto, 2 gold, 8 forex); `src/recommendation/engine.py` imports only `pandas`/stdlib/sibling modules (confirmed by reading the module and by `test_score_universe_zero_network_imports`); `src/pages/recommendations.py` calls `build_recommendations(profile, universe_df)` as its only scoring path and renders all 5 `ASSET_CLASSES` in fixed order. |
| 2 | Each ranked asset shows a composite score with a visible sub-factor breakdown | ✓ VERIFIED | `engine.py`'s `score_universe` produces `composite_score_display` ("{score}/100") and `sub_scores_display` (fixed `SUB_SCORE_ORDER`); `recommendations.py` renders both (`st.write(SCORE_LABEL_TEMPLATE...)`, `render_breakdown_bar_chart(card["sub_scores_display"], ...)`); `search.py` renders the identical fields on the drill-in page. `WR-02` fix (`fig.update_yaxes(autorange="reversed")` in `src/components/charts.py`) confirmed present so the rendered chart order visually matches `SUB_SCORE_ORDER`. |
| 3 | Each recommendation includes a one-sentence plain-English reason | ✓ VERIFIED | `explain.explain(sub_scores, risk_tolerance)` (`src/recommendation/explain.py`) is called with the row's own `sub_scores` dict inside `engine.score_universe` (line 113) and rendered verbatim (`st.write(card["explanation"])`). **CR-01 fix confirmed live**: `explain.py` now has `ONE_FACTOR_TEMPLATE_NO_RISK`/`TWO_FACTOR_TEMPLATE_NO_RISK` fallback templates branched on `if risk_tolerance:`; manually executed `explain(..., None)` returns `"Strong alignment with your preferred sectors matches your risk profile."` (no literal "None"). No directive/imperative language found in `FACTOR_LABELS` or templates (`grep -i "buy\|sell\|you should"` — no matches). |
| 4 | User can search for and view any asset from any supported asset class, including ones not currently recommended | ✓ VERIFIED | `src/pages/search.py`'s `resolve_search_result` calls `infer_asset_class` → `fetch_scorable_row` → `score_universe(..., apply_hard_exclude=False)` — the identical scoring pipeline `build_recommendations` uses, per `test_resolve_search_result_single_source_of_truth_matches_build_recommendations`. **CR-02 fix confirmed live**: `universe.infer_asset_class` now checks `ETF_UNIVERSE` membership before the Stocks fallback; manually executed `infer_asset_class("SPY")` and `infer_asset_class("QQQ")` both return `"ETFs"` (previously misclassified as `"Stocks"`), so ETF searches now score against the correct ETF peer group. |

**Score:** 4/4 truths verified (0 present-but-behavior-unverified)

### Post-Review Fix Verification (03-REVIEW.md → 03-REVIEW-FIX.md)

All 5 in-scope findings (2 critical, 3 warning) were checked directly against the current file contents on disk, not just the fix report's narrative:

| ID | Issue | Fix Commit | Verified in code? |
|----|-------|-----------|--------------------|
| CR-01 | Literal "None" in explanation when `risk_tolerance` unset | f7ef37d | ✓ `explain.py` has `_NO_RISK` fallback templates + falsy-check branch; runtime-executed, produces correct copy |
| CR-02 | ETF tickers misclassified as Stocks in search peer group | 7abd356 | ✓ `universe.py`'s `infer_asset_class` checks `ETF_UNIVERSE` before Stocks fallback; runtime-executed, `SPY`/`QQQ` → `"ETFs"` |
| WR-01 | Bare `except Exception` swallows errors with no logging | 702de4e | ✓ `_universe_loader.py` has `logger = logging.getLogger(__name__)` and `logger.exception(...)` before `return {"status": "not_found"}` |
| WR-02 | Breakdown chart y-axis order not guaranteed to match documented order | 911f458 | ✓ `charts.py`'s `build_breakdown_figure` has `fig.update_yaxes(autorange="reversed")` |
| WR-03 | Failed-fetch tickers silently dropped, no user signal | 21dcc53 | ✓ `recommendations.py` captures `unscorable` from `load_universe_rows` and renders `UNSCORABLE_NOTICE_TEMPLATE` via `st.caption` when non-empty |

IN-01 and IN-02 (info-level, `capital == 0` falsiness and query-param prefill not cleared) were explicitly out of scope for the fix pass per 03-REVIEW-FIX.md frontmatter and remain unaddressed — neither blocks the phase goal (both are minor UX edge cases, not correctness-of-recommendation issues).

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/recommendation/universe.py` | Curated static universe + `infer_asset_class` | ✓ VERIFIED | 5 static lists, zero I/O imports (stdlib only), `infer_asset_class` now correctly branches Forex→Crypto→Gold→ETFs→Stocks |
| `src/recommendation/factor_scoring.py` | Within-class momentum/volatility/quality percentiles | ✓ VERIFIED | `_safe_group_percentile` uses `groupby("asset_class").transform(...)`, `MIN_GROUP_SIZE=3`/`DEFAULT_PERCENTILE_FALLBACK=0.5` guard present, imports `pandas` only |
| `src/recommendation/profile_fit.py` | `is_excluded`/`compute_profile_fit` | ✓ VERIFIED | Pure dict-based, zero imports beyond stdlib, hard-exclude logic matches spec |
| `src/recommendation/explain.py` | Deterministic template explanation | ✓ VERIFIED | `SUB_SCORE_ORDER`, `FACTOR_LABELS`, tie-break logic, no-risk fallback confirmed |
| `src/recommendation/similarity.py` | Content-based cosine-similarity sub-score | ✓ VERIFIED | No `user_id`/session param; pure numpy function; `RISK_ARCHETYPES` fixed 3-entry dict |
| `src/recommendation/engine.py` | `score_universe`/`build_recommendations` orchestrator | ✓ VERIFIED | Excludes before scoring, sorts (composite desc, ticker asc), round-half-up via `math.floor(value+0.5)`, clamps [0,100] |
| `src/pages/_universe_loader.py` | Shared fetch+assemble+gate loader | ✓ VERIFIED | `fetch_scorable_row` distinguishes `not_found`/`insufficient_data`/`ok`, logs exceptions (WR-01 fix) |
| `src/components/disclaimer.py` | Shared disclaimer banner | ✓ VERIFIED | `render_disclaimer_banner()` used by both pages |
| `src/components/charts.py` | Shared breakdown/price-history chart builders | ✓ VERIFIED | `build_breakdown_figure`/`build_price_history_figure` reused by both pages; y-axis reversed (WR-02 fix) |
| `src/pages/recommendations.py` | Ranked shortlist page | ✓ VERIFIED | `require_auth()` first, all 5 asset-class sections render unconditionally, unscorable notice (WR-03 fix) |
| `src/pages/search.py` | Search/drill-in page | ✓ VERIFIED | `require_auth()` first, D-07/D-08 branches, single-source-of-truth scoring |
| `src/app.py` | Navigation registration | ✓ VERIFIED | Both pages registered only in logged-in `st.navigation` branch |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `_universe_loader.py` | `src/data/prices.py`, `src/features/feature_frame.py` | `fetch_ohlcv`/`assemble_feature_frame` | ✓ WIRED | Confirmed via import + call in `fetch_scorable_row` |
| `factor_scoring.py` | pandas groupby | `.groupby("asset_class").transform(...)` | ✓ WIRED | Confirmed in `_safe_group_percentile` |
| `explain.py` | `engine.py` | `explain(sub_scores, risk_tolerance)` called with row's own dict | ✓ WIRED | `engine.py:113` |
| `engine.py` | `factor_scoring.py`, `similarity.py`, `profile_fit.py`, `explain.py`, `universe.py` | orchestration | ✓ WIRED | All 5 sibling modules imported and called, no inline reimplementation |
| `recommendations.py` | `engine.py`, `_universe_loader.py`, `components/` | `build_recommendations`, `load_universe_rows`, `render_disclaimer_banner`/`render_breakdown_bar_chart` | ✓ WIRED | All confirmed by direct read |
| `search.py` | `_universe_loader.py`, `engine.py` | `fetch_scorable_row`, `score_universe(..., apply_hard_exclude=False)` | ✓ WIRED | Confirmed; regression-tested by `test_resolve_search_result_single_source_of_truth_matches_build_recommendations` |
| `app.py` | `recommendations.py`, `search.py` | `st.navigation` logged-in branch | ✓ WIRED | Confirmed; logged-out branch unchanged |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `infer_asset_class("SPY")`/`("QQQ")` classify as ETFs (CR-02 regression) | `python -c "from src.recommendation.universe import infer_asset_class; print(infer_asset_class('SPY'))"` | `ETFs` | ✓ PASS |
| `explain(..., None)` never emits literal "None" (CR-01 regression) | `python -c "from src.recommendation.explain import explain; print(explain({...}, None))"` | `"Strong alignment with your preferred sectors matches your risk profile."` | ✓ PASS |
| `score_universe`/`build_recommendations` handle empty universe without raising | `python -c` inline test | `score_universe({}, pd.DataFrame()).empty == True`; `build_recommendations` returns all 5 classes as `[]` | ✓ PASS |
| Phase-scoped test suite (9 files, 75 tests) | `pytest tests/test_recommendation_*.py tests/test_universe_loader.py tests/test_components.py -q` | `75 passed in 7.77s` | ✓ PASS |
| Full repo test suite (regression check) | `pytest -q` | `129 passed in 136.03s` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan(s) | Description | Status | Evidence |
|-------------|----------------|--------------|--------|----------|
| REC-01 | 03-01, 03-03, 03-04, 03-05, 03-06, 03-08 | Ranked list across 5 asset classes, deterministic hybrid scorer | ✓ SATISFIED | `engine.score_universe`/`build_recommendations`, zero-I/O verified, `recommendations.py` renders all 5 classes |
| REC-02 | 03-01, 03-02, 03-03, 03-04, 03-05, 03-06, 03-08 | Composite score with visible sub-factor breakdown | ✓ SATISFIED | `sub_scores_display` fixed-order dict, rendered via `render_breakdown_bar_chart` on both pages |
| REC-03 | 03-02, 03-05, 03-06, 03-08 | One-sentence plain-English reason | ✓ SATISFIED | `explain.explain()` deterministic templating, CR-01-fixed for null risk_tolerance |
| REC-04 | 03-01, 03-07, 03-08 | Search any asset across all asset classes | ✓ SATISFIED | `search.py`'s `resolve_search_result`, CR-02-fixed classification, single-source-of-truth test passing |

No orphaned requirements — REQUIREMENTS.md's Phase 3 mapping (REC-01..04) matches exactly the union of `requirements:` fields across all 8 plans.

### Anti-Patterns Found

None. Scanned all phase-modified files (`src/recommendation/**`, `src/pages/_universe_loader.py`, `src/pages/recommendations.py`, `src/pages/search.py`, `src/components/**`, `src/app.py`) for `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/`PLACEHOLDER`/directive financial-advice language — zero matches.

### Human Verification Required

None. All must-haves are statically/behaviorally verifiable via code inspection, unit tests, and direct interpreter execution; the end-to-end human walkthrough called for in 03-08-PLAN.md's `workflow.human_verify_mode: end-of-phase` was already the executor's task-1 checkpoint, and the phase's automated test suite (including single-source-of-truth cross-page equality tests) covers the same ground programmatically.

### Gaps Summary

No gaps. Both critical defects found by the code-review pass (CR-01: literal "None" in explanation copy; CR-02: ETF ticker misclassification breaking within-class normalization) are confirmed fixed in the current code on disk — not just claimed in 03-REVIEW-FIX.md — via direct file reads and live interpreter execution reproducing the exact failure conditions the review described. All 3 warnings (WR-01/02/03) are also confirmed fixed in code. The two info-level items (IN-01, IN-02) were explicitly deferred and are minor UX polish, not correctness defects — they do not block the phase goal ("fully deterministic, ranked, explainable shortlist ... zero LLM dependency"), which is fully achieved.

One minor observation (not a gap): no automated regression test was added for the CR-02 ETF-classification fix specifically (`tests/test_recommendation_universe.py` still only tests Forex/Crypto/Gold/default-Stocks branches, not `infer_asset_class("SPY") == "ETFs"`) — the fix report's "manually verified" claim is accurate (confirmed independently above) but the regression is not guarded by a permanent test. This is a test-coverage nicety, not a phase-goal blocker.

---

_Verified: 2026-08-09_
_Verifier: Claude (gsd-verifier)_
