import undetected_chromedriver as uc
from config import BRAVE_PATH


def get_driver(headless=False):
    options = uc.ChromeOptions()
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

    driver = uc.Chrome(
        options=options,
        headless=False,        # let the argument handle it, not UC param
        use_subprocess=True,
        version_main=148
    )

    return driver