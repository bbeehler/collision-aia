import http.server
import os
import threading
from pathlib import Path

import pytest

HTML = (Path(__file__).parent / "fixtures" / "results.html").read_text()


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = HTML if "page=1" in self.path else "<html><body><p>No locations found</p></body></html>"
        self.send_response(200)
        self.send_header("content-type", "text/html")
        self.end_headers()
        self.wfile.write(body.encode())

    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def locator():
    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    from verifier import settings
    settings.BASE_URL = f"http://127.0.0.1:{srv.server_address[1]}/canada/search"
    settings.MIN_DELAY_MS = 0
    from verifier.locator import Locator
    with Locator() as loc:
        yield loc
    srv.shutdown()


SHOP = {"legal_name": "Lakeshore Collision Centre Ltd.", "street": "12 Bayfield Street", "city": "Barrie", "province": "ON",
        "postal": "L4M 3A1", "phone": "705-555-0101", "website": "https://lakeshorecollision.ca"}


def test_extracts_cards(locator):
    from verifier.locator import search_url
    r = locator.load(search_url("L4M3A1", 1))
    assert r["total"] == 3 and len(r["listings"]) == 3
    a, b = r["listings"][0], r["listings"][1]
    assert a["name"] == "Lakeshore Collision Centre"
    assert a["phones"] == ["7055550101"]
    assert a["address"] == "12 Bayfield St Barrie, ON"
    assert sorted(a["brands"]) == ["ford", "hyundai", "kia", "stellantis"]
    assert "genesis" not in b["brands"], "a shop name must not count as a certification"
    assert sorted(b["brands"]) == ["honda", "toyota"]


def test_confirms_listed_brands_and_routes_the_rest(locator):
    from verifier.verify import verify_facility
    out = verify_facility(locator, SHOP, ["ford", "kia", "toyota", "gm"])
    by = {r["brand"]: r for r in out["results"]}
    assert out["match"]["identity"] == "confirmed"
    assert by["ford"]["outcome"] == "confirmed" and by["kia"]["outcome"] == "confirmed"
    assert by["toyota"]["outcome"] == "review" and by["toyota"]["reason"] == "brand_not_listed"
    assert by["gm"]["reason"] == "not_on_locator"


def test_unlisted_shop_goes_to_review(locator):
    from verifier.verify import verify_facility
    shop = {"legal_name": "Maple Ridge Body Works", "street": "77 Mapleview Dr", "city": "Barrie", "province": "ON",
            "postal": "L4N 9A1", "phone": "705-555-0777"}
    r = verify_facility(locator, shop, ["ford"])["results"][0]
    assert r["outcome"] == "review" and r["reason"] == "shop_not_found"


def test_name_only_lookalike_is_not_confirmed():
    from verifier.match import score_listing
    s = score_listing({"legal_name": "Lakeshore Collision", "street": "500 Other Rd", "phone": "4165550000"},
                      {"name": "Lakeshore Collision Centre", "phones": ["7055550101"], "address": "12 Bayfield St Barrie, ON",
                       "links": [], "email": None})
    assert s["identity"] != "confirmed"
