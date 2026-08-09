"""Tests for src/data/cache.py -- the yfinance chokepoint (D-07/D-08/D-09).

All yfinance access is mocked via unittest.mock.patch -- no test in this
file makes a live network call. The SQLite disk cache is isolated to
pytest's tmp_path per test (via monkeypatching cache.DB_PATH), so tests
never touch or depend on the real data/price_cache.db.
"""

import inspect
from unittest.mock import patch

import pandas as pd
import pytest

from src.data import cache


@pytest.fixture(autouse=True)
def isolated_cache(tmp_path, monkeypatch):
    """Point DB_PATH at a per-test tmp file and clear st.cache_data's
    in-memory cache before and after every test, so tests never leak state
    into each other or into the real on-disk cache.
    """
    monkeypatch.setattr(cache, "DB_PATH", str(tmp_path / "price_cache.db"))
    cache.fetch_ohlcv.clear()
    yield
    cache.fetch_ohlcv.clear()


def _sample_df():
    return pd.DataFrame({"Close": [100.0, 101.0, 102.0]})


def test_repeated_fetch_within_ttl_hits_cache_not_live_fetch():
    """D-08: two fetch_ohlcv() calls in a row for the same ticker/period
    within the TTL window must not invoke the live-fetch function twice."""
    with patch("src.data.cache.yf.download", return_value=_sample_df()) as mock_download:
        first_df, first_status = cache.fetch_ohlcv("AAPL", "1y")
        second_df, second_status = cache.fetch_ohlcv("AAPL", "1y")

    assert mock_download.call_count == 1
    assert first_status == "live"
    assert second_status == "live"
    pd.testing.assert_frame_equal(first_df, second_df)


def test_live_fetch_failure_falls_back_to_stale_disk_row():
    """D-09: a live-fetch failure with a prior successful fetch already
    written to the SQLite disk cache returns the stale row + "stale"
    status, not an exception."""
    ticker, period = "MSFT", "1y"

    with patch("src.data.cache.yf.download", return_value=_sample_df()):
        cache.fetch_ohlcv(ticker, period)  # populates disk cache + in-memory cache

    # Simulate TTL expiry / a cold container restart: the in-memory
    # st.cache_data layer is gone, but the SQLite disk row survives.
    cache.fetch_ohlcv.clear()

    with patch(
        "src.data.cache.yf.download", side_effect=RuntimeError("simulated network failure")
    ):
        df, status = cache.fetch_ohlcv(ticker, period)

    assert status == "stale"
    assert not df.empty


def test_live_fetch_failure_with_no_cached_row_raises():
    """Pitfall 4 / D-09 counterpart: a live-fetch failure with no prior row
    in the SQLite disk cache must raise explicitly, never return None or an
    empty result silently."""
    with patch(
        "src.data.cache.yf.download", side_effect=RuntimeError("simulated network failure")
    ):
        with pytest.raises(RuntimeError):
            cache.fetch_ohlcv("GOOG", "1y")


def test_fetch_live_retry_configured_for_three_attempts():
    """Pitfall 6: no hardcoded requests-per-minute constant -- the resilience
    mechanism is tenacity's stop_after_attempt(3), asserted structurally via
    the decorator's own attributes."""
    assert cache._fetch_live.retry.stop.max_attempt_number == 3


def test_fetch_ohlcv_uses_configured_ttl_not_a_literal():
    """fetch_ohlcv must read its ttl from CACHE_TTL_SECONDS (src/config.py),
    never hardcode 3600 a second time in this module (structural check --
    st.cache_data's wrapped function does not expose its ttl at runtime)."""
    module_source = inspect.getsource(cache)

    assert "ttl=CACHE_TTL_SECONDS" in module_source
    assert "ttl=3600" not in module_source


def test_format_stale_cache_message_matches_ui_spec_copywriting_contract():
    """UI-SPEC Copywriting Contract, stale-cache row (D-09)."""
    message = cache.format_stale_cache_message("2026-07-18 10:00 UTC")

    assert message == (
        "Showing saved data from 2026-07-18 10:00 UTC — "
        "live prices are temporarily unavailable."
    )


def test_init_db_creates_missing_parent_directory(tmp_path, monkeypatch):
    """CR-01 regression: on a fresh checkout/deployment the parent directory
    of DB_PATH does not exist yet, and sqlite3.connect() does not create it.
    _init_db() must create it explicitly so the very first fetch_ohlcv()
    call does not crash with OperationalError."""
    nested_db_path = tmp_path / "nested" / "does" / "not" / "exist" / "price_cache.db"
    monkeypatch.setattr(cache, "DB_PATH", str(nested_db_path))

    assert not nested_db_path.parent.exists()

    cache._init_db()

    assert nested_db_path.parent.is_dir()
    assert nested_db_path.exists()


def test_multiindex_columns_from_live_fetch_are_flattened():
    """Regression test: yfinance can return a DataFrame with MultiIndex
    columns (e.g. [("Close", "AAPL"), ("Open", "AAPL")]) even for a single
    ticker. fetch_ohlcv() must flatten these to a plain pd.Index before
    returning, otherwise downstream df["Close"] resolves to a 1-column
    DataFrame instead of a Series and feature computation silently produces
    all-NaN output."""
    columns = pd.MultiIndex.from_tuples([("Close", "AAPL"), ("Open", "AAPL")])
    multiindex_df = pd.DataFrame(
        {
            ("Close", "AAPL"): [100.0, 101.0, 102.0],
            ("Open", "AAPL"): [99.0, 100.0, 101.0],
        }
    )
    multiindex_df.columns = columns

    with patch("src.data.cache.yf.download", return_value=multiindex_df):
        df, status = cache.fetch_ohlcv("AAPL", "1y")

    assert not isinstance(df.columns, pd.MultiIndex)
    assert list(df.columns) == ["Close", "Open"]
    assert status == "live"


def test_sql_statements_use_parameterized_placeholders_not_string_interpolation():
    """Structural check (per plan, not a runtime behavior test): every SQL
    statement referencing ticker/period uses `?` placeholders bound via a
    separate parameters tuple -- never an f-string or %-formatted SQL
    string with those variables inlined (T-01-03)."""
    write_source = inspect.getsource(cache._write_through)
    read_source = inspect.getsource(cache._read_disk_cache)

    assert "VALUES (?, ?, ?, ?)" in write_source
    assert "WHERE ticker = ? AND period = ?" in read_source

    for source in (write_source, read_source):
        assert 'f"' not in source
        assert "f'" not in source
        assert "% (" not in source
        assert ".format(" not in source
