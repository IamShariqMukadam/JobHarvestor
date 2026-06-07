import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
# from config import ROLES, PLATFORMS
from scrapers import internshala, naukri, linkedin
from utils.exporter import save_csv, save_xlsx

os.makedirs("data", exist_ok=True)


def run():
    import json as _json, config as _cfg
    _override = os.path.join(os.getenv("JH_SESSION_DIR","data"), "scrape_config_override.json")
    if os.path.exists(_override):
        with open(_override) as f:
            ov = _json.load(f)
        _cfg.ROLES               = ov.get("roles",            _cfg.ROLES)
        _cfg.MAX_JOBS_PER_SEARCH = ov.get("max_jobs",         _cfg.MAX_JOBS_PER_SEARCH)
        _cfg.TARGET_LOCATIONS    = ov.get("locations",        _cfg.TARGET_LOCATIONS)
        _cfg.BANNED_COMPANIES    = ov.get("banned_companies", _cfg.BANNED_COMPANIES)

    print(f"[DEBUG] Roles: {_cfg.ROLES}")
    print(f"[DEBUG] Max jobs: {_cfg.MAX_JOBS_PER_SEARCH}")
    print(f"[DEBUG] Locations: {_cfg.TARGET_LOCATIONS}")

    # Use first location from list; fall back to "India" if empty
    _location = _cfg.TARGET_LOCATIONS[0] if _cfg.TARGET_LOCATIONS else "India"
    print(f"[DEBUG] Active location for scrape: {_location}")

    all_jobs = []
    USE_CONCURRENT = _cfg.MAX_JOBS_PER_SEARCH < 50
    mode = "concurrent" if USE_CONCURRENT else "sequential"
    print("=" * 55)
    print(f"  JobHarvestor — Day 1  [{mode}]")
    print("=" * 55)

    def _scrape_platform(platform: str) -> list:
        if platform == "internshala":
            return internshala.scrape(_cfg.ROLES, location=_location)
        elif platform == "naukri":
            return naukri.scrape(_cfg.ROLES, location=_location)
        elif platform == "linkedin":
            return linkedin.scrape(_cfg.ROLES, location=_location)
        return []

    if USE_CONCURRENT:
        print(f"\n  Scraping {len(_cfg.PLATFORMS)} platforms concurrently...")
        with ThreadPoolExecutor(max_workers=len(_cfg.PLATFORMS)) as executor:
            future_map = {executor.submit(_scrape_platform, p): p for p in _cfg.PLATFORMS}
            for future in as_completed(future_map):
                p = future_map[future]
                try:
                    jobs = future.result()
                    all_jobs.extend(jobs)
                    print(f"  ✓ {p.title()}: {len(jobs)} jobs")
                except Exception as e:
                    print(f"  ✗ {p} failed: {e}")
    else:
        for i, platform in enumerate(_cfg.PLATFORMS):
            print(f"\n[{i+1}/{len(_cfg.PLATFORMS)}] {platform.title()}...")
            try:
                jobs = _scrape_platform(platform)
                all_jobs.extend(jobs)
                print(f"  ✓ {platform.title()}: {len(jobs)} jobs")
            except Exception as e:
                print(f"  ✗ {platform} failed: {e}")

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