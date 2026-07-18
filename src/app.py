"""App entrypoint.

Constructs ``st.navigation`` conditionally on
``st.session_state.get("logged_in")`` (Pattern 5, RESEARCH.md) so
auth-gated pages are entirely absent from navigation — not
visible-but-redirecting — until the user is logged in (D-03).
"""

import streamlit as st

from src.pages.home import render_home_page
from src.pages.login import render_login_page

login_page = st.Page(render_login_page, title="Log In", url_path="login")
home_page = st.Page(render_home_page, title="Home", url_path="home", default=True)

if st.session_state.get("logged_in"):
    pg = st.navigation({"Home": [home_page]})
else:
    pg = st.navigation([login_page])

pg.run()
