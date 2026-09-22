"""Settings from environment variables (GitHub Actions secrets/vars or a local .env)."""
import os


def _int(name, default):
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


BASE_URL = os.environ.get("LOCATOR_BASE_URL", "https://autobodylocator.ca/canada/search")
RADIUS = _int("LOCATOR_RADIUS", 10)
MAX_PAGES = _int("LOCATOR_MAX_PAGES", 3)
MIN_DELAY_MS = _int("LOCATOR_MIN_DELAY_MS", 3000)
TIMEOUT_MS = _int("LOCATOR_TIMEOUT_MS", 25000)
USER_AGENT = os.environ.get(
    "LOCATOR_USER_AGENT",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36 AIACanada-CredentialCheck/1.0",
)
CHROMIUM_PATH = os.environ.get("CHROMIUM_PATH") or None
AUTO_CONFIRM = os.environ.get("AUTO_CONFIRM", "true").lower() != "false"
RECHECK_DAYS = _int("RECHECK_DAYS", 30)
EVIDENCE_DIR = os.environ.get("EVIDENCE_DIR", "")
EVIDENCE_BUCKET = os.environ.get("EVIDENCE_BUCKET", "verification-evidence")
BATCH_SIZE = _int("BATCH_SIZE", 15)
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
# Brands seen on the locator's Canadian listings. Others go straight to a reviewer.
LOCATOR_BRANDS = {
    b.strip()
    for b in (os.environ.get("LOCATOR_BRANDS") or "ford,stellantis,kia,nissan,infiniti,toyota,lexus,honda,hyundai,genesis,subaru,vinfast").split(",")
    if b.strip()
}
