import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
# from config import ROLES, PLATFORMS
from scrapers import internshala, naukri, linkedin
from utils.exporter import save_csv, save_xlsx

os.makedirs("data", exist_ok=True)


def run():
    import json as _json, config as _cfg
    _override = "data/scrape_config_override.json"
    if os.path.exists(_override):
        with open(_override) as f:
            ov = _json.load(f)
        _cfg.ROLES = ov.get("roles", _cfg.ROLES)
        _cfg.MAX_JOBS_PER_SEARCH = ov.get("max_jobs", _cfg.MAX_JOBS_PER_SEARCH)
        _cfg.TARGET_LOCATIONS = ov.get("locations", _cfg.TARGET_LOCATIONS)

    print(f"[DEBUG] Roles: {_cfg.ROLES}")
    print(f"[DEBUG] Max jobs: {_cfg.MAX_JOBS_PER_SEARCH}")
    print(f"[DEBUG] Locations: {_cfg.TARGET_LOCATIONS}")

    # Use first location from list; fall back to "India" if empty
    _location = _cfg.TARGET_LOCATIONS[0] if _cfg.TARGET_LOCATIONS else "India"
    print(f"[DEBUG] Active location for scrape: {_location}")

    all_jobs = []
    print("=" * 55)
    print("  JobHarvestor — Day 1")
    print("=" * 55)

    # Sequential — more reliable than concurrent
    if "internshala" in _cfg.PLATFORMS:
        print("\n[1/3] Internshala...")
        try:
            jobs = internshala.scrape(_cfg.ROLES, location=_location)
            all_jobs.extend(jobs)
            print(f"  ✓ Internshala: {len(jobs)} jobs")
        except Exception as e:
            print(f"  ✗ Internshala failed: {e}")

    if "naukri" in _cfg.PLATFORMS:
        print("\n[2/3] Naukri...")
        try:
            jobs = naukri.scrape(_cfg.ROLES, location=_location)
            all_jobs.extend(jobs)
            print(f"  ✓ Naukri: {len(jobs)} jobs")
        except Exception as e:
            print(f"  ✗ Naukri failed: {e}")

    if "linkedin" in _cfg.PLATFORMS:
        print("\n[3/3] LinkedIn...")
        try:
            jobs = linkedin.scrape(_cfg.ROLES, location=_location)
            all_jobs.extend(jobs)
            print(f"  ✓ LinkedIn: {len(jobs)} jobs")
        except Exception as e:
            print(f"  ✗ LinkedIn failed: {e}")

    if not all_jobs:
        print("\n[!] No jobs collected.")
        sys.exit(1)

    print(f"\n[Export] Total: {len(all_jobs)} jobs")
    df = save_csv(all_jobs)
    save_xlsx(df)

    print("\n" + "=" * 55)
    print(f"  Done! {len(df)} jobs saved.")
    print(f"  CSV  → {_cfg.CSV_OUTPUT}")
    print(f"  XLSX → {_cfg.XLSX_OUTPUT}")
    print("=" * 55)


if __name__ == "__main__":
    run()