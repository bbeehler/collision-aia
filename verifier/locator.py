"""Loads CPN Auto Body Locator search pages in headless Chromium and extracts the result cards."""
import os
import time
from urllib.parse import urlencode

from playwright.sync_api import sync_playwright

from . import settings
from .parse import is_shop_card, parse_card

# Runs in the page. Each shop card is the largest element around a name heading that contains no other shop heading.
EXTRACT_JS = r"""
() => {
  const clean = (s) => (s || "").replace(/\u00a0/g, " ").trim();
  const bodyText = document.body ? document.body.innerText : "";
  const totalMatch = bodyText.match(/(\d+)\s*(?:location\(s\)|emplacement|établissement|etablissement)/i);
  const noResults = /no (?:locations|results) found|aucun (?:résultat|resultat|emplacement)/i.test(bodyText);
  const cardFor = (anchor, selector) => {
    let el = anchor;
    while (el.parentElement && el.parentElement !== document.body && el.parentElement.querySelectorAll(selector).length === 1) el = el.parentElement;
    return el;
  };
  const toRaw = (el, name) => ({
    name: clean(name),
    text: el.innerText || "",
    alts: [...el.querySelectorAll("img")].map((i) => clean(i.alt || i.title)).filter(Boolean),
    links: [...el.querySelectorAll("a[href]")].map((a) => a.href),
  });
  let cards = [...document.querySelectorAll("h4")].map((h) => toRaw(cardFor(h, "h4"), h.innerText));
  if (!cards.length) {
    const btns = [...document.querySelectorAll("a,button")].filter((b) => /request an appointment|rendez-vous/i.test(b.innerText || ""));
    btns.forEach((b) => b.setAttribute("data-abl-anchor", "1"));
    cards = btns.map((b) => { const el = cardFor(b, "[data-abl-anchor]");
      return toRaw(el, (el.innerText || "").split("\n").map(clean).find((l) => l && !/km$/i.test(l)) || ""); });
  }
  return { total: totalMatch ? Number(totalMatch[1]) : null, noResults, cards };
}
"""

WAIT_JS = "() => /location\\(s\\)|no (?:locations|results) found|aucun/i.test(document.body ? document.body.innerText : '')"


def search_url(query, page=1):
    params = {"search": query, "radius": str(settings.RADIUS), "type": "canada", "country": "CA", "lang": "en"}
    if page > 1:
        params["page"] = str(page)
    return f"{settings.BASE_URL}?{urlencode(params)}"


class Locator:
    """Use as a context manager so one browser serves a whole batch of checks."""

    def __enter__(self):
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(headless=True, executable_path=settings.CHROMIUM_PATH)
        self._last = 0.0
        return self

    def __exit__(self, *exc):
        self._browser.close()
        self._pw.stop()

    def profile_postal(self, url):
        """Opens a shop's CPN Auto Body Locator profile and reads its postal code."""
        import re
        wait = self._last + settings.MIN_DELAY_MS / 1000 - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()
        ctx = self._browser.new_context(user_agent=settings.USER_AGENT, locale="en-CA")
        page = ctx.new_page()
        try:
            page.goto(url.split("?")[0] + "?lang=en", wait_until="domcontentloaded", timeout=settings.TIMEOUT_MS)
            text = page.inner_text("body")
        finally:
            ctx.close()
        m = re.search(r"\b([A-Z]\d[A-Z])\s?(\d[A-Z]\d)\b", text)
        return f"{m.group(1)} {m.group(2)}" if m else None

    def load(self, url, evidence_name=None):
        wait = self._last + settings.MIN_DELAY_MS / 1000 - time.time()
        if wait > 0:
            time.sleep(wait)
        self._last = time.time()
        ctx = self._browser.new_context(user_agent=settings.USER_AGENT, locale="en-CA", viewport={"width": 1280, "height": 1600})
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=settings.TIMEOUT_MS)
            try:
                page.wait_for_function(f"() => document.querySelector('h4') || ({WAIT_JS})()", timeout=settings.TIMEOUT_MS)
            except Exception:
                pass
            try:
                page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass
            data = page.evaluate(EXTRACT_JS)
            evidence = None
            if settings.EVIDENCE_DIR and evidence_name:
                os.makedirs(settings.EVIDENCE_DIR, exist_ok=True)
                evidence = os.path.join(settings.EVIDENCE_DIR, f"{evidence_name}.png")
                page.screenshot(path=evidence, full_page=True)
            listings = [c for c in (parse_card(r) for r in data["cards"]) if is_shop_card(c)]
            return {"url": url, "total": data["total"], "no_results": data["noResults"], "listings": listings, "evidence": evidence}
        finally:
            ctx.close()
