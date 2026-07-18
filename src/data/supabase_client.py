"""Shared, stateless Supabase client.

This module owns exactly one thing: a process-wide, `st.cache_resource`-shared
`supabase.Client` built from the anon/publishable key only.

Why this is safe to share across every user's session (and why it must stay
that way): the client returned here never has a signed-in session attached to
it. It is constructed once from ``SUPABASE_URL``/``SUPABASE_ANON_KEY`` — public,
non-identifying connection info — and reused as-is. Per-user identity (access
token, refresh token, user id) lives exclusively in ``st.session_state``,
which Streamlit already scopes to one browser session. ``src/auth/session.py``
is the only module that reads/writes those tokens, and it always passes them
explicitly into calls like ``.auth.get_user(token)`` rather than expecting
this cached client to already "be" a particular logged-in user.

Do NOT invoke any authenticating auth-module method (password sign-in,
sign-up, or magic-link sign-in) on the client returned by this module. Doing
so would bake one user's session onto a process-wide cached object — the
exact cross-user leak class this phase's threat model (T-01-01) exists to
prevent. See RESEARCH.md Pattern 2 / Pitfall 2.
"""

import streamlit as st
from supabase import Client, create_client

from src.config import get_config


@st.cache_resource
def get_supabase_client() -> Client:
    """Return the shared, stateless Supabase client.

    Cached via ``st.cache_resource`` because the client itself is a stateless
    connection (anon key only) — safe to reuse across every session. Calling
    this twice within the same process returns the identical object.
    """
    return create_client(
        get_config("SUPABASE_URL"),
        get_config("SUPABASE_ANON_KEY"),
    )
