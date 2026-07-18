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

In addition to the ``st.warning`` copy above, the specific field(s) left
blank at the user's most recent submit are given a red border (the standard
web-forms "invalid field" pattern), via ``_highlight_empty_fields`` below.
Streamlit's own widgets have no built-in per-field error styling, so this is
done with scoped CSS injection keyed off each ``st.text_input``'s ``key=``
(Streamlit >=1.3x renders a ``st-key-<key>`` class on that widget's wrapper
element). Which field(s) were empty is tracked per tab in
``st.session_state`` so the highlight applies only to the offending
field(s) — not indiscriminately to every field on every rerun — and clears
once that field is filled in and the form is resubmitted.
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

# UI-SPEC Color contract's "Destructive" token (#DC2626) — reserved for
# error/invalid-state treatment; reused here for the empty-required-field
# red-border highlight rather than inventing a second red.
FIELD_ERROR_BORDER_COLOR = "#DC2626"


def _highlight_empty_fields(*keys: str | None) -> None:
    """Render CSS that puts a red border on the given keyed text input(s).

    ``keys`` may contain ``None`` entries (a field that was *not* left blank
    at the last submit) — these are filtered out, so passing no active keys
    is a no-op and renders nothing.

    Streamlit gives every keyed widget's wrapper element an
    ``st-key-<key>`` CSS class, which lets this scope the red border to
    exactly the field(s) named — never to every ``st.text_input`` on the
    page.
    """
    active_keys = [key for key in keys if key]
    if not active_keys:
        return
    selector = ", ".join(f'div.st-key-{key} input' for key in active_keys)
    st.markdown(
        f"<style>{selector} {{ border: 1px solid {FIELD_ERROR_BORDER_COLOR} "
        "!important; border-radius: 0.5rem; }}</style>",
        unsafe_allow_html=True,
    )


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
            st.session_state["log_in_email_error"] = not email.strip()
            st.session_state["log_in_password_error"] = not password.strip()
        if submitted and email.strip() and password.strip():
            try:
                sign_in(email, password)
                st.rerun()
            except AuthApiError:
                st.error(INVALID_CREDENTIALS_ERROR)
        elif submitted:
            st.warning(EMPTY_EMAIL_AND_PASSWORD_WARNING)
        _highlight_empty_fields(
            "log_in_email" if st.session_state.get("log_in_email_error") else None,
            "log_in_password" if st.session_state.get("log_in_password_error") else None,
        )

    with create_account_tab:
        with st.form("create_account_form"):
            email = st.text_input("Email", key="create_account_email")
            password = st.text_input(
                "Password", type="password", key="create_account_password"
            )
            submitted = st.form_submit_button("Create Account")
        if submitted:
            st.session_state["create_account_email_error"] = not email.strip()
            st.session_state["create_account_password_error"] = not password.strip()
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
        _highlight_empty_fields(
            "create_account_email" if st.session_state.get("create_account_email_error") else None,
            "create_account_password" if st.session_state.get("create_account_password_error") else None,
        )

    with magic_link_tab:
        with st.form("magic_link_form"):
            email = st.text_input("Email", key="magic_link_email")
            submitted = st.form_submit_button("Send Magic Link")
        if submitted:
            st.session_state["magic_link_email_error"] = not email.strip()
        if submitted and email.strip():
            try:
                sign_in_with_magic_link(email)
                st.info("Check your email for a login link.")
            except AuthApiError:
                st.error(MAGIC_LINK_FAILURE_ERROR)
        elif submitted:
            st.warning(EMPTY_EMAIL_WARNING)
        _highlight_empty_fields(
            "magic_link_email" if st.session_state.get("magic_link_email_error") else None
        )
