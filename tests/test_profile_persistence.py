"""AUTH-02 cross-session persistence, last_login write, and insert-idempotency
proof (D-10), against the live local Supabase stack -- no mocking.
"""

import time
from datetime import datetime

import pytest
import streamlit as st
from postgrest.exceptions import APIError
from supabase import create_client

from src.auth import session as auth_session
from src.config import get_config


def _fetch_profile_row(access_token: str, user_id: str) -> dict:
    """Read the profiles row for `user_id` via an anon-key client scoped to
    `access_token` -- exercises the same RLS-gated read path the app would
    use, never a service-role bypass."""
    scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    scoped_client.postgrest.auth(access_token)
    result = (
        scoped_client.table("profiles")
        .select("user_id, created_at, last_login")
        .eq("user_id", user_id)
        .execute()
    )
    assert len(result.data) == 1, f"Expected exactly one profiles row for {user_id}"
    return result.data[0]


def test_profile_row_auto_provisioned_by_trigger_with_last_login_null(test_user_factory):
    """D-10: the profiles row is created by the handle_new_user() trigger at
    signup -- not by application code -- with created_at populated and
    last_login left null until the first sign_in()."""
    _email, _password, signup_response = test_user_factory()
    user_id = signup_response.user.id
    access_token = signup_response.session.access_token

    row = _fetch_profile_row(access_token, user_id)

    assert row["user_id"] == user_id
    assert row["created_at"] is not None
    assert row["last_login"] is None


def test_last_login_persists_across_new_session_and_advances_on_each_sign_in(test_user_factory):
    """AUTH-02 phase success criterion #4: a profiles row written in one
    session is readable again through a freshly re-authenticated session --
    simulating a new browser session/device by discarding all in-memory
    state and calling sign_in() again with the same credentials -- and
    last_login is populated then advances to a strictly later timestamp on
    a second sign_in(), proving the column is live-updated, not
    write-once."""
    email, password, signup_response = test_user_factory()
    user_id = signup_response.user.id

    # Simulate "a new session/device": discard all in-memory state and
    # re-authenticate from scratch.
    st.session_state.clear()

    first_sign_in = auth_session.sign_in(email, password)
    row_after_first = _fetch_profile_row(first_sign_in.session.access_token, user_id)
    assert row_after_first["user_id"] == user_id  # same row, still readable
    assert row_after_first["last_login"] is not None
    first_last_login = datetime.fromisoformat(row_after_first["last_login"])

    time.sleep(1.1)  # ensure a strictly later, distinguishable timestamp
    st.session_state.clear()
    second_sign_in = auth_session.sign_in(email, password)
    row_after_second = _fetch_profile_row(second_sign_in.session.access_token, user_id)
    second_last_login = datetime.fromisoformat(row_after_second["last_login"])

    assert second_last_login > first_last_login


def test_duplicate_insert_for_existing_user_id_raises_unique_violation(
    test_user_factory, supabase_env
):
    """D-10: the profiles table's primary key (user_id) rejects a second row
    for an already-existing user at the database level.

    Uses a service-role-keyed client to perform a raw table-level INSERT,
    bypassing RLS and all application code entirely -- so the failure
    observed here is specifically the Postgres unique-violation on the
    primary key, isolated from the separate (and separately tested, in
    test_rls_policy.py) question of whether RLS/grants would block an
    anon-key client's INSERT in the first place. This proves the constraint
    holds at the database level, not just on paper (D-10's idempotency
    question resolved in Plan 01/02).
    """
    _email, _password, signup_response = test_user_factory()
    user_id = signup_response.user.id

    service_client = create_client(supabase_env["API_URL"], supabase_env["SERVICE_ROLE_KEY"])

    with pytest.raises(APIError) as exc_info:
        service_client.table("profiles").insert(
            {"user_id": user_id, "created_at": "2020-01-01T00:00:00+00:00"}
        ).execute()

    assert exc_info.value.code == "23505"  # Postgres unique_violation
