import streamlit as st

from .. import db
from ..badge import badge_svg, show
from ..config import PROGRAMS, PROVINCES, program_name
from ..logic import fmt


def render():
    st.title("Facility directory")
    st.write("Collision repair facilities with an active AIA Canada badge.")
    st.caption("Requirements are self-declared by each facility. Listed credentials were confirmed by AIA Canada with the "
               "program administrator. AIA Canada has not inspected any facility or specific repair.")
    try:
        rows = db.directory()
    except Exception:
        st.error("The directory couldn't be loaded. Try again in a moment.")
        return

    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Search by name or city")
    prov = c2.selectbox("Province or territory", [""] + list(PROVINCES), format_func=lambda p: PROVINCES.get(p, "All"))
    cred = c3.selectbox("Credential", [""] + [p for p in PROGRAMS if p != "other"], format_func=lambda p: PROGRAMS[p][0] if p else "Any")

    def keep(r):
        text = f"{r['name']} {r.get('city') or ''}".lower()
        return (not q or q.lower() in text) and (not prov or r.get("province") == prov) and (not cred or cred in (r.get("credentials") or []))

    rows = [r for r in rows if keep(r)]
    if not rows:
        st.info("No facilities match. Clear a filter to see more.")
        return
    for r in rows:
        creds = [program_name(c) if c in PROGRAMS else c for c in r.get("credentials") or []]
        with st.container(border=True):
            st.markdown(f"**{r['name']}**")
            st.caption(", ".join(x for x in [r.get("street"), r.get("city"), PROVINCES.get(r.get("province"), "")] if x)
                       + (f". {r['phone']}" if r.get("phone") else ""))
            st.markdown(" ".join(f":green-background[{c}]" for c in creds))
            st.caption(f"Self-declared {fmt(r['declared_at'])}, valid until {fmt(r['expires_at'])}.")
            with st.expander("View badge"):
                show(st, badge_svg(r["name"], r.get("city"), r.get("province"), r["declared_at"], r["expires_at"], r["code"], creds))
