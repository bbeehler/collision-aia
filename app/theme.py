"""AIA Canada look and feel: logo, red edge bar, header language switch, footer."""
import base64
from pathlib import Path

import streamlit as st

from .i18n import lang, pick, set_lang, t

ASSETS = Path(__file__).resolve().parent.parent / "assets"
LOGO_POSITIVE = str(ASSETS / "aia-canada-positive.png")
LOGO_REVERSE = str(ASSETS / "aia-canada-reverse.png")


@st.cache_resource
def logo_b64(which="reverse"):
    return base64.b64encode((ASSETS / f"aia-canada-{which}.png").read_bytes()).decode()


_CSS = """
<style>
%(font_import)s
:root { --aia-dark-blue:#192b56; --aia-red:#e21c47; --aia-light-blue:#84c8e3; --aia-blue-tint:#f2f7fa; }
html, body, .stApp, .stMarkdown, button, input, textarea, select, label { font-family:'Sofia Pro', sofia-pro, Arial, sans-serif; }
/* Red edge bar down the left of every page */
.stApp::before { content:""; position:fixed; left:0; top:0; bottom:0; width:clamp(8px, 1.4vw, 18px); background:var(--aia-red); z-index:999991; }
.block-container { padding-left:calc(clamp(8px, 1.4vw, 18px) + 2rem); padding-top:4.5rem; }
header[data-testid="stHeader"] { padding-left:calc(clamp(8px, 1.4vw, 18px) + 1.25rem); }
[data-testid="stLogo"] { height:2.5rem; margin-right:1rem; }
h1, h2, h3, h4 { color:var(--aia-dark-blue); font-weight:700; letter-spacing:0; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color:var(--aia-dark-blue); opacity:.85; }
*, *::before, *::after { box-shadow:none !important; }
/* Secondary buttons: dark-blue outline. Primary buttons use the theme red with a white label. */
.stButton button[kind="secondary"], [data-testid="stFormSubmitButton"] button[kind="secondaryFormSubmit"],
[data-testid="stPopover"] button, .stDownloadButton button[kind="secondary"], .stLinkButton a {
  border:2px solid var(--aia-dark-blue) !important; color:var(--aia-dark-blue) !important; background:#fff; font-weight:700; }
.stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primaryFormSubmit"], .stDownloadButton button[kind="primary"] { font-weight:700; }
/* Alerts: a coloured bar on the left, echoing the edge bar */
[data-testid="stAlertContainer"] { border-left:4px solid var(--aia-dark-blue); }
[data-testid="stAlertContentError"] { color:var(--aia-red); }
div:has(> [data-testid="stAlertContentError"]) { border-left-color:var(--aia-red); }
/* Brand panels */
.aia-hero { background:var(--aia-dark-blue); color:#fff; padding:2.5rem 2.25rem; margin:0 0 1.5rem; display:flex; gap:2rem; align-items:center; }
.aia-hero img { height:120px; width:auto; padding:0 .5rem; }
.aia-hero h1 { color:#fff !important; font-size:2.6rem; line-height:1.05; margin:0 0 .75rem; padding:0; }
.aia-hero p { color:var(--aia-light-blue); font-size:1.3rem; line-height:1.35; margin:0; }
.aia-footer { background:var(--aia-blue-tint); margin-top:3rem; padding:1.5rem 1.75rem; font-size:.85rem; line-height:1.6; }
.aia-footer a { color:var(--aia-dark-blue); margin-right:1.25rem; }
@media (max-width: 640px) { .aia-hero { flex-direction:column; align-items:flex-start; } .aia-hero img { height:90px; } }
</style>
"""


def apply():
    kit = ""
    try:
        kit = st.secrets.get("ADOBE_FONTS_KIT", "")
    except Exception:
        pass
    font_import = f'@import url("https://use.typekit.net/{kit}.css");' if kit else ""
    st.markdown(_CSS % {"font_import": font_import}, unsafe_allow_html=True)
    st.logo(LOGO_POSITIVE, size="large", link=pick("https://www.aiacanada.com/", "https://www.aiacanada.com/fr/"),
            icon_image=LOGO_POSITIVE)


def language_switch():
    """Mirrors the Français / English link in the aiacanada.com header."""
    other = "fr" if lang() == "en" else "en"
    _, c = st.columns([5, 1])
    if c.button("Français" if other == "fr" else "English", key="lang_switch", type="tertiary"):
        set_lang(other)
        st.rerun()


def hero(title, standfirst):
    st.markdown(
        f'<div class="aia-hero"><img src="data:image/png;base64,{logo_b64("reverse")}" alt="AIA Canada">'
        f'<div><h1>{title}</h1><p>{standfirst}</p></div></div>', unsafe_allow_html=True)


def footer():
    fr = lang() == "fr"
    base = "https://www.aiacanada.com/fr/" if fr else "https://www.aiacanada.com/"
    links = [
        (t("About us"), base + ("a-propos-de-nous/" if fr else "about-us/")),
        (t("Privacy policy"), base + ("politique-de-confidentialite/" if fr else "privacy-policy/")),
        (t("Terms of use"), base + ("conditions-dutilisation/" if fr else "terms-of-use/")),
        (t("Collision repair Statement"), base + ("declaration-2025-de-laia-canada-sur-les-normes-canadiennes-minimales-en-matiere-de-reparation-de-carrosserie/"
                                                  if fr else "2025-aia-canada-statement-on-minimum-canadian-standard-in-collision-repair/")),
    ]
    address = ("Association des industries de l’automobile du Canada<br>B.P. 11356, STATION H, Nepean (Ontario) K2H 7V1"
               if fr else "Automotive Industries Association of Canada<br>PO Box 11356 STN H, Nepean, ON K2H 7V1")
    st.markdown(
        f'<div class="aia-footer"><strong>{address}</strong><br>'
        f'{t("Toll free")} 800.808.2920 · <a href="mailto:info@aiacanada.com">info@aiacanada.com</a><br><br>'
        + "".join(f'<a href="{u}" target="_blank">{l}</a>' for l, u in links) + "</div>", unsafe_allow_html=True)
