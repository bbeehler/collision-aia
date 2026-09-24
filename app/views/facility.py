import re
from datetime import date

import streamlit as st

from .. import ai, db
from .. import locator_lookup as lookup
from ..badge import badge_svg, show
from ..config import (ANSWERS, PROGRAMS, PROVINCES, RENEW_WINDOW_DAYS, REQS, SCOPES, SECTIONS, STEPS, admin_name,
                      answer_label, program_name, province_name, req_text, section_label, statement_name)
from ..i18n import lang, t
from ..logic import (active_declaration, claim_label, claim_state, fmt, latest_declaration, now, profile_missing,
                     req_counts, status, status_label, status_line, ts)
from .common import chip, err_text, flash, shop_name, show_flash

BANNER = {"green": st.success, "blue": st.info, "red": st.error, "gray": st.info}


def render():
    st.title(t("My facility"))
    show_flash()
    facs = db.my_facilities()
    if not facs:
        _start()
        return
    ids = [f["id"] for f in facs]
    pending = st.session_state.pop("pending_facility_id", None)
    if pending in ids:
        st.session_state.facility_id = pending
    if st.session_state.get("facility_id") not in ids:
        st.session_state.facility_id = ids[0]
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    c1.selectbox(t("Facility"), ids, key="facility_id", format_func=lambda i: shop_name(next(f for f in facs if f["id"] == i)))
    with c2.popover(t("Add a facility")):
        _new_facility_form("add")

    f = next(x for x in facs if x["id"] == st.session_state.facility_id)
    claims = db.claims(f["id"])
    decls = db.declarations(f["id"])
    label, tone = status_label(status(f, claims, decls))
    BANNER[tone](f"**{label}.** {status_line(f, claims, decls)}")

    tabs = st.tabs([t(s) for s in STEPS])
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
    st.write(t("Check your facility against {statement}, list your credentials, and declare when every item is met. AIA Canada confirms your credentials, then issues your badge.",
               statement=statement_name()))
    st.markdown("\n".join([
        "1. " + t("Tell us about your facility."),
        "2. " + t("Answer yes, no or not sure for each of the 27 requirements."),
        "3. " + t("List your manufacturer (OEM) certifications and your I-CAR® Gold Class® status."),
        "4. " + t("Get AI guidance on anything you have not met yet."),
        "5. " + t("Declare, and receive your badge once your credentials are confirmed."),
    ]))
    _new_facility_form("start")


def _new_facility_form(key):
    with st.form(f"new_facility_{key}"):
        name = st.text_input(t("Legal business name"))
        if st.form_submit_button(t("Start the self-check") if key == "start" else t("Add facility"), type="primary"):
            if not name.strip():
                st.error(t("Enter the legal business name."))
                return
            try:
                row = db.create_facility(name.strip())
                db.log(row["id"], "created")
                st.session_state.pending_facility_id = row["id"]
                st.rerun()
            except Exception as e:
                st.error(t("The facility could not be created. {detail}", detail=err_text(e)))


