"""App entrypoint.

Constructs ``st.navigation`` conditionally on
``st.session_state.get("logged_in")`` (Pattern 5, RESEARCH.md) so
auth-gated pages are entirely absent from navigation — not
visible-but-redirecting — until the user is logged in (D-03).

``streamlit run src/app.py`` inserts this script's own directory
(``src/``) as ``sys.path[0]``, not the repo root, so the ``src.*``
absolute imports below would otherwise fail with
``ModuleNotFoundError: No module named 'src'``. Insert the repo root
onto ``sys.path`` first so ``src`` itself is importable as a package,
matching pytest's ``pythonpath = ["."]`` behavior (pyproject.toml).
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st  # noqa: E402

from src.pages.home import render_home_page  # noqa: E402
from src.pages.login import render_login_page  # noqa: E402
from src.pages.profile import render_profile_page  # noqa: E402

login_page = st.Page(render_login_page, title="Log In", url_path="login")
home_page = st.Page(render_home_page, title="Home", url_path="home", default=True)
profile_page = st.Page(render_profile_page, title="Investor Profile", url_path="profile")

if st.session_state.get("logged_in"):
    pg = st.navigation({"Home": [home_page], "Profile": [profile_page]})
else:
    pg = st.navigation([login_page])

pg.run()
