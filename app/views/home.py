import streamlit as st

from ..i18n import t
from ..theme import hero


def render(find_page, check_page, account_page):
    hero(t("Collision repair you can trust"),
         t("Find shops that meet AIA Canada's minimum standards for complete, safe and quality collision repairs."))
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown(f"#### {t('Looking for a repair shop?')}")
        st.write(t("Find shops with an active AIA Canada badge, see which manufacturer certifications AIA Canada has confirmed, or check that a badge is genuine."))
        st.page_link(find_page, label=t("Find a shop"), icon=":material/storefront:")
        st.page_link(check_page, label=t("Check a badge"), icon=":material/verified:")
    with c2.container(border=True):
        st.markdown(f"#### {t('Run a collision repair shop?')}")
        st.write(t("Check your shop against the minimum standards, list your certifications, and declare to earn your badge and a place in the directory."))
        st.page_link(account_page, label=t("Shop sign in"), icon=":material/login:")
    with c3.container(border=True):
        st.markdown(f"#### {t('AIA Canada staff')}")
        st.write(t("Review credentials, manage facilities and respond to consumer concerns."))
        st.page_link(account_page, label=t("Staff sign in"), icon=":material/badge:")
