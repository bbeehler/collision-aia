"""AI guidance through the Anthropic API. The AI explains and suggests; it never decides compliance."""
import json
import re

import streamlit as st

from .config import PROVINCES, STATEMENT_VERSION

try:
    import anthropic
except ImportError:  # pragma: no cover
    anthropic = None

GUARDRAIL = ("You help Canadian collision repair shop owners with AIA Canada's Statement on minimum collision repair requirements "
             f"({STATEMENT_VERSION}). You explain requirements and suggest practical next steps. You do not decide whether a shop "
             "complies, and you do not give legal or safety verdicts. Where something depends on provincial or territorial rules, "
             "say so and suggest who to ask (AIA Canada, I-CAR Canada, a program administrator, or the provincial regulator). "
             "Be plain, practical and brief. Say when you are unsure.")


@st.cache_resource
def _client():
    key = st.secrets.get("ANTHROPIC_API_KEY")
    return anthropic.Anthropic(api_key=key) if (anthropic and key) else None


def available():
    return _client() is not None


def _model():
    return st.secrets.get("ANTHROPIC_MODEL", "claude-sonnet-5")


def _ask(prompt, max_tokens):
    msg = _client().messages.create(model=_model(), max_tokens=max_tokens, system=GUARDRAIL,
                                    messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()


@st.cache_data(ttl=7 * 24 * 3600, show_spinner=False)
def explain(req_id, section, text, province):
    prompt = (f'Explain requirement {req_id} ({section}): "{text}"\n'
              f"The shop is in {PROVINCES.get(province, 'Canada')}.\n"
              "Cover what it means in practice, what typically counts as meeting it, common gaps, and what the owner should "
              "check or gather. Plain text, no headings, under 170 words.")
    return _ask(prompt, 600)


def _parse_json(text):
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("{"), text.rfind("}")
    return json.loads(text[start:end + 1])


def gap_plan(facility, gaps, bad_claims):
    prompt = (
        f"Facility: {json.dumps({'province': PROVINCES.get(facility.get('province'), ''), 'scope': facility.get('scope') or []})}\n"
        f"Requirements not yet met: {json.dumps(gaps)}\n"
        f"Credentials that couldn't be confirmed: {json.dumps(bad_claims)}\n\n"
        "Build a gap plan. Where a requirement allows a qualified sublet provider, mention that option. Return only JSON:\n"
        '{"summary": "2-3 sentences on overall readiness and where to start", '
        '"items": [{"id": "requirement ID", "priority": "high|medium|low", "action": "one concrete next step", '
        '"owner": "suggested role at the shop", "timeframe": "realistic target", "resources": ["where to get help"]}], '
        '"credentials": [{"program": "program name", "guidance": "what to do next"}]}\n'
        "Include one item per requirement listed. Use an empty credentials array if none."
    )
    data = _parse_json(_ask(prompt, 3000))
    return {"summary": str(data.get("summary", "")), "items": list(data.get("items") or [])[:40],
            "credentials": list(data.get("credentials") or [])[:20]}


def plan_markdown(name, plan, generated):
    out = [f"# Gap plan: {name}", "", f"Generated {generated} against AIA Canada's {STATEMENT_VERSION}.", "", plan.get("summary", "")]
    for pr in ["high", "medium", "low"]:
        items = [i for i in plan.get("items", []) if str(i.get("priority", "medium")).lower() == pr]
        if items:
            out += ["", f"## {pr.title()} priority"]
            for i in items:
                out += ["", f"**{i.get('id', '')}**: {i.get('action', '')}", f"- Owner: {i.get('owner', '')}", f"- Target: {i.get('timeframe', '')}"]
                out += [f"- Resource: {r}" for r in i.get("resources") or []]
    if plan.get("credentials"):
        out += ["", "## Credentials"] + [f"\n**{c.get('program', '')}**: {c.get('guidance', '')}" for c in plan["credentials"]]
    out += ["", "---", "AI guidance suggests next steps. It doesn't decide whether the facility meets a requirement."]
    return "\n".join(out)
