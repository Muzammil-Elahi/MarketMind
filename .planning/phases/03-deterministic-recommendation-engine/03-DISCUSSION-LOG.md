# Phase 3: Deterministic Recommendation Engine - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-04
**Phase:** 3-Deterministic Recommendation Engine
**Areas discussed:** Scoring model design, Universe & asset selection, Explanation generation, Search & asset drill-in

---

## Scoring model design

| Option | Description | Selected |
|--------|-------------|----------|
| Weighted sum of sub-scores | Composite = weighted sum of normalized sub-factor scores | ✓ |
| Rule-based filter then rank | Hard-filter by profile constraints, then rank by factor score | |
| You decide | Leave combination approach to planning | |

**User's choice:** Weighted sum of sub-scores.

| Option | Description | Selected |
|--------|-------------|----------|
| Similarity between asset profiles | Asset-to-asset similarity (cosine over factor vectors), not true user-user CF | ✓ |
| Defer entirely — factor score only for v1 | Skip collaborative-similarity sub-score for now | |
| You decide | Claude picks during research/planning | |

**User's choice:** Similarity between asset profiles.

| Option | Description | Selected |
|--------|-------------|----------|
| Z-score/percentile within each asset class | Normalize each factor within its own asset-class universe first | ✓ |
| Single global normalization across all assets | Normalize all factors across the entire cross-asset universe at once | |
| You decide | Leave exact method to research/planning | |

**User's choice:** Z-score/percentile within each asset class.
**Notes:** Resolves the cross-asset-class weight normalization question flagged as unresearched in Phase 2's context.

---

## Universe & asset selection

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed curated list per class | Hardcoded/config list per asset class | ✓ |
| Dynamic universe (live index membership) | Pull live index/market-cap membership | |

**User's choice:** Fixed curated list per class.

| Option | Description | Selected |
|--------|-------------|----------|
| Top 10-15 overall, spanning classes | Single ranked list across all classes together | |
| Top N per asset class | Guarantee representation from every asset class (e.g. top 3 per class) | ✓ |

**User's choice:** Top N per asset class.

---

## Explanation generation

| Option | Description | Selected |
|--------|-------------|----------|
| Template driven by top sub-factor | Pick top-contributing sub-factor(s), slot into a template sentence | ✓ |
| Static per-asset-class boilerplate | One fixed sentence per asset class regardless of actual drivers | |

**User's choice:** Template driven by top sub-factor.

---

## Search & asset drill-in

| Option | Description | Selected |
|--------|-------------|----------|
| Direct yfinance lookup by ticker | User types a ticker, validated/fetched via fetch_ohlcv | ✓ |
| Search box with fuzzy name matching | Name-to-ticker lookup table/API | |

**User's choice:** Direct yfinance lookup by ticker.

| Option | Description | Selected |
|--------|-------------|----------|
| Show price chart, skip score | Still show chart, display "insufficient data for scoring" instead of a composite score | ✓ |
| Reject search with an error | Refuse to show the asset at all | |

**User's choice:** Show price chart, skip score.

---

## Claude's Discretion

None — all gray areas were explicitly decided by the user.

## Deferred Ideas

None — discussion stayed within phase scope.
