"""
One-off live check from the command line (no database needed):

    python -m verifier.check --name "Lakeshore Collision Centre" --street "12 Bayfield St" --city Barrie \
        --province ON --postal "L4M 3A1" --phone 7055550101 --brands ford,kia
"""
import argparse
import json

from .locator import Locator
from .verify import verify_facility

p = argparse.ArgumentParser()
for a in ["name", "operating", "street", "city", "province", "postal", "phone", "website"]:
    p.add_argument(f"--{a}", default="")
p.add_argument("--brands", required=True)
a = p.parse_args()
shop = {"legal_name": a.name, "operating_name": a.operating, "street": a.street, "city": a.city, "province": a.province,
        "postal": a.postal, "phone": a.phone, "website": a.website}
with Locator() as loc:
    print(json.dumps(verify_facility(loc, shop, [b.strip() for b in a.brands.split(",")]), indent=2))
