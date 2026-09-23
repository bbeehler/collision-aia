"""Checks one facility's credential claims against the locator and returns a result per brand."""
from datetime import datetime, timezone

from . import settings
from .brands import label
from .locator import search_url
from .match import best_match


def _note(reason, brand, m=None, err=None):
    b = label(brand)
    if reason == "confirmed":
        return f"Listed on CPN Auto Body Locator as {b} certified ({', '.join(m['reasons'])})."
    if reason == "brand_not_listed":
        return f"Shop found on the locator ({', '.join(m['reasons'])}), but it isn't listed for {b}."
    if reason == "identity_uncertain":
        l = m["listing"]
        return f'A possible listing was found ("{l["name"]}", {l.get("address") or "no address"}), but the match isn\'t strong enough to confirm automatically.'
    if reason == "shop_not_found":
        return "No listing on CPN Auto Body Locator matched this facility's name, address or phone number."
    if reason == "search_failed":
        return f"The locator search didn't complete ({err}). It will be retried."
    return f"{b} isn't checked on CPN Auto Body Locator. A reviewer needs to confirm it."


def verify_facility(locator, shop, brands, evidence_key=None):
    """
    shop: dict with legal_name, operating_name, street, city, province, postal, phone, website, email
    brands: claimed program IDs, e.g. ["ford", "kia"]
    """
    checked_at = datetime.now(timezone.utc).isoformat()
    on_locator = [b for b in brands if b in settings.LOCATOR_BRANDS]
    results = [{"brand": b, "outcome": "review", "reason": "not_on_locator", "note": _note("not_on_locator", b)}
               for b in brands if b not in settings.LOCATOR_BRANDS]
    if not on_locator:
        return {"checked_at": checked_at, "searches": [], "match": None, "results": results}

    queries = []
    if shop.get("locator_url"):
        try:
            pp = locator.profile_postal(shop["locator_url"])
            print(f"  locator profile {shop.get('locator_id')}: postal code {pp}")
            if pp:
                queries.append(pp)
        except Exception as e:
            print(f"  couldn't open locator profile: {str(e).splitlines()[0][:150]}")
    if shop.get("postal"):
        pc = "".join(shop["postal"].split()).upper()
        queries.append(f"{pc[:3]} {pc[3:]}" if len(pc) == 6 else pc)
    if shop.get("city"):
        queries.append(f"{shop['city']}, {shop.get('province') or ''}".strip(", "))

    queries = list(dict.fromkeys(queries))
    searches, best, err = [], None, None
    for q in queries:
        for page in range(1, settings.MAX_PAGES + 1):
            url = search_url(q, page)
            try:
                r = locator.load(url, f"{evidence_key}-{len(searches) + 1}" if evidence_key else None)
            except Exception as e:  # network or timeout
                err = str(e).splitlines()[0][:200]
                searches.append({"url": url, "error": err})
                break
            searches.append({"url": url, "total": r["total"], "listings": len(r["listings"]), "evidence": r["evidence"]})
            m = best_match(shop, r["listings"])
            if m and (best is None or (m["identity"] == "confirmed" and best["identity"] != "confirmed") or m["score"] > best["score"]):
                best = m
            per_page = len(r["listings"]) or 1
            if not r["listings"] or r["no_results"] or (r["total"] is not None and page * per_page >= r["total"]):
                break
            if best and best["identity"] == "confirmed":
                break
        if best and best["identity"] == "confirmed":
            break

    ok_search = any("error" not in s for s in searches)
    for b in on_locator:
        if not ok_search:
            reason = "search_failed"
        elif not best or best["identity"] == "none":
            reason = "shop_not_found"
        elif best["identity"] == "possible":
            reason = "identity_uncertain"
        elif b not in best["listing"]["brands"]:
            reason = "brand_not_listed"
        else:
            reason = "confirmed"
        outcome = "confirmed" if reason == "confirmed" and settings.AUTO_CONFIRM else "review"
        results.append({"brand": b, "outcome": outcome, "reason": reason, "note": _note(reason, b, best, err)})

    match = None
    if best:
        match = {"identity": best["identity"], "score": best["score"], "reasons": best["reasons"], "listing": best["listing"]}
    return {"checked_at": checked_at, "searches": searches, "match": match, "results": results}
