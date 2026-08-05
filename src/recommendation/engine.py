"""Zero-I/O scoring orchestrator (REC-01/REC-02/REC-03, D-05).

`score_universe` is the single scoring pipeline both the ranked-list page
and the search/drill-in page call (REC-04's single-source-of-truth
requirement) -- it never reimplements any sibling module's math inline,
only assembles their outputs. `build_recommendations` groups that already-
ranked output into D-05's top-N-per-class shape.

This module performs zero network, database, or LLM calls. It imports
only ``pandas``, the standard library, and sibling
``src.recommendation`` modules -- never ``streamlit``, ``yfinance``,
``sqlite3``, or any agent-orchestration/generative-AI SDK symbol.
"""

import math

import pandas as pd

from src.recommendation import explain, factor_scoring, profile_fit, similarity
from src.recommendation.universe import ASSET_CLASSES

# A documented, tunable v1 choice (RESEARCH.md Assumptions A3), not a
# locked decision -- sums to exactly 1.0.
WEIGHTS = {
    "profile_fit": 0.30,
    "momentum": 0.20,
    "volatility": 0.15,
    "quality": 0.10,
    "similarity": 0.25,
}

# D-05's example top-N-per-asset-class count.
TOP_N_PER_CLASS = 3


def _round_half_up(value: float) -> int:
    """Round-half-up to the nearest integer -- never Python's built-in
    ``round()``, which is banker's-rounding and would silently violate the
    REC-02 precision must-have (82.5 -> 83, never 82)."""
    return math.floor(value + 0.5)


def _compose_score(sub_scores: dict, weights: dict = WEIGHTS) -> float:
    """Return the weighted composite score, defensively clamped to the
    closed range [0, 100] (REC-02 boundary)."""
    raw = sum(weights[key] * sub_scores[key] for key in weights) * 100
    return max(0.0, min(100.0, raw))


def score_universe(
    profile: dict, universe_df: pd.DataFrame, apply_hard_exclude: bool = True
) -> pd.DataFrame:
    """Score every eligible row of `universe_df` against `profile`.

    Returns a DataFrame sorted by (composite_score descending, ticker
    ascending) -- a deterministic tie-break (REC-01 ordering/adjacency).

    When `apply_hard_exclude` is True (the default), every row for which
    `profile_fit.is_excluded` returns True is dropped from `eligible_df`
    BEFORE any factor/similarity/composite computation runs -- excluded
    assets are held out of scoring entirely (T-03-04), never merely
    down-weighted, and never influence another asset's within-class
    percentile computation. When False (Plan 07's search-path escape
    hatch, REC-04), every row is scored using the identical formula --
    there is no second, independently-implemented scoring function
    anywhere in this codebase.
    """
    if universe_df.empty:
        return universe_df

    if apply_hard_exclude:
        excluded_mask = universe_df.apply(
            lambda row: profile_fit.is_excluded(row.to_dict(), profile), axis=1
        )
        eligible_df = universe_df.loc[~excluded_mask].copy()
    else:
        eligible_df = universe_df.copy()

    if eligible_df.empty:
        return eligible_df.iloc[0:0]

    eligible_df["momentum"] = factor_scoring.compute_momentum_score(eligible_df)
    eligible_df["volatility"] = factor_scoring.compute_volatility_score(eligible_df)
    eligible_df["quality"] = factor_scoring.compute_quality_score(eligible_df)
    eligible_df["profile_fit"] = eligible_df.apply(
        lambda row: profile_fit.compute_profile_fit(
            {**row.to_dict(), "momentum_pct": row["momentum"]}, profile
        ),
        axis=1,
    )
    eligible_df["similarity"] = eligible_df.apply(
        lambda row: similarity.similarity_score(
            row["momentum"], row["volatility"], profile.get("risk_tolerance")
        ),
        axis=1,
    )

    records = []
    for _, row in eligible_df.iterrows():
        sub_scores = {key: row[key] for key in explain.SUB_SCORE_ORDER}
        composite_score = _compose_score(sub_scores)
        records.append(
            {
                "ticker": row["ticker"],
                "asset_class": row["asset_class"],
                "sector": row["sector"],
                "composite_score": composite_score,
                "composite_score_display": _round_half_up(composite_score),
                "sub_scores": sub_scores,
                "sub_scores_display": {
                    key: _round_half_up(value * 100) for key, value in sub_scores.items()
                },
                "explanation": explain.explain(sub_scores, profile.get("risk_tolerance")),
            }
        )

    result_df = pd.DataFrame.from_records(records)
    result_df = result_df.sort_values(
        by=["composite_score", "ticker"], ascending=[False, True]
    ).reset_index(drop=True)
    return result_df


def build_recommendations(
    profile: dict, universe_df: pd.DataFrame, top_n: int = TOP_N_PER_CLASS
) -> dict[str, list[dict]]:
    """Group `score_universe`'s already-ranked output into top-N-per-class
    buckets (D-05).

    Every asset class in `ASSET_CLASSES` is always present as a key --
    classes absent from `universe_df` map to an empty list, never omitted
    or padded to reach `top_n` (D-04 zero-one-many/partial-class edges).
    Never recomputes or alters any score value, only groups and truncates.
    """
    result: dict[str, list[dict]] = {asset_class: [] for asset_class in ASSET_CLASSES}

    scored_df = score_universe(profile, universe_df)
    if scored_df.empty:
        return result

    for asset_class, group in scored_df.groupby("asset_class", sort=False):
        result[asset_class] = group.head(top_n).to_dict("records")

    return result
