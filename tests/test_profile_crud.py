"""Profile/holdings CRUD round-trip, idempotency, and mass-assignment
resistance proof (PROFILE-01/PROFILE-02), against the live local Supabase
stack -- no mocking. Mirrors tests/test_profile_persistence.py's real-stack
style.
"""

import inspect

from supabase import create_client

from src.data import profile as profile_module
from src.data.profile import fetch_holdings, fetch_profile, upsert_holdings, upsert_profile


def _service_client(supabase_env):
    return create_client(supabase_env["API_URL"], supabase_env["SERVICE_ROLE_KEY"])


def test_upsert_profile_and_fetch_profile_round_trip_all_scalar_fields(test_user_factory):
    _email, _password, signup = test_user_factory()
    user_id = signup.user.id
    access_token = signup.session.access_token

    upsert_profile(
        access_token,
        user_id,
        risk_tolerance="Moderate",
        time_horizon="3-5yr",
        preferred_sectors=["Tech", "Healthcare"],
        excluded_sectors=["Energy"],
        preferred_asset_types=["stocks", "etfs"],
        capital=10000,
    )

    row = fetch_profile(access_token, user_id)

    assert row["risk_tolerance"] == "Moderate"
    assert row["time_horizon"] == "3-5yr"
    assert row["preferred_sectors"] == ["Tech", "Healthcare"]
    assert row["excluded_sectors"] == ["Energy"]
    assert row["preferred_asset_types"] == ["stocks", "etfs"]
    assert row["capital"] == 10000


def test_upsert_profile_uses_update_never_insert_for_profiles():
    """Structural check: upsert_profile must UPDATE, never INSERT/upsert,
    since public.profiles has no client-facing INSERT policy."""
    source = inspect.getsource(profile_module.upsert_profile)
    assert ".update(" in source
    assert ".upsert(" not in source
    assert ".insert(" not in source


def test_double_upsert_profile_is_idempotent(test_user_factory, supabase_env):
    _email, _password, signup = test_user_factory()
    user_id = signup.user.id
    access_token = signup.session.access_token

    kwargs = dict(
        risk_tolerance="Aggressive",
        time_horizon="10+yr",
        preferred_sectors=["Tech"],
        excluded_sectors=None,
        preferred_asset_types=["crypto"],
        capital=5000,
    )

    upsert_profile(access_token, user_id, **kwargs)
    first = fetch_profile(access_token, user_id)
    upsert_profile(access_token, user_id, **kwargs)
    second = fetch_profile(access_token, user_id)

    assert first == second

    service_client = _service_client(supabase_env)
    count_result = (
        service_client.table("profiles")
        .select("user_id", count="exact")
        .eq("user_id", user_id)
        .execute()
    )
    assert count_result.count == 1


def test_fetch_profile_has_no_cache_data_decorator():
    """D-13: no @st.cache_data/@st.cache_resource decorator wraps any
    function in this module -- profile reads must always be fresh."""
    module_source = inspect.getsource(profile_module)
    assert "@st.cache_data" not in module_source
    assert "@st.cache_resource" not in module_source


def test_upsert_holdings_round_trip_saves_ticker_quantity_optional_cost_basis(test_user_factory):
    _email, _password, signup = test_user_factory()
    user_id = signup.user.id
    access_token = signup.session.access_token

    upsert_holdings(
        access_token,
        user_id,
        [
            {"ticker": "AAPL", "quantity": 10, "cost_basis": 150.0},
            {"ticker": "BTC-USD", "quantity": 0.5},
        ],
    )

    rows = fetch_holdings(access_token, user_id)
    by_ticker = {row["ticker"]: row for row in rows}

    assert len(rows) == 2
    assert by_ticker["AAPL"]["quantity"] == 10
    assert by_ticker["AAPL"]["cost_basis"] == 150.0
    assert by_ticker["BTC-USD"]["quantity"] == 0.5
    assert by_ticker["BTC-USD"]["cost_basis"] is None


def test_upsert_holdings_ignores_spoofed_user_id_in_row_payload(two_users, supabase_env):
    """T-02-04 proof: a row dict containing an extra, mismatched user_id key
    must not override the real caller-supplied user_id argument."""
    (_email_a, _password_a, signup_a), (_email_b, _password_b, signup_b) = two_users
    user_id_a = signup_a.user.id
    user_id_b = signup_b.user.id
    access_token_a = signup_a.session.access_token

    upsert_holdings(
        access_token_a,
        user_id_a,
        [{"ticker": "MSFT", "quantity": 5, "user_id": user_id_b}],
    )

    service_client = _service_client(supabase_env)
    rows_for_a = (
        service_client.table("holdings")
        .select("ticker, user_id")
        .eq("user_id", user_id_a)
        .execute()
        .data
    )
    rows_for_b = (
        service_client.table("holdings")
        .select("ticker, user_id")
        .eq("user_id", user_id_b)
        .execute()
        .data
    )

    assert any(row["ticker"] == "MSFT" for row in rows_for_a)
    assert not any(row["ticker"] == "MSFT" for row in rows_for_b)