# ---------------------------------------------------------------- step 1
def _profile(f):
    st.subheader(t("Your facility"))
    st.caption(t("Declarations are per location, so add each shop separately."))
    with st.form(f"profile_{f['id']}"):
        c1, c2 = st.columns(2)
        legal = c1.text_input(t("Legal business name"), f.get("legal_name") or "")
        op = c2.text_input(t("Operating name, if different"), f.get("operating_name") or "")
        street = st.text_input(t("Street address"), f.get("street") or "")
        c1, c2, c3 = st.columns([2, 2, 1])
        city = c1.text_input(t("City"), f.get("city") or "")
        prov = c2.selectbox(t("Province or territory"), PROVINCES, index=PROVINCES.index(f["province"]) if f.get("province") in PROVINCES else None,
                            format_func=province_name, placeholder=t("Select"))
        postal = c3.text_input(t("Postal code"), f.get("postal") or "", help=t("Used to find your listing on CPN Auto Body Locator"))
        c1, c2 = st.columns(2)
        phone = c1.text_input(t("Phone"), f.get("phone") or "", help=t("Use the number on your OEM program listings. It is how your shop is found on CPN Auto Body Locator."))
        web = c2.text_input(t("Website"), f.get("website") or "")
        scope = st.multiselect(t("Repair scope"), SCOPES, default=[s for s in (f.get("scope") or []) if s in SCOPES], format_func=t)
        c1, c2 = st.columns(2)
        rep = c1.text_input(t("Authorized representative"), f.get("rep_name") or "")
        title = c2.text_input(t("Title"), f.get("rep_title") or "")
        email = st.text_input(t("Representative email"), f.get("rep_email") or "")
        if st.form_submit_button(t("Save facility details"), type="primary"):
            if not legal.strip():
                st.error(t("The legal business name cannot be empty."))
                return
            try:
                db.update_facility(f["id"], {"legal_name": legal.strip(), "operating_name": op.strip() or None, "street": street.strip(),
                                             "city": city.strip(), "province": prov, "postal": postal.strip().upper(), "phone": phone.strip(),
                                             "website": web.strip(), "scope": scope, "rep_name": rep.strip(), "rep_title": title.strip(),
                                             "rep_email": email.strip()})
                flash(t("Facility details saved."))
                st.rerun()
            except Exception as e:
                st.error(t("Facility details were not saved. {detail}", detail=err_text(e)))
    miss = profile_missing(f)
    if miss:
        st.warning(t("Still needed before you can declare: {items}.", items=", ".join(miss)))
    _locator_section(f)


# ---------------------------------------------------------------- CPN Auto Body Locator
@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _search(postal):
    return lookup.search(postal)


def _shop_id(url):
    m = re.search(r"-(\d+)(?:/|\?|$)", url or "")
    return m.group(1) if m else None


def _ranked(f):
    """Locator listings near the facility, best match first. None if the lookup cannot run."""
    if not f.get("postal") or not (f.get("phone") or f.get("street")):
        return None
    try:
        return lookup.rank(f, _search(lookup.postal_query(f["postal"])))
    except Exception:
        return None


def _linked_listing(f, ranked):
    sid = _shop_id(f.get("locator_url"))
    return next((r["listing"] for r in ranked or [] if r["listing"].get("shop_id") == sid), None) if sid else None


def _add_listed(f, listing, key):
    brands = [b for b in listing.get("brands", []) if b in PROGRAMS]
    claimed = {c["program"] for c in db.claims(f["id"])}
    missing = [b for b in brands if b not in claimed]
    if brands:
        st.write(t("Certifications listed there: {items}.", items=", ".join(program_name(b) for b in brands)))
    if missing and st.button(t("Add {items} to my credentials", items=", ".join(program_name(b) for b in missing)), key=key, type="primary"):
        for b in missing:
            db.add_claim(f["id"], {"program": b, "program_ref": f"CPN {listing.get('shop_id') or ''}".strip()})
            db.log(f["id"], "claim_added", f"{b} (from locator listing)")
        flash(t("Added {n} certifications. They will be confirmed against your locator listing within the hour.", n=len(missing)))
        st.rerun()
    elif brands:
        st.caption(t("Every certification on your listing is in your credentials."))


