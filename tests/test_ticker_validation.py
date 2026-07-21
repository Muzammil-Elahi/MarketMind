"""D-08 ticker-validation unit tests -- fully mocked, no live network call.

Mirrors tests/test_cache.py's unittest.mock.patch style: mock
src.data.profile.fetch_ohlcv directly rather than exercising the real
yfinance chokepoint.
"""

from unittest.mock import patch

import pandas as pd

from src.data.profile import validate_ticker


def _sample_df():
    return pd.DataFrame({"Close": [100.0, 101.0, 102.0]})


def test_validate_ticker_true_for_live_nonempty_dataframe():
    with patch(
        "src.data.profile.fetch_ohlcv", return_value=(_sample_df(), "live")
    ) as mock_fetch:
        assert validate_ticker("AAPL") is True
    mock_fetch.assert_called_once()


def test_validate_ticker_false_for_live_empty_dataframe():
    """Pitfall 1: fetch_ohlcv succeeds (no exception) but returns an empty
    DataFrame for an unrecognized/delisted ticker -- must be flagged
    invalid, not silently accepted."""
    with patch(
        "src.data.profile.fetch_ohlcv", return_value=(pd.DataFrame(), "live")
    ):
        assert validate_ticker("NOTAREALTICKER") is False


def test_validate_ticker_true_fail_open_on_exception():
    """A genuine live-fetch failure with no cached row at all (Pitfall 4) is
    inconclusive, not evidence the ticker itself is invalid -- fail open."""
    with patch("src.data.profile.fetch_ohlcv", side_effect=RuntimeError("simulated failure")):
        assert validate_ticker("AAPL") is True


def test_validate_ticker_calls_fetch_ohlcv_with_short_period():
    with patch(
        "src.data.profile.fetch_ohlcv", return_value=(_sample_df(), "live")
    ) as mock_fetch:
        validate_ticker("AAPL")
    mock_fetch.assert_called_once_with("AAPL", period="5d")
