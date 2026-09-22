import streamlit as st


def flash(msg, kind="success"):
    st.session_state.flash = (kind, msg)


def show_flash():
    f = st.session_state.pop("flash", None)
    if f:
        getattr(st, f[0])(f[1])


def shop_name(f):
    return (f.get("operating_name") or "").strip() or f.get("legal_name") or "Unnamed facility"


def err_text(e):
    return getattr(e, "message", None) or str(e)


def chip(label, color):
    return f":{color}-background[{label}]"
