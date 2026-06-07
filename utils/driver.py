import os
import re
import subprocess
import undetected_chromedriver as uc
from config import BRAVE_PATH


def _detect_chrome_major() -> int | None:
    """
    Reads the major version number from the installed Chrome/Chromium binary.
    Returns an int (e.g. 148) or None if detection fails.
    """
    candidates = []

    # Prefer whatever BRAVE_PATH points to (works locally and on Streamlit Cloud)
    if os.path.exists(BRAVE_PATH):
        candidates.append(BRAVE_PATH)

    # Common fallback paths in cloud / CI environments
    candidates += [
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
    ]

    for binary in candidates:
        if not os.path.exists(binary):
            continue
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            # Output looks like: "Chromium 148.0.7778.215 built on …"
            m = re.search(r"(\d+)\.\d+\.\d+", result.stdout)
            if m:
                major = int(m.group(1))
                print(f"  [Driver] Detected browser version: {major} ({binary})")
                return major
        except Exception:
            continue

    return None


def get_driver(headless=False):
    options = uc.ChromeOptions()

    # Use Brave locally if it exists, else fall back to Chromium (cloud)
    if os.path.exists(BRAVE_PATH):
        options.binary_location = BRAVE_PATH

    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=0")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    )

    if headless:
        options.add_argument("--headless=new")

    # Pin version_main so uc downloads a driver that actually matches the
    # installed browser. Without this, uc may grab a mismatched driver on
    # cloud deployments where Chrome and ChromeDriver update independently.
    version_main = _detect_chrome_major()

    driver = uc.Chrome(
        options=options,
        use_subprocess=True,
        version_main=version_main,  # None → uc auto-detects (safe fallback)
    )

    return driver