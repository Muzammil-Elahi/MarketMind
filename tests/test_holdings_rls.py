"""T-02-01: public.holdings Row Level Security enforcement proof, against
the live local Supabase stack -- no mocking.

Mirrors tests/test_rls_policy.py's two-user pattern, retargeted at
holdings. Unlike profiles (select/update only), holdings has client-facing
INSERT and DELETE policies too, so this file covers all four verbs. Every
assertion (except fixture setup) uses an anon-key client scoped to one
user's own access token -- never a service-role client.
"""

from supabase import create_client

from src.auth import session as auth_session
from src.config import get_config


def _scoped_client(access_token: str):
    """An anon-key client with one user's access token attached -- exactly
    the shape of client the deployed app would use for a signed-in user's
    request (never the service-role key)."""
    client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    client.postgrest.auth(access_token)
    return client


def test_cross_user_select_holdings_returns_zero_rows(two_users):
    """User A inserts a holdings row for themselves; User B's scoped client
    querying for User A's user_id gets zero rows back -- the RLS SELECT
    policy filters cross-user reads."""
    (email_a, password_a, signup_a), (email_b, password_b, _signup_b) = two_users
    user_id_a = signup_a.user.id

    sign_in_a = auth_session.sign_in(email_a, password_a)
    client_a = _scoped_client(sign_in_a.session.access_token)
    client_a.table("holdings").insert(
        {"user_id": user_id_a, "ticker": "AAPL", "quantity": 10}
    ).execute()

    sign_in_b = auth_session.sign_in(email_b, password_b)
    client_b = _scoped_client(sign_in_b.session.access_token)
    result = client_b.table("holdings").select("*").eq("user_id", user_id_a).execute()

    assert result.data == []


def test_cross_user_insert_with_other_user_id_is_blocked_by_rls(two_users):
    """User A's scoped client attempts to insert a holdings row with
    user_id set to User B's id -- the INSERT policy's `with check` clause
    rejects the mismatch by raising, unlike a SELECT/UPDATE mismatch which
    just returns/affects zero rows."""
    (email_a, password_a, _signup_a), (_email_b, _password_b, signup_b) = two_users
    user_id_b = signup_b.user.id

    sign_in_a = auth_session.sign_in(email_a, password_a)
    client_a = _scoped_client(sign_in_a.session.access_token)

    try:
        client_a.table("holdings").insert(
            {"user_id": user_id_b, "ticker": "MSFT", "quantity": 1}
        ).execute()
        raised = False
    except Exception:
        raised = True

    assert raised, "Inserting a holdings row with a mismatched user_id must raise"


def test_cross_user_delete_holdings_affects_zero_rows(two_users):
    """User B has a holdings row; User A's scoped client attempts to delete
    it by id -- zero rows are affected and the row still exists when User B
    queries for it."""
    (email_a, password_a, _signup_a), (email_b, password_b, signup_b) = two_users
    user_id_b = signup_b.user.id

    sign_in_b = auth_session.sign_in(email_b, password_b)
    client_b = _scoped_client(sign_in_b.session.access_token)
    insert_result = (
        client_b.table("holdings")
        .insert({"user_id": user_id_b, "ticker": "GOOG", "quantity": 3})
        .execute()
    )
    holding_id = insert_result.data[0]["id"]

    sign_in_a = auth_session.sign_in(email_a, password_a)
    client_a = _scoped_client(sign_in_a.session.access_token)
    delete_result = client_a.table("holdings").delete().eq("id", holding_id).execute()

    assert delete_result.data == []

    still_there = client_b.table("holdings").select("*").eq("id", holding_id).execute()
    assert len(still_there.data) == 1
    assert still_there.data[0]["ticker"] == "GOOG"


def test_same_user_full_crud_holdings_succeeds_positive_control(test_user_factory):
    """Positive control (must accompany the negative checks above): the RLS
    policy filters cross-user access, it does not simply block all access --
    a user's own scoped client can insert, select, update, and delete their
    own holdings row."""
    email, password, signup_response = test_user_factory()
    user_id = signup_response.user.id

    sign_in_response = auth_session.sign_in(email, password)
    client = _scoped_client(sign_in_response.session.access_token)

    insert_result = (
        client.table("holdings")
        .insert({"user_id": user_id, "ticker": "SPY", "quantity": 2, "cost_basis": 400.0})
        .execute()
    )
    assert len(insert_result.data) == 1
    holding_id = insert_result.data[0]["id"]

    select_result = client.table("holdings").select("*").eq("id", holding_id).execute()
    assert len(select_result.data) == 1
    assert select_result.data[0]["user_id"] == user_id

    update_result = (
        client.table("holdings").update({"quantity": 5}).eq("id", holding_id).execute()
    )
    assert len(update_result.data) == 1
    assert update_result.data[0]["quantity"] == 5

    delete_result = client.table("holdings").delete().eq("id", holding_id).execute()
    assert len(delete_result.data) == 1

    final_select = client.table("holdings").select("*").eq("id", holding_id).execute()
    assert final_select.data == []
