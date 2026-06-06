# utils/cookies.py
# Saves LinkedIn login cookies so you only log in ONCE
# Every run after that loads cookies automatically — no re-login needed

import pickle
import os
from config import COOKIES_FILE


def save_cookies(driver):
    """Call this after manual LinkedIn login to save your session."""
    os.makedirs(os.path.dirname(COOKIES_FILE), exist_ok=True)
    with open(COOKIES_FILE, "wb") as f:
        pickle.dump(driver.get_cookies(), f)
    print(f"  [Cookies] Saved → {COOKIES_FILE}")


def load_cookies(driver):
    """
    Loads saved cookies into the browser.
    Must navigate to linkedin.com first before loading cookies.
    Returns True if cookies loaded, False if no saved cookies found.
    """
    if not os.path.exists(COOKIES_FILE):
        return False

    with open(COOKIES_FILE, "rb") as f:
        cookies = pickle.load(f)

    for cookie in cookies:
        try:
            driver.add_cookie(cookie)
        except Exception:
            pass

    print("  [Cookies] Loaded saved LinkedIn session.")
    return True


def cookies_exist():
    return os.path.exists(COOKIES_FILE)