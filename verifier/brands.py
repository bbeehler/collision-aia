"""Maps certification wording on the locator (English and French) to the program IDs used by the app."""
import re
import unicodedata


def normalize(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


BRANDS = {
    "ford": ("Ford", r"\bford\b"),
    "stellantis": ("Stellantis (Chrysler, Dodge, Jeep, Ram)", r"fiat chrysler|\bfca\b|stellantis|chrysler|\bjeep\b|\bdodge\b|\bram\b"),
    "gm": ("GM", r"general motors|\bgm\b|chevrolet|\bgmc\b|\bbuick\b|cadillac"),
    "kia": ("Kia", r"\bkia\b"),
    "nissan": ("Nissan", r"\bnissan\b"),
    "infiniti": ("INFINITI", r"\binfiniti\b"),
    "toyota": ("Toyota", r"\btoyota\b"),
    "lexus": ("Lexus", r"\blexus\b"),
    "honda": ("Honda", r"\bhonda\b"),
    "acura": ("Acura", r"\bacura\b"),
    "hyundai": ("Hyundai", r"\bhyundai\b"),
    "genesis": ("Genesis", r"\bgenesis\b"),
    "subaru": ("Subaru", r"\bsubaru\b"),
    "mazda": ("Mazda", r"\bmazda\b"),
    "mitsubishi": ("Mitsubishi", r"\bmitsubishi\b"),
    "volkswagen": ("Volkswagen", r"volkswagen|\bvw\b"),
    "audi": ("Audi", r"\baudi\b"),
    "bmw": ("BMW", r"\bbmw\b"),
    "mini": ("MINI", r"\bmini\b"),
    "mercedes-benz": ("Mercedes-Benz", r"mercedes"),
    "porsche": ("Porsche", r"\bporsche\b"),
    "volvo": ("Volvo", r"\bvolvo\b"),
    "polestar": ("Polestar", r"\bpolestar\b"),
    "jaguar-land-rover": ("Jaguar Land Rover", r"jaguar|land rover"),
    "tesla": ("Tesla", r"\btesla\b"),
    "rivian": ("Rivian", r"\brivian\b"),
    "vinfast": ("VinFast", r"\bvinfast\b"),
}
_COMPILED = {k: re.compile(p) for k, (_, p) in BRANDS.items()}


def label(brand_id):
    return BRANDS.get(brand_id, (brand_id, ""))[0]


def detect_brands(text):
    t = normalize(text)
    return [k for k, rx in _COMPILED.items() if rx.search(t)]
