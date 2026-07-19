"""AUTH-03 database-level Row Level Security enforcement proof (D-11),
against the live local Supabase stack -- no mocking.

Uses two distinct authenticated anon-key clients (User A and User B, each
with their own real access token attached) to prove the profiles table's
RLS policies filter by `auth.uid() = user_id` at the Postgres engine level,
not merely as an app-layer `if row.user_id == current_user_id` check
(RESEARCH.md "Don't Hand-Roll" table / Pattern 4).
"""

from supabase import create_client

from src.auth import session as auth_session
from src.config import get_config


def _scoped_client(access_token: str):
    """An anon-key client with one user's access token attached -- exactly
    the shape of client the deployed app would use for a signed-in user's
    request (never the service-role key -- Pitfall 5)."""
    client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    client.postgrest.auth(access_token)
    return client


def test_cross_user_select_returns_zero_rows(two_users):
    """User A's client, querying profiles for User B's user_id, receives
    zero rows -- the RLS SELECT policy blocks cross-user reads -- rather
    than User B's row."""
    (email_a, password_a, _signup_a), (_email_b, _password_b, signup_b) = two_users

    sign_in_a = auth_session.sign_in(email_a, password_a)
    user_id_b = signup_b.user.id

    client_a = _scoped_client(sign_in_a.session.access_token)
    result = client_a.table("profiles").select("*").eq("user_id", user_id_b).execute()

    assert result.data == []


def test_cross_user_update_affects_zero_rows(two_users):
    """An UPDATE attempt by User A's client against User B's profiles row
    affects zero rows rather than succeeding."""
    (email_a, password_a, _signup_a), (_email_b, _password_b, signup_b) = two_users

    sign_in_a = auth_session.sign_in(email_a, password_a)
    user_id_b = signup_b.user.id

    client_a = _scoped_client(sign_in_a.session.access_token)
    result = (
        client_a.table("profiles")
        .update({"last_login": "2020-01-01T00:00:00+00:00"})
        .eq("user_id", user_id_b)
        .execute()
    )

    assert result.data == []  # zero rows affected -- RLS blocked the update


def test_same_user_select_and_update_succeed_positive_control(test_user_factory):
    """Positive control (must accompany the negative checks above): the RLS
    policy filters cross-user access, it does not simply block all access --
    each user's own client CAN read and update their own row."""
    email, password, signup_response = test_user_factory()
    user_id = signup_response.user.id

    sign_in_response = auth_session.sign_in(email, password)
    client = _scoped_client(sign_in_response.session.access_token)

    select_result = client.table("profiles").select("*").eq("user_id", user_id).execute()
    assert len(select_result.data) == 1
    assert select_result.data[0]["user_id"] == user_id

    update_result = (
        client.table("profiles")
        .update({"last_login": "2021-06-15T12:00:00+00:00"})
        .eq("user_id", user_id)
        .execute()
    )
    assert len(update_result.data) == 1
    assert update_result.data[0]["user_id"] == user_id
