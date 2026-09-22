"""The badge, styled like a vehicle door-jamb certification label."""
from html import escape

from .logic import fmt
from .config import PROVINCES

FONT = "font-family=\"Archivo, 'Arial Narrow', Arial, sans-serif\""


def _wrap(text, width):
    lines, line = [], ""
    for w in text.split():
        if len((line + " " + w).strip()) > width:
            lines.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        lines.append(line)
    return lines


def badge_svg(name, city, province, declared_at, expires_at, code, credentials):
    name = name if len(name) <= 38 else name[:37] + "…"
    cred = _wrap(", ".join(credentials) if credentials else "Pending confirmation", 52)[:3]
    h = 268 + len(cred) * 16
    loc = ", ".join(x for x in [city, PROVINCES.get(province, province)] if x)
    e = lambda s: escape(str(s or ""), quote=True)
    rows = "".join(f'<text x="20" y="{226 + i * 16}" {FONT} font-size="13" font-weight="650" fill="#1B2126">{e(l)}</text>' for i, l in enumerate(cred))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 440 {h}" width="440" role="img" aria-label="AIA Canada minimum requirements badge for {e(name)}">
<rect x="1.5" y="1.5" width="437" height="{h - 3}" rx="8" fill="#FFFFFF" stroke="#1B2126" stroke-width="3"/>
<rect x="1.5" y="1.5" width="437" height="58" rx="8" fill="#1D4F91"/><rect x="1.5" y="40" width="437" height="20" fill="#1D4F91"/>
<text x="20" y="28" {FONT} font-size="13" font-weight="700" fill="#DCE6F3">AIA CANADA</text>
<text x="20" y="48" {FONT} font-size="15.5" font-weight="800" fill="#FFFFFF">Meets the minimum collision repair requirements</text>
<text x="20" y="84" {FONT} font-size="10.5" fill="#4A5561">Facility</text>
<text x="20" y="104" {FONT} font-size="18" font-weight="800" fill="#1B2126">{e(name)}</text>
<text x="20" y="124" {FONT} font-size="12.5" fill="#1B2126">{e(loc)}</text>
<line x1="1.5" y1="140" x2="438.5" y2="140" stroke="#1B2126" stroke-width="1.5"/>
<line x1="150" y1="140" x2="150" y2="188" stroke="#1B2126" stroke-width="1.5"/><line x1="296" y1="140" x2="296" y2="188" stroke="#1B2126" stroke-width="1.5"/>
<text x="20" y="158" {FONT} font-size="10.5" fill="#4A5561">Self-declared</text><text x="20" y="177" {FONT} font-size="13.5" font-weight="700" fill="#1B2126">{e(fmt(declared_at))}</text>
<text x="166" y="158" {FONT} font-size="10.5" fill="#4A5561">Valid until</text><text x="166" y="177" {FONT} font-size="13.5" font-weight="700" fill="#1B2126">{e(fmt(expires_at))}</text>
<text x="312" y="158" {FONT} font-size="10.5" fill="#4A5561">Declaration ID</text><text x="312" y="177" {FONT} font-size="13.5" font-weight="700" fill="#1B2126">{e(code)}</text>
<line x1="1.5" y1="188" x2="438.5" y2="188" stroke="#1B2126" stroke-width="1.5"/>
<text x="20" y="207" {FONT} font-size="10.5" fill="#4A5561">Credentials confirmed with program administrators</text>
{rows}
<line x1="1.5" y1="{h - 46}" x2="438.5" y2="{h - 46}" stroke="#1B2126" stroke-width="1.5"/>
<text x="20" y="{h - 28}" {FONT} font-size="9.5" fill="#4A5561">Requirements self-declared by the facility against AIA Canada's Statement.</text>
<text x="20" y="{h - 14}" {FONT} font-size="9.5" fill="#4A5561">Credentials confirmed by AIA Canada with each program administrator.</text>
</svg>"""


def show(st, svg, max_width=440):
    st.markdown(f'<div style="max-width:{max_width}px">{svg}</div>', unsafe_allow_html=True)
