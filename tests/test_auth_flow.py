"""AUTH-01/AUTH-02 behavior proof against the live local Supabase stack.

No mocking of supabase-py itself — every test in this file exercises
src.auth.session against the real local Supabase CLI Docker stack (Postgres,
GoTrue, Inbucket/Mailpit) started in Plan 01. See tests/conftest.py for the
supabase_env/test_user_factory fixtures that wire this up.
"""

import time
from urllib import request as urllib_request
from urllib.parse import quote

import pytest
from supabase_auth.errors import AuthApiError

from src.auth import session as auth_session
from src.data.supabase_client import get_supabase_client


def _mailpit_messages_to(supabase_env, email: str) -> list:
    """Query the local Inbucket/Mailpit instance for messages sent to `email`."""
    url = f"{supabase_env['INBUCKET_URL']}/api/v1/search?query={quote('to:' + email)}"
    with urllib_request.urlopen(url) as response:
        import json

        return json.load(response)["messages"]


def test_sign_up_returns_populated_session_immediately(test_user_factory):
    """D-02: email confirmation is disabled, so sign_up() returns a usable
    session with no separate verification step."""
    email, password, response = test_user_factory()

    assert response.session is not None
    assert response.session.access_token
    assert response.session.refresh_token
    assert response.user is not None
    assert response.user.email == email


def test_sign_up_sets_session_state(test_user_factory):
    email, password, response = test_user_factory()

    import streamlit as st

    assert st.session_state.get("access_token") == response.session.access_token
    assert st.session_state.get("refresh_token") == response.session.refresh_token
    assert st.session_state.get("logged_in") is True


def test_duplicate_sign_up_does_not_crash_or_create_second_account(test_user_factory):
    """Signing up twice with the same email must not silently succeed as a
    new account, and must not crash the app."""
    email, password, _first_response = test_user_factory()

    # Second sign_up with the same email: either raises AuthApiError, or
    # returns a response distinguishable from a genuine new signup (no
    # session / no new identity) -- either way, the app does not crash and
    # does not treat this as a fresh account.
    try:
        second_response = auth_session.sign_up(email, password)
    except AuthApiError:
        return  # Recognized duplicate-signup error -- acceptable outcome.

    # If no exception was raised, Supabase's "fake user" convention for an
    # already-registered email applies: no new session is established and no
    # identities are attached, distinguishing it from a genuine new account.
    assert second_response.session is None or second_response.user.identities in (
        None,
        [],
    )


def test_sign_in_after_sign_up_succeeds_with_no_confirmation_gate(test_user_factory):
    """D-02: no 'unconfirmed account' state to handle -- sign_in succeeds
    immediately after sign_up with no separate verification gate."""
    email, password, _ = test_user_factory()

    response = auth_session.sign_in(email, password)

    assert response.session is not None
    assert response.user.email == email


def test_sign_in_invalid_credentials_raises(test_user_factory):
    email, _password, _ = test_user_factory()

    with pytest.raises(AuthApiError):
        auth_session.sign_in(email, "definitely-the-wrong-password-123!")


def test_sign_in_updates_last_login_across_two_calls(test_user_factory):
    """D-10/COVERAGE.md: sign_in() persists profiles.last_login via a
    short-lived per-call authenticated client -- the Postgres CRUD proof."""
    email, password, sign_up_response = test_user_factory()
    user_id = sign_up_response.user.id

    get_supabase_client()  # sanity: shared client resolves without error

    first_sign_in = auth_session.sign_in(email, password)
    first_client_token = first_sign_in.session.access_token

    from supabase import create_client

    from src.config import get_config

    def _fetch_last_login(access_token: str):
        scoped_client = create_client(
            get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY")
        )
        scoped_client.postgrest.auth(access_token)
        row = (
            scoped_client.table("profiles")
            .select("last_login")
            .eq("user_id", user_id)
            .execute()
        )
        return row.data[0]["last_login"]

    last_login_after_first = _fetch_last_login(first_client_token)
    assert last_login_after_first is not None  # populated by first sign_in()

    time.sleep(1.1)  # ensure a distinguishable timestamp on the second call
    second_sign_in = auth_session.sign_in(email, password)
    last_login_after_second = _fetch_last_login(second_sign_in.session.access_token)

    assert last_login_after_second != last_login_after_first


