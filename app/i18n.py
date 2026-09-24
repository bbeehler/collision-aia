"""English and French. English text is the key; French lives in i18n_fr.py. Add ?lang=fr to a link to open in French."""
import streamlit as st

from .i18n_fr import FR

LANGS = {"en": "English", "fr": "Français"}
_MONTHS_EN = ["Jan.", "Feb.", "March", "April", "May", "June", "July", "Aug.", "Sept.", "Oct.", "Nov.", "Dec."]  # Canadian Press
_MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]


def lang():
    q = st.query_params.get("lang")
    if q in LANGS and st.session_state.get("_lang_from_url") != q:
        st.session_state.lang = q
        st.session_state._lang_from_url = q
    return st.session_state.get("lang", "en")


def set_lang(code):
    st.session_state.lang = code
    st.session_state._lang_from_url = code
    st.query_params["lang"] = code


def t(text, **kw):
    s = FR.get(text, text) if lang() == "fr" else text
    return s.format(**kw) if kw else s


def pick(en, fr):
    return fr if lang() == "fr" else en


def fmt_date(d):
    if d is None:
        return ""
    if lang() == "fr":
        return f"{'1er' if d.day == 1 else d.day} {_MONTHS_FR[d.month - 1]} {d.year}"
    return f"{_MONTHS_EN[d.month - 1]} {d.day}, {d.year}"
