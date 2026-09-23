from pathlib import Path

from app.locator_lookup import extract, rank

HTML = (Path(__file__).parent / "fixtures" / "locator_results.html").read_text()


def test_reads_real_results_layout():
    cards = extract(HTML)
    assert [c["name"] for c in cards] == ["Assured Orleans South (Ottawa)", "CARSTAR Orleans (Myers)", "Fix Auto Gatineau Centre"]
    carstar = cards[1]
    assert carstar["shop_id"] == "270153"
    assert carstar["profile_url"] == "https://autobodylocator.ca/shop/carstar-orleans-myers-orleans-on-270153/canada"
    assert carstar["phones"] == ["6138349538"]
    assert carstar["address"].startswith("420 Vantage Dr")
    assert sorted(carstar["brands"]) == ["genesis", "hyundai", "kia", "nissan"]
    assert sorted(cards[2]["brands"]) == ["acura", "ford", "honda", "lexus"]


def test_finds_the_facility_from_what_it_entered():
    fac = {"legal_name": "CARSTAR Orleans (Myers)", "street": "420 Vantage Dr", "phone": "613-834-9538", "postal": "K4A 3W1"}
    top = rank(fac, extract(HTML))[0]
    assert top["identity"] == "confirmed" and top["listing"]["shop_id"] == "270153"


def test_chain_email_domain_alone_is_not_a_match():
    fac = {"legal_name": "Fix Auto Orleans", "street": "1 Other Rd", "phone": "613-555-0000", "website": "https://fixauto.com"}
    assert rank(fac, extract(HTML))[0]["identity"] == "none"


def test_same_street_different_shop_is_not_confirmed():
    fac = {"legal_name": "Vanguard Paint Ltd", "street": "240 Vanguard Dr", "phone": "613-555-0101"}
    assert rank(fac, extract(HTML))[0]["identity"] != "confirmed"
