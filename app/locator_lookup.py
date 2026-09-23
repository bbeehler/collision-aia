"""Finds a facility on CPN Auto Body Locator from the details it entered. The results page is plain HTML."""
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from verifier.match import score_listing
from verifier.parse import is_shop_card, parse_card

SEARCH_URL = "https://autobodylocator.ca/search"
USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 "
              "AIACanada-CredentialCheck/1.0")
_RANK = {"confirmed": 2, "possible": 1, "none": 0}


def postal_query(postal):
    pc = "".join((postal or "").split()).upper()
    return f"{pc[:3]} {pc[3:]}" if len(pc) == 6 else pc


def search_url(postal):
    return requests.Request("GET", SEARCH_URL, params={"search": postal_query(postal), "radius": "25", "type": "canada",
                                                      "country": "CA", "lang": "en"}).prepare().url


def extract(html, base=SEARCH_URL):
    """Each shop card is the largest element around a name heading that holds no other shop heading."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for h in soup.find_all("h4"):
        el = h
        while el.parent is not None and el.parent.name not in ("body", "html", "[document]") and len(el.parent.find_all("h4")) == 1:
            el = el.parent
        raw = {
            "name": h.get_text(" ", strip=True),
            "text": el.get_text("\n"),
            "alts": [i.get("alt", "") for i in el.find_all("img")],
            "links": [urljoin(base, a["href"]) for a in el.find_all("a", href=True)],
        }
        card = parse_card(raw)
        if is_shop_card(card):
            out.append(card)
    return out


def search(postal):
    r = requests.get(search_url(postal), headers={"User-Agent": USER_AGENT}, timeout=20)
    r.raise_for_status()
    return extract(r.text)


def rank(facility, listings):
    """Scores every listing against the facility, best first."""
    shop = {"legal_name": facility.get("legal_name"), "operating_name": facility.get("operating_name"),
            "street": facility.get("street"), "phone": facility.get("phone"), "website": facility.get("website"),
            "email": facility.get("rep_email")}
    scored = [{**score_listing(shop, l), "listing": l} for l in listings]
    scored.sort(key=lambda s: (_RANK[s["identity"]], s["score"]), reverse=True)
    return scored
