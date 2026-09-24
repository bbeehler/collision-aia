import streamlit as st


def render(find_page, check_page, account_page):
    st.title("Check and Declare")
    st.write("AIA Canada's program for collision repair shops that meet the industry's minimum requirements for safe, "
             "quality repairs.")
    c1, c2, c3 = st.columns(3)
    with c1.container(border=True):
        st.markdown("**Looking for a repair shop?**")
        st.caption("Find shops with an active AIA Canada badge, see which manufacturer certifications AIA Canada has "
                   "confirmed, or check that a badge is genuine.")
        st.page_link(find_page, label="Find a shop", icon=":material/storefront:")
        st.page_link(check_page, label="Check a badge", icon=":material/verified:")
    with c2.container(border=True):
        st.markdown("**Run a collision repair shop?**")
        st.caption("Check your shop against the minimum requirements, list your certifications, and declare to earn "
                   "your badge and a place in the directory.")
        st.page_link(account_page, label="Sign in or create an account", icon=":material/login:")
    with c3.container(border=True):
        st.markdown("**AIA Canada staff**")
        st.caption("Review credentials, manage facilities and respond to consumer concerns.")
        st.page_link(account_page, label="Staff sign in", icon=":material/badge:")
