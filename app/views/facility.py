import re
from datetime import date

import streamlit as st

from .. import ai, db
from ..badge import badge_svg, show
from ..config import (ADMINS, ANSWERS, PROGRAMS, PROVINCES, RENEW_WINDOW_DAYS, REQS, SCOPES, SECTIONS, STEPS,
                      program_admin, program_name)
from ..logic import (CLAIM_LABEL, STATUS, active_declaration, claim_state, fmt, latest_declaration, now, profile_missing,
                     req_counts, status, status_line, ts)
from .common import chip, err_text, flash, shop_name, show_flash

BANNER = {"green": st.success, "blue": st.info, "orange": st.warning, "red": st.error, "gray": st.info}


def render():
    st.title("My facility")
    show_flash()
    facs = db.my_facilities()
    if not facs:
        _start()
        return
    ids = [f["id"] for f in facs]
    if st.session_state.get("facility_id") not in ids:
        st.session_state.facility_id = ids[0]
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.selectbox("Facility", ids, key="facility_id", format_func=lambda i: shop_name(next(f for f in facs if f["id"] == i)))
    with c2.popover("Add a facility"):
        _new_facility_form("add")

    f = next(x for x in facs if x["id"] == st.session_state.facility_id)
    claims = db.claims(f["id"])
    decls = db.declarations(f["id"])
    label, tone = STATUS[status(f, claims, decls)]
    BANNER[tone](f"**{label}.** {status_line(f, claims, decls)}")

    tabs = st.tabs(STEPS)
    with tabs[0]:
        _profile(f)
    with tabs[1]:
        _requirements(f, decls)
    with tabs[2]:
        _credentials(f, claims)
    with tabs[3]:
        _review(f, claims)
    with tabs[4]:
        _declare(f, claims, decls)


# ---------------------------------------------------------------- start
def _start():
    st.write("Check your facility against AIA Canada's Statement on minimum collision repair requirements, list your "
             "credentials, and declare when every item is met. AIA Canada confirms your credentials, then issues your badge.")
    st.markdown("1. Tell us about your facility.\n2. Answer yes, no or not sure for each of the 27 requirements.\n"
                "3. List your OEM certifications and I-CAR Gold Class status.\n4. Get AI guidance on anything you haven't met yet.\n"
                "5. Declare, and receive your badge once your credentials are confirmed.")
    _new_facility_form("start")


def _new_facility_form(key):
    with st.form(f"new_facility_{key}"):
        name = st.text_input("Legal business name")
        if st.form_submit_button("Start the self-check" if key == "start" else "Add facility", type="primary"):
            if not name.strip():
                st.error("Enter the legal business name.")
                return
            try:
                row = db.create_facility(name.strip())
                db.log(row["id"], "created")
                st.session_state.facility_id = row["id"]
                st.rerun()
            except Exception as e:
                st.error(f"The facility couldn't be created. {err_text(e)}")


