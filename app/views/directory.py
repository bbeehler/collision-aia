import streamlit as st

from .. import db
from ..badge import badge_svg, show
from ..config import PROGRAMS, PROVINCES, program_name, province_name, statement_name
from ..i18n import t
from ..logic import fmt


def _creds(r):
    return [program_name(c) if c in PROGRAMS else c for c in r.get("credentials") or []]


def render():
    try:
        rows = db.directory()
    except Exception:
        st.title(t("Find a shop"))
        st.error(t("The directory could not be loaded. Try again in a moment."))
        return
    sel = st.session_state.get("dir_shop")
    row = next((r for r in rows if r["facility_id"] == sel), None) if sel else None
    if row:
        _detail(row)
        return

    st.title(t("Find a collision repair shop"))
    st.write(t("Every shop listed here has declared that it meets AIA Canada's minimum standards for collision repair, and AIA Canada has confirmed its manufacturer (OEM) and I-CAR® credentials."))
    c1, c2, c3 = st.columns([2, 1, 1])
    q = c1.text_input(t("Name, city or postal code"), placeholder=t("For example, Orleans or K4A"))
    prov = c2.selectbox(t("Province or territory"), [""] + PROVINCES, format_func=lambda p: province_name(p) if p else t("All"))
    cred = c3.selectbox(t("Certified for"), [""] + [p for p in PROGRAMS if p != "other"], format_func=lambda p: program_name(p) if p else t("Any"))

    ql = "".join(q.lower().split())

    def keep(r):
        hay = "".join(f"{r['name']}{r.get('city') or ''}".lower().split())
        postal = "".join((r.get("postal") or "").lower().split())
        text_ok = not ql or ql in hay or (len(ql) >= 3 and postal.startswith(ql))
        return text_ok and (not prov or r.get("province") == prov) and (not cred or cred in (r.get("credentials") or []))

    found = [r for r in rows if keep(r)]
    st.caption(t("{n} shops", n=len(found)) if len(found) != 1 else t("1 shop"))
    if not found:
        st.info(t("No shops match. Try a nearby city or clear a filter."))
    for r in found:
        with st.container(border=True):
            a, b = st.columns([4, 1], vertical_alignment="center")
            a.markdown(f"**{r['name']}**")
            a.caption(", ".join(x for x in [r.get("street"), r.get("city"), province_name(r.get("province"))] if x))
            a.markdown(" ".join(f":green-background[{c}]" for c in _creds(r)))
            if b.button(t("View details"), key=f"dir_{r['facility_id']}"):
                st.session_state.dir_shop = r["facility_id"]
                st.rerun()


def _detail(r):
    if st.button(t("Back to results")):
        st.session_state.pop("dir_shop", None)
        st.rerun()
    st.title(r["name"])
    st.write(", ".join(x for x in [r.get("street"), r.get("city"), province_name(r.get("province")), r.get("postal")] if x))
    c1, c2, _ = st.columns([2, 1, 1], vertical_alignment="center")
    if r.get("phone"):
        c1.markdown(f"**{t('Phone')}** {r['phone']}")
    if r.get("website"):
        url = r["website"] if r["website"].startswith("http") else f"https://{r['website']}"
        c2.link_button(t("Visit website"), url)

    st.success(t("**Active AIA Canada badge**, valid until {date}.", date=fmt(r["expires_at"])))
    creds = _creds(r)
    st.markdown(f"#### {t('What this badge means')}")
    st.markdown(
        "- " + t("**Minimum standards: self-declared.** On {date}, the shop declared that it meets every item in {statement}, covering business practices, technician training, facility and equipment, and repair processes. AIA Canada has not inspected the shop.",
                 date=fmt(r["declared_at"]), statement=statement_name()) + "\n"
        "- " + t("**Credentials: confirmed by AIA Canada.** AIA Canada confirmed each credential below with the program that issues it, and re-checks them regularly.") + "\n"
        "- " + t("**Renewed every year.** The badge expires unless the shop renews its declaration, and it is removed if a requirement or credential stops being met."))
    st.markdown(f"#### {t('Confirmed credentials')}")
    st.markdown(" ".join(f":green-background[{c}]" for c in creds) or t("None listed."))
    st.caption(t("A manufacturer certification means the shop has the training, tools and equipment that manufacturer requires to repair its vehicles."))
    st.markdown(f"#### {t('Badge')}")
    show(st, badge_svg(r["name"], r.get("city"), r.get("province"), r["declared_at"], r["expires_at"], r["code"], creds))
    st.caption(t("Badge ID {code}. Anyone can confirm a badge on the Check a badge page.", code=r["code"]))

    with st.expander(t("Report a concern about this shop")):
        st.caption(t("Tell AIA Canada if something about this shop does not match its badge, for example a certification it does not seem to hold. AIA Canada reviews every report. For a dispute about a specific repair, contact the shop or your insurer first."))
        with st.form(f"concern_{r['facility_id']}", clear_on_submit=True):
            name = st.text_input(t("Your name (optional)"))
            contact = st.text_input(t("Email or phone, if you would like a reply (optional)"))
            msg = st.text_area(t("What is the concern?"), max_chars=4000)
            if st.form_submit_button(t("Send to AIA Canada"), type="primary"):
                if len(msg.strip()) < 10:
                    st.error(t("Add a few more details so AIA Canada can look into it."))
                else:
                    try:
                        res = db.submit_concern(r["facility_id"], name, contact, msg)
                        if res == "ok":
                            st.success(t("Thank you. Your concern has been sent to AIA Canada."))
                        elif res == "busy":
                            st.error(t("AIA Canada is receiving a large number of reports right now. Try again in an hour."))
                        else:
                            st.error(t("Your concern could not be sent. Try again."))
                    except Exception:
                        st.error(t("Your concern could not be sent. Try again."))
