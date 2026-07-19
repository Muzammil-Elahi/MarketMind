"""Central auth gate and Supabase Auth wrappers.

D-04: `require_auth()` is the single, central auth-check helper every
auth-gated page must call — no per-page inline auth checks. It re-verifies
the access token server-side via `get_user(token)` — never the
client-trusted, locally-cached `get_session()` accessor — on every call,
attempts a `refresh_session()` before giving up on an expired token, and
halts rendering (`st.stop()`) if the caller turns out not to be
authenticated.

Per-user identity (`access_token`, `refresh_token`, `logged_in`) lives
exclusively in `st.session_state` — this module never stores a token on the
shared `get_supabase_client()` `cache_resource` instance (see
`src/data/supabase_client.py`'s docstring; threat register T-01-01).

Every authenticating call (sign-up, password sign-in, magic-link sign-in,
session refresh) is routed through `_scoped_client()` — a fresh, uncached
`create_client(...)` built for that one call only — never through the
shared `get_supabase_client()`. This is not optional: `supabase-auth`'s
`sign_in_with_password()`, `sign_up()`, `sign_in_with_otp()`, and
`refresh_session()` all internally call `_save_session()`/`_remove_session()`
on whichever client instance they're invoked on. Calling any of them on the
shared, process-wide `get_supabase_client()` instance would persist one
user's session onto that object (or wipe another in-flight user's), which is
exactly the cross-user leak this phase's threat model (T-01-01) and D-05's
isolation test exist to catch. Only genuinely stateless calls that take an
explicit token/JWT argument (`get_user(token)`,
`admin.sign_out(access_token, scope)`) are made against the shared client.
"""

from contextlib import suppress
from datetime import datetime, timezone

import streamlit as st
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError

from src.config import get_config
from src.data.supabase_client import get_supabase_client


def _scoped_client() -> Client:
    """Build a fresh, uncached Supabase client for one authenticating call.

    Every authenticating call (sign-up, sign-in, magic-link, refresh) must
    go through a client built here — never the shared
    `get_supabase_client()` `cache_resource` instance — so no user's session
    ever gets persisted onto that process-wide, supposedly-stateless object.
    The client returned here goes out of scope immediately after its single
    call and is never stored in `st.session_state` or any cached/global
    object (same discipline as `_touch_last_login`, below).
    """
    return create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))


def sign_up(email: str, password: str):
    """Sign up a new user with email/password.

    With "Confirm email" disabled at the project level (D-02), a successful
    signup returns a populated ``response.session`` immediately — the caller
    is considered logged in with no separate verification step. On success,
    stores ``access_token``/``refresh_token``/``logged_in`` in
    ``st.session_state``.

    Does not call :func:`_touch_last_login` — the ``handle_new_user()``
    trigger already creates the ``profiles`` row with ``last_login`` left
    null; that null-then-populated transition (on the user's first
    :func:`sign_in`) is itself part of AUTH-02's persistence proof.

    A duplicate signup for an already-registered email either raises
    ``AuthApiError`` or returns a response with no session/no new identity,
    depending on the project's Supabase Auth configuration — either way, no
    second ``profiles`` row is created, since the trigger only fires on a
    genuine new ``auth.users`` insert.
    """
    response = _scoped_client().auth.sign_up({"email": email, "password": password})
    if response.session is not None:
        st.session_state["access_token"] = response.session.access_token
        st.session_state["refresh_token"] = response.session.refresh_token
        st.session_state["logged_in"] = True
    return response


def sign_in(email: str, password: str):
    """Sign in an existing user with email/password.

    On success, stores the same three ``st.session_state`` keys as
    :func:`sign_up`, and updates ``profiles.last_login`` for this user via a
    short-lived, per-call authenticated client (:func:`_touch_last_login`) —
    never the shared ``get_supabase_client()`` ``cache_resource`` instance.

    Raises ``AuthApiError`` on invalid credentials.
    """
    response = _scoped_client().auth.sign_in_with_password({"email": email, "password": password})
    st.session_state["access_token"] = response.session.access_token
    st.session_state["refresh_token"] = response.session.refresh_token
    st.session_state["logged_in"] = True
    _touch_last_login(response.session.access_token, response.user.id)
    return response


