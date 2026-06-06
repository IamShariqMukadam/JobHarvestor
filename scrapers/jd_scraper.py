import requests
from bs4 import BeautifulSoup
import time
import random
import re
from config import JD_MIN_DELAY, JD_MAX_DELAY

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def extract_linkedin_job_id(url: str) -> str | None:
    match = re.search(r"(\d{10,})", url)  # job IDs are always 10+ digits
    return match.group(1) if match else None


def scrape_linkedin_jd(url: str) -> str:
    job_id = extract_linkedin_job_id(url)
    if not job_id:
        print(f"      [DEBUG] LinkedIn job_id extract failed: {url}")
        return ""

    api_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}"
    try:
        response = requests.get(api_url, headers=HEADERS, timeout=15)
        print(f"      [DEBUG] LinkedIn status={response.status_code} id={job_id}")
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            desc = soup.find("div", class_="show-more-less-html__markup")
            return desc.get_text(separator=" ", strip=True) if desc else ""
    except Exception as e:
        print(f"      [!] LinkedIn JD error: {e}")
    return ""


def scrape_naukri_jd(url: str, driver=None) -> str:
    from utils.driver import get_driver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    own_driver = False
    if driver is None:
        driver = get_driver(headless=True)
        own_driver = True

    try:
        driver.get(url)
        # Wait for body only — not specific selectors that may not exist
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(6)  # extra wait for JS to render content

        soup = BeautifulSoup(driver.page_source, "html.parser")
        exp_tag = (soup.select_one(".exp-wrap") or
           soup.select_one("[class*='experience']") or
           soup.select_one(".exp") or
           soup.select_one("[class*='exp']"))

        exp_text = exp_tag.get_text(strip=True) if exp_tag else ""

        # Try known selectors first
        desc = (soup.select_one(".job-desc") or
                soup.select_one(".dang-inner-html") or
                soup.select_one(".jd-desc") or
                soup.select_one("#job-desc") or
                soup.select_one(".jobDescription") or
                soup.select_one("[class*='description']") or
                soup.select_one("[class*='job-desc']") or
                soup.select_one("section.job-desc") or
                soup.select_one("article"))

        skills = (soup.select_one(".key-skill") or
                  soup.select_one(".chip-wrapper") or
                  soup.select_one("[class*='skill']"))

        # FALLBACK — if no selector matched, grab main content area
        if not desc:
            # Remove nav, header, footer noise
            for tag in soup(["nav", "header", "footer", "script", "style"]):
                tag.decompose()
            desc = soup.find("main") or soup.find("body")

        text = desc.get_text(separator=" ", strip=True) if desc else ""
        if skills:
            text += " " + skills.get_text(separator=" ", strip=True)
        if exp_text:
            text += " Experience required: " + exp_text  # ADDED

        print(f"      [DEBUG] Naukri chars={len(text)}")
        return text[:3000]  # cap at 3000 — same as LLM limit anyway

    except Exception as e:
        print(f"      [!] Naukri JD error: {e}")
        return ""
    finally:
        if own_driver:
            driver.quit()


def scrape_internshala_jd(url: str) -> str:
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            desc = (soup.select_one(".internship_details") or
                    soup.select_one(".job_details_section") or
                    soup.select_one("#about_internship"))
            return desc.get_text(separator=" ", strip=True) if desc else ""
    except Exception as e:
        print(f"      [!] Internshala JD error: {e}")
    return ""


def scrape_jd(url: str, platform: str, naukri_driver=None) -> str:
    if not url or url == "N/A":
        return ""

    time.sleep(random.uniform(JD_MIN_DELAY, JD_MAX_DELAY))

    platform = platform.lower()
    if platform == "linkedin":
        text = scrape_linkedin_jd(url)
    elif platform == "naukri":
        text = scrape_naukri_jd(url, naukri_driver)
    elif platform == "internshala":
        text = scrape_internshala_jd(url)
    else:
        text = ""

    print(f"      [JD] {platform} | chars: {len(text)}")
    return text