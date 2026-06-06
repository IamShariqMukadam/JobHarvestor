# utils/humanize.py
# Human-like behavior — critical for avoiding detection on LinkedIn/Naukri

import time
import random
from selenium.webdriver.common.action_chains import ActionChains


def random_sleep(min_s=None, max_s=None):
    """Sleep for a random duration. Uses config defaults if not specified."""
    from config import MIN_DELAY, MAX_DELAY
    lo = min_s if min_s is not None else MIN_DELAY
    hi = max_s if max_s is not None else MAX_DELAY
    duration = random.uniform(lo, hi)
    time.sleep(duration)


def human_scroll(driver, scrolls=3):
    """Scroll down page gradually like a human reading it."""
    for _ in range(scrolls):
        scroll_px = random.randint(300, 700)
        driver.execute_script(f"window.scrollBy(0, {scroll_px});")
        time.sleep(random.uniform(0.8, 1.8))


def scroll_to_bottom(driver):
    """Scroll to page bottom to trigger lazy-loaded content."""
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(random.uniform(1.5, 3.0))


def move_mouse_randomly(driver):
    """Random mouse movement to simulate human presence."""
    try:
        action = ActionChains(driver)
        x = random.randint(100, 800)
        y = random.randint(100, 600)
        action.move_by_offset(x, y).perform()
        time.sleep(random.uniform(0.3, 0.8))
    except Exception:
        pass  # Non-critical, skip if it fails