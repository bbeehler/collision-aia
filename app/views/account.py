import streamlit as st

from .. import db


def render():
    if db.user():
        st.title("Account")
        st.write(f"Signed in as {db.user()['email']}.")
        if db.is_admin():
            st.caption("You have reviewer access to the Verification page.")
        if st.button("Sign out"):
            db.sign_out()
            st.rerun()
        return

    st.title("Sign in")
    st.write("For collision repair shops and AIA Canada staff. Looking for a repair shop? You don't need an account: "
             "use Find a shop.")
    t_in, t_up = st.tabs(["Sign in", "Create account"])
    with t_in:
        with st.form("sign_in"):
            email = st.text_input("Email", autocomplete="email")
            pw = st.text_input("Password", type="password", autocomplete="current-password")
            if st.form_submit_button("Sign in", type="primary"):
                try:
                    db.sign_in(email.strip(), pw)
                    st.rerun()
                except Exception:
                    st.error("Email or password is incorrect, or the email address hasn't been confirmed yet.")
    with t_up:
        with st.form("sign_up"):
            email = st.text_input("Work email", autocomplete="email")
            pw = st.text_input("Password", type="password", help="At least 8 characters", autocomplete="new-password")
            pw2 = st.text_input("Confirm password", type="password", autocomplete="new-password")
            if st.form_submit_button("Create account", type="primary"):
                if len(pw) < 8:
                    st.error("Use at least 8 characters for your password.")
                elif pw != pw2:
                    st.error("The passwords don't match.")
                else:
                    try:
                        if db.sign_up(email.strip(), pw):
                            st.rerun()
                        st.success("Check your email to confirm your account, then sign in.")
                    except Exception as e:
                        st.error(f"The account couldn't be created. {getattr(e, 'message', '')}")
