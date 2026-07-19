"""AUTH-03 session-isolation proof (D-05) -- the real cache_resource leak
vector, not a trivially-passing session_state comparison.

Per RESEARCH.md Pitfall 3: a naive test that creates two `AppTest`
instances, sets different `session_state` values on each, and asserts
`session_state` differs *always passes*, even in the presence of a real
leak, because `AppTest` guarantees per-instance `session_state` isolation by
construction -- that only tests the testing framework, not the app.

This file instead exercises the real leak vector end-to-end: it runs the
actual `require_auth()`/`get_supabase_client()` code path (through a real
`AppTest` run of the gated home page, via the thin
`tests/apptest_scripts/home_page_target.py` wrapper) for two distinct real
users against the live local Supabase stack, and asserts the shared
`st.cache_resource` client object itself -- not `session_state` -- carries no
trace of either user's identity.

`st.cache_resource`'s default `scope="global"` backs onto a single,
process-wide cache keyed with no session id (see
`streamlit.runtime.caching.cache_resource_api.ResourceCaches`), independent
of `AppTest`'s per-run mocked `Runtime` -- so `get_supabase_client()` called
directly from this test process returns the exact same object that was
resolved inside each `AppTest` run, letting this test capture and inspect
it directly.
"""

from pathlib import Path

from streamlit.testing.v1 import AppTest

from src.auth import session as auth_session
from src.data.supabase_client import get_supabase_client

_TARGET_SCRIPT = str(Path(__file__).parent / "apptest_scripts" / "home_page_target.py")


def _run_home_page_as(access_token: str, refresh_token: str | None = None) -> AppTest:
    at = AppTest.from_file(_TARGET_SCRIPT)
    at.session_state["access_token"] = access_token
    if refresh_token is not None:
        at.session_state["refresh_token"] = refresh_token
    at.run()
    return at


def test_shared_client_carries_no_identity_across_two_real_user_sessions(two_users):
    """The core D-05 proof: run User A's session through the real
    require_auth()/get_supabase_client() code path via AppTest, then User
    B's -- and assert the shared cache_resource client is the same object
    across both runs (expected -- it's a stateless connection, sharing it is
    correct per D-06) but carries no trace of either user's token/identity,
    and each user's require_auth() call resolves only to their own
    identity."""
    (email_a, password_a, signup_a), (email_b, password_b, signup_b) = two_users

    sign_in_a = auth_session.sign_in(email_a, password_a)
    sign_in_b = auth_session.sign_in(email_b, password_b)

    at_a = _run_home_page_as(sign_in_a.session.access_token)
    assert not at_a.exception, f"User A's AppTest run raised: {at_a.exception}"
    assert at_a.session_state["_resolved_user_id"] == signup_a.user.id
    assert at_a.session_state["_resolved_user_email"] == email_a

    client_after_a = get_supabase_client()
    # The shared client must carry no trace of User A's session/identity --
    # get_session() returning None proves no authenticating call ever
    # persisted a session onto this cached, process-wide object (T-01-01).
    assert client_after_a.auth.get_session() is None

    at_b = _run_home_page_as(sign_in_b.session.access_token)
    assert not at_b.exception, f"User B's AppTest run raised: {at_b.exception}"

    client_after_b = get_supabase_client()

    # (a) Same shared instance across both runs -- expected, it's a
    # stateless connection and sharing it is correct (D-06).
    assert client_after_a is client_after_b

    # (b) User B's require_auth() call -- exercised for real, through the
    # gated home page -- resolves to User B's identity, never User A's.
    assert at_b.session_state["_resolved_user_id"] == signup_b.user.id
    assert at_b.session_state["_resolved_user_email"] == email_b
    assert at_b.session_state["_resolved_user_id"] != at_a.session_state["_resolved_user_id"]

    # (c) After User B's run, the shared client still carries no trace of
    # either user's session -- it never had one attached in the first place.
    assert client_after_b.auth.get_session() is None


def test_shared_client_carries_no_identity_after_refresh_token_path(two_users):
    """Same leak vector, forced through require_auth()'s refresh-token
    branch: an invalid access_token paired with a valid refresh_token still
    must not leave any trace of the refreshing user's session on the shared
    cache_resource client -- this is the specific path RESEARCH.md's Pitfall
    2/3 flag as the actual real-world failure mode (refresh_session() calls
    internally persist a session onto whichever client they're invoked on)."""
    (email_a, password_a, signup_a), (email_b, password_b, signup_b) = two_users

    sign_in_a = auth_session.sign_in(email_a, password_a)
    sign_in_b = auth_session.sign_in(email_b, password_b)

    # Force User A through the refresh-token branch: an invalid access_token
    # paired with a valid refresh_token.
    at_a = _run_home_page_as(
        "this-is-not-a-valid-jwt-and-will-fail-get_user",
        refresh_token=sign_in_a.session.refresh_token,
    )
    assert not at_a.exception, f"User A's refresh-path AppTest run raised: {at_a.exception}"
    assert at_a.session_state["_resolved_user_id"] == signup_a.user.id

    # The shared client must carry no trace of User A's refreshed session.
    assert get_supabase_client().auth.get_session() is None

    at_b = _run_home_page_as(sign_in_b.session.access_token)
    assert not at_b.exception, f"User B's AppTest run raised: {at_b.exception}"
    assert at_b.session_state["_resolved_user_id"] == signup_b.user.id
    assert at_b.session_state["_resolved_user_id"] != at_a.session_state["_resolved_user_id"]
    assert get_supabase_client().auth.get_session() is None
