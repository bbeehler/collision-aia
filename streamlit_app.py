"""Check and Declare: AIA Canada collision repair minimum requirements. Entry point for Streamlit Community Cloud."""
import streamlit as st

st.set_page_config(page_title="Check and Declare | AIA Canada", page_icon="🛠️", layout="centered")

from app import db  # noqa: E402
from app.views import account, directory, facility, verification  # noqa: E402

try:
    configured = bool(st.secrets.get("SUPABASE_URL")) and bool(st.secrets.get("SUPABASE_ANON_KEY"))
except Exception:
    configured = False
if not configured:
    st.error("Add SUPABASE_URL and SUPABASE_ANON_KEY to the app's secrets. See README.md, step 4.")
    st.stop()

db.restore_session()
signed_in = db.user() is not None

pages = []
facility_page = st.Page(facility.render, title="My facility", icon=":material/home_repair_service:", url_path="facility", default=True)
if signed_in:
    pages.append(facility_page)
    if db.is_admin():
        pages.append(st.Page(verification.render, title="Verification", icon=":material/fact_check:", url_path="verification"))
pages.append(st.Page(directory.render, title="Directory", icon=":material/storefront:", url_path="directory"))
pages.append(st.Page(account.render, title="Account" if signed_in else "Sign in", icon=":material/person:", url_path="account",
                     default=not signed_in))

with st.sidebar:
    st.markdown("**Check and Declare**")
    st.caption("AIA Canada Statement on minimum collision repair requirements")

nav = st.navigation(pages)
if signed_in and st.session_state.pop("goto_facility", False):
    st.switch_page(facility_page)
nav.run()
