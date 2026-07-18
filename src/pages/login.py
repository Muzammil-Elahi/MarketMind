"""Login / signup / magic-link page.

Renders the app's single unauthenticated entry point (D-03): email/password
log in, email/password create-account, and passwordless magic-link sign-in,
each in its own tab. No third-party/social-provider login is offered (D-01)
— only the two methods above.

Every submit path is wrapped in an ``st.form`` so native Streamlit
required-field validation blocks an empty submit before any auth call is
even attempted (UI-SPEC empty-state row).
"""

import streamlit as st
from supabase_auth.errors import AuthApiError

from src.auth.session import sign_in, sign_in_with_magic_link, sign_up

INVALID_CREDENTIALS_ERROR = (
    "We couldn't verify that email and password. Double-check them and try again."
)
MAGIC_LINK_FAILURE_ERROR = "We couldn't send your login link. Check your email address and try again."


def render_login_page() -> None:
    """Render the login/signup/magic-link page."""
    st.title("Popcorn Pilot")

    log_in_tab, create_account_tab, magic_link_tab = st.tabs(
        ["Log In", "Create Account", "Magic Link"]
    )

    with log_in_tab:
        with st.form("log_in_form"):
            email = st.text_input("Email", key="log_in_email")
            password = st.text_input("Password", type="password", key="log_in_password")
            submitted = st.form_submit_button("Log In")
        if submitted:
            try:
                sign_in(email, password)
                st.rerun()
            except AuthApiError:
                st.error(INVALID_CREDENTIALS_ERROR)

    with create_account_tab:
        with st.form("create_account_form"):
            email = st.text_input("Email", key="create_account_email")
            password = st.text_input(
                "Password", type="password", key="create_account_password"
            )
            submitted = st.form_submit_button("Create Account")
        if submitted:
            try:
                sign_up(email, password)
                st.rerun()
            except AuthApiError:
                # No separate duplicate-account copy exists in the
                # Copywriting Contract — reuse the invalid-credentials-style
                # error text for any signup failure, including a duplicate
                # email attempt.
                st.error(INVALID_CREDENTIALS_ERROR)

    with magic_link_tab:
        with st.form("magic_link_form"):
            email = st.text_input("Email", key="magic_link_email")
            submitted = st.form_submit_button("Send Magic Link")
        if submitted:
            try:
                sign_in_with_magic_link(email)
                st.info("Check your email for a login link.")
            except AuthApiError:
                st.error(MAGIC_LINK_FAILURE_ERROR)
