# scrapers/naukri.py
# Strategy: harvest nkparam token via Selenium (intercept network request),
# then use Naukri's internal API directly — no HTML scraping, much safer.
# Source: github.com/Traverser25/NopeRi

import json
import time
import random
import requests
import pickle
import os
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from utils.driver import get_driver
from utils.humanize import random_sleep, human_scroll
from config import  NAUKRI_API, NAUKRI_BASE
import config
from config import MIN_DELAY, MAX_DELAY   # these don't change so fine to keep

NAUKRI_COOKIES_FILE = "data/naukri_cookies.pkl"

def save_naukri_cookies(driver):
    os.makedirs("data", exist_ok=True)
    with open(NAUKRI_COOKIES_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print("  [Naukri] Cookies saved.")


def load_naukri_cookies(driver):
    if not os.path.exists(NAUKRI_COOKIES_FILE):
        return False
    with open(NAUKRI_COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)
    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass
    print("  [Naukri] Loaded saved session.")
    return True


def harvest_nkparam(role: str) -> str | None:
    """
    Opens Naukri in Brave, waits for the search API call,
    intercepts the nkparam token from network logs.
    Returns the token string or None if not found.
    """
    driver = get_driver(headless=False)

    # Enable Chrome performance logging to capture network requests
    # UC supports this via CDP
    driver.execute_cdp_cmd("Network.enable", {})

    # ── Login block ──────────────────────────────────────────
    driver.get("https://www.naukri.com")
    time.sleep(2)
    # ─────────────────────────────────────────────────────────

    role_slug = role.lower().replace(" ", "-")
    url = f"{NAUKRI_BASE}/{role_slug}-jobs"

    print(f"  [Naukri] Opening browser to harvest nkparam token...")
    driver.get(url)
    human_scroll(driver, scrolls=2)
    time.sleep(3)

    nkparam = None
    try:
        # Get all network requests captured by CDP
        logs = driver.execute_script("""
            return window.performance.getEntriesByType('resource')
                .filter(r => r.name.includes('/jobapi/'))
                .map(r => r.name);
        """)

        for log_url in (logs or []):
            if "nkparam=" in log_url:
                nkparam = log_url.split("nkparam=")[1].split("&")[0]
                print(f"  [Naukri] nkparam harvested: {nkparam[:20]}...")
                break

        # Fallback: try cookies-based approach (Naukri sets nktoken in cookies)
        if not nkparam:
            cookies = driver.get_cookies()
            for c in cookies:
                if "nk" in c["name"].lower():
                    nkparam = c["value"]
                    print(f"  [Naukri] nkparam from cookie: {c['name']}")
                    break

    except Exception as e:
        print(f"  [Naukri] Token harvest error: {e}")
    finally:
        driver.quit()

    return nkparam


def api_scrape_role(role: str, nkparam: str, location: str = "India") -> list[dict]:
    """
    Hits Naukri's internal search API directly using the harvested token.
    Returns parsed job list.
    """
    jobs = []
    page = 1
    per_page = 20

    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Referer": NAUKRI_BASE,
        "nkparam": nkparam,
        "appid": "109",
        "systemid": "Naukri",
    }

    print(f"  [Naukri API] Scraping: {role} | location: {location}")

    while len(jobs) < config.MAX_JOBS_PER_SEARCH:
        if os.path.exists(config.STOP_FLAG):
            print("  [Naukri] Stop signal received."); break
        params = {
            "noOfResults": per_page,
            "urlType": "search_by_keyword",
            "searchType": "adv",
            "keyword": role,
            "location": location,
            "pageNo": page,
            "k": role,
            "l": location,
            "seoKey": role.lower().replace(" ", "-") + "-jobs",
            "src": "jobsearchDesk",
        }

        try:
            response = requests.get(NAUKRI_API, headers=headers, params=params, timeout=15)

            if response.status_code == 403:
                print(f"  [Naukri] 403 — nkparam expired, re-harvesting needed.")
                break

            if response.status_code != 200:
                print(f"  [Naukri] Status {response.status_code} on page {page}.")
                break

            data = response.json()
            job_list = data.get("jobDetails", [])

            if not job_list:
                print(f"  [Naukri] No more jobs at page {page}.")
                break

            for job in job_list:
                if len(jobs) >= config.MAX_JOBS_PER_SEARCH:
                    break

                # Extract skills list safely
                skills = job.get("skills", [])
                if isinstance(skills, list):
                    skill_str = ", ".join(
                        s.get("label", "") for s in skills if isinstance(s, dict)
                    )
                else:
                    skill_str = str(skills)

                jobs.append({
                    "Title": job.get("title", "N/A"),
                    "Company": job.get("companyName", "N/A"),
                    "Platform": "Naukri",
                    "Location": ", ".join(job.get("placeholders", [{}])[0].get("label", "N/A") if job.get("placeholders") else ["N/A"]),
                    "Skills Required": skill_str or "N/A",
                    "Salary": job.get("placeholders", [{}])[-1].get("label", "N/A") if job.get("placeholders") else "N/A",
                    "Date Posted": job.get("footerPlaceholderLabel", "N/A"),
                    "URL": "https://www.naukri.com" + job.get("jdURL", ""),
                    "_JD": job.get("jobDescription", ""),
                    "Status": "To Apply",
                    "Role Searched": role
                })

            print(f"    Page {page}: {len(job_list)} jobs | Total: {len(jobs)}")
            page += 1
            time.sleep(random.uniform(2, 4))   # lower delay OK since it's API not HTML

        except Exception as e:
            print(f"  [Naukri] API error: {e}")
            break

    return jobs


