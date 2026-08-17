"""Zero-I/O walk-forward fold generator (PRED-04, no-lookahead-bias
guarantee).

`make_folds` is the single source of expanding-window walk-forward folds
every model's backtest evaluation (Plans 04/05/06) calls, rather than each
implementing its own fold-splitting logic -- eliminating the class of
off-by-one lookahead bug 04-RESEARCH.md's Anti-Patterns section warns
against (04-RESEARCH.md Pattern 1).

This module performs zero network, database, or LLM calls. It imports
only ``sklearn.model_selection`` -- never ``streamlit``, ``yfinance``, or
``sqlite3``.
"""

from sklearn.model_selection import TimeSeriesSplit

# Enough for a stable average metric while staying cheap on free-tier CPU
# -- 04-RESEARCH.md Pitfall 2.
N_FOLDS = 5

# 252 (one trading year -- Prophet's minimum yearly-seasonality cycle) +
# 5 * 90 (worst-case 90-day horizon across all N_FOLDS folds) = 702, plus a
# safety margin, per 04-RESEARCH.md Pitfall 2. Visibly larger than Phase 3's
# MIN_HISTORY_ROWS=20 (src/recommendation/universe.py), per D-07.
MIN_PREDICTION_HISTORY_ROWS = 750


def make_folds(
    n_rows: int, horizon_days: int, n_folds: int = N_FOLDS
) -> list[tuple]:
    """Return a list of (train_index, test_index) numpy-array pairs.

    Expanding-window: train_index for fold k is always a superset of fold
    k-1's train_index. test_index is always strictly after max(train_index)
    for its fold -- this is the structural guarantee against lookahead bias
    (PRED-04). test_size == horizon_days so backtest folds match the
    forecast horizon the user actually selected.

    Raises sklearn's own ValueError (never silently returns fewer folds)
    when n_rows is too small for the requested n_folds/horizon_days
    combination.
    """
    splitter = TimeSeriesSplit(n_splits=n_folds, test_size=horizon_days)
    return list(splitter.split(range(n_rows)))
