"""Placeholder home page.

Per CONTEXT.md's Phase Boundary, this is a placeholder only — no investor
profile, recommendation, or prediction content exists yet (that ships in
Phase 2+). ``require_auth()`` is called first, and only, per D-04 — no
inline auth logic is duplicated here.
"""

import streamlit as st

from src.auth.session import require_auth, sign_out


def render_home_page() -> None:
    """Render the require_auth()-gated placeholder home page."""
    require_auth()

    st.title("You're in")
    st.write(
        "This is your home base for Popcorn Pilot. Your investor profile and "
        "recommendations are coming in a future update — check back soon."
    )

    if st.button("Log Out"):
        sign_out()
        st.rerun()
