from collections import Counter

import streamlit as st

from .. import db
from ..config import PROVINCES, REQS, answer_label, program_admin, program_name, province_name, section_label
from ..i18n import t
from ..logic import STATUS, active_declaration, claim_label, claim_state, fmt, req_counts, status, status_label
from .common import chip, err_text, flash, shop_name, show_flash


def _guard():
    if not db.is_admin():
        st.error(t("This page is for AIA Canada staff."))
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
    st.title(t("Dashboard"))
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

    m1, m2 = st.columns(2)
    m1.metric(t("Badges active"), counts.get("badge", 0))
    m2.metric(t("Declared, awaiting credentials"), counts.get("verifying", 0) + counts.get("action", 0))
    m3, m4 = st.columns(2)
    m3.metric(t("Claims needing a reviewer"), len(needs_person))
    m4.metric(t("New concerns"), new_concerns)
    st.page_link(verification_page, label=t("Review credentials"), icon=":material/fact_check:")
    st.page_link(facilities_page, label=t("All facilities"), icon=":material/store:")
    st.page_link(concerns_page, label=t("Consumer concerns"), icon=":material/report:")

    st.markdown(f"#### {t('Facilities by status')}")
    st.dataframe([{t("Status"): status_label(k)[0], t("Facilities"): counts.get(k, 0)} for k in STATUS], hide_index=True)
    st.markdown(f"#### {t('Active badges by province or territory')}")
    prov = Counter(f.get("province") for f in facs if st_by[f["id"]] == "badge")
    rows = [{t("Province or territory"): province_name(p), t("Badges"): prov[p]} for p in PROVINCES if prov.get(p)]
    if rows:
        st.dataframe(rows, hide_index=True)
    else:
        st.caption(t("No active badges yet."))


# ---------------------------------------------------------------- facilities
def facilities():
    if not _guard():
        return
    st.title(t("Facilities"))
    show_flash()
    facs, claims, decls = _load()
    if not facs:
        st.info(t("No facilities yet."))
        return
    c1, c2 = st.columns([2, 1])
    q = c1.text_input(t("Search by name, city or postal code"))
    stat = c2.selectbox(t("Status"), [""] + list(STATUS), format_func=lambda k: status_label(k)[0] if k else t("All"))
    ql = q.lower().strip()
    rows = []
    for f in facs:
        k = status(f, claims.get(f["id"], []), decls.get(f["id"], []))
        text = f"{shop_name(f)} {f.get('legal_name')} {f.get('city') or ''} {f.get('postal') or ''}".lower()
        if (ql and ql not in text) or (stat and k != stat):
            continue
        rows.append((f, k))
    st.dataframe([{t("Facility"): shop_name(f), t("Location"): ", ".join(x for x in [f.get("city"), f.get("province")] if x),
                   t("Status"): status_label(k)[0], t("Requirements yes"): req_counts(f.get("answers"))["yes"],
                   t("Credentials confirmed"): t("{a} of {b}", a=sum(claim_state(c) == "confirmed" for c in claims.get(f["id"], [])),
                                                 b=len(claims.get(f["id"], [])))}
                  for f, k in rows], hide_index=True)
    if not rows:
        return
    ids = [f["id"] for f, _ in rows]
    fid = st.selectbox(t("Open a facility"), ids, format_func=lambda i: shop_name(next(f for f, _ in rows if f["id"] == i)))
    f = next(x for x, _ in rows if x["id"] == fid)
    _facility_detail(f, claims.get(fid, []), decls.get(fid, []))