# ---------------------------------------------------------------- step 1
def _profile(f):
    st.subheader("Your facility")
    st.caption("Declarations are per location, so add each shop separately.")
    provs = list(PROVINCES)
    with st.form(f"profile_{f['id']}"):
        c1, c2 = st.columns(2)
        legal = c1.text_input("Legal business name", f.get("legal_name") or "")
        op = c2.text_input("Operating name, if different", f.get("operating_name") or "")
        street = st.text_input("Street address", f.get("street") or "")
        c1, c2, c3 = st.columns([2, 2, 1])
        city = c1.text_input("City", f.get("city") or "")
        prov = c2.selectbox("Province or territory", provs, index=provs.index(f["province"]) if f.get("province") in provs else None,
                            format_func=PROVINCES.get, placeholder="Select")
        postal = c3.text_input("Postal code", f.get("postal") or "", help="Used to find your listing on CPN Auto Body Locator")
        c1, c2 = st.columns(2)
        phone = c1.text_input("Phone", f.get("phone") or "", help="Use the number on your OEM program listings")
        web = c2.text_input("Website", f.get("website") or "")
        locator = st.text_input("CPN Auto Body Locator profile link (optional)", f.get("locator_url") or "",
                                help="If your shop is listed on autobodylocator.ca, open your shop's page there and paste its address here. Your OEM certifications can then be confirmed exactly.")
        scope = st.multiselect("Repair scope", SCOPES, default=[s for s in (f.get("scope") or []) if s in SCOPES])
        c1, c2 = st.columns(2)
        rep = c1.text_input("Authorized representative", f.get("rep_name") or "")
        title = c2.text_input("Title", f.get("rep_title") or "")
        email = st.text_input("Representative email", f.get("rep_email") or "")
        if st.form_submit_button("Save facility details", type="primary"):
            if not legal.strip():
                st.error("The legal business name can't be empty.")
                return
            if locator.strip() and not re.search(r"autobodylocator\.ca/shop/.+-\d+", locator):
                st.error("That doesn't look like a CPN Auto Body Locator shop page. It should start with https://autobodylocator.ca/shop/")
                return
            try:
                db.update_facility(f["id"], {"legal_name": legal.strip(), "operating_name": op.strip() or None, "street": street.strip(),
                                             "city": city.strip(), "province": prov, "postal": postal.strip().upper(), "phone": phone.strip(),
                                             "website": web.strip(), "locator_url": locator.strip().split("?")[0] or None, "scope": scope, "rep_name": rep.strip(), "rep_title": title.strip(),
                                             "rep_email": email.strip()})
                flash("Facility details saved.")
                st.rerun()
            except Exception as e:
                st.error(f"Facility details didn't save. {err_text(e)}")
    miss = profile_missing(f)
    if miss:
        st.warning("Still needed before you can declare: " + ", ".join(miss) + ".")


# ---------------------------------------------------------------- step 2
def _save_answer(fid, rid, key, was_active):
    val = st.session_state.get(key)
    try:
        current = db.facility(fid)
        answers = dict(current.get("answers") or {})
        answers[rid] = val
        db.update_facility(fid, {"answers": answers})
        db.log(fid, "answer", f"{rid}={val}")
        if rid == "T2" and val == "yes" and not any(c["program"] == "icar-gold" for c in db.claims(fid)):
            db.add_claim(fid, {"program": "icar-gold"})
            flash("I-CAR Gold Class was added to your credentials because you answered yes to T2.", "info")
        if was_active and val != "yes":
            flash(f"Your declaration was withdrawn because {rid} is no longer a yes. Declare again once it's met.", "warning")
    except Exception as e:
        flash(f"Your answer to {rid} didn't save. {err_text(e)}", "error")


def _requirements(f, decls):
    answers = f.get("answers") or {}
    was_active = bool(active_declaration(decls))
    st.subheader("Minimum requirements")
    st.caption("Answer every item. Only a yes counts toward your declaration. If you use a qualified sublet provider where "
               "the requirement allows it, answer yes.")
    opts = list(ANSWERS)
    for sec in SECTIONS:
        items = [r for r in REQS if r[1] == sec]
        yes = sum(answers.get(r[0]) == "yes" for r in items)
        st.markdown(f"#### {sec}")
        st.caption(f"{yes} of {len(items)} yes")
        for rid, section, text in items:
            with st.container(border=True):
                a, b = st.columns([1, 11])
                a.markdown(f"**{rid}**")
                with b:
                    st.write(text)
                    key = f"ans_{f['id']}_{rid}"
                    cur = answers.get(rid)
                    st.radio(f"Answer for {rid}", opts, index=opts.index(cur) if cur in opts else None, format_func=ANSWERS.get,
                             horizontal=True, key=key, label_visibility="collapsed", on_change=_save_answer,
                             args=(f["id"], rid, key, was_active))
                    if ai.available():
                        with st.expander("Explain this"):
                            _explain(rid, section, text, f.get("province"))


def _explain(rid, section, text, province):
    k = f"explain_{rid}_{province}"
    if k not in st.session_state and st.button("Get an explanation", key=f"btn_{k}"):
        with st.spinner("Thinking"):
            try:
                st.session_state[k] = ai.explain(rid, section, text, province or "")
            except Exception:
                st.error("The AI couldn't answer this time. Try again.")
    if k in st.session_state:
        st.write(st.session_state[k])
        st.caption("AI guidance explains the requirement. It doesn't decide whether your facility meets it.")


