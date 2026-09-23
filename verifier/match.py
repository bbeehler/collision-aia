"""Decides whether a locator listing is the facility that made the claim."""
import re

from .brands import normalize
from .parse import digits

NAME_STOP = set(
    "auto autos autobody body collision collisions centre center centres ltd inc limited corp co the and de du des la le les et "
    "carrosserie repair repairs shop services service automotive ltee enr group groupe canada".split()
)
STREET_STOP = set(
    "st street rd road ave avenue blvd boulevard dr drive rue ch chemin boul way cres crescent crt court pl place hwy highway "
    "unit suite n s e w north south east west nord sud est ouest".split()
)
FREE_MAIL = re.compile(r"gmail|hotmail|outlook|yahoo|live|icloud|bell|rogers|shaw|telus|videotron|sympatico")


def _tokens(s, stop):
    return [t for t in re.sub(r"[^a-z0-9 ]", " ", normalize(s)).split() if len(t) > 1 and t not in stop]


def _jaccard(a, b):
    if not a or not b:
        return 0.0
    A, B = set(a), set(b)
    return len(A & B) / len(A | B)


def _street_number(s):
    m = re.match(r"^\s*(\d+[a-z]?)\b", str(s or ""), re.I)
    return m.group(1).lower() if m else None


def _domain(s):
    m = re.search(r"(?:@|//|^)(?:www\.)?([a-z0-9-]+\.[a-z0-9.-]+)", str(s or "").lower())
    return m.group(1) if m else None


def score_listing(shop, listing):
    id_match = bool(shop.get("locator_id")) and listing.get("shop_id") == str(shop["locator_id"])
    reasons = ["CPN Auto Body Locator profile matches"] if id_match else []
    shop_phone = digits(shop.get("phone"))[-10:]
    phone = len(shop_phone) == 10 and shop_phone in listing["phones"]
    if phone:
        reasons.append("phone number matches")

    num, lnum = _street_number(shop.get("street")), _street_number(listing.get("address"))
    street_num = bool(num) and num == lnum
    s_tok = _tokens(re.sub(r"^\s*\d+[a-z]?\s*", "", str(shop.get("street") or ""), flags=re.I), STREET_STOP)
    a_tok = set(_tokens(listing.get("address") or "", STREET_STOP))
    overlap = sum(t in a_tok for t in s_tok) / len(s_tok) if s_tok else 0
    street = street_num and overlap >= 0.5
    if street:
        reasons.append("street address matches")
    elif street_num:
        reasons.append("street number matches")

    l_name = _tokens(listing["name"], NAME_STOP)
    name_sim = max(_jaccard(_tokens(shop.get("legal_name") or "", NAME_STOP), l_name),
                   _jaccard(_tokens(shop.get("operating_name") or "", NAME_STOP), l_name))
    if name_sim >= 0.34:
        reasons.append(f"name similarity {round(name_sim * 100)}%")

    shop_dom = _domain(shop.get("website")) or _domain(shop.get("email"))
    list_dom = _domain(listing.get("email")) or next((d for d in map(_domain, listing.get("links") or []) if d), None)
    web = bool(shop_dom) and shop_dom == list_dom and not FREE_MAIL.search(shop_dom)
    if web:
        reasons.append("email or website domain matches")

    score = min(100, (45 if phone else 0) + (30 if street else 10 if street_num else 0) + round(name_sim * 25) + (15 if web else 0))
    if id_match and (phone or street_num or name_sim >= 0.5):
        identity, score = "confirmed", 100
    elif (phone and (street or name_sim >= 0.34 or web)) or (street and (name_sim >= 0.34 or web)):
        identity = "confirmed"
    elif id_match or phone or street or name_sim >= 0.6:
        identity = "possible"
    else:
        identity = "none"
    return {"identity": identity, "score": score, "reasons": reasons, "name_sim": round(name_sim, 2)}


_RANK = {"confirmed": 2, "possible": 1, "none": 0}


def best_match(shop, listings):
    best = None
    for l in listings:
        s = score_listing(shop, l)
        if best is None or (_RANK[s["identity"]], s["score"]) > (_RANK[best["identity"]], best["score"]):
            best = {**s, "listing": l}
    return best