def _facility_detail(f, claims, decls):
    label, color = status_label(status(f, claims, decls))
    st.markdown(f"### {shop_name(f)}")
    st.markdown(chip(label, color))
    st.write(", ".join(x for x in [f.get("street"), f.get("city"), f.get("province"), f.get("postal")] if x))
    rep = " ".join(x for x in [f.get("rep_name"), f.get("rep_title"), f.get("rep_email")] if x)
    st.caption(" | ".join(x for x in [t("Legal name: {name}", name=f.get("legal_name")), f.get("phone"), f.get("website"),
                                      t("Representative: {rep}", rep=rep) if rep else ""] if x))
    if f.get("locator_url"):
        st.link_button(t("CPN Auto Body Locator listing"), f["locator_url"])

    t1, t2, t3, t4 = st.tabs([t("Requirements"), t("Credentials"), t("Declarations"), t("Activity")])
    with t1:
        a = f.get("answers") or {}
        c = req_counts(a)
        st.caption(t("{yes} yes, {no} no, {unsure} not sure, {blank} unanswered", **{k: c[k] for k in ("yes", "no", "unsure", "blank")}))
        st.dataframe([{t("ID"): r[0], t("Section"): section_label(r[1]), t("Answer"): answer_label(a.get(r[0]))} for r in REQS], hide_index=True)
    with t2:
        if not claims:
            st.caption(t("No credentials listed."))
        else:
            st.dataframe([{t("Credential"): program_name(c), t("Status"): claim_label(claim_state(c))[0], t("Confirmed through"): c.get("source") or "",
                           t("Reviewed"): fmt(c.get("reviewed_at")), t("Next re-check"): fmt(c.get("recheck_at")),
                           t("Note to the shop"): c.get("note") or ""} for c in claims], hide_index=True)
    with t3:
        if not decls:
            st.caption(t("No declarations yet."))
        else:
            st.dataframe([{t("ID"): d["code"], t("Declared"): fmt(d["declared_at"]), t("By"): d["signer"], t("Valid until"): fmt(d["expires_at"]),
                           t("Ended"): fmt(d.get("withdrawn_at")), t("Reason"): d.get("withdrawn_reason") or ""} for d in decls], hide_index=True)
        active = active_declaration(decls)
        if active:
            with st.popover(t("Revoke this badge")):
                st.write(t("The shop's badge and directory listing are removed right away, and the shop sees the reason."))
                reason = st.text_input(t("Reason, shown to the shop"), key=f"rv_reason_{active['id']}")
                if st.button(t("Revoke badge"), type="primary", key=f"rv_{active['id']}"):
                    if not reason.strip():
                        st.error(t("Enter a reason."))
                    else:
                        try:
                            db.revoke(active["id"], f"Revoked by AIA Canada: {reason.strip()}")
                            db.log(f["id"], "revoked", reason.strip())
                            flash(t("Badge {code} revoked.", code=active["code"]))
                            st.rerun()
                        except Exception as e:
                            st.error(t("That change was not saved. {detail}", detail=err_text(e)))
    with t4:
        try:
            hist = db.history(f["id"])
        except Exception:
            hist = []
        if hist:
            st.dataframe([{t("When"): fmt(h["at"]), t("Event"): h["type"].replace("_", " "), t("Detail"): h.get("detail") or ""} for h in hist], hide_index=True)
        else:
            st.caption(t("No activity recorded."))
    if db.is_super():
        _super_actions(f)


def _super_actions(f):
    st.markdown(f"#### {t('Super admin actions')}")
    name = shop_name(f)
    c1, c2 = st.columns(2)
    if f.get("suspended_at"):
        c1.error(t("Revoked on {date}: {reason}", date=fmt(f["suspended_at"]), reason=f.get("suspended_reason") or ""))
        if c1.button(t("Reinstate facility"), key=f"reinstate_{f['id']}"):
            db.reinstate_facility(f["id"])
            flash(t("{name} reinstated. The shop can declare again.", name=name))
            st.rerun()
    else:
        with c1.popover(t("Revoke facility")):
            st.write(t("Withdraws the badge, removes the shop from the directory, and blocks it from declaring again until you reinstate it. The shop sees your reason."))
            reason = st.text_input(t("Reason, shown to the shop"), key=f"susp_reason_{f['id']}")
            if st.button(t("Revoke facility"), type="primary", key=f"susp_{f['id']}"):
                if not reason.strip():
                    st.error(t("Enter a reason."))
                else:
                    try:
                        db.suspend_facility(f["id"], reason.strip())
                        flash(t("{name} revoked.", name=name))
                        st.rerun()
                    except Exception as e:
                        st.error(t("That change was not saved. {detail}", detail=err_text(e)))
    with c2.popover(t("Delete facility")):
        st.warning(t("Permanently deletes this facility with its answers, credentials, declarations, history and screenshots. This cannot be undone. Consumer concerns about it are kept."))
        typed = st.text_input(t("Type {name} to confirm", name=name), key=f"del_confirm_{f['id']}")
        if st.button(t("Delete permanently"), type="primary", key=f"del_{f['id']}", disabled=typed.strip() != name):
            try:
                db.delete_facility(f["id"])
                flash(t("{name} deleted.", name=name))
                st.rerun()
            except Exception as e:
                st.error(t("That did not work. {detail}", detail=err_text(e)))


# ---------------------------------------------------------------- concerns
CONCERN_STATUS = {"new": "New", "reviewing": "Reviewing", "closed": "Closed"}