def _locator_section(f):
    st.markdown("#### CPN Auto Body Locator")
    if not f.get("postal") or not (f.get("phone") or f.get("street")):
        st.caption(t("Save your street address, postal code and phone number above to find your shop on CPN Auto Body Locator. Certifications listed there are confirmed automatically."))
        return
    with st.spinner(t("Looking for your shop on CPN Auto Body Locator")):
        ranked = _ranked(f)
    if ranked is None:
        st.caption(t("CPN Auto Body Locator could not be reached just now. You can still add your credentials on the Credentials tab."))
        return

    if f.get("locator_url"):
        listing = _linked_listing(f, ranked)
        with st.container(border=True):
            if listing:
                st.success(t("**Your shop on CPN Auto Body Locator:** {name}, {address}", name=listing["name"], address=listing.get("address") or ""))
                _add_listed(f, listing, key=f"add_listed_{f['id']}")
            else:
                st.success(t("Your shop is linked to its CPN Auto Body Locator listing."))
            c1, c2, _ = st.columns([1, 1, 2])
            c1.link_button(t("View the listing"), f["locator_url"])
            if c2.button(t("This is not my shop"), key=f"unlink_{f['id']}"):
                st.session_state.setdefault("locator_declined", set()).add(_shop_id(f["locator_url"]))
                db.update_facility(f["id"], {"locator_url": None})
                db.log(f["id"], "locator_unlinked")
                st.rerun()
        return

    declined = st.session_state.get("locator_declined", set())
    ranked = [r for r in ranked if r["listing"].get("shop_id") not in declined]
    top = ranked[0] if ranked else None
    if top and top["identity"] == "confirmed" and top["listing"].get("profile_url"):
        db.update_facility(f["id"], {"locator_url": top["listing"]["profile_url"]})
        db.log(f["id"], "locator_linked", f"automatic: {', '.join(top['reasons'])}")
        st.rerun()

    candidates = [r for r in ranked if r["identity"] == "possible"][:3]
    if candidates:
        st.write(t("These shops near you are on CPN Auto Body Locator. Is one of them yours?"))
        for r in candidates:
            l = r["listing"]
            with st.container(border=True):
                a, b = st.columns([3, 1], vertical_alignment="center")
                phone = f"  \n{l['phones'][0][:3]}-{l['phones'][0][3:6]}-{l['phones'][0][6:]}" if l.get("phones") else ""
                a.markdown(f"**{l['name']}**  \n{l.get('address') or ''}{phone}")
                if b.button(t("This is my shop"), key=f"pick_{f['id']}_{l.get('shop_id')}"):
                    db.update_facility(f["id"], {"locator_url": l["profile_url"]})
                    db.log(f["id"], "locator_linked", f"chosen by shop: {l.get('shop_id')}")
                    st.rerun()
        st.caption(t("If none of these is your shop, you can ignore this. A listing you choose is still checked against your phone number and address before any certification is confirmed."))
    else:
        st.info(t("Your shop was not found on CPN Auto Body Locator near {postal}. Check that your phone number and street address match your OEM program listings. If you are not listed there, add your certifications on the Credentials tab and AIA Canada will confirm them.",
                  postal=lookup.postal_query(f["postal"])))


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
            flash(t("I-CAR® Gold Class® was added to your credentials because you answered yes to T2."), "info")
        if was_active and val != "yes":
            flash(t("Your declaration was withdrawn because {rid} is no longer a yes. Declare again once it is met.", rid=rid), "warning")
    except Exception as e:
        flash(t("Your answer to {rid} was not saved. {detail}", rid=rid, detail=err_text(e)), "error")


def _requirements(f, decls):
    answers = f.get("answers") or {}
    was_active = bool(active_declaration(decls))
    st.subheader(t("Minimum standards"))
    st.caption(t("Answer every item. Only a yes counts toward your declaration. If you use a qualified sublet provider where the requirement allows it, answer yes."))
    opts = list(ANSWERS)
    for sec in SECTIONS:
        items = [r for r in REQS if r[1] == sec]
        yes = sum(answers.get(r[0]) == "yes" for r in items)
        st.markdown(f"#### {section_label(sec)}")
        st.caption(t("{yes} of {n} yes", yes=yes, n=len(items)))
        for r in items:
            rid = r[0]
            with st.container(border=True):
                a, b = st.columns([1, 11])
                a.markdown(f"**{rid}**")
                with b:
                    st.write(req_text(r))
                    key = f"ans_{f['id']}_{rid}"
                    cur = answers.get(rid)
                    st.radio(t("Answer for {rid}", rid=rid), opts, index=opts.index(cur) if cur in opts else None, format_func=answer_label,
                             horizontal=True, key=key, label_visibility="collapsed", on_change=_save_answer,
                             args=(f["id"], rid, key, was_active))
                    if ai.available():
                        with st.expander(t("Explain this")):
                            _explain(r, f.get("province"))


