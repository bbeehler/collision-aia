from urllib.parse import urlencode

import requests
import streamlit as st

from .. import db
from ..config import PROGRAMS, admin_name, program_admin, program_name
from ..i18n import t
from ..logic import active_declaration, claim_state, fmt, status, status_label
from .common import chip, err_text, flash, shop_name, show_flash

SOURCES = ["CPN Auto Body Locator listing", "Program administrator confirmation", "Certificate reviewed with the manufacturer"]


def _automated(pid):
    return PROGRAMS.get(pid, (pid, "none"))[1] == "oec"


def _needs_person(c):
    state = claim_state(c)
    if c.get("status") == "review":
        return True
    return state in ("pending", "recheck") and not _automated(c["program"])


def _dispatch_verifier():
    tok, repo = st.secrets.get("GITHUB_TOKEN"), st.secrets.get("GITHUB_REPO")
    r = requests.post(f"https://api.github.com/repos/{repo}/actions/workflows/verify.yml/dispatches",
                      headers={"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"},
                      json={"ref": st.secrets.get("GITHUB_BRANCH", "main")}, timeout=15)
    return r.status_code == 204


def render():
    if not db.is_admin():
        st.error(t("This page is for AIA Canada staff."))
        return
    st.title(t("Credential verification"))
    show_flash()
    facs = {f["id"]: f for f in db.all_facilities()}
    claims = db.all_claims()
    decls = db.all_declarations()
    claims_by, decls_by = {}, {}
    for c in claims:
        claims_by.setdefault(c["facility_id"], []).append(c)
    for d in decls:
        decls_by.setdefault(d["facility_id"], []).append(d)

    open_claims = [c for c in claims if claim_state(c) in ("pending", "review", "recheck")]
    person = [c for c in open_claims if _needs_person(c)]
    auto = [c for c in open_claims if not _needs_person(c)]
    badges = sum(status(f, claims_by.get(fid, []), decls_by.get(fid, [])) == "badge" for fid, f in facs.items())
    m1, m2 = st.columns(2)
    m1.metric(t("Needs a reviewer"), len(person))
    m2.metric(t("Waiting for automated check"), len(auto))
    m3, m4 = st.columns(2)
    m3.metric(t("Could not confirm"), sum(claim_state(c) == "not_found" for c in claims))
    m4.metric(t("Badges active"), badges)

    if st.secrets.get("GITHUB_TOKEN") and st.secrets.get("GITHUB_REPO"):
        if st.button(t("Run automated checks now")):
            try:
                if _dispatch_verifier():
                    st.success(t("Automated checks started. Results appear here in a few minutes."))
                else:
                    st.error(t("GitHub did not accept the request. Check GITHUB_TOKEN and GITHUB_REPO."))
            except Exception as e:
                st.error(t("GitHub could not be reached. {detail}", detail=err_text(e)))
    st.caption(t("Certifications listed on CPN Auto Body Locator are checked automatically every hour. Anything the check cannot confirm, and every other program, comes here. Confirmed credentials come back for re-check on schedule."))

    views = ["Needs a reviewer", "All open claims"]
    view = st.radio(t("Show"), views, format_func=t, horizontal=True, label_visibility="collapsed")
    queue = person if view == views[0] else open_claims
    queue = sorted(queue, key=lambda c: (not bool(active_declaration(decls_by.get(c["facility_id"], []))), c.get("submitted_at") or ""))
    if not queue:
        st.info(t("Nothing is waiting for review."))
    for c in queue:
        f = facs.get(c["facility_id"])
        if f:
            _claim_card(c, f, bool(active_declaration(decls_by.get(f["id"], []))))

    st.markdown(f"#### {t('All facilities')}")
    rows = []
    for fid, f in facs.items():
        cl = claims_by.get(fid, [])
        d = active_declaration(decls_by.get(fid, []))
        rows.append({t("Facility"): shop_name(f), t("Location"): ", ".join(x for x in [f.get("city"), f.get("province")] if x),
                     t("Status"): status_label(status(f, cl, decls_by.get(fid, [])))[0],
                     t("Requirements yes"): sum(v == "yes" for v in (f.get("answers") or {}).values()),
                     t("Credentials confirmed"): t("{a} of {b}", a=sum(claim_state(x) == "confirmed" for x in cl), b=len(cl)),
                     t("Declared"): fmt(d["declared_at"]) if d else ""})
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info(t("No facilities yet."))


