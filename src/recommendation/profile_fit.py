"""Pure, zero-I/O profile-driven hard-exclude/fit rule engine (D-01's
profile-fit sub-score).

Both functions here operate on plain ``dict`` inputs -- an asset row (a
subset of universe/feature data) and a profile dict (Phase 2's
Supabase-backed investor profile shape) -- never on a pandas ``DataFrame``.
Neither function performs any network, database, or Streamlit call.

``is_excluded`` is the single authoritative hard-exclude decision (T-03-04):
callers (``engine.py``, Plan 05) MUST call it on every asset row BEFORE any
factor/similarity/composite scoring math runs, and MUST drop any row for
which it returns ``True`` from the universe entirely -- never merely
down-weight an excluded asset.

``compute_profile_fit`` assumes ``is_excluded(asset_row, profile)`` is
already ``False`` for its input; it never re-implements the exclusion
check itself, avoiding two independently-computed exclusion paths that
could drift.

This module imports nothing beyond the standard library.
"""


def is_excluded(asset_row: dict, profile: dict) -> bool:
    """Return True if `asset_row` must be held out of scoring entirely.

    An asset is excluded when either:
    - its sector is present and appears in the profile's excluded_sectors, or
    - the profile has a non-empty preferred_asset_types list and the
      asset's asset_class is not in it (Open Question 1's hard-filter
      resolution).

    A `None`/missing sector never matches a sector-based exclusion (a
    non-stock asset with no sector is never excluded on that basis).
    """
    excluded_sectors = profile.get("excluded_sectors") or []
    sector = asset_row.get("sector")
    if sector is not None and sector in excluded_sectors:
        return True

    preferred_asset_types = profile.get("preferred_asset_types") or []
    if preferred_asset_types and asset_row.get("asset_class") not in preferred_asset_types:
        return True

    return False


def compute_profile_fit(asset_row: dict, profile: dict) -> float:
    """Return a [0, 1]-bounded rule-based profile-fit score.

    Assumes `is_excluded(asset_row, profile)` is already False for this
    input -- callers (engine.py) must pre-filter excluded assets before
    calling this function. Always returns a value in the closed range
    [0, 1] regardless of which profile/asset_row fields are None/missing.

    Starts from a neutral 0.5 baseline:
    - +0.3 if the asset's sector is in the profile's preferred_sectors.
    - +0.2 if the profile's time_horizon is "5-10yr" or "10+yr" AND the
      asset's momentum_pct is not None and >= 0.5 (Open Question 3's
      resolution -- time_horizon only nudges this sub-score, never a
      second similarity-archetype dimension).
    """
    score = 0.5

    preferred_sectors = profile.get("preferred_sectors") or []
    if asset_row.get("sector") in preferred_sectors:
        score += 0.3

    time_horizon = profile.get("time_horizon")
    momentum_pct = asset_row.get("momentum_pct")
    if (
        time_horizon in ("5-10yr", "10+yr")
        and momentum_pct is not None
        and momentum_pct >= 0.5
    ):
        score += 0.2

    return min(score, 1.0)
