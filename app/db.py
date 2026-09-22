"""Supabase access. Each browser session gets its own client so row-level security applies per user."""
from datetime import datetime, timedelta, timezone

import streamlit as st
from supabase import Client, create_client


def sb() -> Client:
    if "_sb" not in st.session_state:
        st.session_state._sb = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_ANON_KEY"])
    return st.session_state._sb


def _now():
    return datetime.now(timezone.utc).isoformat()


# ---------- auth ----------
def user():
    return st.session_state.get("user")


def uid():
    u = user()
    return u["id"] if u else None


def _set_session(session):
    st.session_state.user = {"id": session.user.id, "email": session.user.email}
    st.session_state.goto_facility = True
    sb().postgrest.auth(session.access_token)
    try:
        st.session_state.is_admin = bool(sb().rpc("is_admin").execute().data)
    except Exception:
        st.session_state.is_admin = False


def restore_session():
    """Called on every run: refreshes the access token when it has expired."""
    if not user():
        return
    try:
        s = sb().auth.get_session()
    except Exception:
        s = None
    if s:
        sb().postgrest.auth(s.access_token)
    else:
        sign_out()


def sign_in(email, password):
    res = sb().auth.sign_in_with_password({"email": email, "password": password})
    _set_session(res.session)


def sign_up(email, password):
    res = sb().auth.sign_up({"email": email, "password": password})
    if res.session:
        _set_session(res.session)
        return True
    return False  # email confirmation required


def sign_out():
    try:
        sb().auth.sign_out()
    except Exception:
        pass
    for k in ["_sb", "user", "is_admin", "facility_id"]:
        st.session_state.pop(k, None)


def is_admin():
    return bool(st.session_state.get("is_admin"))


# ---------- shop data ----------
def my_facilities():
    return sb().table("facilities").select("*").eq("owner_id", uid()).order("created_at").execute().data


def facility(fid):
    return sb().table("facilities").select("*").eq("id", fid).single().execute().data


def create_facility(legal_name):
    return sb().table("facilities").insert({"legal_name": legal_name, "owner_id": uid()}).execute().data[0]


def update_facility(fid, fields):
    sb().table("facilities").update(fields).eq("id", fid).execute()


def claims(fid):
    return sb().table("credential_claims").select("*").eq("facility_id", fid).order("created_at").execute().data


def add_claim(fid, data):
    sb().table("credential_claims").insert({"facility_id": fid, **data}).execute()


def update_claim(cid, data):
    sb().table("credential_claims").update(data).eq("id", cid).execute()


def delete_claim(cid):
    sb().table("credential_claims").delete().eq("id", cid).execute()


def declarations(fid):
    return sb().table("declarations").select("*").eq("facility_id", fid).order("declared_at", desc=True).execute().data


def declare(fid, signer, title):
    return sb().table("declarations").insert({"facility_id": fid, "signer": signer, "title": title}).execute().data[0]


def withdraw(did, reason):
    sb().table("declarations").update({"withdrawn_at": _now(), "withdrawn_reason": reason}).eq("id", did).execute()


def log(fid, type_, detail=""):
    try:
        sb().table("facility_history").insert({"facility_id": fid, "type": type_, "detail": detail}).execute()
    except Exception:
        pass


# ---------- reviewers ----------
def all_facilities():
    return sb().table("facilities").select("*").order("legal_name").execute().data


def all_claims():
    return sb().table("credential_claims").select("*").order("submitted_at").execute().data


def all_declarations():
    return sb().table("declarations").select("*").order("declared_at", desc=True).execute().data


def review_claim(cid, status, source, note):
    data = {"status": status, "source": source if status == "confirmed" else None, "note": note or None,
            "reviewed_at": _now(), "reviewed_by": uid(), "review_reason": None,
            "recheck_at": None}
    if status == "confirmed":
        data["recheck_at"] = (datetime.now(timezone.utc) + timedelta(days=365)).isoformat()
    sb().table("credential_claims").update(data).eq("id", cid).execute()


def latest_run(cid):
    rows = sb().table("verification_runs").select("*").eq("claim_id", cid).order("ran_at", desc=True).limit(1).execute().data
    return rows[0] if rows else None


def evidence_url(path):
    try:
        return sb().storage.from_("verification-evidence").create_signed_url(path, 600)["signedURL"]
    except Exception:
        return None


# ---------- public ----------
def directory():
    return sb().rpc("get_directory").execute().data
