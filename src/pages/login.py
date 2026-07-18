"""Login / signup / magic-link page.

Renders the app's single unauthenticated entry point (D-03): email/password
log in, email/password create-account, and passwordless magic-link sign-in,
each in its own tab. No third-party/social-provider login is offered (D-01)
— only the two methods above.

Every submit path is wrapped in an ``st.form``. Streamlit's ``st.form``/
``st.text_input`` provide no built-in required-field blocking (unlike HTML5
``required`` inputs) — an empty ``st.form_submit_button`` press still
submits. Each handler below therefore guards explicitly: if a required field
is blank (or whitespace-only), the handler renders a plain ``st.warning``
telling the user which field(s) to fill in and returns before calling into
``src.auth.session`` at all — so no auth call is ever made with empty
credentials, and the user is never left without feedback (UI-SPEC empty-state
row; the "no custom empty-state copy needed" assumption at UI-SPEC line 109
does not hold in practice, since Streamlit has no native required-field
blocking or visual cue).
"""

import streamlit as st
from supabase_auth.errors import AuthApiError

from src.auth.session import sign_in, sign_in_with_magic_link, sign_up

INVALID_CREDENTIALS_ERROR = (
    "We couldn't verify that email and password. Double-check them and try again."
)
MAGIC_LINK_FAILURE_ERROR = "We couldn't send your login link. Check your email address and try again."

# Empty-required-field validation copy. Streamlit's st.form/st.text_input have no
# built-in required-field blocking (see module docstring) — these messages fill that
# gap. They are distinct from INVALID_CREDENTIALS_ERROR/MAGIC_LINK_FAILURE_ERROR,
# which are reserved for actual failed auth attempts against non-empty credentials.
EMPTY_EMAIL_AND_PASSWORD_WARNING = "Please enter both your email and password."
EMPTY_EMAIL_WARNING = "Please enter an email address."


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
        if submitted and email.strip() and password.strip():
            try:
                sign_in(email, password)
                st.rerun()
            except AuthApiError:
                st.error(INVALID_CREDENTIALS_ERROR)
        elif submitted:
            st.warning(EMPTY_EMAIL_AND_PASSWORD_WARNING)

    with create_account_tab:
        with st.form("create_account_form"):
            email = st.text_input("Email", key="create_account_email")
            password = st.text_input(
                "Password", type="password", key="create_account_password"
            )
            submitted = st.form_submit_button("Create Account")
        if submitted and email.strip() and password.strip():
            try:
                sign_up(email, password)
                st.rerun()
            except AuthApiError:
                # No separate duplicate-account copy exists in the
                # Copywriting Contract — reuse the invalid-credentials-style
                # error text for any signup failure, including a duplicate
                # email attempt.
                st.error(INVALID_CREDENTIALS_ERROR)
        elif submitted:
            st.warning(EMPTY_EMAIL_AND_PASSWORD_WARNING)

    with magic_link_tab:
        with st.form("magic_link_form"):
            email = st.text_input("Email", key="magic_link_email")
            submitted = st.form_submit_button("Send Magic Link")
        if submitted and email.strip():
            try:
                sign_in_with_magic_link(email)
                st.info("Check your email for a login link.")
            except AuthApiError:
                st.error(MAGIC_LINK_FAILURE_ERROR)
        elif submitted:
            st.warning(EMPTY_EMAIL_WARNING)
