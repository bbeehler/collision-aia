import streamlit as st

from .. import db
from ..config import PROGRAMS, PROVINCES, program_name
from ..logic import fmt


def render():
    st.title("Check a badge")
    st.write("Every AIA Canada badge carries a Declaration ID, like AIA-CD-7K2M9Q. Enter it to confirm the badge is "
             "genuine and still current.")
    with st.form("check_badge"):
        code = st.text_input("Declaration ID", value=st.query_params.get("code", ""), placeholder="AIA-CD-")
        submitted = st.form_submit_button("Check", type="primary")
    code = code.strip()
    if not (submitted or st.query_params.get("code")) or not code:
        return
    try:
        b = db.check_badge(code)
    except Exception:
        st.error("The check couldn't be completed. Try again in a moment.")
        return
    if not b:
        st.error(f"There's no AIA Canada badge with the ID {code.upper()}. Check the ID and try again. If a shop is "
                 "displaying this badge, you can let AIA Canada know through the shop's page in Find a shop, or contact AIA Canada.")
        return
    where = ", ".join(x for x in [b.get("city"), PROVINCES.get(b.get("province"), "")] if x)
    creds = [program_name(c) if c in PROGRAMS else c for c in b.get("credentials") or []]
    if b["status"] == "active":
        st.success(f"**Genuine and current.** This badge belongs to **{b['name']}** ({where}). It was declared "
                   f"{fmt(b['declared_at'])} and is valid until {fmt(b['expires_at'])}.")
        if creds:
            st.markdown("Credentials confirmed by AIA Canada: " + " ".join(f":green-background[{c}]" for c in creds))
    elif b["status"] == "expired":
        st.warning(f"**Expired.** This badge belonged to **{b['name']}** ({where}) and expired on {fmt(b['expires_at'])}. "
                   "The shop hasn't renewed its declaration.")
    elif b["status"] == "withdrawn":
        st.error(f"**No longer valid.** This badge for **{b['name']}** ({where}) was withdrawn on {fmt(b['withdrawn_at'])}.")
    else:
        st.warning(f"**Not active.** **{b['name']}** ({where}) has declared, but AIA Canada hasn't confirmed all of its "
                   "credentials, so the badge isn't active yet.")
