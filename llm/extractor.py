import json
import time
import itertools
import requests
from ratelimit import limits, sleep_and_retry
from config import GROQ_API_KEY, GROQ_MODEL

# Load second key if available (doubles throughput)
try:
    from config import GROQ_API_KEY_2
    _KEYS = [k for k in [GROQ_API_KEY, GROQ_API_KEY_2] if k]
except ImportError:
    _KEYS = [GROQ_API_KEY]

_key_cycle = itertools.cycle(_KEYS)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

SYSTEM_PROMPT = """You are a job description parser. Extract structured information from job descriptions.
Always respond with ONLY valid JSON, no explanation, no markdown, no backticks.
If a field is not found, use null for salary/experience and empty array [] for skills."""

EXTRACTION_PROMPT = """Extract from this job description:
1. required_skills: list of must-have technical skills
2. nice_to_have: list of optional/preferred skills
3. experience_required: years of experience as string. Look for patterns like 'X years', 'X+ years', 'X to Y years', 'fresher', 'entry level'. Return null ONLY if truly not mentioned anywhere.
4. salary: salary/CTC mentioned as string (e.g. "15-25 LPA", null if not mentioned)

Respond ONLY with this JSON structure:
{
  "required_skills": ["skill1", "skill2"],
  "nice_to_have": ["skill3"],
  "experience_required": "2-4 years",
  "salary": "15-25 LPA"
}

Job Description:
"""

@sleep_and_retry
@limits(calls=15, period=60)  # conservative: 15/min per key avoids 429 bursts
def extract(jd_text: str, retries: int = 4) -> dict:
    empty = {
        "required_skills": [],
        "nice_to_have": [],
        "experience_required": None,
        "salary": None
    }

    if not jd_text or len(jd_text.strip()) < 50:
        return empty

    jd_trimmed = jd_text[:3000]
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": EXTRACTION_PROMPT + jd_trimmed}
        ],
        "max_tokens": 500,
        "temperature": 0
    }

    for attempt in range(retries):
        api_key = next(_key_cycle)  # rotate keys each attempt
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(GROQ_URL, headers=headers,
                                     json=payload, timeout=30)

            if response.status_code == 429:
                # Respect Retry-After if provided, else exponential backoff
                retry_after = int(response.headers.get("Retry-After", 0))
                wait = retry_after if retry_after > 0 else (2 ** attempt) * 5
                print(f"      [Groq] 429 — waiting {wait}s (attempt {attempt+1}/{retries})")
                time.sleep(wait)
                continue  # retry with next key

            if response.status_code != 200:
                print(f"      [Groq] Status {response.status_code}")
                return empty

            content = response.json()["choices"][0]["message"]["content"]
            content = content.strip().strip("```json").strip("```").strip()
            parsed = json.loads(content)
            return {
                "required_skills": parsed.get("required_skills", []),
                "nice_to_have": parsed.get("nice_to_have", []),
                "experience_required": parsed.get("experience_required"),
                "salary": parsed.get("salary")
            }

        except json.JSONDecodeError:
            print(f"      [Groq] JSON parse failed attempt {attempt + 1}")
            time.sleep(2)
        except Exception as e:
            print(f"      [Groq] Error: {e}")
            time.sleep(2)

    return empty