def _explain(r, province):
    k = f"explain_{r[0]}_{province}_{lang()}"
    if k not in st.session_state and st.button(t("Get an explanation"), key=f"btn_{k}"):
        with st.spinner(t("Thinking")):
            try:
                st.session_state[k] = ai.explain(r[0], section_label(r[1]), req_text(r), province or "", lang())
            except Exception:
                st.error(t("The AI could not answer this time. Try again."))
    if k in st.session_state:
        st.write(st.session_state[k])
        st.caption(t("AI guidance explains the requirement. It does not decide whether your facility meets it."))


# ---------------------------------------------------------------- step 3
def _credentials(f, claims):
    t2_yes = (f.get("answers") or {}).get("T2") == "yes"
    st.subheader(t("Credentials"))
    st.caption(t("List your I-CAR® Gold Class® status and every manufacturer (OEM) certification you hold. Each one is confirmed with its program administrator before your badge is issued. Certifications listed on CPN Auto Body Locator are checked automatically within about an hour."))
    if f.get("locator_url"):
        listing = _linked_listing(f, _ranked(f))
        if listing:
            with st.container(border=True):
                st.markdown(t("**From your CPN Auto Body Locator listing** ({name})", name=listing["name"]))
                _add_listed(f, listing, key=f"add_listed_creds_{f['id']}")
    if not claims:
        st.info(t("No credentials listed yet."))
    for c in claims:
        state = claim_state(c)
        label, color = claim_label(state)
        with st.container(border=True):
            a, b = st.columns([4, 1])
            details = [t("Confirmed by {admin}", admin=admin_name(c["program"]))]
            if c.get("program_ref"):
                details.append(t("ID {ref}", ref=c["program_ref"]))
            if c.get("cert_number"):
                details.append(t("Certificate {number}", number=c["cert_number"]))
            if c.get("cert_expiry"):
                details.append(t("Expires {date}", date=fmt(c["cert_expiry"])))
            a.markdown(f"**{program_name(c)}**")
            a.caption(". ".join(details) + ".")
            b.markdown(chip(label, color))
            if state == "confirmed":
                st.caption(t("Confirmed on {date} through {source}. Next re-check {next}.", date=fmt(c.get("reviewed_at")),
                             source=c.get("source") or admin_name(c["program"]), next=fmt(c.get("recheck_at"))))
            elif state == "not_found" and c.get("note"):
                st.error(t("Reviewer note: {note}", note=c["note"]))
            elif state == "expired":
                st.error(t("The certificate expiry date has passed. Enter the renewed certificate details."))
            elif state == "review":
                st.caption(t("A reviewer is confirming this credential."))
            e1, e2, _ = st.columns([2, 1, 3])
            with e1.popover(t("Edit and resubmit")):
                with st.form(f"edit_{c['id']}"):
                    ref = st.text_input(t("Program or facility ID"), c.get("program_ref") or "")
                    num = st.text_input(t("Certificate number"), c.get("cert_number") or "")
                    exp = st.date_input(t("Certificate expiry"), value=date.fromisoformat(c["cert_expiry"]) if c.get("cert_expiry") else None)
                    if st.form_submit_button(t("Resubmit for review"), type="primary"):
                        try:
                            db.update_claim(c["id"], {"program_ref": ref.strip() or None, "cert_number": num.strip() or None,
                                                      "cert_expiry": exp.isoformat() if exp else None})
                            db.log(f["id"], "claim_resubmitted", c["program"])
                            flash(t("{program} resubmitted for review.", program=program_name(c)))
                            st.rerun()
                        except Exception as e:
                            st.error(t("That change was not saved. {detail}", detail=err_text(e)))
            if not (c["program"] == "icar-gold" and t2_yes):
                if e2.button(t("Remove"), key=f"rm_{c['id']}"):
                    db.delete_claim(c["id"])
                    db.log(f["id"], "claim_removed", c["program"])
                    st.rerun()

    st.markdown(f"#### {t('Add a credential')}")
    taken = {c["program"] for c in claims if c["program"] != "other"}
    options = [p for p in PROGRAMS if p not in taken]
    with st.form(f"add_claim_{f['id']}", clear_on_submit=True):
        prog = st.selectbox(t("Program"), options, index=None, placeholder=t("Select a program"),
                            format_func=lambda p: f"{program_name(p)} ({admin_name(p)})")
        other = st.text_input(t("Program name, if you chose Other program"))
        c1, c2, c3 = st.columns(3)
        ref = c1.text_input(t("Program or facility ID"), help=t("As shown on your program account or certificate"))
        num = c2.text_input(t("Certificate number"))
        exp = c3.date_input(t("Certificate expiry"), value=None)
        if st.form_submit_button(t("Add credential"), type="primary"):
            if not prog:
                st.error(t("Select a program."))
            elif prog == "other" and not other.strip():
                st.error(t("Enter the program name."))
            elif not ref.strip() and not num.strip():
                st.error(t("Enter a program ID or certificate number so the credential can be confirmed."))
            else:
                try:
                    db.add_claim(f["id"], {"program": prog, "other_name": other.strip() or None, "program_ref": ref.strip() or None,
                                           "cert_number": num.strip() or None, "cert_expiry": exp.isoformat() if exp else None})
                    db.log(f["id"], "claim_added", prog)
                    flash(t("{program} added. It will be confirmed with {admin}.", program=program_name(prog, other), admin=admin_name(prog)))
                    st.rerun()
                except Exception as e:
                    st.error(t("The credential could not be added. {detail}", detail=err_text(e)))


