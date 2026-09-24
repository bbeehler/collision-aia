import streamlit as st

from ..i18n import t


def flash(msg, kind="success"):
    st.session_state.flash = (kind, msg)


def show_flash():
    f = st.session_state.pop("flash", None)
    if f:
        getattr(st, f[0])(f[1])


def shop_name(f):
    return (f.get("operating_name") or "").strip() or f.get("legal_name") or t("Unnamed facility")


def err_text(e):
    msg = getattr(e, "message", None) or str(e)
    known = {
        "Every requirement must be answered yes before declaring.": "Every requirement must be answered yes before declaring.",
        "This facility has been revoked by AIA Canada. Contact AIA Canada for details.": "This facility has been revoked by AIA Canada. Contact AIA Canada for details.",
    }
    for k in known:
        if k in msg:
            return t(known[k])
    return msg


def chip(label, color):
    return f":{color}-background[{label}]"
