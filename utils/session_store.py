# utils/session_store.py
# Persists user preferences to disk so they survive page refreshes

import json
import os

SESSION_FILE = os.path.join(os.getenv("JH_SESSION_DIR","data"), "user_session.json")


def load_session() -> dict:
    """Load saved session. Returns empty dict if none exists."""
    os.makedirs("data", exist_ok=True)
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_session(data: dict):
    """Save session data to disk."""
    os.makedirs("data", exist_ok=True)
    existing = load_session()
    existing.update(data)
    with open(SESSION_FILE, "w") as f:
        json.dump(existing, f, indent=2)


def get(key: str, default=None):
    return load_session().get(key, default)


def set(key: str, value):
    save_session({key: value})