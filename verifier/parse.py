"""Turns the raw text of one locator result card into structured fields."""
import re

from .brands import detect_brands, normalize

PROV = "AB|BC|MB|NB|NL|NS|NT|NU|ON|PE|QC|SK|YT"
PHONE_RE = re.compile(r"\(?\b\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
PROV_RE = re.compile(rf",\s*({PROV})\b")
DAY_RE = re.compile(r"(monday|tuesday|wednesday|thursday|friday|saturday|sunday|lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)")
UI_RE = re.compile(r"^(request an appointment|demander un rendez-vous|prendre rendez-vous|directions|itineraire|email|courriel|web|site web|list view|map view|back to search)$")
KM_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*km\b", re.I)


def digits(s):
    return re.sub(r"\D", "", str(s or ""))


def parse_card(raw):
    name = (raw.get("name") or "").strip()
    text = raw.get("text") or ""
    lines = [l.strip() for l in re.split(r"\n+", text) if l.strip()]
    phones = list(dict.fromkeys(digits(m.group(0))[-10:] for m in PHONE_RE.finditer(text)))
    em = EMAIL_RE.search(text)
    km = KM_RE.search(text)
    addr_line = next((l for l in lines if PROV_RE.search(l)), None)
    address = PHONE_RE.sub("", EMAIL_RE.sub("", addr_line)).strip() if addr_line else None
    province = PROV_RE.search(addr_line).group(1) if addr_line else None

    cert_lines = []
    for l in lines:
        n = normalize(l)
        if l in (name, addr_line) or EMAIL_RE.search(l) or re.search(r"\bkm\b", l, re.I) or DAY_RE.search(n) or UI_RE.match(n):
            continue
        if not re.sub(r"directions|email|web|courriel|itineraire", "", PHONE_RE.sub("", l), flags=re.I).strip():
            continue
        if re.match(r"^https?://", l) or re.match(r"^[\w-]+\.(ca|com|net|org)\b", l, re.I):
            continue
        cert_lines.append(l)
    cert_text = "\n".join(cert_lines + list(raw.get("alts") or []))
    links = [h for h in (raw.get("links") or []) if h.startswith("http") and not re.search(r"autobodylocator|google\.|maps\.", h, re.I)][:5]
    return {
        "name": name,
        "distance_km": float(km.group(1).replace(",", ".")) if km else None,
        "phones": phones,
        "email": em.group(0) if em else None,
        "address": address,
        "province": province,
        "brands": detect_brands(cert_text),
        "cert_text": cert_text[:1000],
        "links": links,
    }


def is_shop_card(c):
    return bool(c["name"]) and bool(c["phones"] or c["address"] or c["distance_km"] is not None)
