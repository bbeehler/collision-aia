"""Check and Declare, by AIA Canada. Entry point for Streamlit Community Cloud. Add ?lang=fr to open in French."""
import streamlit as st

from app.theme import LOGO_POSITIVE

st.set_page_config(page_title="Check and Declare | AIA Canada", page_icon=LOGO_POSITIVE, layout="centered")

from app import db, theme  # noqa: E402
from app.i18n import lang, t  # noqa: E402
from app.views import account, admin, badge_check, directory, facility, home, verification  # noqa: E402

theme.apply()
try:
    configured = bool(st.secrets.get("SUPABASE_URL")) and bool(st.secrets.get("SUPABASE_ANON_KEY"))
except Exception:
    configured = False
if not configured:
    st.error("Add SUPABASE_URL and SUPABASE_ANON_KEY to the app's secrets. See README.md, step 4.")
    st.stop()

lang()
db.restore_session()
signed_in = db.user() is not None
staff = signed_in and db.is_admin()

if signed_in and st.session_state.get("must_change_password"):
    st.navigation([st.Page(account.set_password, title=t("Choose your password"), icon=":material/key:",
                           url_path="set-password", default=True)], position="hidden").run()
    st.stop()

# Pages everyone can use, with or without an account
find_page = st.Page(directory.render, title=t("Find a shop"), icon=":material/storefront:", url_path="directory")
check_page = st.Page(badge_check.render, title=t("Check a badge"), icon=":material/verified:", url_path="check")
account_page = st.Page(account.render, title=t("Account") if signed_in else t("Sign in"), icon=":material/person:", url_path="account")

if staff:
    verify_page = st.Page(verification.render, title=t("Verification"), icon=":material/fact_check:", url_path="verification")
    facilities_page = st.Page(admin.facilities, title=t("Facilities"), icon=":material/store:", url_path="facilities")
    concerns_page = st.Page(admin.concerns, title=t("Concerns"), icon=":material/report:", url_path="concerns")
    dash_page = st.Page(lambda: admin.dashboard(verify_page, facilities_page, concerns_page), title=t("Dashboard"),
                        icon=":material/dashboard:", url_path="dashboard", default=True)
    admin_pages = [dash_page, verify_page, facilities_page, concerns_page]
    if db.is_super():
        admin_pages.append(st.Page(admin.staff, title=t("Staff"), icon=":material/group:", url_path="staff"))
    landing = dash_page
    sections = {t("Administration"): admin_pages, t("Public site"): [find_page, check_page], t("Account"): [account_page]}
elif signed_in:
    landing = st.Page(facility.render, title=t("My facility"), icon=":material/home_repair_service:", url_path="facility", default=True)
    sections = {t("My shop"): [landing], t("Public site"): [find_page, check_page], t("Account"): [account_page]}
else:
    landing = st.Page(lambda: home.render(find_page, check_page, account_page), title=t("Home"), icon=":material/home:",
                      url_path="home", default=True)
    sections = {"": [landing, find_page, check_page, account_page]}

nav = st.navigation(sections, position="top")
if signed_in and st.session_state.pop("goto_facility", False):
    st.switch_page(landing)
theme.language_switch()
nav.run()
theme.footer()
