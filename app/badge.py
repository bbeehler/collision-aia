"""The badge: AIA Canada reverse logo on a dark-blue band, with the red edge bar, square corners and no gradients."""
from html import escape

from .badge_logo import LOGO_SIZE, REVERSE_LOGO_PNG
from .config import province_name
from .i18n import t
from .logic import fmt

FONT = "font-family=\"'Sofia Pro', sofia-pro, Arial, sans-serif\""
NAVY, RED, LIGHT = "#192b56", "#e21c47", "#84c8e3"


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
    e = lambda s: escape(str(s or ""), quote=True)
    name = name if len(name) <= 36 else name[:35] + "…"
    cred = _wrap(", ".join(credentials) if credentials else t("Pending confirmation"), 50)[:3]
    loc = ", ".join(x for x in [city, province_name(province)] if x)
    head = _wrap(t("Meets the minimum Canadian standards in collision repair"), 30)[:3]
    foot = _wrap(t("Requirements self-declared by the facility. Check this badge at the AIA Canada Check a badge page."), 70)[:2]
    w, h_logo = 460, 64
    lw = round(LOGO_SIZE[0] * h_logo / LOGO_SIZE[1])
    band = 108                       # logo plus one maple-leaf height of clear space above and below
    x0 = 30                          # red edge bar, then clear space before the logo and content
    top = band + 30
    cred_y = top + 141
    h = cred_y + len(cred) * 17 + 18 + len(foot) * 13 + 8
    head_size = 19 if len(head) <= 2 else 17
    step = head_size + 3
    head_top = band / 2 - (len(head) - 1) * step / 2 + head_size * 0.35
    head_svg = "".join(f'<text x="{x0 + lw + 34}" y="{head_top + i * step}" {FONT} font-size="{head_size}" font-weight="700" fill="#ffffff">{e(l)}</text>'
                       for i, l in enumerate(head))
    rows = "".join(f'<text x="{x0}" y="{cred_y + i * 17}" {FONT} font-size="13.5" font-weight="700" fill="{NAVY}">{e(l)}</text>'
                   for i, l in enumerate(cred))
    foot_y = cred_y + len(cred) * 17 + 14
    foot_svg = "".join(f'<text x="{x0}" y="{foot_y + i * 13}" {FONT} font-size="10" fill="{NAVY}">{e(l)}</text>' for i, l in enumerate(foot))
    col = [x0, 178, 322]
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" viewBox="0 0 {w} {h}" width="{w}" role="img" aria-label="{e(t('AIA Canada badge for {name}', name=name))}">
<rect x="0" y="0" width="{w}" height="{h}" fill="#ffffff" stroke="{NAVY}" stroke-width="2"/>
<rect x="0" y="0" width="{w}" height="{band}" fill="{NAVY}"/>
<rect x="0" y="0" width="8" height="{h}" fill="{RED}"/>
<image x="{x0}" y="{(band - h_logo) / 2}" width="{lw}" height="{h_logo}" href="data:image/png;base64,{REVERSE_LOGO_PNG}" xlink:href="data:image/png;base64,{REVERSE_LOGO_PNG}"/>
{head_svg}
<text x="{x0}" y="{top}" {FONT} font-size="11" fill="{NAVY}">{e(t('Facility'))}</text>
<text x="{x0}" y="{top + 22}" {FONT} font-size="20" font-weight="700" fill="{NAVY}">{e(name)}</text>
<text x="{x0}" y="{top + 42}" {FONT} font-size="13" fill="{NAVY}">{e(loc)}</text>
<line x1="8" y1="{top + 56}" x2="{w}" y2="{top + 56}" stroke="{LIGHT}" stroke-width="2"/>
<text x="{col[0]}" y="{top + 76}" {FONT} font-size="11" fill="{NAVY}">{e(t('Self-declared'))}</text>
<text x="{col[0]}" y="{top + 95}" {FONT} font-size="14" font-weight="700" fill="{NAVY}">{e(fmt(declared_at))}</text>
<text x="{col[1]}" y="{top + 76}" {FONT} font-size="11" fill="{NAVY}">{e(t('Valid until'))}</text>
<text x="{col[1]}" y="{top + 95}" {FONT} font-size="14" font-weight="700" fill="{NAVY}">{e(fmt(expires_at))}</text>
<text x="{col[2]}" y="{top + 76}" {FONT} font-size="11" fill="{NAVY}">{e(t('Declaration ID'))}</text>
<text x="{col[2]}" y="{top + 95}" {FONT} font-size="14" font-weight="700" fill="{NAVY}">{e(code)}</text>
<line x1="8" y1="{top + 108}" x2="{w}" y2="{top + 108}" stroke="{LIGHT}" stroke-width="2"/>
<text x="{x0}" y="{top + 124}" {FONT} font-size="11" fill="{NAVY}">{e(t('Credentials confirmed by AIA Canada'))}</text>
{rows}
{foot_svg}
</svg>"""


def show(st, svg, max_width=460):
    st.markdown(f'<div style="max-width:{max_width}px">{svg}</div>', unsafe_allow_html=True)