# ---------------------------------------------------------------- step 4
def _review(f, claims):
    answers = f.get("answers") or {}
    c = req_counts(answers)
    st.subheader(t("Review and guidance"))
    m = st.columns(4)
    m[0].metric(t("Yes"), c["yes"])
    m[1].metric(t("No"), c["no"])
    m[2].metric(t("Not sure"), c["unsure"])
    m[3].metric(t("Unanswered"), c["blank"])

    gaps = [r for r in REQS if answers.get(r[0]) != "yes"]
    bad = [x for x in claims if claim_state(x) in ("not_found", "expired")]
    if gaps:
        st.markdown(f"#### {t('Requirements to address ({n})', n=len(gaps))}")
        for r in gaps:
            a = answers.get(r[0])
            tag = chip(t("No"), "red") if a == "no" else chip(t("Not sure"), "blue") if a == "unsure" else chip(t("Unanswered"), "gray")
            st.markdown(f"**{r[0]}** {tag}  \n{req_text(r)}")
    if bad:
        st.markdown(f"#### {t('Credentials to fix ({n})', n=len(bad))}")
        for x in bad:
            st.markdown(f"**{program_name(x)}** {chip(claim_label(claim_state(x))[0], 'red')}" + (f"  \n{x['note']}" if x.get("note") else ""))

    st.markdown(f"#### {t('Gap plan')}")
    plan = f.get("gap_plan")
    if not gaps and not bad:
        st.write(t("Nothing to plan for. Every requirement is a yes and no credential is blocked."))
        return
    if not ai.available():
        st.info(t("AI guidance is not set up. Use the lists above to plan your next steps."))
    elif st.button(t("Rebuild my gap plan") if plan else t("Build my gap plan"), type="primary"):
        with st.spinner(t("Building your gap plan. This can take up to a minute.")):
            try:
                p = ai.gap_plan(
                    f,
                    [{"id": r[0], "section": section_label(r[1]), "requirement": req_text(r), "answer": answers.get(r[0]) or "unanswered"} for r in gaps],
                    [{"program": program_name(x), "administrator": admin_name(x["program"]),
                      "issue": "certificate expired" if claim_state(x) == "expired" else "could not be confirmed",
                      "reviewer_note": x.get("note") or ""} for x in bad])
                p["generated_at"] = now().isoformat()
                p["lang"] = lang()
                db.update_facility(f["id"], {"gap_plan": p})
                db.log(f["id"], "gap_plan")
                st.rerun()
            except Exception:
                st.error(t("The AI could not build a plan this time. Try again."))
    if plan:
        if plan.get("lang", "en") != lang():
            st.caption(t("This plan was written in another language. Rebuild it to get it in this language."))
        st.write(plan.get("summary", ""))
        for pr in ["high", "medium", "low"]:
            items = [i for i in plan.get("items", []) if str(i.get("priority", "medium")).lower() == pr]
            if not items:
                continue
            st.markdown(f"**{t(pr.title() + ' priority')}**")
            for i in items:
                who = ". ".join(x for x in [t("Owner: {owner}", owner=i["owner"]) if i.get("owner") else "",
                                            t("Target: {when}", when=i["timeframe"]) if i.get("timeframe") else ""] if x)
                res = "".join(f"\n  - {r}" for r in i.get("resources") or [])
                st.markdown(f"- **{i.get('id', '')}**: {i.get('action', '')}  \n  {who}{res}")
        for cg in plan.get("credentials") or []:
            st.markdown(f"- **{cg.get('program', '')}**: {cg.get('guidance', '')}")
        st.caption(t("Generated {date}. AI guidance suggests next steps. It does not decide whether your facility meets a requirement.", date=fmt(plan.get("generated_at"))))
        st.download_button(t("Download gap plan"), ai.plan_markdown(shop_name(f), plan, fmt(plan.get("generated_at"))),
                           file_name=f"gap-plan-{shop_name(f).lower().replace(' ', '-')}.md", mime="text/markdown")


