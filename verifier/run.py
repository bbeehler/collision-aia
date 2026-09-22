"""
Picks up credential claims that are waiting for an automated check (or due for a re-check), checks them on
CPN Auto Body Locator and writes the results back to Supabase. GitHub Actions runs this on a schedule:

    python -m verifier.run
"""
import os
import sys
from datetime import datetime, timedelta, timezone

from supabase import create_client

from . import settings
from .locator import Locator
from .verify import verify_facility


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def due_claims(sb):
    now = _iso(datetime.now(timezone.utc))
    brands = sorted(settings.LOCATOR_BRANDS)
    cols = "id, facility_id, program, status, recheck_at, next_auto_check_at, created_at"
    pending = (sb.table("credential_claims").select(cols).eq("status", "pending").in_("program", brands)
               .or_(f"next_auto_check_at.is.null,next_auto_check_at.lte.{now}").order("created_at").limit(200).execute().data)
    recheck = (sb.table("credential_claims").select(cols).eq("status", "confirmed").in_("program", brands)
               .lte("recheck_at", now).order("recheck_at").limit(200).execute().data)
    return pending + recheck


def upload_evidence(sb, paths, facility_id):
    keys = []
    for p in [p for p in paths if p]:
        key = f"{facility_id}/{os.path.basename(p)}"
        try:
            with open(p, "rb") as fh:
                sb.storage.from_(settings.EVIDENCE_BUCKET).upload(key, fh.read(), {"content-type": "image/png", "upsert": "true"})
            keys.append(key)
        except Exception as e:
            print(f"  evidence upload failed: {e}")
        finally:
            try:
                os.remove(p)
            except OSError:
                pass
    return keys


def main():
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY.")
    sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY)
    claims = due_claims(sb)
    by_fac = {}
    for c in claims:
        by_fac.setdefault(c["facility_id"], []).append(c)
    print(f"{len(claims)} claims due across {len(by_fac)} facilities")
    if not by_fac:
        return

    with Locator() as loc:
        for fid, fclaims in list(by_fac.items())[: settings.BATCH_SIZE]:
            f = sb.table("facilities").select("*").eq("id", fid).single().execute().data
            if not f:
                continue
            shop = {"legal_name": f["legal_name"], "operating_name": f.get("operating_name"), "street": f["street"], "city": f["city"],
                    "province": f["province"], "postal": f["postal"], "phone": f.get("phone"), "website": f.get("website"),
                    "email": f.get("rep_email")}
            stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
            res = verify_facility(loc, shop, sorted({c["program"] for c in fclaims}), evidence_key=f"{fid}-{stamp}")
            evidence = upload_evidence(sb, [s.get("evidence") for s in res["searches"]], fid)
            print(f"- {f['legal_name']}: " + ", ".join(f"{r['brand']}={r['reason']}" for r in res["results"]))

            for c in fclaims:
                r = next((x for x in res["results"] if x["brand"] == c["program"]), None)
                if not r:
                    continue
                now = datetime.now(timezone.utc)
                if r["outcome"] == "confirmed":
                    update = {"status": "confirmed", "source": "CPN Auto Body Locator (automated)", "reviewed_at": res["checked_at"],
                              "reviewed_by": "verifier", "recheck_at": _iso(now + timedelta(days=settings.RECHECK_DAYS)),
                              "note": r["note"], "review_reason": None, "next_auto_check_at": None}
                elif r["reason"] == "search_failed":
                    update = {"next_auto_check_at": _iso(now + timedelta(hours=1))}
                else:
                    update = {"status": "review", "note": r["note"], "next_auto_check_at": None,
                              "review_reason": "recheck_failed" if c["status"] == "confirmed" else r["reason"]}
                update["last_auto_check_at"] = res["checked_at"]
                sb.table("credential_claims").update(update).eq("id", c["id"]).execute()
                sb.table("verification_runs").insert({
                    "claim_id": c["id"], "facility_id": fid, "ran_at": res["checked_at"], "outcome": r["outcome"], "reason": r["reason"],
                    "note": r["note"], "match_score": (res["match"] or {}).get("score"), "match_identity": (res["match"] or {}).get("identity"),
                    "matched_listing": (res["match"] or {}).get("listing"),
                    "searches": [{k: v for k, v in s.items() if k != "evidence"} for s in res["searches"]], "evidence_paths": evidence,
                }).execute()


if __name__ == "__main__":
    main()
