"""Shared persistent educational-use disclaimer banner.

Per STATE.md's decision, the disclaimer UI component is introduced as
early as Phase 3 (this plan) and consolidated/audited for non-directive
language in Phase 6. Both `src/pages/recommendations.py` and
`src/pages/search.py` (Plans 06/07) call `render_disclaimer_banner()`
directly rather than hardcoding their own copy of the string, so there is
exactly one call site per page for Phase 6's consolidation audit to find.
"""

import streamlit as st

DISCLAIMER_TEXT = (
    "For informational and educational purposes only — not financial "
    "advice. Scores and rankings are not personalized recommendations, "
    "and past performance does not predict future results."
)


def render_disclaimer_banner() -> None:
    """Render the persistent, non-dismissible educational-use disclaimer
    banner inside a bordered container (Secondary/#F0F2F6 card-surface
    treatment per 03-UI-SPEC.md)."""
    with st.container(border=True):
        st.caption(DISCLAIMER_TEXT)