# ---------------------------------------------------------------- step 5
def _declare(f, claims, decls):
    if f.get("suspended_at"):
        st.subheader(t("Declare"))
        st.error(t("AIA Canada revoked this facility on {date}. Reason: {reason}. You cannot declare until AIA Canada reinstates it. Contact AIA Canada to discuss.",
                   date=fmt(f["suspended_at"]), reason=f.get("suspended_reason") or t("not given")))
        return
    active = active_declaration(decls)
    if active:
        _active_declaration(f, claims, decls, active)
        return
    st.subheader(t("Declare"))
    c = req_counts(f.get("answers"))
    miss = profile_missing(f)
    if not c["all_yes"] or miss:
        st.write(t("You can declare once every requirement is a yes and your facility details are complete."))
        if not c["all_yes"]:
            st.warning(t("{n} requirements still need a yes. Go to the Requirements tab.", n=c["total"] - c["yes"]))
        if miss:
            st.warning(t("Facility details missing: {items}. Go to the Facility tab.", items=", ".join(miss)))
        last = latest_declaration(decls)
        if last:
            if last.get("withdrawn_at"):
                st.caption(t("Previous declaration {code} was withdrawn on {date}.", code=last["code"], date=fmt(last["withdrawn_at"])))
            else:
                st.caption(t("Previous declaration {code} expired on {date}.", code=last["code"], date=fmt(last["expires_at"])))
        return
    statements = [
        t("I am authorized to make this declaration on behalf of {name}.", name=shop_name(f)),
        t("Every requirement in {statement} applies to this facility, and each answer I gave is accurate.", statement=statement_name()),
        t("The credentials I listed are current, and AIA Canada may confirm them with the program administrators."),
        t("I will update this declaration if anything changes that affects a requirement or credential."),
        t("I understand my badge is issued only after every listed credential is confirmed, and that it expires after one year unless renewed."),
    ]
    st.write(t("Every requirement is a yes. Confirm each statement and sign to submit your declaration."))
    with st.form(f"declare_{f['id']}"):
        checks = [st.checkbox(s, key=f"att_{f['id']}_{i}") for i, s in enumerate(statements)]
        c1, c2 = st.columns(2)
        signer = c1.text_input(t("Full name"), f.get("rep_name") or "")
        title = c2.text_input(t("Title"), f.get("rep_title") or "")
        if st.form_submit_button(t("Submit declaration"), type="primary"):
            if not all(checks):
                st.error(t("Confirm every statement to declare."))
            elif not signer.strip():
                st.error(t("Enter your full name."))
            else:
                try:
                    d = db.declare(f["id"], signer.strip(), title.strip())
                    db.log(f["id"], "declared", d["code"])
                    all_ok = claims and all(claim_state(x) == "confirmed" for x in claims)
                    flash(t("Declaration submitted. Your badge is active.") if all_ok else
                          t("Declaration submitted. Your badge is issued once your credentials are confirmed."))
                    st.rerun()
                except Exception as e:
                    st.error(t("The declaration was not accepted. {detail}", detail=err_text(e)))