def fallback_selenium_scrape(role: str, location: str = "India") -> list[dict]:
    """
    Fallback if API approach fails — classic Selenium + BS4.
    Only used if nkparam harvest fails.
    """
    from bs4 import BeautifulSoup
    from selenium.webdriver.common.by import By

    jobs = []
    driver = get_driver(headless=True)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    page = 1
    loc_slug = location.lower().strip().replace(" ", "-")
    print(f"  [Naukri Fallback] Selenium scraping: {role} | location: {location}")

    try:
        while len(jobs) < config.MAX_JOBS_PER_SEARCH:
            if os.path.exists(config.STOP_FLAG):
                print("  [Naukri] Stop signal received."); break
            role_slug = role.lower().replace(" ", "-")
            url = f"https://www.naukri.com/{role_slug}-jobs-in-{loc_slug}-{page}"
            driver.get(url)

            try:
                WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".srp-jobtuple-wrapper"))
                )
            except:
                print(f"    [!] Timeout on page {page}.")
                break

            human_scroll(driver)
            soup = BeautifulSoup(driver.page_source, "html.parser")
            cards = soup.select(".srp-jobtuple-wrapper")

            if not cards:
                break

            for card in cards:
                if len(jobs) >= config.MAX_JOBS_PER_SEARCH:
                    break
                try:
                    title = card.select_one("a.title")
                    company = card.select_one("a.comp-name") or card.select_one(".comp-name")
                    location = card.select_one(".locWdth") or card.select_one("li.location")
                    salary = card.select_one(".sal") or card.select_one("li.salary")
                    date = card.select_one("span.job-post-day")

                    jobs.append({
                        "Title": title.get_text(strip=True) if title else "N/A",
                        "Company": company.get_text(strip=True) if company else "N/A",
                        "Platform": "Naukri",
                        "Location": location.get_text(strip=True) if location else "N/A",
                        "Skills Required": "N/A",
                        "Salary": salary.get_text(strip=True) if salary else "N/A",
                        "Date Posted": date.get_text(strip=True) if date else "N/A",
                        "URL": title["href"] if title and title.get("href") else "N/A",
                        "Status": "To Apply",
                        "Role Searched": role
                    })
                except Exception:
                    continue

            page += 1
            time.sleep(random.uniform(4, 8))
    finally:
        driver.quit()

    return jobs


def scrape(roles: list[str], location: str = "India") -> list[dict]:
    all_jobs = []
    for role in roles:
        if os.path.exists(config.STOP_FLAG):
            print("  [Naukri] Stop signal received."); break
        # Skip API attempt entirely — go straight to Selenium fallback
        print(f"  [Naukri] No nkparam, using Selenium fallback.")
        jobs = fallback_selenium_scrape(role, location)
        all_jobs.extend(jobs)
        print(f"  [Naukri] '{role}' → {len(jobs)} jobs")
    return all_jobs