"""AppTest target script for tests/test_auth_isolation.py.

`src/pages/home.py` defines `render_home_page()` as a plain function
(Streamlit's function-based `st.Page` pattern, per `src/app.py`) with no
top-level script execution -- `AppTest.from_file()` needs an actual script
that runs statements, so this thin wrapper is that script (per the plan's
interfaces note). It performs no auth logic of its own: it calls the exact
same `require_auth()` the real app calls -- once directly, to capture the
resolved identity for the isolation test to assert on (there is no other way
to observe what a script-level AppTest run resolved, since the home page
itself never displays the user's id/email), and once more inside
`render_home_page()` (proving the real page's own auth gate also resolves
correctly) -- and records the result into `st.session_state`.
"""

import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import streamlit as st  # noqa: E402

from src.auth.session import require_auth  # noqa: E402
from src.pages.home import render_home_page  # noqa: E402

_resolved_user = require_auth()
st.session_state["_resolved_user_id"] = _resolved_user.id if _resolved_user else None
st.session_state["_resolved_user_email"] = _resolved_user.email if _resolved_user else None

render_home_page()
