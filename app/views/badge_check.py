import streamlit as st

from .. import db
from ..config import PROGRAMS, program_name, province_name
from ..i18n import t
from ..logic import fmt


def render():
    st.title(t("Check a badge"))
    st.write(t("Every AIA Canada badge carries a Declaration ID, such as AIA-CD-7K2M9Q. Enter it to confirm the badge is genuine and current."))
    with st.form("check_badge"):
        code = st.text_input(t("Declaration ID"), value=st.query_params.get("code", ""), placeholder="AIA-CD-")
        submitted = st.form_submit_button(t("Check"), type="primary")
    code = code.strip()
    if not (submitted or st.query_params.get("code")) or not code:
        return
    try:
        b = db.check_badge(code)
    except Exception:
        st.error(t("The check could not be completed. Try again in a moment."))
        return
    if not b:
        st.error(t("There is no AIA Canada badge with the ID {code}. Check the ID and try again. If a shop is displaying this badge, let AIA Canada know through the shop's page in Find a shop, or contact AIA Canada.", code=code.upper()))
        return
    where = ", ".join(x for x in [b.get("city"), province_name(b.get("province"))] if x)
    creds = [program_name(c) if c in PROGRAMS else c for c in b.get("credentials") or []]
    if b["status"] == "active":
        st.success(t("**Genuine and current.** This badge belongs to **{name}** ({where}). It was declared on {declared} and is valid until {expires}.",
                     name=b["name"], where=where, declared=fmt(b["declared_at"]), expires=fmt(b["expires_at"])))
        if creds:
            st.markdown(t("Credentials confirmed by AIA Canada:") + " " + " ".join(f":green-background[{c}]" for c in creds))
    elif b["status"] == "expired":
        st.warning(t("**Expired.** This badge belonged to **{name}** ({where}) and expired on {date}. The shop has not renewed its declaration.",
                     name=b["name"], where=where, date=fmt(b["expires_at"])))
    elif b["status"] == "withdrawn":
        st.error(t("**No longer valid.** This badge for **{name}** ({where}) was withdrawn on {date}.",
                   name=b["name"], where=where, date=fmt(b["withdrawn_at"])))
    else:
        st.warning(t("**Not active.** **{name}** ({where}) has declared, but AIA Canada has not confirmed all of its credentials, so the badge is not active yet.",
                     name=b["name"], where=where))
