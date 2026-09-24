"""Status rules shared by every page."""
import re
from datetime import date, datetime, timezone

from .config import REQS
from .i18n import fmt_date, t


def ts(value):
    """Parse a Supabase timestamp or date string."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    s = str(value).replace("Z", "+00:00")
    s = re.sub(r"\.(\d+)", lambda m: "." + m.group(1)[:6].ljust(6, "0"), s)
    try:
        d = datetime.fromisoformat(s)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def fmt(value):
    return fmt_date(ts(value))


def now():
    return datetime.now(timezone.utc)


def claim_state(c):
    exp = c.get("cert_expiry")
    if exp and date.fromisoformat(str(exp)[:10]) < date.today():
        return "expired"
    if c.get("status") == "confirmed" and c.get("recheck_at") and ts(c["recheck_at"]) < now():
        return "recheck"
    return c.get("status") or "pending"


# English labels; translate with t() where shown. Colours map to the AIA Canada palette in .streamlit/config.toml.
CLAIM_LABEL = {
    "pending": ("In review", "blue"), "review": ("In review", "blue"), "recheck": ("Re-check due", "blue"),
    "confirmed": ("Confirmed", "green"), "not_found": ("Could not confirm", "red"), "expired": ("Certificate expired", "red"),
}


def claim_label(state):
    label, color = CLAIM_LABEL[state]
    return t(label), color


def req_counts(answers):
    a = answers or {}
    vals = [a.get(r[0]) for r in REQS]
    yes, no, unsure = vals.count("yes"), vals.count("no"), vals.count("unsure")
    return {"yes": yes, "no": no, "unsure": unsure, "blank": len(REQS) - yes - no - unsure, "total": len(REQS), "all_yes": yes == len(REQS)}


def profile_missing(f):
    miss = []
    if not f.get("legal_name"):
        miss.append(t("legal business name"))
    if not f.get("street"):
        miss.append(t("street address"))
    if not f.get("city"):
        miss.append(t("city"))
    if not f.get("province"):
        miss.append(t("province or territory"))
    if not re.match(r"^[A-Za-z]\d[A-Za-z][ -]?\d[A-Za-z]\d$", (f.get("postal") or "").strip()):
        miss.append(t("valid postal code"))
    if not f.get("rep_name"):
        miss.append(t("authorized representative"))
    if not f.get("rep_email"):
        miss.append(t("representative email"))
    return miss


def active_declaration(decls):
    for d in decls or []:
        if not d.get("withdrawn_at") and ts(d["expires_at"]) > now():
            return d
    return None


def latest_declaration(decls):
    return (decls or [None])[0]


def status(f, claims, decls):
    if f.get("suspended_at"):
        return "suspended"
    active = active_declaration(decls)
    if not active:
        last = latest_declaration(decls)
        if last and not last.get("withdrawn_at") and ts(last["expires_at"]) <= now():
            return "expired"
        return "ready" if req_counts(f.get("answers"))["all_yes"] else "draft"
    states = [claim_state(c) for c in claims]
    if any(s in ("not_found", "expired") for s in states):
        return "action"
    if not states or any(s in ("pending", "review", "recheck") for s in states):
        return "verifying"
    return "badge"


STATUS = {
    "draft": ("Self-check in progress", "gray"), "ready": ("Ready to declare", "blue"),
    "verifying": ("Declared, credentials in review", "blue"), "action": ("Action needed on credentials", "red"),
    "badge": ("Badge active", "green"), "expired": ("Declaration expired", "red"),
    "suspended": ("Revoked by AIA Canada", "red"),
}


def status_label(key):
    label, color = STATUS[key]
    return t(label), color


def status_line(f, claims, decls):
    key = status(f, claims, decls)
    c = req_counts(f.get("answers"))
    d = active_declaration(decls) or latest_declaration(decls)
    if key == "draft":
        return t("{n} of {total} requirements still need a yes.", n=c["total"] - c["yes"], total=c["total"])
    if key == "ready":
        return t("Every requirement is answered yes. Check your credentials, then declare.")
    if key == "verifying":
        return t("Your declaration is in. Your credentials are being confirmed with the program administrators.")
    if key == "action":
        return t("One or more credentials could not be confirmed. Update or remove them to receive your badge.")
    if key == "badge":
        return t("Your badge is active until {date}.", date=fmt(d and d["expires_at"]))
    if key == "expired":
        return t("Your declaration expired on {date}. Check your answers and declare again.", date=fmt(d and d["expires_at"]))
    return t("AIA Canada revoked this facility on {date}: {reason} Contact AIA Canada to discuss reinstatement.",
             date=fmt(f.get("suspended_at")), reason=f.get("suspended_reason") or "")
