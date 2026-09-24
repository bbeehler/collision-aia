from collections import Counter

import streamlit as st

from .. import db
from ..config import ANSWERS, PROVINCES, REQS, program_admin, program_name
from ..logic import CLAIM_LABEL, STATUS, active_declaration, claim_state, fmt, req_counts, status
from .common import chip, err_text, flash, shop_name, show_flash


def _guard():
    if not db.is_admin():
        st.error("This page is for AIA Canada staff.")
        return False
    return True


def _load():
    facs = db.all_facilities()
    claims, decls = {}, {}
    for c in db.all_claims():
        claims.setdefault(c["facility_id"], []).append(c)
    for d in db.all_declarations():
        decls.setdefault(d["facility_id"], []).append(d)
    return facs, claims, decls


# ---------------------------------------------------------------- dashboard
def dashboard(verification_page, facilities_page, concerns_page):
    if not _guard():
        return
    st.title("Dashboard")
    show_flash()
    facs, claims, decls = _load()
    st_by = {f["id"]: status(f, claims.get(f["id"], []), decls.get(f["id"], [])) for f in facs}
    counts = Counter(st_by.values())
    all_claims = [c for cl in claims.values() for c in cl]
    needs_person = [c for c in all_claims if c.get("status") == "review" or
                    (claim_state(c) in ("pending", "recheck") and program_admin(c["program"])["name"] != "OEC Certified Collision Care")]
    try:
        new_concerns = sum(c["status"] == "new" for c in db.concerns())
    except Exception:
        new_concerns = 0

    m = st.columns(4)
    m[0].metric("Badges active", counts.get("badge", 0))
    m[1].metric("Declared, awaiting credentials", counts.get("verifying", 0) + counts.get("action", 0))
    m[2].metric("Claims needing a reviewer", len(needs_person))
    m[3].metric("New concerns", new_concerns)
    c1, c2, c3 = st.columns(3)
    c1.page_link(verification_page, label="Review credentials", icon=":material/fact_check:")
    c2.page_link(facilities_page, label="All facilities", icon=":material/store:")
    c3.page_link(concerns_page, label="Consumer concerns", icon=":material/report:")

    st.markdown("#### Facilities by status")
    st.dataframe([{"Status": STATUS[k][0], "Facilities": counts.get(k, 0)} for k in STATUS], hide_index=True)
    st.markdown("#### Active badges by province")
    prov = Counter(f.get("province") for f in facs if st_by[f["id"]] == "badge")
    rows = [{"Province or territory": PROVINCES[p], "Badges": prov[p]} for p in PROVINCES if prov.get(p)]
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.caption("No active badges yet.")


# ---------------------------------------------------------------- facilities
def facilities():
    if not _guard():
        return
    st.title("Facilities")
    show_flash()
    facs, claims, decls = _load()
    if not facs:
        st.info("No facilities yet.")
        return
    c1, c2 = st.columns([2, 1])
    q = c1.text_input("Search by name, city or postal code")
    stat = c2.selectbox("Status", [""] + list(STATUS), format_func=lambda k: STATUS[k][0] if k else "All")
    ql = q.lower().strip()
    rows = []
    for f in facs:
        k = status(f, claims.get(f["id"], []), decls.get(f["id"], []))
        text = f"{shop_name(f)} {f.get('legal_name')} {f.get('city') or ''} {f.get('postal') or ''}".lower()
        if (ql and ql not in text) or (stat and k != stat):
            continue
        rows.append((f, k))
    st.dataframe([{"Facility": shop_name(f), "Location": ", ".join(x for x in [f.get("city"), f.get("province")] if x),
                   "Status": STATUS[k][0], "Requirements yes": req_counts(f.get("answers"))["yes"],
                   "Credentials confirmed": f"{sum(claim_state(c) == 'confirmed' for c in claims.get(f['id'], []))} of {len(claims.get(f['id'], []))}"}
                  for f, k in rows], hide_index=True)
    if not rows:
        return
    ids = [f["id"] for f, _ in rows]
    fid = st.selectbox("Open a facility", ids, format_func=lambda i: shop_name(next(f for f, _ in rows if f["id"] == i)))
    f = next(x for x, _ in rows if x["id"] == fid)
    _facility_detail(f, claims.get(fid, []), decls.get(fid, []))


