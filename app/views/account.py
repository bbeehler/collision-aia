import streamlit as st

from .. import db
from ..i18n import t


def render():
    if db.user():
        st.title(t("Account"))
        st.write(t("Signed in as {email}.", email=db.user()["email"]))
        if db.is_super():
            st.caption(t("You are a super admin."))
        elif db.is_admin():
            st.caption(t("You have AIA Canada staff access."))
        with st.expander(t("Change password")):
            _password_form("change_pw")
        if st.button(t("Sign out")):
            db.sign_out()
            st.rerun()
        return

    st.title(t("Sign in"))
    st.write(t("For collision repair shops and AIA Canada staff. Looking for a repair shop? You do not need an account: use Find a shop."))
    t_in, t_up = st.tabs([t("Sign in"), t("Create an account")])
    with t_in:
        with st.form("sign_in"):
            email = st.text_input(t("Email"), autocomplete="email")
            pw = st.text_input(t("Password"), type="password", autocomplete="current-password")
            if st.form_submit_button(t("Sign in"), type="primary"):
                try:
                    db.sign_in(email.strip(), pw)
                    st.rerun()
                except Exception:
                    st.error(t("The email or password is incorrect, or the email address has not been confirmed yet."))
    with t_up:
        with st.form("sign_up"):
            email = st.text_input(t("Work email"), autocomplete="email")
            pw = st.text_input(t("Password"), type="password", help=t("At least eight characters"), autocomplete="new-password")
            pw2 = st.text_input(t("Confirm password"), type="password", autocomplete="new-password")
            if st.form_submit_button(t("Create an account"), type="primary"):
                if len(pw) < 8:
                    st.error(t("Use at least eight characters for your password."))
                elif pw != pw2:
                    st.error(t("The passwords do not match."))
                else:
                    try:
                        if db.sign_up(email.strip(), pw):
                            st.rerun()
                        st.success(t("Check your email to confirm your account, then sign in."))
                    except Exception as e:
                        st.error(t("The account could not be created. {detail}", detail=getattr(e, "message", "")))


def _password_form(key):
    with st.form(key, clear_on_submit=True):
        pw = st.text_input(t("New password"), type="password", help=t("At least eight characters"), autocomplete="new-password")
        pw2 = st.text_input(t("Confirm new password"), type="password", autocomplete="new-password")
        if st.form_submit_button(t("Save password"), type="primary"):
            if len(pw) < 8:
                st.error(t("Use at least eight characters for your password."))
            elif pw != pw2:
                st.error(t("The passwords do not match."))
            else:
                try:
                    db.change_password(pw)
                    st.session_state.goto_facility = True
                    st.rerun()
                except Exception as e:
                    st.error(t("The password could not be changed. {detail}", detail=getattr(e, "message", "")))


def set_password():
    """Shown instead of everything else when someone signs in with a temporary password."""
    st.title(t("Choose your password"))
    st.write(t("You signed in as {email} with a temporary password. Choose your own password to continue.", email=db.user()["email"]))
    _password_form("first_pw")
    if st.button(t("Sign out")):
        db.sign_out()
        st.rerun()
