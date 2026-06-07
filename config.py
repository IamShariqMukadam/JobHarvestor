# config.py
from dotenv import load_dotenv
import os
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2")
# GROQ_MODEL = "llama-3.3-70b-versatile"    # fastest + best free model on Groq
GROQ_MODEL = "llama-3.1-8b-instant"  # 30,000 TPM free, fast, fine for JSON extraction

ROLES = [
    # # Core
    # "Data Analyst",
    # "Junior Data Analyst",
    # "Associate Data Analyst",

    # # BI focused — huge in Pune (TCS, Infosys, Capgemini all post these)
    # "Business Intelligence Analyst",
    # "BI Analyst",
    # "Reporting Analyst",
    # "MIS Analyst",          # very common Indian title, same job different name

    # # Analytics variants
    # "Operations Analyst",
    # "Product Analyst",
    # "Marketing Analyst",
    # "SQL Analyst",
    # "Insights Analyst",
    "Data Analyst",
    "Data Scientist",
    "AI/ML Engineer",
    "Machine Learning Engineer",
    "Junior Data Analyst",
    "AI Engineer"
]

PLATFORMS = ["internshala", "naukri", "linkedin"]

# TARGET_LOCATIONS = ["Mumbai", "Pune", "Bangalore", "Bengaluru", "Remote"]
TARGET_LOCATIONS = [
    "Pune",
    "Pimpri",       # Pimpri-Chinchwad — separate city code on Naukri
    "Remote",
    "Work from home",   # how Internshala lists WFH
    "Hybrid"
]
# TARGET_LOCATIONS = []
# Bengaluru = how Naukri spells it, Bangalore = how LinkedIn spells it
# Remote included so you don't miss WFH roles
# empty = no filter, all locations

# BRAVE_PATH = "/snap/bin/brave"
import os
BRAVE_PATH = os.getenv("CHROME_PATH", "/usr/bin/chromium")

MAX_JOBS_PER_SEARCH = 50

# Output paths
DATA_DIR = os.getenv("JH_SESSION_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)
CSV_OUTPUT = os.path.join(DATA_DIR, "JobHarvestor.csv")
XLSX_OUTPUT = os.path.join(DATA_DIR, "JobHarvestor.xlsx")
COOKIES_FILE = os.path.join(DATA_DIR, "linkedin_cookies.pkl")
STOP_FLAG   = os.path.join(DATA_DIR, "scraping_stop.flag")

# Delays — do NOT lower these
MIN_DELAY = 4
MAX_DELAY = 8

JD_MIN_DELAY = 3
JD_MAX_DELAY = 6
# Save progress every N jobs (resume if crash)
CHECKPOINT_EVERY = 25

# Naukri API
# Companies to exclude from results (case-insensitive substring match).
# Override at runtime via Streamlit sidebar → saved to scrape_config_override.json
BANNED_COMPANIES: list[str] = []

NAUKRI_API = "https://www.naukri.com/jobapi/v3/search"
NAUKRI_BASE = "https://www.naukri.com"