"""Tests for src/prediction/walk_forward.py (PRED-04, D-11-style
structural no-lookahead-bias proof).

Pure, zero-I/O tests -- no network calls, no yfinance, no Streamlit.
Mirrors tests/test_features_leakage.py's structural-proof style, adapted
for fold-splitting rather than feature computation.
"""

import numpy as np
import pytest

from src.prediction.walk_forward import (
    MIN_PREDICTION_HISTORY_ROWS,
    N_FOLDS,
    make_folds,
)
from src.recommendation.universe import MIN_HISTORY_ROWS


def test_make_folds_returns_n_folds_pairs_of_numpy_arrays():
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    assert len(folds) == 5
    for train_index, test_index in folds:
        assert isinstance(train_index, np.ndarray)
        assert isinstance(test_index, np.ndarray)


def test_folds_never_overlap_and_test_always_after_train():
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    for train_index, test_index in folds:
        assert max(train_index) < min(test_index)


def test_expanding_window_train_sets_are_supersets():
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    for (train_a, _), (train_b, _) in zip(folds, folds[1:]):
        assert set(train_a).issubset(set(train_b))


def test_make_folds_raises_when_n_rows_too_small_for_request():
    with pytest.raises(ValueError):
        make_folds(n_rows=10, horizon_days=90, n_folds=5)


def test_min_prediction_history_rows_is_750_and_larger_than_phase3_gate():
    assert MIN_PREDICTION_HISTORY_ROWS == 750
    assert MIN_PREDICTION_HISTORY_ROWS > MIN_HISTORY_ROWS


def test_n_folds_is_5():
    assert N_FOLDS == 5


def test_min_prediction_history_rows_boundary_succeeds_at_750():
    # 750 is MIN_PREDICTION_HISTORY_ROWS -- the safety-margin threshold this
    # module declares as sufficient; it must not raise.
    folds = make_folds(n_rows=750, horizon_days=90, n_folds=5)
    assert len(folds) == 5


def test_true_sklearn_failure_boundary_raises_at_n_splits_times_test_size():
    # Deviation note (Rule 1): 04-RESEARCH.md Pitfall 2's derivation implies
    # the literal TimeSeriesSplit failure boundary is 702 (252 + 5*90), so
    # 701 "must raise". Empirically verified against sklearn's actual
    # TimeSeriesSplit(n_splits=5, test_size=90): it only requires
    # n_samples > n_splits * test_size (450) -- n_rows=701 (and even 451)
    # succeeds with a smaller-than-252 first-fold train window. The true
    # sklearn-enforced failure boundary is exactly 450 (raises), 451
    # (succeeds). MIN_PREDICTION_HISTORY_ROWS=750 sits 300 rows above this
    # literal sklearn floor, proving the safety margin is genuinely
    # conservative without asserting an incorrect boundary value.
    with pytest.raises(ValueError):
        make_folds(n_rows=450, horizon_days=90, n_folds=5)


def test_make_folds_succeeds_just_above_sklearn_failure_floor():
    folds = make_folds(n_rows=451, horizon_days=90, n_folds=5)
    assert len(folds) == 5
