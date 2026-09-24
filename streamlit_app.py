"""Check and Declare: AIA Canada collision repair minimum requirements. Entry point for Streamlit Community Cloud."""
import streamlit as st

st.set_page_config(page_title="Check and Declare | AIA Canada", page_icon="🛠️", layout="centered")

from app import db  # noqa: E402
from app.views import account, admin, badge_check, directory, facility, home, verification  # noqa: E402

try:
    configured = bool(st.secrets.get("SUPABASE_URL")) and bool(st.secrets.get("SUPABASE_ANON_KEY"))
except Exception:
    configured = False
if not configured:
    st.error("Add SUPABASE_URL and SUPABASE_ANON_KEY to the app's secrets. See README.md, step 4.")
    st.stop()

db.restore_session()
signed_in = db.user() is not None
staff = signed_in and db.is_admin()

# Pages everyone can use, with or without an account
find_page = st.Page(directory.render, title="Find a shop", icon=":material/storefront:", url_path="directory")
check_page = st.Page(badge_check.render, title="Check a badge", icon=":material/verified:", url_path="check")
account_page = st.Page(account.render, title="Account" if signed_in else "Sign in", icon=":material/person:", url_path="account")

if staff:
    verify_page = st.Page(verification.render, title="Verification", icon=":material/fact_check:", url_path="verification")
    facilities_page = st.Page(admin.facilities, title="Facilities", icon=":material/store:", url_path="facilities")
    concerns_page = st.Page(admin.concerns, title="Concerns", icon=":material/report:", url_path="concerns")
    dash_page = st.Page(lambda: admin.dashboard(verify_page, facilities_page, concerns_page), title="Dashboard",
                        icon=":material/dashboard:", url_path="dashboard", default=True)
    reviewers_page = st.Page(admin.reviewers, title="Reviewers", icon=":material/group:", url_path="reviewers")
    landing = dash_page
    sections = {"Administration": [dash_page, verify_page, facilities_page, concerns_page, reviewers_page],
                "Public site": [find_page, check_page], "Account": [account_page]}
elif signed_in:
    landing = st.Page(facility.render, title="My facility", icon=":material/home_repair_service:", url_path="facility", default=True)
    sections = {"My shop": [landing], "Public site": [find_page, check_page], "Account": [account_page]}
else:
    landing = st.Page(lambda: home.render(find_page, check_page, account_page), title="Home", icon=":material/home:",
                      url_path="home", default=True)
    sections = {"": [landing, find_page, check_page], "Shops and staff": [account_page]}

with st.sidebar:
    st.markdown("**Check and Declare**")
    st.caption("AIA Canada Statement on minimum collision repair requirements")
    if signed_in:
        st.caption(f"Signed in as {db.user()['email']}" + (" (AIA Canada staff)" if staff else ""))

nav = st.navigation(sections)
if signed_in and st.session_state.pop("goto_facility", False):
    st.switch_page(landing)
nav.run()
