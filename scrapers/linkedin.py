# scrapers/linkedin.py
# Uses LinkedIn's guest jobs API — no login needed, stable selectors,
# much safer than scraping the logged-in feed

import requests
from bs4 import BeautifulSoup
import time
import random
import os
import config
from config import MIN_DELAY, MAX_DELAY   # these don't change so fine to keep

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def build_url(role: str, start: int = 0, location: str = "India") -> str:
    role_encoded = role.replace(" ", "%20")
    loc_encoded  = location.replace(" ", "%20")
    return (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={role_encoded}"
        f"&location={loc_encoded}"
        f"&f_TPR=r604800"    # last 7 days
        f"&start={start}"
    )


def scrape_role(role: str, location: str = "India") -> list[dict]:
    jobs = []
    start = 0
    print(f"  [LinkedIn] Scraping: {role} | location: {location}")

    while len(jobs) < config.MAX_JOBS_PER_SEARCH:
        if os.path.exists("scraping_stop.flag"):
            print("  [LinkedIn] Stop signal received."); break
        url = build_url(role, start, location)
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)

            if response.status_code == 429:
                print(f"    [!] Rate limited. Waiting 30s...")
                time.sleep(30)
                continue

            if response.status_code != 200 or not response.text.strip():
                print(f"    [!] Status {response.status_code} at offset {start}, stopping.")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select("li")

            if not cards:
                print(f"    [!] No cards at offset {start}, done.")
                break

            for card in cards:
                if len(jobs) >= config.MAX_JOBS_PER_SEARCH:
                    break
                try:
                    title = card.select_one("h3.base-search-card__title")
                    company = card.select_one("h4.base-search-card__subtitle")
                    card_location = card.select_one("span.job-search-card__location")
                    date_tag = card.select_one("time")
                    url_tag = card.select_one("a.base-card__full-link")

                    # skip empty cards
                    if not title:
                        continue

                    jobs.append({
                        "Title": title.get_text(strip=True),
                        "Company": company.get_text(strip=True) if company else "N/A",
                        "Platform": "LinkedIn",
                        "Location": card_location.get_text(strip=True) if card_location else "N/A",
                        "Skills Required": "N/A",
                        "Salary": "N/A",
                        "Date Posted": date_tag.get("datetime", "N/A") if date_tag else "N/A",
                        "URL": url_tag["href"].split("?")[0] if url_tag else "N/A",
                        "Status": "To Apply",
                        "Role Searched": role
                    })

                except Exception as e:
                    continue

            print(f"    Offset {start}: {len(cards)} cards | Total: {len(jobs)}")
            start += 25
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        except Exception as e:
            print(f"    [!] Error: {e}")
            break

    return jobs


def scrape(roles: list[str], location: str = "India") -> list[dict]:
    all_jobs = []
    for role in roles:
        if os.path.exists("scraping_stop.flag"):
            print("  [LinkedIn] Stop signal received."); break
        jobs = scrape_role(role, location)
        all_jobs.extend(jobs)
        print(f"  [LinkedIn] '{role}' → {len(jobs)} jobs")
        time.sleep(random.uniform(5, 10))
    return all_jobs