def _active_declaration(f, claims, decls, d):
    st.subheader(t("Your declaration"))
    days = max(0, (ts(d["expires_at"]) - now()).days)
    by = d["signer"] + (f", {d['title']}" if d.get("title") else "")
    st.markdown(
        f"| | |\n|---|---|\n| {t('Declaration ID')} | {d['code']} |\n| {t('Declared by')} | {by} |\n"
        f"| {t('Declared')} | {fmt(d['declared_at'])} |\n| {t('Valid until')} | {fmt(d['expires_at'])} ({t('{n} days', n=days)}) |\n"
        f"| {t('Statement')} | {statement_name()} |")
    confirmed = [program_name(c) for c in claims if claim_state(c) == "confirmed"]
    svg = badge_svg(shop_name(f), f.get("city"), f.get("province"), d["declared_at"], d["expires_at"], d["code"], confirmed)
    st.markdown(f"#### {t('Badge')}")
    if status(f, claims, decls) == "badge":
        st.write(t("Use this badge on your website, in your shop and on estimates."))
        show(st, svg)
        st.download_button(t("Download badge"), svg, file_name=f"aia-canada-badge-{d['code'].lower()}-{lang()}.svg", mime="image/svg+xml", type="primary")
    else:
        waiting = [program_name(c) for c in claims if claim_state(c) != "confirmed"]
        st.info(t("Your badge is issued when every credential is confirmed.") + " " +
                (t("Waiting on: {items}.", items=", ".join(waiting)) if waiting else t("Add at least one credential.")))
        st.markdown(f'<div style="max-width:460px;opacity:.45;filter:grayscale(1)">{svg}</div>', unsafe_allow_html=True)
    c1, c2, _ = st.columns([1, 1, 2])
    if days <= RENEW_WINDOW_DAYS and c1.button(t("Renew for another year")):
        try:
            nd = db.declare(f["id"], d["signer"], d.get("title") or "")
            db.log(f["id"], "renewed", nd["code"])
            flash(t("Declaration renewed."))
            st.rerun()
        except Exception as e:
            st.error(t("The renewal was not accepted. {detail}", detail=err_text(e)))
    with c2.popover(t("Withdraw declaration")):
        st.write(t("Your badge and directory listing are removed right away."))
        if st.button(t("Withdraw now"), type="primary", key=f"wd_{d['id']}"):
            db.withdraw(d["id"], "Withdrawn by the facility")
            db.log(f["id"], "withdrawn", d["code"])
            flash(t("Declaration withdrawn."), "info")
            st.rerun()
    st.caption(t("If anything changes that affects a requirement, change the answer. Your declaration is withdrawn automatically until the item is met again."))
