"""Pure, zero-I/O deterministic template-based one-sentence explanation
generator (REC-03/D-06).

`explain(sub_scores, risk_tolerance)` selects its top factor(s) directly
from the SAME `sub_scores` dict the caller (`engine.py`, Plan 05) displays
in REC-02's breakdown -- never a separately-computed "most important
factor" (Pattern 5's traceability requirement). No LLM call, no network,
no Streamlit -- imports nothing beyond the standard library.
"""

# The single fixed sub-factor order used both for REC-02's displayed
# breakdown order in engine.py (Plan 05) and for this file's tie-break.
# Do not redefine this list a second time anywhere else in the codebase --
# engine.py imports it from here.
SUB_SCORE_ORDER = ["profile_fit", "momentum", "volatility", "quality", "similarity"]

FACTOR_LABELS = {
    "profile_fit": "alignment with your preferred sectors",
    "momentum": "momentum",
    "volatility": "low volatility",
    "quality": "price stability",
    "similarity": "profile similarity",
}

TWO_FACTOR_TEMPLATE = "Strong {factor_a} and {factor_b} match your {risk_tolerance} risk profile."
ONE_FACTOR_TEMPLATE = "Strong {factor_a} matches your {risk_tolerance} risk profile."
# Fallback templates used when risk_tolerance hasn't been set yet (nullable
# profile field, Phase 2). Never interpolate a missing risk_tolerance into
# user-facing copy -- that renders the literal string "None".
TWO_FACTOR_TEMPLATE_NO_RISK = "Strong {factor_a} and {factor_b} match your risk profile."
ONE_FACTOR_TEMPLATE_NO_RISK = "Strong {factor_a} matches your risk profile."


def explain(sub_scores: dict, risk_tolerance: str | None) -> str:
    """Return a deterministic one-sentence explanation string.

    Ties for the top value are broken using the fixed SUB_SCORE_ORDER.
    When exactly two sub-scores are tied for the top value, the
    two-factor template fires (REC-03 adjacency). When the top value is
    shared by three or more sub-scores (REC-03 empty -- no single factor
    or pair is meaningfully dominant), or when there is a single clear
    winner, the one-factor template fires on whichever tied factor ranks
    first in SUB_SCORE_ORDER -- the explanation is never left blank.

    `risk_tolerance` is a nullable profile field. When it is `None` (or
    otherwise falsy), the risk-profile clause is dropped from the
    sentence entirely rather than interpolating the literal string
    "None" into user-facing copy.
    """
    ordered = sorted(
        sub_scores.items(), key=lambda kv: (-kv[1], SUB_SCORE_ORDER.index(kv[0]))
    )
    top_value = ordered[0][1]
    tied_top = [key for key, value in ordered if value == top_value]

    if len(tied_top) == 2:
        if risk_tolerance:
            return TWO_FACTOR_TEMPLATE.format(
                factor_a=FACTOR_LABELS[tied_top[0]],
                factor_b=FACTOR_LABELS[tied_top[1]],
                risk_tolerance=risk_tolerance,
            )
        return TWO_FACTOR_TEMPLATE_NO_RISK.format(
            factor_a=FACTOR_LABELS[tied_top[0]],
            factor_b=FACTOR_LABELS[tied_top[1]],
        )

    if risk_tolerance:
        return ONE_FACTOR_TEMPLATE.format(
            factor_a=FACTOR_LABELS[ordered[0][0]],
            risk_tolerance=risk_tolerance,
        )
    return ONE_FACTOR_TEMPLATE_NO_RISK.format(
        factor_a=FACTOR_LABELS[ordered[0][0]],
    )