def _facility_detail(f, claims, decls):
    k = status(f, claims, decls)
    st.markdown(f"### {shop_name(f)}")
    st.markdown(chip(STATUS[k][0], STATUS[k][1]))
    st.write(", ".join(x for x in [f.get("street"), f.get("city"), f.get("province"), f.get("postal")] if x))
    st.caption(" | ".join(x for x in [f"Legal name: {f.get('legal_name')}", f.get("phone"), f.get("website"),
                                      f"Representative: {f.get('rep_name') or ''} {f.get('rep_title') or ''} {f.get('rep_email') or ''}".strip()] if x))
    if f.get("locator_url"):
        st.link_button("CPN Auto Body Locator listing", f["locator_url"])

    t1, t2, t3, t4 = st.tabs(["Requirements", "Credentials", "Declarations", "Activity"])
    with t1:
        a = f.get("answers") or {}
        c = req_counts(a)
        st.caption(f"{c['yes']} yes, {c['no']} no, {c['unsure']} not sure, {c['blank']} unanswered")
        st.dataframe([{"ID": rid, "Section": sec, "Answer": ANSWERS.get(a.get(rid), "Unanswered")} for rid, sec, _ in REQS], hide_index=True)
    with t2:
        if not claims:
            st.caption("No credentials listed.")
        else:
            st.dataframe([{"Credential": program_name(c), "Status": CLAIM_LABEL[claim_state(c)][0], "Confirmed via": c.get("source") or "",
                           "Reviewed": fmt(c.get("reviewed_at")), "Next re-check": fmt(c.get("recheck_at")),
                           "Note to shop": c.get("note") or ""} for c in claims], hide_index=True)
    with t3:
        if not decls:
            st.caption("No declarations yet.")
        else:
            st.dataframe([{"ID": d["code"], "Declared": fmt(d["declared_at"]), "By": d["signer"], "Valid until": fmt(d["expires_at"]),
                           "Ended": fmt(d.get("withdrawn_at")), "Reason": d.get("withdrawn_reason") or ""} for d in decls], hide_index=True)
        active = active_declaration(decls)
        if active:
            with st.popover("Revoke this badge"):
                st.write("The shop's badge and directory listing are removed right away, and the shop sees the reason.")
                reason = st.text_input("Reason, shown to the shop", key=f"rv_reason_{active['id']}")
                if st.button("Revoke badge", type="primary", key=f"rv_{active['id']}"):
                    if not reason.strip():
                        st.error("Enter a reason.")
                    else:
                        try:
                            db.revoke(active["id"], f"Revoked by AIA Canada: {reason.strip()}")
                            db.log(f["id"], "revoked", reason.strip())
                            flash(f"Badge {active['code']} revoked.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"That didn't save. {err_text(e)}")
    with t4:
        try:
            hist = db.history(f["id"])
        except Exception:
            hist = []
        if hist:
            st.dataframe([{"When": fmt(h["at"]), "Event": h["type"].replace("_", " "), "Detail": h.get("detail") or ""} for h in hist], hide_index=True)
        else:
            st.caption("No activity recorded.")
    if db.is_super():
        _super_actions(f)


def _super_actions(f):
    st.markdown("#### Super admin actions")
    name = shop_name(f)
    c1, c2 = st.columns(2)
    if f.get("suspended_at"):
        c1.error(f"Revoked {fmt(f['suspended_at'])}: {f.get('suspended_reason') or ''}")
        if c1.button("Reinstate facility", key=f"reinstate_{f['id']}"):
            db.reinstate_facility(f["id"])
            flash(f"{name} reinstated. The shop can declare again.")
            st.rerun()
    else:
        with c1.popover("Revoke facility"):
            st.write("Withdraws the badge, removes the shop from the directory, and blocks it from declaring again until "
                     "you reinstate it. The shop sees your reason.")
            reason = st.text_input("Reason, shown to the shop", key=f"susp_reason_{f['id']}")
            if st.button("Revoke facility", type="primary", key=f"susp_{f['id']}"):
                if not reason.strip():
                    st.error("Enter a reason.")
                else:
                    try:
                        db.suspend_facility(f["id"], reason.strip())
                        flash(f"{name} revoked.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"That didn't save. {err_text(e)}")
    with c2.popover("Delete facility"):
        st.warning("Permanently deletes this facility with its answers, credentials, declarations, history and screenshots. "
                   "This can't be undone. Consumer concerns about it are kept.")
        typed = st.text_input(f"Type {name} to confirm", key=f"del_confirm_{f['id']}")
        if st.button("Delete permanently", type="primary", key=f"del_{f['id']}", disabled=typed.strip() != name):
            try:
                db.delete_facility(f["id"])
                flash(f"{name} deleted.")
                st.rerun()
            except Exception as e:
                st.error(f"That didn't work. {err_text(e)}")


# ---------------------------------------------------------------- concerns
def concerns():
    if not _guard():
        return
    st.title("Consumer concerns")
    show_flash()
    try:
        rows = db.concerns()
    except Exception:
        st.error("Concerns couldn't be loaded. Check that the 003 database update has been run.")
        return
    view = st.radio("Show", ["New", "Reviewing", "Closed", "All"], horizontal=True, label_visibility="collapsed")
    if view != "All":
        rows = [r for r in rows if r["status"] == view.lower()]
    if not rows:
        st.info("Nothing here.")
    labels = {"new": "New", "reviewing": "Reviewing", "closed": "Closed"}
    for r in rows:
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(f"**{r.get('facility_name') or 'Unknown facility'}**" + (f"  \nBadge {r['badge_code']}" if r.get("badge_code") else ""))
            b.markdown(chip(labels[r["status"]], {"new": "red", "reviewing": "orange", "closed": "gray"}[r["status"]]))
            st.caption(f"Received {fmt(r['submitted_at'])}" + (f" from {r['reporter_name']}" if r.get("reporter_name") else "")
                       + (f", {r['reporter_contact']}" if r.get("reporter_contact") else ""))
            st.write(r["message"])
            with st.form(f"concern_{r['id']}"):
                c1, c2 = st.columns([1, 2])
                new_status = c1.selectbox("Status", list(labels), index=list(labels).index(r["status"]), format_func=labels.get)
                note = c2.text_input("Internal note", r.get("admin_note") or "")
                if st.form_submit_button("Save"):
                    try:
                        db.update_concern(r["id"], new_status, note.strip())
                        flash("Concern updated.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"That didn't save. {err_text(e)}")


# ---------------------------------------------------------------- staff (super admins)
ROLES = {"reviewer": "Reviewer", "super_admin": "Super admin"}


def _role_changed(user_id, email, key):
    role = st.session_state.get(key)
    try:
        db.set_staff_role(user_id, role)
        flash(f"{email} is now a {ROLES[role].lower()}.")
    except Exception as e:
        flash(f"The role for {email} couldn't be changed. {err_text(e)}", "error")


def staff():
    if not db.is_super():
        st.error("This page is for super admins.")
        return
    st.title("Staff")
    show_flash()
    st.write("**Reviewers** confirm credentials, handle consumer concerns and can revoke a badge. **Super admins** can also "
             "manage staff and revoke or delete facilities.")

    new = st.session_state.get("new_staff")
    if new:
        with st.container(border=True):
            st.success(f"Account created for **{new['email']}** as {ROLES[new['role']].lower()}.")
            st.write("Send them this temporary password. They'll be asked to choose their own the first time they sign in.")
            st.code(new["password"], language=None)
            st.caption("For security, this password isn't shown again once you close this box.")
            if st.button("Done"):
                st.session_state.pop("new_staff", None)
                st.rerun()

    try:
        rows = db.reviewers()
    except Exception:
        st.error("Staff couldn't be loaded. Check that the 004 database update has been run.")
        return
    for r in rows:
        me = r["user_id"] == db.uid()
        with st.container(border=True):
            a, b, c = st.columns([3, 2, 1], vertical_alignment="center")
            a.write(f"**{r['email']}**  \n:gray[Added {fmt(r['added_at'])}]")
            if me:
                b.write(f"{ROLES.get(r['role'], r['role'])} (you)")
                continue
            key = f"role_{r['user_id']}"
            b.selectbox("Role", list(ROLES), index=list(ROLES).index(r["role"]) if r["role"] in ROLES else 0,
                        format_func=ROLES.get, key=key, label_visibility="collapsed",
                        on_change=_role_changed, args=(r["user_id"], r["email"], key))
            if c.button("Remove", key=f"rm_staff_{r['user_id']}"):
                db.remove_reviewer(r["user_id"])
                flash(f"{r['email']} no longer has staff access. Their account still exists and works as a shop account.")
                st.rerun()

    st.markdown("#### Add staff")
    direct = db.can_create_accounts()
    st.caption("Enter their work email. If they don't have an account yet, one is created for you with a temporary password."
               if direct else
               "They need an account first. To create accounts for staff yourself, add SUPABASE_SERVICE_ROLE_KEY to the app's "
               "secrets (see README, step 4).")
    with st.form("add_staff", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        email = c1.text_input("Work email")
        role = c2.selectbox("Role", list(ROLES), format_func=ROLES.get)
        if st.form_submit_button("Add staff", type="primary"):
            email = email.strip()
            if "@" not in email:
                st.error("Enter a valid email address.")
                return
            try:
                if direct:
                    password, res = db.create_staff_account(email, role)
                    if password:
                        st.session_state.new_staff = {"email": email, "password": password, "role": role}
                    else:
                        flash(f"{email} already had an account and is now a {ROLES[role].lower()}. They can sign in with their existing password.")
                    st.rerun()
                res = db.add_staff(email, role)
                if res == "added":
                    flash(f"{email} is now a {ROLES[role].lower()}.")
                    st.rerun()
                st.error("There's no account with that email yet. Ask them to create one on the Sign in page, then add them here.")
            except Exception as e:
                st.error(f"That didn't work. {err_text(e)}")
