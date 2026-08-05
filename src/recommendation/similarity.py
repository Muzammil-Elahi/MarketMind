"""Content-based profile-archetype <-> asset similarity sub-score (D-02).

`similarity_score(momentum_score, volatility_score, risk_tolerance)` is a
pure numpy cosine-similarity function over a fixed 2-dimension
``[momentum, volatility]`` archetype vector per risk_tolerance level. It
takes no `user_id`, session, or interaction-history argument of any kind,
so it is structurally incapable of depending on prior interaction data --
the classic collaborative-filtering cold-start problem does not apply to
this content-based design.
"""

import numpy as np

# Target archetype vectors over [momentum, stability/volatility] dimensions.
# A tunable v1 design choice, not derived from an external benchmark
# (per RESEARCH.md Assumptions Log A2).
RISK_ARCHETYPES = {
    "Conservative": np.array([0.3, 0.9]),
    "Moderate": np.array([0.6, 0.6]),
    "Aggressive": np.array([0.9, 0.2]),
}


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Return the cosine similarity of two vectors, guarded against
    division-by-zero when either vector is the zero vector."""
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def similarity_score(
    momentum_score: float, volatility_score: float, risk_tolerance: str
) -> float:
    """Return the content-based similarity of an asset's
    [momentum_score, volatility_score] vector to the target archetype
    vector for the given risk_tolerance.

    Falls back to the "Moderate" archetype for any risk_tolerance not in
    RISK_ARCHETYPES (defensive default for a not-yet-set profile field).
    """
    archetype = RISK_ARCHETYPES.get(risk_tolerance, RISK_ARCHETYPES["Moderate"])
    asset_vector = np.array([momentum_score, volatility_score])
    return cosine_similarity(asset_vector, archetype)
