# scrapers/internshala.py
# Internshala = mostly static HTML → requests + BS4, no browser needed
# Safest scraper, no account risk at all

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
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def build_url(role: str, page: int = 1, location: str = "") -> str:
    role_slug = role.lower().replace(" ", "%20")
    # Internshala supports city-scoped URLs: /jobs/{city}/keywords-{role}/page-{n}/
    if location and location.lower() not in ("india", ""):
        loc_slug = location.lower().replace(" ", "-")
        return f"https://internshala.com/jobs/{loc_slug}/keywords-{role_slug}/page-{page}/"
    return f"https://internshala.com/jobs/keywords-{role_slug}/page-{page}/"


def scrape_role(role: str, location: str = "") -> list[dict]:
    jobs = []
    page = 1
    print(f"  [Internshala] Scraping: {role} | location: {location or 'India-wide'}")

    while len(jobs) < config.MAX_JOBS_PER_SEARCH:
        if os.path.exists(config.STOP_FLAG):
            print("  [Internshala] Stop signal received."); break
        url = build_url(role, page, location)
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            if response.status_code != 200:
                print(f"    [!] Status {response.status_code} on page {page}.")
                break

            soup = BeautifulSoup(response.text, "html.parser")
            cards = soup.select(".individual_internship")

            if not cards:
                print(f"    [!] No cards on page {page}, done.")
                break

            for card in cards:
                if len(jobs) >= config.MAX_JOBS_PER_SEARCH:
                    break
                try:
                    title = (card.select_one(".job-internship-name") or
                             card.select_one(".profile"))
                    company = card.select_one(".company-name")
                    card_location = (card.select_one(".locations span") or
                                     card.select_one(".location_link"))
                    salary = (card.select_one(".stipend") or
                              card.select_one(".salary"))
                    url_tag = (card.select_one("a.job-title-href") or
                               card.select_one("a[href*='/jobs/']"))
                    date_tag = card.select_one(".status-info")

                    jobs.append({
                        "Title": title.get_text(strip=True) if title else "N/A",
                        "Company": company.get_text(strip=True) if company else "N/A",
                        "Platform": "Internshala",
                        "Location": card_location.get_text(strip=True) if card_location else "N/A",
                        "Skills Required": "N/A",
                        "Salary": salary.get_text(strip=True) if salary else "N/A",
                        "Date Posted": date_tag.get_text(strip=True) if date_tag else "N/A",
                        "URL": "https://internshala.com" + url_tag["href"] if url_tag and url_tag.get("href") else "N/A",
                        "Status": "To Apply",
                        "Role Searched": role
                    })
                except Exception as e:
                    print(f"    [!] Card error: {e}")
                    continue

            print(f"    Page {page}: {len(cards)} cards | Total: {len(jobs)}")
            page += 1
            time.sleep(random.uniform(MIN_DELAY, MAX_DELAY))

        except Exception as e:
            print(f"    [!] Request error: {e}")
            break

    return jobs


def scrape(roles: list[str], location: str = "") -> list[dict]:
    all_jobs = []
    for role in roles:
        if os.path.exists(config.STOP_FLAG):
            print("  [Internshala] Stop signal received."); break
        jobs = scrape_role(role, location)
        all_jobs.extend(jobs)
        print(f"  [Internshala] '{role}' → {len(jobs)} jobs")
    return all_jobs