def test_magic_link_sign_in_sends_email_via_local_inbucket(test_user_factory, supabase_env):
    """Magic-link send path actually delivers an email end-to-end -- no
    mocking, verified against the local Inbucket/Mailpit instance."""
    email, _password, _ = test_user_factory()

    # sign_in_with_magic_link should not raise for a valid, existing email.
    auth_session.sign_in_with_magic_link(email)

    # Poll briefly -- local Inbucket/Mailpit delivery is near-instant but not
    # synchronous with the API call returning.
    messages = []
    for _ in range(10):
        messages = _mailpit_messages_to(supabase_env, email)
        if messages:
            break
        time.sleep(0.5)

    assert messages, f"Expected at least one email delivered to {email} via Inbucket/Mailpit"


def test_require_auth_with_no_token_halts_without_returning_user():
    """No access_token in st.session_state -> halts, does not return a user."""
    import streamlit as st

    st.session_state.clear()

    result = auth_session.require_auth()

    assert result is None


def test_require_auth_with_valid_token_returns_user(test_user_factory):
    email, password, _ = test_user_factory()
    sign_in_response = auth_session.sign_in(email, password)

    import streamlit as st

    st.session_state["access_token"] = sign_in_response.session.access_token
    st.session_state["refresh_token"] = sign_in_response.session.refresh_token

    user = auth_session.require_auth()

    assert user is not None
    assert user.email == email


def test_require_auth_uses_get_user_never_get_session():
    """Non-discretionary D-04 constraint, enforced structurally: assert the
    source code path, not just behavior, to guarantee no regression back to
    the client-trusted get_session()."""
    import inspect

    source = inspect.getsource(auth_session.require_auth)

    assert ".auth.get_user(" in source
    assert ".auth.get_session(" not in source


def test_require_auth_expired_token_refreshes_before_giving_up(test_user_factory):
    """With an expired access_token but a valid refresh_token, require_auth()
    refreshes the session and retries get_user() before giving up."""
    email, password, _ = test_user_factory()
    sign_in_response = auth_session.sign_in(email, password)

    import streamlit as st

    st.session_state["access_token"] = "this-is-not-a-valid-jwt-and-will-fail-get_user"
    st.session_state["refresh_token"] = sign_in_response.session.refresh_token

    user = auth_session.require_auth()

    assert user is not None
    assert user.email == email
    # require_auth() must have updated session_state with the refreshed token
    # rather than leaving the invalid one in place.
    assert st.session_state["access_token"] != "this-is-not-a-valid-jwt-and-will-fail-get_user"


def test_require_auth_both_tokens_invalid_clears_session_and_halts():
    import streamlit as st

    st.session_state.clear()
    st.session_state["access_token"] = "invalid-token"
    st.session_state["refresh_token"] = "invalid-refresh-token"

    result = auth_session.require_auth()

    assert result is None
    assert "access_token" not in st.session_state
    assert "refresh_token" not in st.session_state


def test_sign_out_clears_session_state_only(test_user_factory):
    email, password, _ = test_user_factory()
    auth_session.sign_in(email, password)

    import streamlit as st

    assert st.session_state.get("logged_in") is True

    auth_session.sign_out()

    assert "access_token" not in st.session_state
    assert "refresh_token" not in st.session_state
    assert "logged_in" not in st.session_state


def test_signup_does_not_call_touch_last_login_leaving_it_null_until_first_sign_in(
    test_user_factory,
):
    """The auto-provisioning trigger creates the profiles row with
    last_login left null; sign_up() itself must not populate it -- only
    sign_in() does, which is itself part of the AUTH-02 persistence proof."""
    email, password, sign_up_response = test_user_factory()
    user_id = sign_up_response.user.id
    access_token = sign_up_response.session.access_token

    from supabase import create_client

    from src.config import get_config

    scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    scoped_client.postgrest.auth(access_token)
    row = (
        scoped_client.table("profiles")
        .select("last_login")
        .eq("user_id", user_id)
        .execute()
    )

    assert row.data[0]["last_login"] is None