def _claim_card(c, f, declared):
    adm = program_admin(c["program"])
    state = claim_state(c)
    with st.container(border=True):
        a, b = st.columns([3, 2])
        addr = ", ".join(x for x in [f.get("street"), f.get("city"), f.get("province"), f.get("postal")] if x)
        a.markdown(f"**{shop_name(f)}**  \n{addr}" + (f"  \n{t('Phone')} {f['phone']}" if f.get("phone") else ""))
        tags = [chip(t("Re-check due"), "blue") if state == "recheck" else chip(t("Needs a reviewer"), "red") if c.get("status") == "review"
                else chip(t("New claim"), "blue"), chip(t("Declared"), "green") if declared else chip(t("Not yet declared"), "gray")]
        b.markdown(" ".join(tags))
        details = [t("Confirmed by {admin}", admin=admin_name(c["program"]))]
        if c.get("program_ref"):
            details.append(t("ID {ref}", ref=c["program_ref"]))
        if c.get("cert_number"):
            details.append(t("Certificate {number}", number=c["cert_number"]))
        if c.get("cert_expiry"):
            details.append(t("Expires {date}", date=fmt(c["cert_expiry"])))
        details.append(t("Submitted {date}", date=fmt(c.get("submitted_at"))))
        st.markdown(f"**{program_name(c)}**. " + ". ".join(details) + ".")
        if c.get("status") == "review" and c.get("note"):
            st.warning(t("Automated check: {note}", note=c["note"]))
        st.caption(t(adm["how"], make=program_name(c), postal=f.get("postal") or t("the shop's postal code")))
        if adm.get("lookup"):
            url = adm["lookup"]
            if _automated(c["program"]) and f.get("postal"):
                pc = "".join(f["postal"].split()).upper()
                url = "https://autobodylocator.ca/search?" + urlencode({
                    "search": f"{pc[:3]} {pc[3:]}" if len(pc) == 6 else pc,
                    "radius": "25", "type": "canada", "country": "CA", "lang": "en"})
            st.link_button(t("Search the locator near {postal}", postal=f["postal"]) if url != adm["lookup"] else t(adm["lookup_label"]), url)
            if _automated(c["program"]) and f.get("locator_url"):
                st.link_button(t("Open the shop's locator profile"), f["locator_url"])
        if c.get("last_auto_check_at") and st.toggle(t("Show the last automated check"), key=f"run_{c['id']}"):
            run = db.latest_run(c["id"])
            if run:
                listing = run.get("matched_listing") or {}
                st.write(t("Ran on {date}. Result: {reason}. Match score {score}.", date=fmt(run["ran_at"]),
                           reason=run["reason"].replace("_", " "), score=run.get("match_score") or 0))
                if listing:
                    st.json({k: listing.get(k) for k in ["name", "address", "phones", "email", "brands"]}, expanded=False)
                for p in run.get("evidence_paths") or []:
                    url = db.evidence_url(p)
                    if url:
                        st.image(url, caption=t("The locator search as the check saw it"))
        opts = SOURCES if _automated(c["program"]) else SOURCES[1:]
        with st.form(f"review_{c['id']}"):
            s1, s2 = st.columns([1, 2])
            src = s1.selectbox(t("Confirmed through"), opts, format_func=t)
            note = s2.text_input(t("Note to the shop"), placeholder=t("Required if you cannot confirm"))
            b1, b2, _ = st.columns([1, 1, 2])
            ok = b1.form_submit_button(t("Confirm"), type="primary")
            nf = b2.form_submit_button(t("Could not confirm"))
            if ok or nf:
                if nf and not note.strip():
                    st.error(t("Add a note telling the shop what could not be confirmed."))
                else:
                    try:
                        db.review_claim(c["id"], "confirmed" if ok else "not_found", src, note.strip())
                        db.log(f["id"], "claim_confirmed" if ok else "claim_not_found", c["program"])
                        flash(t("{program} for {shop} confirmed.", program=program_name(c), shop=shop_name(f)) if ok else
                              t("{program} for {shop} marked as not confirmed.", program=program_name(c), shop=shop_name(f)))
                        st.rerun()
                    except Exception as e:
                        st.error(t("That change was not saved. {detail}", detail=err_text(e)))
