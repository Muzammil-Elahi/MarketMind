"""Tests for src/pages/search.py's resolve_forecast_request (PRED-02, T-04-03).

Fully mocked -- no live network call, no Streamlit-runtime-dependent
assertions. Patches src.pages.search.generate_forecast (the name as
imported into src.pages.search), mirroring tests/test_recommendation_search.py's
convention. Mirrors tests/test_cache.py's isolated_cache fixture pattern by
clearing resolve_forecast_request's st.cache_data in-memory cache before and
after every test, so no cached result leaks between tests.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from src.pages.search import resolve_forecast_request


@pytest.fixture(autouse=True)
def isolated_forecast_cache():
    resolve_forecast_request.clear()
    yield
    resolve_forecast_request.clear()


def _sample_feature_frame():
    return pd.DataFrame({"returns": [0.01, 0.02, 0.03]})


def _sample_price_series():
    return pd.Series([100.0, 101.0, 102.0])


def test_resolve_forecast_request_calls_generate_forecast_once_and_returns_unchanged():
    """Thin caching wrapper, no added logic beyond caching -- returns
    generate_forecast's return value unchanged."""
    feature_frame = _sample_feature_frame()
    price_series = _sample_price_series()
    expected = {"status": "ok", "model": "sma"}

    with patch(
        "src.pages.search.generate_forecast", return_value=expected
    ) as mock_generate_forecast:
        result = resolve_forecast_request(
            "AAPL", "sma", 7, feature_frame, price_series, "Stocks"
        )

    mock_generate_forecast.assert_called_once_with(
        "AAPL", "sma", 7, feature_frame, price_series, "Stocks"
    )
    assert result == expected


def test_resolve_forecast_request_deduplicates_identical_calls():
    """Calling resolve_forecast_request twice with byte-identical arguments
    invokes the underlying generate_forecast mock only once -- the second
    call is a cache hit."""
    feature_frame = _sample_feature_frame()
    price_series = _sample_price_series()
    expected = {"status": "ok", "model": "xgboost"}

    with patch(
        "src.pages.search.generate_forecast", return_value=expected
    ) as mock_generate_forecast:
        result_1 = resolve_forecast_request(
            "AAPL", "xgboost", 30, feature_frame, price_series, "Stocks"
        )
        result_2 = resolve_forecast_request(
            "AAPL", "xgboost", 30, feature_frame, price_series, "Stocks"
        )

    mock_generate_forecast.assert_called_once()
    assert result_1 == expected
    assert result_2 == expected