# ---------------------------------------------------------------- step 3
def _credentials(f, claims):
    t2_yes = (f.get("answers") or {}).get("T2") == "yes"
    st.subheader("Credentials")
    st.caption("List your I-CAR Gold Class status and every OEM certification you hold. Each one is confirmed with its program "
               "administrator before your badge is issued. Certifications listed on CPN Auto Body Locator are checked "
               "automatically within about an hour.")
    if not claims:
        st.info("No credentials listed yet.")
    for c in claims:
        state = claim_state(c)
        label, color = CLAIM_LABEL[state]
        adm = program_admin(c["program"])
        with st.container(border=True):
            a, b = st.columns([4, 1])
            details = [f"Confirmed by {adm['name']}"]
            if c.get("program_ref"):
                details.append(f"ID {c['program_ref']}")
            if c.get("cert_number"):
                details.append(f"Certificate {c['cert_number']}")
            if c.get("cert_expiry"):
                details.append(f"Expires {fmt(c['cert_expiry'])}")
            a.markdown(f"**{program_name(c)}**")
            a.caption(". ".join(details) + ".")
            b.markdown(chip(label, color))
            if state == "confirmed":
                st.caption(f"Confirmed {fmt(c.get('reviewed_at'))} via {c.get('source') or adm['name']}. Next re-check {fmt(c.get('recheck_at'))}.")
            elif state == "not_found" and c.get("note"):
                st.error(f"Reviewer note: {c['note']}")
            elif state == "expired":
                st.error("The certificate expiry date has passed. Enter the renewed certificate details.")
            elif state == "review":
                st.caption("A reviewer is confirming this credential.")
            e1, e2, _ = st.columns([2, 1, 3])
            with e1.popover("Edit and resubmit"):
                with st.form(f"edit_{c['id']}"):
                    ref = st.text_input("Program or facility ID", c.get("program_ref") or "")
                    num = st.text_input("Certificate number", c.get("cert_number") or "")
                    exp = st.date_input("Certificate expiry", value=date.fromisoformat(c["cert_expiry"]) if c.get("cert_expiry") else None)
                    if st.form_submit_button("Resubmit for review", type="primary"):
                        try:
                            db.update_claim(c["id"], {"program_ref": ref.strip() or None, "cert_number": num.strip() or None,
                                                      "cert_expiry": exp.isoformat() if exp else None})
                            db.log(f["id"], "claim_resubmitted", c["program"])
                            flash(f"{program_name(c)} resubmitted for review.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"That didn't save. {err_text(e)}")
            if not (c["program"] == "icar-gold" and t2_yes):
                if e2.button("Remove", key=f"rm_{c['id']}"):
                    db.delete_claim(c["id"])
                    db.log(f["id"], "claim_removed", c["program"])
                    st.rerun()

    st.markdown("#### Add a credential")
    taken = {c["program"] for c in claims if c["program"] != "other"}
    options = [p for p in PROGRAMS if p not in taken]
    with st.form(f"add_claim_{f['id']}", clear_on_submit=True):
        prog = st.selectbox("Program", options, index=None, placeholder="Select a program",
                            format_func=lambda p: f"{PROGRAMS[p][0]} ({ADMINS[PROGRAMS[p][1]]['name']})")
        other = st.text_input("Program name, if you chose Other program")
        c1, c2, c3 = st.columns(3)
        ref = c1.text_input("Program or facility ID", help="As shown on your program account or certificate")
        num = c2.text_input("Certificate number")
        exp = c3.date_input("Certificate expiry", value=None)
        if st.form_submit_button("Add credential", type="primary"):
            if not prog:
                st.error("Select a program.")
            elif prog == "other" and not other.strip():
                st.error("Enter the program name.")
            elif not ref.strip() and not num.strip():
                st.error("Enter a program ID or certificate number so the credential can be confirmed.")
            else:
                try:
                    db.add_claim(f["id"], {"program": prog, "other_name": other.strip() or None, "program_ref": ref.strip() or None,
                                           "cert_number": num.strip() or None, "cert_expiry": exp.isoformat() if exp else None})
                    db.log(f["id"], "claim_added", prog)
                    flash(f"{program_name(prog, other)} added. It will be confirmed with {program_admin(prog)['name']}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"The credential couldn't be added. {err_text(e)}")


# ---------------------------------------------------------------- step 4
def _review(f, claims):
    answers = f.get("answers") or {}
    c = req_counts(answers)
    st.subheader("Review and guidance")
    m = st.columns(4)
    m[0].metric("Yes", c["yes"])
    m[1].metric("No", c["no"])
    m[2].metric("Not sure", c["unsure"])
    m[3].metric("Unanswered", c["blank"])

    gaps = [r for r in REQS if answers.get(r[0]) != "yes"]
    bad = [x for x in claims if claim_state(x) in ("not_found", "expired")]
    if gaps:
        st.markdown(f"#### Requirements to address ({len(gaps)})")
        for rid, _, text in gaps:
            a = answers.get(rid)
            tag = chip("No", "red") if a == "no" else chip("Not sure", "orange") if a == "unsure" else chip("Unanswered", "gray")
            st.markdown(f"**{rid}** {tag}  \n{text}")
    if bad:
        st.markdown(f"#### Credentials to fix ({len(bad)})")
        for x in bad:
            st.markdown(f"**{program_name(x)}** {chip(CLAIM_LABEL[claim_state(x)][0], 'red')}" + (f"  \n{x['note']}" if x.get("note") else ""))

    st.markdown("#### Gap plan")
    plan = f.get("gap_plan")
    if not gaps and not bad:
        st.write("Nothing to plan for. Every requirement is a yes and no credential is blocked.")
        return
    if not ai.available():
        st.info("AI guidance isn't set up. Use the lists above to plan your next steps.")
    elif st.button("Rebuild my gap plan" if plan else "Build my gap plan", type="primary"):
        with st.spinner("Building your gap plan. This can take up to a minute."):
            try:
                p = ai.gap_plan(
                    f,
                    [{"id": r[0], "section": r[1], "requirement": r[2], "answer": answers.get(r[0]) or "unanswered"} for r in gaps],
                    [{"program": program_name(x), "administrator": program_admin(x["program"])["name"],
                      "issue": "certificate expired" if claim_state(x) == "expired" else "could not be confirmed",
                      "reviewer_note": x.get("note") or ""} for x in bad])
                p["generated_at"] = now().isoformat()
                db.update_facility(f["id"], {"gap_plan": p})
                db.log(f["id"], "gap_plan")
                st.rerun()
            except Exception:
                st.error("The AI couldn't build a plan this time. Try again.")
    if plan:
        st.write(plan.get("summary", ""))
        for pr in ["high", "medium", "low"]:
            items = [i for i in plan.get("items", []) if str(i.get("priority", "medium")).lower() == pr]
            if not items:
                continue
            st.markdown(f"**{pr.title()} priority**")
            for i in items:
                who = ". ".join(x for x in [f"Owner: {i['owner']}" if i.get("owner") else "", f"Target: {i['timeframe']}" if i.get("timeframe") else ""] if x)
                res = "".join(f"\n  - {r}" for r in i.get("resources") or [])
                st.markdown(f"- **{i.get('id', '')}**: {i.get('action', '')}  \n  {who}{res}")
        for cg in plan.get("credentials") or []:
            st.markdown(f"- **{cg.get('program', '')}**: {cg.get('guidance', '')}")
        st.caption(f"Generated {fmt(plan.get('generated_at'))}. AI guidance suggests next steps. It doesn't decide whether your facility meets a requirement.")
        st.download_button("Download gap plan", ai.plan_markdown(shop_name(f), plan, fmt(plan.get("generated_at"))),
                           file_name=f"gap-plan-{shop_name(f).lower().replace(' ', '-')}.md", mime="text/markdown")


# ---------------------------------------------------------------- step 5
def _declare(f, claims, decls):
    active = active_declaration(decls)
    if active:
        _active_declaration(f, claims, decls, active)
        return
    st.subheader("Declare")
    c = req_counts(f.get("answers"))
    miss = profile_missing(f)
    if not c["all_yes"] or miss:
        st.write("You can declare once every requirement is a yes and your facility details are complete.")
        if not c["all_yes"]:
            st.warning(f"{c['total'] - c['yes']} requirements still need a yes. Go to the Requirements tab.")
        if miss:
            st.warning("Facility details missing: " + ", ".join(miss) + ". Go to the Facility tab.")
        last = latest_declaration(decls)
        if last:
            ended = "withdrawn " + fmt(last["withdrawn_at"]) if last.get("withdrawn_at") else "expired " + fmt(last["expires_at"])
            st.caption(f"Previous declaration {last['code']} was {ended}.")
        return
    statements = [
        f"I am authorized to make this declaration on behalf of {shop_name(f)}.",
        "Every requirement in AIA Canada's Statement applies to this facility, and each answer I gave is accurate.",
        "The credentials I listed are current, and AIA Canada may confirm them with the program administrators.",
        "I will update this declaration if anything changes that affects a requirement or credential.",
        "I understand my badge is issued only after every listed credential is confirmed, and that it expires after one year unless renewed.",
    ]
    st.write("Every requirement is a yes. Confirm each statement and sign to submit your declaration.")
    with st.form(f"declare_{f['id']}"):
        checks = [st.checkbox(s, key=f"att_{f['id']}_{i}") for i, s in enumerate(statements)]
        c1, c2 = st.columns(2)
        signer = c1.text_input("Full name", f.get("rep_name") or "")
        title = c2.text_input("Title", f.get("rep_title") or "")
        if st.form_submit_button("Submit declaration", type="primary"):
            if not all(checks):
                st.error("Confirm every statement to declare.")
            elif not signer.strip():
                st.error("Enter your full name.")
            else:
                try:
                    d = db.declare(f["id"], signer.strip(), title.strip())
                    db.log(f["id"], "declared", d["code"])
                    all_ok = claims and all(claim_state(x) == "confirmed" for x in claims)
                    flash("Declaration submitted. Your badge is active." if all_ok else
                          "Declaration submitted. Your badge is issued once your credentials are confirmed.")
                    st.rerun()
                except Exception as e:
                    st.error(f"The declaration wasn't accepted. {err_text(e)}")


def _active_declaration(f, claims, decls, d):
    st.subheader("Your declaration")
    days = max(0, (ts(d["expires_at"]) - now()).days)
    st.markdown(
        f"| | |\n|---|---|\n| Declaration ID | {d['code']} |\n| Declared by | {d['signer']}{', ' + d['title'] if d.get('title') else ''} |\n"
        f"| Declared | {fmt(d['declared_at'])} |\n| Valid until | {fmt(d['expires_at'])} ({days} days) |\n| Statement | {d['statement_version']} |")
    confirmed = [program_name(c) for c in claims if claim_state(c) == "confirmed"]
    svg = badge_svg(shop_name(f), f.get("city"), f.get("province"), d["declared_at"], d["expires_at"], d["code"], confirmed)
    st.markdown("#### Badge")
    if status(f, claims, decls) == "badge":
        st.write("Use this badge on your website, in your shop and on quotes.")
        show(st, svg)
        st.download_button("Download badge", svg, file_name=f"aia-canada-badge-{d['code'].lower()}.svg", mime="image/svg+xml", type="primary")
    else:
        waiting = [program_name(c) for c in claims if claim_state(c) != "confirmed"]
        st.info("Your badge is issued when every credential is confirmed." + (f" Waiting on: {', '.join(waiting)}." if waiting else " Add at least one credential."))
        st.markdown(f'<div style="max-width:440px;opacity:.45;filter:grayscale(1)">{svg}</div>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    if days <= RENEW_WINDOW_DAYS and c1.button("Renew for another year"):
        try:
            nd = db.declare(f["id"], d["signer"], d.get("title") or "")
            db.log(f["id"], "renewed", nd["code"])
            flash("Declaration renewed.")
            st.rerun()
        except Exception as e:
            st.error(f"The renewal wasn't accepted. {err_text(e)}")
    with c2.popover("Withdraw declaration"):
        st.write("Your badge and directory listing are removed right away.")
        if st.button("Withdraw now", type="primary", key=f"wd_{d['id']}"):
            db.withdraw(d["id"], "Withdrawn by the facility")
            db.log(f["id"], "withdrawn", d["code"])
            flash("Declaration withdrawn.", "info")
            st.rerun()
    st.caption("If anything changes that affects a requirement, change the answer. Your declaration is withdrawn automatically until the item is met again.")
