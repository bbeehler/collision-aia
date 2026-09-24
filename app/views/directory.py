import streamlit as st

from .. import db
from ..badge import badge_svg, show
from ..config import PROGRAMS, PROVINCES, program_name
from ..logic import fmt


def _creds(r):
    return [program_name(c) if c in PROGRAMS else c for c in r.get("credentials") or []]


def render():
    try:
        rows = db.directory()
    except Exception:
        st.title("Find a shop")
        st.error("The directory couldn't be loaded. Try again in a moment.")
        return
    sel = st.session_state.get("dir_shop")
    row = next((r for r in rows if r["facility_id"] == sel), None) if sel else None
    if row:
        _detail(row)
        return

    st.title("Find a certified collision repair shop")
    st.write("Every shop listed here has declared that it meets AIA Canada's minimum requirements for collision repair, "
             "and AIA Canada has confirmed its manufacturer (OEM) and I-CAR credentials.")
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input("Name, city or postal code", placeholder="e.g. Orleans or K4A")
    prov = c2.selectbox("Province or territory", [""] + list(PROVINCES), format_func=lambda p: PROVINCES.get(p, "All"))
    cred = c3.selectbox("Certified for", [""] + [p for p in PROGRAMS if p != "other"], format_func=lambda p: PROGRAMS[p][0] if p else "Any")

    ql = "".join(q.lower().split())

    def keep(r):
        hay = "".join(f"{r['name']}{r.get('city') or ''}".lower().split())
        postal = "".join((r.get("postal") or "").lower().split())
        text_ok = not ql or ql in hay or (len(ql) >= 3 and postal.startswith(ql))
        return text_ok and (not prov or r.get("province") == prov) and (not cred or cred in (r.get("credentials") or []))

    found = [r for r in rows if keep(r)]
    st.caption(f"{len(found)} shop{'s' if len(found) != 1 else ''}")
    if not found:
        st.info("No shops match. Try a nearby city or clear a filter.")
    for r in found:
        with st.container(border=True):
            a, b = st.columns([4, 1], vertical_alignment="center")
            a.markdown(f"**{r['name']}**")
            a.caption(", ".join(x for x in [r.get("street"), r.get("city"), PROVINCES.get(r.get("province"), "")] if x))
            a.markdown(" ".join(f":green-background[{c}]" for c in _creds(r)))
            if b.button("View details", key=f"dir_{r['facility_id']}"):
                st.session_state.dir_shop = r["facility_id"]
                st.rerun()


def _detail(r):
    if st.button("Back to results"):
        st.session_state.pop("dir_shop", None)
        st.rerun()
    st.title(r["name"])
    st.write(", ".join(x for x in [r.get("street"), r.get("city"), PROVINCES.get(r.get("province"), ""), r.get("postal")] if x))
    c1, c2, _ = st.columns([1, 1, 2])
    if r.get("phone"):
        c1.markdown(f"**Phone** {r['phone']}")
    if r.get("website"):
        url = r["website"] if r["website"].startswith("http") else f"https://{r['website']}"
        c2.link_button("Visit website", url)

    st.success(f"**Active AIA Canada badge**, valid until {fmt(r['expires_at'])}.")
    creds = _creds(r)
    st.markdown("#### What this badge means")
    st.markdown(
        f"- **Minimum requirements: self-declared.** On {fmt(r['declared_at'])}, the shop declared that it meets every item "
        "in AIA Canada's Statement on minimum collision repair requirements, covering business practices, technician "
        "training, facility and equipment, and repair processes. AIA Canada has not inspected the shop.\n"
        "- **Credentials: confirmed by AIA Canada.** AIA Canada confirmed each credential below with the program that "
        "issues it, and re-checks them regularly.\n"
        "- **Renewed yearly.** The badge expires unless the shop renews its declaration, and it's removed if a "
        "requirement or credential stops being met.")
    st.markdown("#### Confirmed credentials")
    st.markdown(" ".join(f":green-background[{c}]" for c in creds) or "None listed.")
    st.caption("A manufacturer certification means the shop has the training, tools and equipment that manufacturer "
               "requires to repair its vehicles.")
    st.markdown("#### Badge")
    show(st, badge_svg(r["name"], r.get("city"), r.get("province"), r["declared_at"], r["expires_at"], r["code"], creds))
    st.caption(f"Badge ID {r['code']}. Anyone can confirm a badge on the Check a badge page.")

    with st.expander("Report a concern about this shop"):
        st.caption("Tell AIA Canada if something about this shop doesn't match its badge, for example a certification it "
                   "doesn't seem to hold. AIA Canada reviews every report. For a dispute about a specific repair, contact "
                   "the shop or your insurer first.")
        with st.form(f"concern_{r['facility_id']}", clear_on_submit=True):
            name = st.text_input("Your name (optional)")
            contact = st.text_input("Email or phone, if you'd like a reply (optional)")
            msg = st.text_area("What's the concern?", max_chars=4000)
            if st.form_submit_button("Send to AIA Canada", type="primary"):
                if len(msg.strip()) < 10:
                    st.error("Add a few more details so AIA Canada can look into it.")
                else:
                    try:
                        res = db.submit_concern(r["facility_id"], name, contact, msg)
                        if res == "ok":
                            st.success("Thanks. Your concern has been sent to AIA Canada.")
                        elif res == "busy":
                            st.error("We're receiving a lot of reports right now. Try again in an hour.")
                        else:
                            st.error("That couldn't be sent. Try again.")
                    except Exception:
                        st.error("That couldn't be sent. Try again.")