def sign_in_with_magic_link(email: str) -> None:
    """Send a passwordless magic-link sign-in email to ``email``.

    Session establishment happens when the user clicks the emailed link
    (handled by whatever page the redirect target renders) — this call only
    triggers the send and does not raise for a valid, existing email.
    """
    _scoped_client().auth.sign_in_with_otp({"email": email})


def require_auth():
    """Central auth gate. Call at the top of every auth-gated page.

    Reads the access token from ``st.session_state`` and re-verifies it
    server-side via ``get_user(token)`` — never the client-trusted,
    locally-cached ``get_session()`` accessor (D-04). If the access
    token is rejected but a ``refresh_token`` is present, attempts
    ``refresh_session()`` via a short-lived scoped client (never the shared
    ``get_supabase_client()`` — see module docstring) and retries
    ``get_user()`` once with the refreshed token before giving up. On any
    failure, clears the auth keys from ``st.session_state`` and halts
    rendering (``st.stop()``) so no gated content renders past this point.

    Returns the server-verified ``User`` object on success. When the caller
    is not authenticated, calls ``st.stop()`` and returns ``None`` — the
    explicit ``None`` return exists so this function is also testable
    outside a running Streamlit script context, where ``st.stop()`` is a
    no-op rather than halting execution.
    """
    token = st.session_state.get("access_token")
    if not token:
        st.stop()
        return None

    try:
        return get_supabase_client().auth.get_user(token).user
    except AuthApiError:
        pass

    refresh_token = st.session_state.get("refresh_token")
    if refresh_token:
        try:
            refreshed = _scoped_client().auth.refresh_session(refresh_token)
            st.session_state["access_token"] = refreshed.session.access_token
            st.session_state["refresh_token"] = refreshed.session.refresh_token
            return get_supabase_client().auth.get_user(refreshed.session.access_token).user
        except AuthApiError:
            pass

    st.session_state.clear()
    st.stop()
    return None


def sign_out() -> None:
    """Sign out the current session's user and clear its auth state.

    Clears only this session's ``st.session_state`` auth keys — never a
    shared/global object — and revokes the current session server-side via
    the shared, stateless client's ``admin.sign_out(access_token, scope)`` —
    a stateless call that takes the token explicitly rather than the
    stateful ``auth.sign_out()`` wrapper, which looks up the token via
    ``get_session()`` and would only work by relying on a session having
    been persisted onto the shared client (exactly what this module must
    never do; see module docstring).
    """
    access_token = st.session_state.get("access_token")
    try:
        if access_token:
            with suppress(AuthApiError):
                get_supabase_client().auth.admin.sign_out(access_token, "global")
    finally:
        st.session_state.pop("access_token", None)
        st.session_state.pop("refresh_token", None)
        st.session_state.pop("logged_in", None)


def _touch_last_login(access_token: str, user_id: str) -> None:
    """Update ``profiles.last_login`` for ``user_id`` via a short-lived client.

    Builds a fresh, uncached client (``create_client`` imported directly —
    never the shared ``get_supabase_client()`` ``cache_resource`` instance —
    same as :func:`_scoped_client`, kept as a direct call here since it also
    needs ``.postgrest.auth()``, not just ``.auth``) and attaches the
    just-authenticated user's JWT to it for this call only, so the write is
    scoped to this one request under RLS (``auth.uid() = user_id``) and the
    shared client stays exactly as stateless as
    ``src/data/supabase_client.py`` requires. The fresh client goes out of
    scope immediately after — it is never stored in ``st.session_state`` or
    any cached/global object.
    """
    scoped_client = create_client(get_config("SUPABASE_URL"), get_config("SUPABASE_ANON_KEY"))
    scoped_client.postgrest.auth(access_token)
    scoped_client.table("profiles").update(
        {"last_login": datetime.now(timezone.utc).isoformat()}
    ).eq("user_id", user_id).execute()