def concerns():
    if not _guard():
        return
    st.title(t("Consumer concerns"))
    show_flash()
    try:
        rows = db.concerns()
    except Exception:
        st.error(t("Concerns could not be loaded. Check that the 003 database update has been run."))
        return
    views = ["new", "reviewing", "closed", "all"]
    view = st.radio(t("Show"), views, format_func=lambda v: t(CONCERN_STATUS.get(v, "All")), horizontal=True, label_visibility="collapsed")
    if view != "all":
        rows = [r for r in rows if r["status"] == view]
    if not rows:
        st.info(t("Nothing here."))
    for r in rows:
        with st.container(border=True):
            a, b = st.columns([3, 1])
            a.markdown(f"**{r.get('facility_name') or t('Unknown facility')}**" + (f"  \n{t('Badge {code}', code=r['badge_code'])}" if r.get("badge_code") else ""))
            b.markdown(chip(t(CONCERN_STATUS[r["status"]]), {"new": "red", "reviewing": "blue", "closed": "gray"}[r["status"]]))
            who = t(" from {name}", name=r["reporter_name"]) if r.get("reporter_name") else ""
            st.caption(t("Received {date}", date=fmt(r["submitted_at"])) + who + (f", {r['reporter_contact']}" if r.get("reporter_contact") else ""))
            st.write(r["message"])
            with st.form(f"concern_{r['id']}"):
                c1, c2 = st.columns([1, 2])
                new_status = c1.selectbox(t("Status"), list(CONCERN_STATUS), index=list(CONCERN_STATUS).index(r["status"]),
                                          format_func=lambda k: t(CONCERN_STATUS[k]))
                note = c2.text_input(t("Internal note"), r.get("admin_note") or "")
                if st.form_submit_button(t("Save")):
                    try:
                        db.update_concern(r["id"], new_status, note.strip())
                        flash(t("Concern updated."))
                        st.rerun()
                    except Exception as e:
                        st.error(t("That change was not saved. {detail}", detail=err_text(e)))


# ---------------------------------------------------------------- staff (super admins)
ROLES = {"reviewer": "Reviewer", "super_admin": "Super admin"}


def _role_changed(user_id, email, key):
    role = st.session_state.get(key)
    try:
        db.set_staff_role(user_id, role)
        flash(t("{email} is now a {role}.", email=email, role=t(ROLES[role]).lower()))
    except Exception as e:
        flash(t("The role for {email} could not be changed. {detail}", email=email, detail=err_text(e)), "error")


def staff():
    if not db.is_super():
        st.error(t("This page is for super admins."))
        return
    st.title(t("Staff"))
    show_flash()
    st.write(t("**Reviewers** confirm credentials, handle consumer concerns and can revoke a badge. **Super admins** can also manage staff and revoke or delete facilities."))

    new = st.session_state.get("new_staff")
    if new:
        with st.container(border=True):
            st.success(t("Account created for **{email}** as {role}.", email=new["email"], role=t(ROLES[new["role"]]).lower()))
            st.write(t("Send them this temporary password. They will be asked to choose their own password the first time they sign in."))
            st.code(new["password"], language=None)
            st.caption(t("For security, this password is not shown again once you close this box."))
            if st.button(t("Done")):
                st.session_state.pop("new_staff", None)
                st.rerun()

    try:
        rows = db.reviewers()
    except Exception:
        st.error(t("Staff could not be loaded. Check that the 004 database update has been run."))
        return
    for r in rows:
        me = r["user_id"] == db.uid()
        with st.container(border=True):
            a, b, c = st.columns([3, 2, 1], vertical_alignment="center")
            a.write(f"**{r['email']}**  \n{t('Added {date}', date=fmt(r['added_at']))}")
            if me:
                b.write(t("{role} (you)", role=t(ROLES.get(r["role"], r["role"]))))
                continue
            key = f"role_{r['user_id']}"
            b.selectbox(t("Role"), list(ROLES), index=list(ROLES).index(r["role"]) if r["role"] in ROLES else 0,
                        format_func=lambda k: t(ROLES[k]), key=key, label_visibility="collapsed",
                        on_change=_role_changed, args=(r["user_id"], r["email"], key))
            if c.button(t("Remove"), key=f"rm_staff_{r['user_id']}"):
                db.remove_reviewer(r["user_id"])
                flash(t("{email} no longer has staff access. Their account still exists and works as a shop account.", email=r["email"]))
                st.rerun()

    st.markdown(f"#### {t('Add staff')}")
    direct = db.can_create_accounts()
    st.caption(t("Enter their work email. If they do not have an account yet, one is created for you with a temporary password.") if direct else
               t("They need an account first. To create accounts for staff yourself, add SUPABASE_SERVICE_ROLE_KEY to the app's secrets (see README, step 4)."))
    with st.form("add_staff", clear_on_submit=True):
        c1, c2 = st.columns([2, 1])
        email = c1.text_input(t("Work email"))
        role = c2.selectbox(t("Role"), list(ROLES), format_func=lambda k: t(ROLES[k]))
        if st.form_submit_button(t("Add staff"), type="primary"):
            email = email.strip()
            if "@" not in email:
                st.error(t("Enter a valid email address."))
                return
            try:
                if direct:
                    password, res = db.create_staff_account(email, role)
                    if password:
                        st.session_state.new_staff = {"email": email, "password": password, "role": role}
                    else:
                        flash(t("{email} already had an account and is now a {role}. They can sign in with their existing password.",
                                email=email, role=t(ROLES[role]).lower()))
                    st.rerun()
                res = db.add_staff(email, role)
                if res == "added":
                    flash(t("{email} is now a {role}.", email=email, role=t(ROLES[role]).lower()))
                    st.rerun()
                st.error(t("There is no account with that email yet. Ask them to create one on the Sign in page, then add them here."))
            except Exception as e:
                st.error(t("That did not work. {detail}", detail=err_text(e)))
