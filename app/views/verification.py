import requests
import streamlit as st

from .. import db
from ..config import PROGRAMS, PROVINCES, program_admin, program_name
from ..logic import STATUS, active_declaration, claim_state, fmt, status
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
        st.error("The verification page is for AIA Canada reviewers.")
        return
    st.title("Credential verification")
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
    m = st.columns(4)
    m[0].metric("Needs a reviewer", len(person))
    m[1].metric("Waiting for automated check", len(auto))
    m[2].metric("Couldn't confirm", sum(claim_state(c) == "not_found" for c in claims))
    m[3].metric("Badges active", badges)

    if st.secrets.get("GITHUB_TOKEN") and st.secrets.get("GITHUB_REPO"):
        if st.button("Run automated checks now"):
            try:
                ok = _dispatch_verifier()
                st.success("Automated checks started. Results appear here in a few minutes.") if ok else st.error("GitHub didn't accept the request. Check GITHUB_TOKEN and GITHUB_REPO.")
            except Exception as e:
                st.error(f"GitHub couldn't be reached. {err_text(e)}")
    st.caption("Certifications listed on CPN Auto Body Locator are checked automatically every hour. Anything the check can't "
               "confirm, and every other program, comes here. Confirmed credentials come back for re-check on schedule.")

    view = st.radio("Show", ["Needs a reviewer", "All open claims"], horizontal=True, label_visibility="collapsed")
    queue = person if view == "Needs a reviewer" else open_claims
    queue = sorted(queue, key=lambda c: (not bool(active_declaration(decls_by.get(c["facility_id"], []))), c.get("submitted_at") or ""))
    if not queue:
        st.info("Nothing is waiting for review.")
    for c in queue:
        f = facs.get(c["facility_id"])
        if f:
            _claim_card(c, f, bool(active_declaration(decls_by.get(f["id"], []))))

    st.markdown("#### All facilities")
    rows = []
    for fid, f in facs.items():
        cl = claims_by.get(fid, [])
        d = active_declaration(decls_by.get(fid, []))
        rows.append({"Facility": shop_name(f), "Location": ", ".join(x for x in [f.get("city"), f.get("province")] if x),
                     "Status": STATUS[status(f, cl, decls_by.get(fid, []))][0],
                     "Requirements yes": sum(v == "yes" for v in (f.get("answers") or {}).values()),
                     "Credentials confirmed": f"{sum(claim_state(x) == 'confirmed' for x in cl)} of {len(cl)}",
                     "Declared": fmt(d["declared_at"]) if d else ""})
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.info("No facilities yet.")


def _claim_card(c, f, declared):
    adm = program_admin(c["program"])
    state = claim_state(c)
    with st.container(border=True):
        a, b = st.columns([3, 2])
        addr = ", ".join(x for x in [f.get("street"), f.get("city"), f.get("province"), f.get("postal")] if x)
        a.markdown(f"**{shop_name(f)}**  \n{addr}" + (f"  \nPhone {f['phone']}" if f.get("phone") else ""))
        tags = [chip("Re-check due", "orange") if state == "recheck" else chip("Needs a reviewer", "orange") if c.get("status") == "review"
                else chip("New claim", "orange"), chip("Declared", "blue") if declared else chip("Not yet declared", "gray")]
        b.markdown(" ".join(tags))
        details = [f"Confirmed by {adm['name']}"]
        for k, lab in [("program_ref", "ID"), ("cert_number", "Certificate")]:
            if c.get(k):
                details.append(f"{lab} {c[k]}")
        if c.get("cert_expiry"):
            details.append(f"Expires {fmt(c['cert_expiry'])}")
        details.append(f"Submitted {fmt(c.get('submitted_at'))}")
        st.markdown(f"**{program_name(c)}**. " + ". ".join(details) + ".")
        if c.get("status") == "review" and c.get("note"):
            st.warning(f"Automated check: {c['note']}")
        st.caption(adm["how"].format(make=program_name(c), postal=f.get("postal") or "the shop's postal code"))
        if adm.get("lookup"):
            st.link_button(adm["lookup_label"], adm["lookup"])
        if c.get("last_auto_check_at") and st.toggle("Show the last automated check", key=f"run_{c['id']}"):
            run = db.latest_run(c["id"])
            if run:
                listing = run.get("matched_listing") or {}
                st.write(f"Ran {fmt(run['ran_at'])}. Result: {run['reason'].replace('_', ' ')}. Match score {run.get('match_score') or 0}.")
                if listing:
                    st.json({k: listing.get(k) for k in ["name", "address", "phones", "email", "brands"]}, expanded=False)
                for p in run.get("evidence_paths") or []:
                    url = db.evidence_url(p)
                    if url:
                        st.image(url, caption="Locator search as the check saw it")
        opts = SOURCES if _automated(c["program"]) else SOURCES[1:]
        with st.form(f"review_{c['id']}"):
            s1, s2 = st.columns([1, 2])
            src = s1.selectbox("Confirmed through", opts)
            note = s2.text_input("Note to the shop", placeholder="Required if you can't confirm")
            b1, b2, _ = st.columns([1, 1, 2])
            ok = b1.form_submit_button("Confirm", type="primary")
            nf = b2.form_submit_button("Couldn't confirm")
            if ok or nf:
                if nf and not note.strip():
                    st.error("Add a note telling the shop what couldn't be confirmed.")
                else:
                    try:
                        db.review_claim(c["id"], "confirmed" if ok else "not_found", src, note.strip())
                        db.log(f["id"], "claim_confirmed" if ok else "claim_not_found", c["program"])
                        flash(f"{program_name(c)} for {shop_name(f)} marked {'confirmed' if ok else 'not confirmed'}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"That didn't save. {err_text(e)}")
